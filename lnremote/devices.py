import binascii
import ctypes
import socket
import struct
import threading
import time

import logging

import serial
import serial.tools.list_ports

from lnremote.config_loader import LoadConfig

# create logger
logger = logging.getLogger(__name__)


class LNSM10:
    """Represent Luigs and Neumann SM10 manipulator.\n
    To issue commands, the following general structure must be followed:\n
    `<SYN><CommandID><nFollowingBytes><Args><CRCMSB><CRCLSB>`
    """

    # set speed limit when pipette is inside the brain
    INSIDE_BRAIN_SPEED_LIMIT = 10  # um/s

    SYN = "16"  # SYN character
    ACK = "06"  # ACK character

    CONFIG = LoadConfig().Manipulator()
    IP = CONFIG["ip"]
    PORT = int(CONFIG["port"])
    SERIAL = CONFIG["serial"]
    BAUDRATE = int(CONFIG["baudrate"])
    CONNECTION = CONFIG["connection"].lower()

    def __init__(self):
        self._inside_brain = False
        self._timeout = None
        self._homed = False
        self._socket_timeout = 1
        self._unit = 1
        self._selected_axes = [1, 2, 3]

        if LNSM10.CONNECTION == "serial":
            logger.info("Establishing serial connection...")
            self.io_lock = threading.Lock()
            self.port = self.findManipulator(LNSM10.SERIAL)
            self.ser = self.establishSerialConnection(self.port,
                                                      LNSM10.BAUDRATE,
                                                      self._timeout)

    def __del__(self):
        try:
            self.ser.close()
        except AttributeError:
            pass
        finally:
            logger.info("Connection to SM10 closed.")

    def __repr__(self):
        return "Luigs and Neumann SM10 manipulator"

    def checkDevice(self):
        # check ethernet connection
        if LNSM10.CONNECTION == "socket":
            logger.info("Testing ethernet connection...")
            s = socket.socket()
            # s.settimeout(self._socket_timeout)
            try:
                s.connect((LNSM10.IP, LNSM10.PORT))
            except Exception as e:
                logger.error(
                    f"Could not establish connection to IP {LNSM10.IP} and "
                    f"port {LNSM10.PORT}.\n{e}")
            finally:
                s.close()

        elif LNSM10.CONNECTION == "dummy":
            logger.info("Initializing dummy manipulator...")

    @staticmethod
    def clearBuffer(ser):
        ser.reset_input_buffer()
        ser.reset_output_buffer()

    @staticmethod
    def findManipulator(serial_number):
        """Find the manipulator connected to the computer with the given
        serial number.

        Parameters
        ----------
        serial_number : str
            Alphanumeric serial number of the manipulator.

        Returns
        -------
        str
            Port where the manipulator is connected.

        Raises
        ------
        IOError
            If the manipulator is not connected to the computer, an error
            is raised.
        """
        comports = serial.tools.list_ports.comports()
        correct_device = None
        try:
            for comport in comports:
                # make sure the comport is real
                ser = comport.serial_number
                device = str(comport.device)

                if ser == serial_number:
                    correct_device = device
                    break

            if correct_device is None:
                raise IOError("Could not find manipulator... Is it connected?")

            return correct_device

        except IOError as e:
            logger.error(str(e))

    @staticmethod
    def establishSerialConnection(port, baud, timeout):
        """Establish serial connection with the manipulator.

        Parameters
        ----------
        port : str
            Port where the manipulator is connected.
        baud : int
            Baud rate of serial connection.
        timeout : float
            Time to wait for a response from the manipulator.

        Returns
        -------
        serial.Serial
            Serial object to communicate with the manipulator.
        """
        ser = serial.Serial(port,
                            baudrate=baud,
                            timeout=timeout,
                            write_timeout=2)

        logger.info(f"Connected to SM10 on {port}.")

        return ser

    def setUnit(self, unit):
        """Set the unit of the manipulator.

        Parameters
        ----------
        unit : int
            Unit of the manipulator. Can be 1 or 2.
        """
        assert unit == 1 or unit == 2
        self._unit = unit

    # SEND COMMANDS
    def sendCommand(self, cmd_id, data_n_bytes, data, resp_nbytes=0):
        """The heart of the communication protocol.
        This method sends a command to the manipulator, waits for a response
        and returns it raw. The initiator of `sendCommand` is responsible for
        interpreting the response.

        Parameters
        ----------
        cmd_id : str
            Command identifier, as defined in the LN SM10 serial protocol
            manual.
        data_n_bytes : int
            Number of bytes to be sent.
        data : list
            Arguments to be sent with the command.
        resp_nbytes : int, optional
            Expected response size, in bytes, by default 0

        Returns
        -------
        str
            Raw response from the manipulator, to be decoded downstream.

        Raises
        ------
        IndexError
            Raised if the number of bytes sent does not match the data array.
        serial.SerialException
            Raised if, after attempting to read the manipulator's response
            buffer five times, the response is not read comletely.
        """

        # calculate CRC for command parameters
        (MSB, LSB) = self.crc16(data)

        logger.debug(f"{data_n_bytes} {len(data)} {data}")

        try:
            if data_n_bytes != len(data):
                raise IndexError(
                    "The number of bytes sent does not match the data array.")
        except IndexError as e:
            logger.error(str(e))
            raise

        # compile full command string
        command = LNSM10.SYN + cmd_id + "%0.2X" % data_n_bytes
        for i in range(len(data)):
            command += "%0.2X" % data[i]
        command += "%0.2X%0.2X" % (MSB, LSB)

        # convert command to bytes
        bytes_command = binascii.unhexlify(command)

        logger.debug(f"Cmd: {cmd_id} {command}")
        logger.debug(f"Raw cmd: {bytes_command}")

        ans = None  # assign ans to None to avoid UnboundLocalError
        if LNSM10.CONNECTION == "serial":
            logger.debug("Sending command over serial...")
            with self.io_lock:
                if resp_nbytes == 0:
                    logger.debug("No response expected")

                    self.ser.write(bytes_command)

                    logger.debug("Cmd sent")
                    self.clearBuffer()

                    ans = None

                else:
                    self.ser.write(bytes_command)

                    logger.debug("Cmd sent")

                    time.sleep(0.01)

                    ans = self.ser.read(size=resp_nbytes)

                    logger.debug(f"Dev. resp: {ans}")

                    read_attempts = 0
                    while len(ans) < resp_nbytes:
                        if read_attempts >= 5:
                            self.ser.write(bytes_command)
                            ans = self.ser.read(resp_nbytes)

                            try:
                                if not len(ans) == resp_nbytes:
                                    msg = "Could not get a response from "
                                    f"manipulator for command {cmd_id}"
                                    raise serial.SerialException(msg)
                                else:
                                    break
                            except serial.SerialException as e:
                                logger.error(str(e))
                                raise

                        msg = f"Only received {len(ans)}/{resp_nbytes} bytes. "
                        "Attempting to read again."
                        logger.debug(msg)

                        ans += self.ser.read(resp_nbytes - len(ans))
                        read_attempts += 1

                self.clearBuffer(self.ser)  # clear serial buffer
                self.checkResponse(
                    cmd_id, ans)  # check manipulator response for errors

        elif LNSM10.CONNECTION == "socket":
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                address = (LNSM10.IP, LNSM10.PORT)
                while True:
                    try:
                        s.connect(address)
                    except (TimeoutError, socket.error) as e:
                        # if we can't communicate with the manipulator,
                        # wait 250ms before attempting to connect again
                        logger.error(f"Couldn't connect to manipulator - {e}.")
                        time.sleep(0.25)
                        logger.info("Retrying...")
                    else:
                        break

                s.sendall(bytes_command)
                if resp_nbytes == 0:
                    ans = None
                else:
                    while True:
                        try:
                            ans = s.recv(resp_nbytes)
                        except Exception as e:
                            logger.error(
                                f"Got hung-up reading manipulator: {e}")
                        else:
                            break

        elif LNSM10.CONNECTION == "dummy":
            ans = None
            logger.debug(command)

        logger.debug(f"Raw response: {ans}")

        return ans

    # COMMANDS
    def stepAxis(self, axis, steps, resolution):
        """Set step resolution and perform a number of steps in the
        signed direction.

        Parameters
        ----------
        axis : int
            Axis selection
        steps : int
            Number of steps to travel
        resolution : int
            Single step resolution
        """
        assert steps > -127 and steps < 127

        self.setStepResolution(axis, resolution)
        time.sleep(0.01)
        mapped_steps = steps + 127
        cmd_id = "0147"
        nbytes = 1
        data = [axis, mapped_steps]
        resp_nbytes = 4

        logger.debug(
            f"Stepping axis {axis} by {steps} steps at {resolution} um/step")
        self.sendCommand(cmd_id, nbytes, data, resp_nbytes)

    def setStepResolution(self, axis, resolution):
        """Set resolution of a single step.

        Parameters
        ----------
        axis : int
            Axis selection
        resolution : int
            Single step resolution
        """
        assert resolution > 0 and resolution < 255
        cmd_id = "0146"
        nbytes = 1
        data = [axis, resolution]
        resp_nbytes = 4

        logger.debug(
            f"Setting step resolution of axis {axis} to {resolution} um/step")
        self.sendCommand(cmd_id, nbytes, data, resp_nbytes)

    def singleStep(self, axis, direction, increment=None, velocity=None):
        """Move desired `axis` by a single step in the chosen `direction`.

        Parameters
        ----------
        axis : int
            Axis selection
        direction : int
            Desired direction to move the manipulator. Can be 1 or -1.
        increment : float
            Distance to travel in each step, in um.
        velocity : int
            Speed of the step.
        """
        assert direction == 1 or direction == -1
        if direction == 1:
            cmd_id = "0140"  # step increment
        elif direction == -1:
            cmd_id = "0141"  # step decrement

        if (increment is not None) and (velocity is not None):
            increment = self.convertToFloatBytes(increment)
            self.setStepDistance(axis, increment)
            time.sleep(0.01)
            self.setStepVelocity(axis, velocity)
            time.sleep(0.01)

        nbytes = 1
        data = [axis]
        resp_nbytes = 4

        logger.debug(f"Stepping axis {axis} in direction {direction}")
        self.sendCommand(cmd_id, nbytes, data, resp_nbytes)

    def setStepDistance(self, axis, increment):
        """Set distance traveled in a single step increment/decrement, in um.

        Parameters
        ----------
        axis : int
            Axis selection
        increment : float
            Step increment, in um.
        """
        cmd_id = "044F"
        nbytes = 5
        data = [axis] + list(increment)
        resp_nbytes = 0

        logger.debug(f"Setting step distance of axis {axis} to {increment} um")
        self.sendCommand(cmd_id, nbytes, data, resp_nbytes)

    def setStepVelocity(self, axis, velocity):
        """Set velocity at which a single step is performed.

        Parameters
        ----------
        axis : int
            Axis selection
        velocity : int
            Velocity of the step.
        """
        assert velocity > 0 and velocity < 16
        cmd_id = "0158"
        nbytes = 2
        data = [axis, velocity]
        resp_nbytes = 0

        logger.debug(
            f"Setting step velocity of axis {axis} to {velocity} A.U.")
        self.sendCommand(cmd_id, nbytes, data, resp_nbytes)

    def moveAxis(self, axis, speed_mode, direction, velocity=None):
        """Continuously move axis in the desired direction
        (positive or negative). Command remains active until a stop command is
        sent or a limit switch is reached in the selected axis.

        Parameters
        ----------
        axis : int
            Axis selection
        speed_mode : str
            Desired speed mode for movement, fast (1) or slow (0)
        direction : int
            Direction of movement, positive (1) or negative (-1).
        velocity : int
            Velocity stage for desired speed mode. Must be greater than 0 and
            smaller than 15.
        """
        if speed_mode == 1:
            if direction == 1:
                cmd_id = "0012"
            elif direction == -1:
                cmd_id = "0013"
        if speed_mode == 0:
            if direction == 1:
                cmd_id = "0014"
            elif direction == -1:
                cmd_id = "0015"

        if velocity is not None:
            self.setMovementVelocity(axis, speed_mode, velocity)
            time.sleep(0.1)

        nbytes = 1
        data = [axis]
        response_n_bytes = 4

        logger.debug(
            f"Moving axis {axis} in direction {direction} at speed mode "
            f"{speed_mode} and velocity {velocity} A.U.")
        self.sendCommand(cmd_id, nbytes, data, response_n_bytes)

    def setMovementVelocity(self, axis, speed_mode, velocity):
        """Set movement velocity for selected speed mode.

        Parameters
        ----------
        axis : int
            Axis selection
        speed_mode : str
            Movement speed mode, fast (1) or slow (0)
        velocity : int
            Velocity stage for the chosen speed mode.
        """
        assert velocity > 0 and velocity < 16
        if speed_mode == 1:
            cmd_id = "0134"
        elif speed_mode == 0:
            cmd_id = "0135"

        nbytes = 2
        data = [axis, velocity]
        resp_nbytes = 4

        logger.debug(f"Setting movement velocity of axis {axis} to speed mode "
                     f"{speed_mode} and {velocity} A.U.")
        self.sendCommand(cmd_id, nbytes, data, resp_nbytes)

    def approachPosition(self, axis, approach_mode, position, speed_mode):
        """Approach the input position. Approach can be relative or absolute,
        and fast or slow.

        Parameters
        ----------
        axis : int
            Axis selection
        approach_mode : str
            Approach approach_mode. If `0` (absolute), input coordinates will
            be obeyed verbatim. If `1` (relative), movement will be relative
            to the current position; if the axis is currently at -100um and
            the input `position` is +500um, the final absolute position
            will be +400um.
        position : float
            Goal position, in um.
        speed_mode : int
            Movement speed mode, fast (1) or slow (0)
        """
        assert isinstance(approach_mode, int)
        assert isinstance(speed_mode, int)
        assert approach_mode == 0 or approach_mode == 1
        assert speed_mode == 0 or speed_mode == 1
        if approach_mode == 0:
            if speed_mode == 1:
                cmd_id = "0048"
            elif speed_mode == 0:
                cmd_id = "0049"
        if approach_mode == 1:
            if speed_mode == 1:
                cmd_id = "004A"
            elif speed_mode == 0:
                cmd_id = "004B"

        nbytes = 5
        data = [axis] + list(self.convertToFloatBytes(position))
        resp_nbytes = 4

        if approach_mode == 0:
            logger.debug(
                f"Approaching axis {axis} to absolute position {position} um "
                f"in speed mode {speed_mode}")
        elif approach_mode == 1:
            logger.debug(
                f"Approaching axis {axis} to relative position {position} um "
                f"in speed mode {speed_mode}")

        self.sendCommand(cmd_id, nbytes, data, resp_nbytes)

    def setPositioningSpeedMode(self, axis, speed_mode=0):
        """Set speed mode for positioning using stored coordinates

        Parameters
        ----------
        speed_mode : int
            Select speed mode for positioning. Can be 0 (slow) or 1 (fast).
            By default, 0.
        """
        cmd_id = "0191"
        nbytes = 2
        data = axis + [speed_mode]
        resp_nbytes = 4

        logger.debug(
            f"Setting positioning speed mode for axis {axis} to {speed_mode}")
        self.sendCommand(cmd_id, nbytes, data, resp_nbytes)

    def setPositioningVelocity(self, axis, speed_mode, velocity):
        """Set positioning velocity to any of 16 stages

        Parameters
        ----------
        axis : int
            Axis selection
        speed_mode : int
            Movement speed mode, fast (1) or slow(0)
        velocity : int
            Velocity of the movement
        """

        assert isinstance(velocity, int)
        assert velocity > 0 and velocity < 16
        if speed_mode == 1:
            cmd_id = "0144"
        elif speed_mode == 0:
            cmd_id = "018F"

        nbytes = 2
        data = axis + [velocity]
        resp_nbytes = 4

        logger.debug(
            f"Setting positioning velocity for axis {axis} to speed mode "
            f"{speed_mode} with velocity {velocity} A.U.")
        self.sendCommand(cmd_id, nbytes, data, resp_nbytes)

    def setPositioningVelocityLinear(self, axis, speed_mode, velocity):
        """Set positioning velocity in steps per second (`speed_mode = 1`)
        and micro-steps per second (`speed_mode = 0`).

        Parameters
        ----------
        axis : int
            Axis selection
        speed_mode : int
            Movement speed mode, fast (1) or slow (0)
        velocity : int
            Velocity of the movement
        """
        assert isinstance(velocity, int)
        if speed_mode == 1:
            assert velocity > 0 and velocity < 3000
            cmd_id = "003D"
        elif speed_mode == 0:
            assert velocity > 0 and velocity < 18000
            cmd_id = "003C"

        velocity = velocity.to_bytes(2, "big")
        velocity = [velocity[i:i + 1] for i in range(len(velocity))]

        nbytes = 3
        data = [axis] + velocity
        resp_nbytes = 4

        if speed_mode == 0:
            logger.debug(
                f"Setting linear positioning velocity for axis {axis} to "
                f"speed mode {speed_mode} with velocity {velocity} "
                f"micro-steps per second")
        elif speed_mode == 1:
            logger.debug(
                f"Setting linear positioning velocity for axis {axis} to "
                f"speed mode {speed_mode} with velocity {velocity} steps "
                "per second")

        self.sendCommand(cmd_id, nbytes, data, resp_nbytes)

    def storePosition(self, axis, slot_number):
        """Store axis's current position in `slot_number`. There are 5 slots
        in total.
        NOT YET TESTED.

        Parameters
        ----------
        axis : int
            Axis selection
        slot_number : int
            Slot into which the current position of the axis will be stored.
        """
        assert slot_number > 0 and slot_number <= 5
        cmd_id = "010A"
        nbytes = 2
        data = [axis, slot_number]
        resp_nbytes = 4

        logger.debug(f"Storing axis {axis} position in slot {slot_number}")
        self.sendCommand(cmd_id, nbytes, data, resp_nbytes)

    def goToStoredPosition(self, axis, slot_number):
        """Go to the stored position for `axis` in `slot_number`. There are
        5 slots in total.
        NOT YET TESTED.

        Parameters
        ----------
        axis : int
            Axis selection
        slot_number : int
            Slot into which the current position of the axis will be stored.
        """
        assert slot_number > 0 and slot_number <= 5
        cmd_id = "0110"
        nbytes = 2
        data = [axis, slot_number]
        resp_nbytes = 4

        logger.debug(
            f"Going to axis {axis} stored position in slot {slot_number}")
        self.sendCommand(cmd_id, nbytes, data, resp_nbytes)

    def switchAxisPower(self, axis, power):
        """Switch axis on or off.
        NOT YET TESTED.

        Parameters
        ----------
        axis : int
            Axis selection
        power : int
            Switch power on (1) or off (0).
        """
        if power == 0:
            cmd_id = "0034"
        elif power == 1:
            cmd_id = "0035"
        nbytes = 1

        data = [axis]
        resp_nbytes = 4

        logger.debug(f"Switching axis {axis} power to {power}")
        self.sendCommand(cmd_id, nbytes, data, resp_nbytes)

    def moveHome(self, axis, velocity=None, direction=None):
        """Stores current position of `axis` and moves at `velocity` towards
        `direction` until the limit switch.
        NOT YET TESTED.

        Parameters
        ----------
        axis : int
            Axis selection
        velocity : int
            Velocity at which to retreat and approach the home position.
        direction : int
            Direction of home. NOTE: A bit unclear in the docs. Must test
            first to determine which direction is which.
        """
        if velocity is not None:
            self.setHomingVelocity(axis, velocity)
            time.sleep(0.05)
        if direction is not None:
            self.setHomeDirection(axis, direction)
            time.sleep(0.05)

        cmd_id = "0104"
        nbytes = 1
        data = [axis]
        resp_nbytes = 4

        logger.debug(
            f"Moving axis {axis} to home position at velocity {velocity} and "
            f"direction {direction}")
        self.sendCommand(cmd_id, nbytes, data, resp_nbytes)
        self.homed = True

    def setHomingVelocity(self, axis, velocity):
        """Set the velocity at which the home position will be approached.

        Parameters
        ----------
        axis : int
            Axis selection
        velocity : int
            Velocity at which to approach home.
        """
        assert velocity > 0 and velocity < 16
        cmd_id = "0139"
        nbytes = 2

        data = [axis, velocity]
        resp_nbytes = 4

        logger.debug(f"Setting homing velocity for axis {axis} to {velocity}")
        self.sendCommand(cmd_id, nbytes, data, resp_nbytes)

    def setHomeDirection(self, axis, direction):
        """Set the direction of home.

        Parameters
        ----------
        axis : int
            Axis selection
        direction : int
            Direction of home. NOTE: A bit unclear in the docs. Must test
            first to determine which direction is which.
        """
        cmd_id = "013C"
        nbytes = 2

        data = [axis, direction]
        resp_nbytes = 4

        logger.debug(f"Setting home direction for axis {axis} to {direction}")
        self.sendCommand(cmd_id, nbytes, data, resp_nbytes)

    def returnAxisHome(self, axis):
        """Return the manipulator to the position previously stored as home.

        Parameters
        ----------
        axis : int
            Axis selection
        """
        assert axis >= 1 and axis <= 3
        cmd_id = "0022"
        nbytes = 1

        data = [axis]
        resp_nbytes = 4

        if self._homed:
            logger.debug(f"Returning axis {axis} to home position")
            self.sendCommand(cmd_id, nbytes, data, resp_nbytes)
            self._homed = False  # prevent accidentally homing to arbitrary loc
        else:
            logger.warning(
                "Home command has not been executed. Could not return "
                "axis home.")

    def abortHome(self, axis):
        """Abort home function.

        Parameters
        ----------
        axis : int
            Axis selection
        """
        cmd_id = "013F"
        nbytes = 1

        data = [axis]
        resp_nbytes = 4

        logger.debug(f"Aborting home for axis {axis}")
        self.sendCommand(cmd_id, nbytes, data, resp_nbytes)

    def resetZero(self, axis):
        """Reset the main location counter to 0.

        Parameters
        ----------
        axis : int
            Axis selection
        """
        assert axis >= 1 and axis <= 3
        cmd_id = "00F0"
        nbytes = 1

        data = [axis]
        resp_nbytes = 4

        logger.debug(f"Resetting axis {axis} main counter to 0")
        self.sendCommand(cmd_id, nbytes, data, resp_nbytes)

    def resetZero2(self, axis):
        """Reset the secondary location counter to 0.

        Parameters
        ----------
        axis : int
            Axis selection
        """
        assert axis >= 1 and axis <= 3
        cmd_id = "0132"
        nbytes = 2
        counter = 2

        data = [axis, counter]
        resp_nbytes = 4

        logger.debug(f"Resetting axis {axis} secondary counter to 0")
        self.sendCommand(cmd_id, nbytes, data, resp_nbytes)

    def moveaxisToZero(self, axis):
        """Move selected axis to zero.

        Parameters
        ----------
        axis : int
            Axis selection
        """
        assert axis >= 1 and axis <= 3
        cmd_id = "0024"
        nbytes = 1

        data = [axis]
        resp_nbytes = 4

        logger.debug(f"Moving axis {axis} to 0")
        self.sendCommand(cmd_id, nbytes, data, resp_nbytes)

    def stopMovement(self, axis):
        """Stop selected axis from moving further.

        Parameters
        ----------
        axis : int
            Axis selection
        """
        assert axis >= 1 and axis <= 3
        cmd_id = "00FF"
        nbytes = 1

        data = [axis]
        resp_nbytes = 4

        logger.debug(f"Stopping axis {axis} movement")
        self.sendCommand(cmd_id, nbytes, data, resp_nbytes)

    def switchSlowRamp(self, axis, switch=1):
        """Switch the slow movement onset and offset ramp on or off.
        This affects the speed at which motion will begin.
        Probably best to keep on.

        Parameters
        ----------
        axis : int
            Axis selection
        switch : int
            Switch ramp on (1) or off (2)
        """
        if switch == 0:
            cmd_id = "042F"
        if switch == 1:
            cmd_id = "0430"

        nbytes = 1
        data = [axis]
        resp_nbytes = 4

        logger.debug(f"Switching slow ramp for axis {axis} to {switch}")
        self.sendCommand(cmd_id, nbytes, data, resp_nbytes)

    def setRampLength(self, axis, length):
        """Set the length of the acceleration and deceleration ramps,
        in 16 stages.

        Parameters
        ----------
        axis : int
            Axis selection
        length : int
            Ramp length.
        """
        assert length > 0 and length < 16
        cmd_id = "003A"

        nbytes = 2
        data = [axis]
        resp_nbytes = 4

        logger.debug(f"Setting ramp length for axis {axis} to {length}")
        self.sendCommand(cmd_id, nbytes, data, resp_nbytes)

    # QUERIES
    def readPosition(self, axis):
        """Get the current position of `axis`.

        Parameters
        ----------
        axis : int
            Axis selection

        Returns
        -------
        float
            Current position of `axis` in um
        """
        assert axis >= 1 and axis <= 3
        cmd_id = "0101"
        nbytes = 1

        data = [axis]
        resp_nbytes = 8

        logger.debug(f"Reading main position counter for axis {axis}")
        ans = self.sendCommand(cmd_id, nbytes, data, resp_nbytes)
        return struct.unpack("f", ans[4:8])[0]

    def readCounterTwo(self, axis):
        """Get the current position of `axis`.

        Parameters
        ----------
        axis : int
            Axis selection

        Returns
        -------
        float
            Current position of `axis` in um
        """
        assert axis >= 1 and axis <= 3
        cmd_id = "0131"
        nbytes = 1

        data = [axis]
        resp_nbytes = 8

        logger.debug(f"Reading secondary position counter for axis {axis}")
        ans = self.sendCommand(cmd_id, nbytes, data, resp_nbytes)
        return struct.unpack("f", ans[4:8])[0]

    def readPositioningSpeedMode(self, axis):
        """Get the speed mode set (slow or fast) for movement to a position.

        Parameters
        ----------
        axis : int
            Axis selection

        Returns
        -------
        int
            Speed mode, slow (0) or fast (1).
        """
        assert axis >= 1 and axis <= 3
        cmd_id = "0192"
        nbytes = 1
        data = [axis]
        resp_nbytes = 5

        logger.debug(f"Reading speed mode for axis {axis}")
        ans = self.sendCommand(cmd_id, nbytes, data, resp_nbytes)
        return struct.unpack("i", ans[4:6])[0]

    # TODO: Add the rest of the individual axis inquiries.

    # COLLECTION COMMANDS
    def switchAxesPower(self, axes, power):
        """Switch selected axes' power on or off.

        Parameters
        ----------
        axes : list of int
            List of axes to group for command.
        power : int
            Power on (1) or off (2).
        """
        assert isinstance(axes, list)
        if power == 0:
            cmd_id = "A034"
        elif power == 1:
            cmd_id = "A035"

        group = self.calculateGroupAddress(axes)
        nbytes = 0x0A
        group_flag = 0xA0
        data = [group_flag] + group

        logger.debug(f"Switching power for axes {axes} to {power}")
        self.sendCommand(cmd_id, nbytes, data)

    def resetAxesZero(self, axes):
        """Reset grouped axes' location counter to 0.

        Parameters
        ----------
        axes : list of int
            List of axes to group for command.
        """
        cmd_id = "A0F0"
        group = self.calculateGroupAddress(axes)

        nbytes = 0x0A
        group_flag = 0xA0
        data = [group_flag] + group

        logger.debug(f"Resetting main location counter for axes {axes} to 0")
        self.sendCommand(cmd_id, nbytes, data)

    def resetAxesZero2(self, axes):
        """Reset grouped axes' secondary location counter to 0.

        Parameters
        ----------
        axes : list of int
            List of axes to group for command.
        """
        cmd_id = "A132"
        group = self.calculateGroupAddress(axes)

        nbytes = 0x0A
        group_flag = 0xA0
        data = [group_flag] + group

        logger.debug(
            f"Resetting secondary location counter for axes {axes} to 0")
        self.sendCommand(cmd_id, nbytes, data)

    def stopAxes(self, axes):
        """Stop the selected axes from moving.

        Parameters
        ----------
        axes : list of int
            List of axes to group for command
        """
        cmd_id = "A0FF"
        group = self.calculateGroupAddress(axes)
        nbytes = 0x0A
        group_flag = 0xA0

        data = [group_flag] + group

        logger.debug(f"Stopping axes {axes}")
        self.sendCommand(cmd_id, nbytes, data)

    def moveAxesToZero(self, axes, velocity):
        """Move selected axes to zero at `velocity`.

        Parameters
        ----------
        axes : list of int
            List of axes to group for command.
        velocity : int
            Velocity at which to move axes.
        """
        assert velocity > 0 and velocity < 16

        cmd_id = "A024"
        group = self.calculateGroupAddress(axes)
        nbytes = 0x0B
        group_flag = 0xA0

        data = [group_flag] + group + [velocity]

        logger.debug(f"Moving axes {axes} to zero at velocity {velocity}")
        self.sendCommand(cmd_id, nbytes, data)

    def storeAxesPosition(self, axes, slot_number):
        """Store current position of selected axes in `slot_number`.
        There are 5 slots in total.

        Parameters
        ----------
        axes : list of int
            List of axes to group for command.
        slot_number : int
            Slot in which to save the current position of the axes.
        """
        assert slot_number > 0 and slot_number <= 5

        cmd_id = "A10A"
        group = self.calculateGroupAddress(axes)
        nbytes = 0x0B
        group_flag = 0xA0

        data = [group_flag] + group + [slot_number]

        logger.debug(f"Storing axes {axes} position in slot {slot_number}")
        self.sendCommand(cmd_id, nbytes, data)

    def approachStoredAxesPosition(self, axes, slot_number, velocity):
        """Approach position stored in `slot_number`.


        Parameters
        ----------
        axes : list of int
            List of axes to group for command.
        slot_number : int
            Slot in which to save the current position of the axes.
        velocity : int
            Velocity for movement.
        """
        assert slot_number > 0 and slot_number <= 5
        assert velocity > 0 and velocity < 16

        cmd_id = "A110"
        group = self.calculateGroupAddress(axes)
        nbytes = 0x0C
        group_flag = 0xA0

        data = [group_flag] + group + [slot_number, velocity]

        logger.debug(
            f"Approaching stored position {slot_number} for axes {axes} at "
            f"velocity {velocity}")
        self.sendCommand(cmd_id, nbytes, data)

    def stepAxes(self, axes, direction, velocity, distance):
        """Step all three axes in the desired direction.

        Parameters
        ----------
        axes : list of int
            List of axes to group for command.
        direction : int
            Direction of movement, +1 for positive (CW) and
            -1 for negative (CCW).
        velocity : int
            How fast the motors will step
        distance : int
            How much distance each step will travel, in um
        """
        assert velocity > 0 and velocity < 16

        if direction == 1:
            cmd_id = "A140"
        elif direction == -1:
            cmd_id = "A141"

        group = self.calculateGroupAddress(axes)
        nbytes = 0x0F
        group_flag = 0xA0

        data = [group_flag] + group + [velocity, distance]

        logger.debug(
            f"Stepping axes {axes} in direction {direction} at velocity "
            f"{velocity} and distance {distance}")
        self.sendCommand(cmd_id, nbytes, data)

    def moveAxesHome(self, axes, velocity, direction=None):
        """Stores current position of `axes` and moves at `velocity` towards
        `direction` until the limit switch.
        NOT YET TESTED.

        Parameters
        ----------
        axis : list of int
            List of axes to group for command
        velocity : int
            Velocity at which to retreat from the home position.
        direction : int
            Direction of home. NOTE: A bit unclear in the docs. Must test
            first to determine which direction is which.
        """
        cmd_id = "A104"
        group = self.calculateGroupAddress(axes)
        nbytes = 0x0B
        group_flag = 0xA0

        data = [group_flag] + group + [velocity]

        logger.debug(
            f"Moving axes {axes} away from home at velocity {velocity}")
        self.sendCommand(cmd_id, nbytes, data)
        self._homed = True

    def returnAxesHome(self, axes, velocity):
        """Return the manipulator to the position previously stored as home.

        Parameters
        ----------
        axes : list of int
            List of axes to group for command
        velocity : int
            Velocity at which to approach the home position.
        """
        assert velocity > 0 and velocity < 16

        cmd_id = "A022"
        group = self.calculateGroupAddress(axes)
        nbytes = 0x0B
        group_flag = 0xA0

        data = [group_flag] + group + [velocity]
        if self._homed:
            logger.debug(f"Returning axes {axes} home at velocity {velocity}")
            self.sendCommand(cmd_id, nbytes, data)
            self._homed = False  # prevent accidentally homing to arbitrary loc
        else:
            logger.warning(
                "Home command has not been executed. Could not return "
                "axis home.")

    def abortAxesHome(self, axes):
        """Abort home function.

        Parameters
        ----------
        axis : list of int
            List of axes to group for command
        """
        cmd_id = "A13F"
        group = self.calculateGroupAddress(axes)
        nbytes = 0x0A
        group_flag = 0xA0

        data = [group_flag] + group

        logger.debug(f"Aborting home for axes {axes}")
        self.sendCommand(cmd_id, nbytes, data)

    # GROUP COMMANDS
    def approachAxesPosition(self, axes, approach_mode, positions, speed_mode):
        """Approach the input positions. Approach can be relative or absolute,
        and fast or slow.

        Parameters
        ----------
        axes : list of int
            List of axes to group for command.
        approach_mode : int
            Approach approach_mode. If `0` (absolute), input coordinates will
            be obeyed verbatim. If `1` (relative), movement will be relative
            to the current position; if the axis is currently at -100um and
            the input `position` is +500um, the final absolute position
            will be +400um.
        positions : list of float
            Goal position, in um.
        speed_mode : int
            Movement speed mode, fast (1) or slow(0).
        """
        if approach_mode == 0:
            if speed_mode == 1:
                cmd_id = "A048"
            elif speed_mode == 0:
                cmd_id = "A049"
        if approach_mode == 1:
            if speed_mode == 1:
                cmd_id = "A04A"
            elif speed_mode == 0:
                cmd_id = "A04B"

        adr = [0] * 4
        adr[:len(axes)] = axes
        pos = [0] * 4
        pos[:len(pos)] = positions

        pos = self.convertToFloatBytes(pos)

        nbytes = 1 + len(adr) + len(pos)
        group_flag = 0xA0
        data = [group_flag] + adr + pos

        logger.debug(f"Approaching position {positions} for axes {axes} in "
                     f"mode {approach_mode}")
        self.sendCommand(cmd_id, nbytes, data)

    # GROUP QUERIES
    def readManipulator(self):
        cmd_id = "A101"
        axes = self._selected_axes

        adr = [0] * 4
        adr[:len(axes)] = axes

        nbytes = 5
        group_flag = 0xA0
        data = [group_flag] + adr
        resp_nbytes = 26

        logger.debug(f"Reading manipulator position for axes {axes}")
        ans = self.sendCommand(cmd_id, nbytes, data, resp_nbytes)

        try:
            ans_decoded = [
                struct.unpack("f", ans[8:12])[0],
                struct.unpack("f", ans[12:16])[0],
                struct.unpack("f", ans[16:20])[0],
                struct.unpack("f", ans[20:24])[0],
            ]
        except Exception as e:
            logger.error(str(e))
            ans_decoded = [None, None, None, None]
        finally:
            return ans_decoded

    def readManipulator2(self, axes):
        cmd_id = "A131"

        adr = [0] * 4
        adr[:len(axes)] = axes

        nbytes = 5
        group_flag = 0xA0
        data = [group_flag] + adr
        resp_nbytes = 26

        logger.debug(f"Reading position for axes {axes} on Counter 2")
        ans = self.sendCommand(cmd_id, nbytes, data, resp_nbytes)

        try:
            ans_decoded = [
                struct.unpack("f", ans[8:12])[0],
                struct.unpack("f", ans[12:16])[0],
                struct.unpack("f", ans[16:20])[0],
                struct.unpack("f", ans[20:24])[0],
            ]
        except Exception as e:
            logger.error(str(e))
            ans_decoded = [None, None, None, None]
        finally:
            return ans_decoded

    def queryAxesState(self, axes):
        """Query the state of the input axes. The command response is a list
        of 4 tuples, each containing the status of the limit switch, the
        current power, motor status, and the single step resolution.

        Limit switch:
            `0`: no limit switch active
            `1`: negative limit switch active
            `2`: positive limit switch active
        Axis power:
            `0`: axis is powered off
            `1`: axis is powered on
        Motor status:
            `0`: motor is stopped
            `1`: motor is moving
        Single step resolution:
            `0`-`255`: Set number of microsteps per single step command

        Parameters
        ----------
        axes : list of int
            Axes to query state for.

        Returns
        -------
        list of tuples
            Status of the input axes as described above. The location of each
            tuple corresponds to the input axes list (i.e. the first tuple in
            the list corresponds to the first input axis).
        """
        adr = [0] * 4
        adr[:len(axes)] = axes

        cmd_id = "A120"
        nbytes = 5
        group_flag = 0xA0

        data = [group_flag] + adr
        resp_nbytes = 26

        logger.debug(f"Querying state for axes {axes}")
        ans = self.sendCommand(cmd_id, nbytes, data, resp_nbytes)

        try:
            ans_decoded = [
                (ans[8], ans[9], ans[10], ans[11]),
                (ans[12], ans[13], ans[14], ans[15]),
                (ans[16], ans[17], ans[18], ans[19]),
                (ans[20], ans[21], ans[22], ans[23]),
            ]
        except Exception as e:
            logger.error(str(e))
            ans_decoded = [None, None, None, None]
        finally:
            return ans_decoded

    @staticmethod
    def convertToFloatBytes(arg):
        if isinstance(arg, float):
            return bytearray(struct.pack("f", arg))
        elif isinstance(arg, int):
            return bytearray(struct.pack("f", float(arg)))
        elif isinstance(arg, list):
            return [
                byte for item in arg
                for byte in bytearray(struct.pack("f", item))
            ]

    @staticmethod
    def calculateGroupAddress(axes):
        """Calculate the group address for the input axes.

        Parameters
        ----------
        axes : list
            A list of integers representing the axes.
            Must match axes numbering in the SM10.

        Returns
        -------
        list
            A list of integers representing the group address.
        """
        SBs = [1, 2, 4, 8] * 18
        ax_mask = [0] * len(SBs)
        for ax in axes:
            ax_mask[ax - 1] = 1
        binary = [SBs[i] * ax_mask[i] for i in range(len(SBs))]
        binsum = [sum(binary[i:i + 4]) for i in range(0, len(binary), 4)]
        adr = [binsum[i + 1] + binsum[i] for i in range(0, len(binsum) - 1, 2)]
        return adr[::-1]

    @staticmethod
    def checkResponse(cmd_id, ans):
        """Check if the response received is the expected one.
        If not, throw an error and log it.

        Parameters
        ----------
        cmd_id : str
            Command ID
        ans : bytes
            Response received from the SM10.
        """
        expected_response = binascii.unhexlify("06" + cmd_id)
        if ans[:len(expected_response)] == expected_response:
            logger.debug("Expected response checks out")
            pass
        else:
            e = ("Expected response to start with "
                 f"{binascii.hexlify(expected_response)}," +
                 f" but got {binascii.hexlify(ans[:len(expected_response)])} "
                 "instead.")
            logger.info(e)

    # CRC Calculation
    @staticmethod
    def crc16(data_bytes: bytes):
        """Use the given polynomial to calculate the CRC of the given data
        in bytes.

        Parameters
        ----------
        data_bytes : bytes
            Data to calculate the CRC of.

        Returns
        -------
        tuple of bytes
            MSB and LSB of the CRC.
        """
        polyn = 0x1021

        crc = 0xFFFF
        for _ in data_bytes:
            crc = (crc << 8) ^ polyn
            crc &= 0xFFFF

        crcMSB = ctypes.c_ubyte(crc >> 8)
        crcLSB = ctypes.c_ubyte(crc)

        return (crcMSB.value, crcLSB.value)
