""""""
"""
File: d:/GitHub/raul-exps/manipulator.py

Created on: 10/14/2022 14:56:24
Author: rmojica
"""

import sys
import time
import numpy as np
import binascii
import ctypes
import struct
import warnings
import threading

import serial
import serial.tools.list_ports


class LuigsAndNeumannSM10:
    """Represent Luigs and Neumann SM10 manipulator.\n
    To issue commands, the following general structure must be followed:
    `<SYN><CommandID><nFollowingBytes><Args><CRCMSB><CRCLSB>`
    """
    # set speed limit when pipette is inside the brain
    INSIDE_BRAIN_SPEED_LIMIT = 10  # um/s

    SYN = '16'      # SYN character

    # Define group addresses to control groups of axes on unit 1
    # TODO: allow user to select units and axes and decode the group address
    GROUPADDRESSXYZ = [0,0,0,0,0,0,0,0,7]
    GROUPADDRESSYZ = [0,0,0,0,0,0,0,0,6]
    GROUPADDRESSXZ = [0,0,0,0,0,0,0,0,5]
    GROUPADDRESSXY = [0,0,0,0,0,0,0,0,3]

    full_command = ''

    def __init__(self):
        super().__init__()
        self._calibrated = False
        self._inside_brain = False
        self._can_write_cmd = True
        self._reset_timer = 0.1
        self._verbose = True

        # establish serial connection
        serial_number = 'AQ01JPC8A'
        self.device = self.findManipulator(serial_number)
        self.manipulator = self.establishSerialConnection(self.device, self._reset_timer)

    def __del__(self):
        try:
            self.manipulator.close()
        except AttributeError:
            pass
        if self._verbose:
            print('Connection to SM10 closed.')

    @staticmethod
    def findManipulator(serial_number):
        comports = serial.tools.list_ports.comports()
        try:
            for comport in comports:
                # make sure the comport is real
                ser = comport.serial_number
                device = str(comport.device)

                if ser == serial_number:
                    return device
        except Exception:
            raise IOError('Could not find manipulator... Is it connected?')

    def establishSerialConnection(self, device, timeout):
        if self._verbose:
            print('Connecting...')
        ser = serial.Serial(device, baudrate=115200, bytesize=serial.EIGHTBITS, parity=serial.PARITY_NONE, stopbits=serial.STOPBITS_ONE, timeout=timeout)
        if self._verbose:
            print(f'Connected to SM10 on {device}.')
        return ser

        # SEND COMMANDS
    def sendCommand(self, cmd_id, data_n_bytes, data, resp, resp_n_bytes=0):
        self._just_wrote = False

        # calculate CRC for command parameters
        (MSB, LSB) = self.calculateCRC(data, len(data))

        if data_n_bytes != len(data):
            raise IndexError('The number of bytes sent does not match the data array.')

        # compile full command string
        command = self.SYN + cmd_id + '%0.2X' % data_n_bytes
        for i in range(len(data)):
            command += '%0.2X' % data[i]
        command += '%0.2X%0.2X' % (MSB, LSB)

        # convert command to bytes for COM interface
        self.bytes_command = binascii.unhexlify(command)

        if self._verbose:
            print(cmd_id, command, MSB, LSB)

        ##### experimental. How can we split writing streams appropriately?

        # Solution #2: Thread locks
        
        with threading.Lock():
            self.manipulator.write(self.bytes_command)

        # Solution #1: Hardcode access with boolean logic
        ## Didn't work as well as I thought. Commands get tangled.

        # print('Can command?', self._can_write_cmd)
        # if self._can_write_cmd and cmd_id == 'A101':
        #     self._can_write_cmd = False
        #     self.manipulator.write(self.bytes_command)
        #     self._just_wrote = True

        #     if self._verbose:
        #         print('Position inquiry sent')
                
        # if self._can_write_cmd and cmd_id != 'A101':
        #     self.manipulator.write(self.bytes_command)
        #     self._just_wrote = True

        #     if self._verbose:
        #         print('Command sent')

        # time.sleep(1)
        # n_loops = 0
        # if self._just_wrote:
        #     while True:
        #         ans = self.manipulator.read(resp_n_bytes)

        #         if resp == None:
        #             if self._verbose:
        #                 print('Group command. No response expected.')
        #             break

        #         elif ans[:len(resp)] == resp:
        #             if self._verbose and n_loops > 0:
        #                 print('Response read')
        #             break

        #         elif n_loops >= 5:
        #             warnings.warn('Command failed')
        #             break

        #         if self._verbose and n_loops > 0:
        #             print('Unexpected answer: ', ans, len(ans))  

        #         n_loops += 1

        #     self._just_wrote = False

            return ans

    # COMMANDS
    def stepXIn(self, steps):
        # cmd_id = '0147'
        # nbytes = '2'
        # unit = '1'
        # steps = abs(steps)
        # self.sendCommand(cmd_id, nbytes, unit, steps)
        
        print('Step X In')
        cmd_id = '0140'
        nbytes = '1'
        unit = '1'
        self.sendCommand(cmd_id, nbytes, unit)

    def setStepResolution(self, resolution):
        cmd_id = '0146'
        nbytes = '2'
        unit = '1'
        self.sendCommand(cmd_id, nbytes, unit, resolution)

    def stepXOut(self, steps):
        # cmd_id = '0147'
        # nbytes = '2'
        # unit = '1'
        # steps = -steps
        # self.sendCommand(cmd_id, nbytes, unit, steps)

        print('Step X Out')
        cmd_id = '0141'
        nbytes = '1'
        unit = '1'
        self.sendCommand(cmd_id, nbytes, unit)

    def setStepDistance(self, increment):
        cmd_id = '044F'
        nbytes = '5'
        unit = '1'
        data = f'{unit}{increment}'
        self.sendCommand(cmd_id, nbytes, data)

    def setStepSpeed(self, speed):
        cmd_id = '0158'
        nbytes = '2'
        unit = '1'
        data = f'{unit}{speed}'
        self.sendCommand(cmd_id, nbytes, data)

    def moveXIn(self):
        # <16><0014><0101><AsAAA>
        cmd_id = '0015'
        nbytes = 1
        axis = 1
        data = ([axis])
        response = b'\x06\x00\x15\x00\xbb\xbb'
        resp_n_bytes = len(response)
        self.sendCommand(cmd_id, nbytes, data, response, resp_n_bytes)

    def moveXOut(self):
        cmd_id = '0014'
        nbytes = 1
        axis = 1
        data = ([axis])
        response = b'\x06\x00\x14\x00\xbb\xbb'
        resp_n_bytes = len(response)
        self.sendCommand(cmd_id, nbytes, data, response, resp_n_bytes)

    def fastApproachAbsolutePosition(self, position):
        cmd_id = '0048'
        nbytes = '5'
        unit = '1'
        data = f'{unit}{position}'
        self.sendCommand(cmd_id, nbytes, data)

    def slowApproachAbsolutePosition(self, position):
        cmd_id = '0049'
        nbytes = '5'
        unit = '1'
        data = f'{unit}{position}'
        self.sendCommand(cmd_id, nbytes, data)

    def fastApproachRelativePosition(self, position):
        cmd_id = '004A'
        nbytes = '5'
        unit = '1'
        data = f'{unit}{position}'
        self.sendCommand(cmd_id, nbytes, data)

    def slowApproachRelativePosition(self, position):
        cmd_id = '004B'
        nbytes = '5'
        unit = '1'
        data = f'{unit}{position}'
        self.sendCommand(cmd_id, nbytes, data)

    def setPositioningSpeedMode(self, speed_selection=0):
        """Set speed for positioning using stored coordinates

        Parameters
        ----------
        speed_selection : int
            Select speed for positioning. Can be 0 (slow) or 1 (fast). By default, 0.
        """
        cmd_id = '0191'
        nbytes = '2'
        unit = '1'
        speed_selection = str(speed_selection)
        data = f'{unit}{speed_selection}'
        self.sendCommand(cmd_id, nbytes, data)

    def setPositioningVelocityFast(self, velocity):
        """Set velocity for Fast positioning mode.

        Parameters
        ----------
        velocity : int
            Select unit velocity for fast positioning. Can be any integer between 0 and 16. By
            default, 0.
        """
        assert (velocity > 0 and velocity < 16)
        cmd_id = '0144'
        nbytes = '2'
        unit = '1'
        velocity = str(velocity)
        data = f'{unit}{velocity}'
        self.sendCommand(cmd_id, nbytes, data)

    def setPositioningVelocitySlow(self, velocity):
        """Set velocity for Slow positioning mode.

        Parameters
        ----------
        velocity : int
            Select unit velocity for slow positioning. Can be any integer between 0 and 16. By
            default, 0.
        """
        assert (velocity > 0 and velocity < 16)
        cmd_id = '018F'
        nbytes = '2'
        unit = '1'
        velocity = str(velocity)
        data = f'{unit}{velocity}'
        self.sendCommand(cmd_id, nbytes, data)

    def setPositioningVelocityFastLinear(self, velocity):
        assert (velocity > 0 and velocity < 3000)
        cmd_id = '003D'
        nbytes = '3'
        unit = '1'
        velocity = str(velocity)
        data = f'{unit}{velocity}'
        self.sendCommand(cmd_id, nbytes, data)

    def setPositioningVelocitySlowLinear(self, velocity):
        assert (velocity > 0 and velocity < 18000)
        cmd_id = '003C'
        nbytes = '3'
        unit = '1'
        velocity = str(velocity)
        data = f'{unit}{velocity}'
        self.sendCommand(cmd_id, nbytes, data)

    def storeCurrentPosition(self, slot_number):
        assert (slot_number > 0 and slot_number <= 5)
        cmd_id = '010A'
        nbytes = '2'
        unit = '1'
        slot_number = str(slot_number)
        data = f'{unit}{slot_number}'
        self.sendCommand(cmd_id, nbytes, data)

    def goToStoredPosition(self, slot_number):
        assert (slot_number > 0 and slot_number <= 5)
        cmd_id = '0110'
        nbytes = '2'
        unit = '1'
        slot_number = str(slot_number)
        data = f'{unit}{slot_number}'
        self.sendCommand(cmd_id, nbytes, data)

    def switchAxisOff(self, unit):
        cmd_id = '0034'
        nbytes = '1'
        unit = str(unit)
        self.sendCommand(cmd_id, nbytes, unit)

    def switchAxisOn(self, unit):
        cmd_id = '0035'
        nbytes = '1'
        unit = str(unit)
        self.sendCommand(cmd_id, nbytes, unit)

    def storeHome(self):
        cmd_id = '0104'
        nbytes = '1'
        self.sendCommand(cmd_id, nbytes, '1')
        self.sendCommand(cmd_id, nbytes, '2')
        self.sendCommand(cmd_id, nbytes, '3')

    def setHomingVelocity(self, velocity):
        assert (velocity > 0 and velocity <= 15)
        cmd_id = '0139'
        nbytes = '2'
        unit = '1'
        data = f'{unit}{velocity}'
        self.sendCommand(cmd_id, nbytes, data)

        unit = '2'
        data = f'{unit}{velocity}'
        self.sendCommand(cmd_id, nbytes, data)

        unit = '3'
        data = f'{unit}{velocity}'
        self.sendCommand(cmd_id, nbytes, data)

    def setHomeDirection(self):
        """Must calibrate with control box.
        """
        cmd_id = '013C'
        nbytes = '2'
        unit = '1'
        direction = '1'
        data = f'{unit}{direction}'
        self.sendCommand(cmd_id, nbytes, data)

    def returnAxisHome(self, unit):
        assert (unit >= 1 and unit <= 3)
        cmd_id = '0022'
        nbytes = '1'
        unit = str(unit)
        self.sendCommand(cmd_id, nbytes, unit)

    def abortHome(self):
        cmd_id = '013F'
        nbytes = '1'
        unit = '1'
        self.sendCommand(cmd_id, nbytes, unit)

        unit = '2'
        self.sendCommand(cmd_id, nbytes, unit)

        unit = '3'
        self.sendCommand(cmd_id, nbytes, unit)

    def resetZeroCounterOne(self, unit):
        assert (unit >= 1 and unit <= 3)
        cmd_id = '00F0'
        nbytes = '1'
        unit = str(unit)
        self.sendCommand(cmd_id, nbytes, unit)

    def moveAxisToZero(self, unit):
        assert (unit >= 1 and unit <= 3)
        cmd_id = '0024'
        nbytes = '1'
        unit = str(unit)
        self.sendCommand(cmd_id, nbytes, unit)

    def resetZeroCounterTwo(self, unit):
        assert (unit >= 1 and unit <= 3)
        cmd_id = '0132'
        nbytes = '2'
        unit = str(unit)
        counter = '2'
        data = f'{unit}{counter}'
        self.sendCommand(cmd_id, nbytes, data)

    def stopMovement(self):
        # assert (unit >= 1 and unit <= 3)
        cmd_id = '00FF'
        nbytes = 1
        unit = 1
        arg = ([unit])
        response = b'\x06\x00\xff\x00\xbb\xbb'
        resp_n_bytes = 6
        self.sendCommand(cmd_id, nbytes, arg, response, resp_n_bytes)

    def switchSlowRampOff(self):
        cmd_id = '042F'
        nbytes = '1'
        self.sendCommand(cmd_id, nbytes, '1')
        self.sendCommand(cmd_id, nbytes, '2')
        self.sendCommand(cmd_id, nbytes, '3')

    def switchSlowRampOn(self):
        cmd_id = '0430'
        nbytes = '1'
        self.sendCommand(cmd_id, nbytes, '1')
        self.sendCommand(cmd_id, nbytes, '2')
        self.sendCommand(cmd_id, nbytes, '3')

    def setRampLength(self, length):
        assert (length > 0 and length <= 15)
        cmd_id = '003A'
        nbytes = '2'
        unit = '1'
        data = f'{unit}{length}'
        self.sendCommand(cmd_id, nbytes, data)

        unit = '2'
        data = f'{unit}{length}'
        self.sendCommand(cmd_id, nbytes, data)

        unit = '3'
        data = f'{unit}{length}'
        self.sendCommand(cmd_id, nbytes, data)

    # QUERIES
    def readPosition(self, unit):
        assert (unit >= 1 and unit <= 3)
        cmd_id = '0101'
        nbytes = 1
        data = ([unit])
        response = b'\x06\x01\x01\x04'
        resp_n_bytes = 10
        ans = self.sendCommand(cmd_id, nbytes, data, response, resp_n_bytes)
        return struct.unpack('f', ans[4:8])[0]

    def readCounterTwo(self, unit):
        assert (unit >= 1 and unit <= 3)
        cmd_id = '0131'
        nbytes = 1
        data = ([unit])
        response = b'\x06\x01\x01\x04'
        resp_n_bytes = 10
        self.sendCommand(cmd_id, nbytes, data)
        ans = self.sendCommand(cmd_id, nbytes, data, response, resp_n_bytes)
        return struct.unpack('f', ans[4:8])[0]

    def readPositioningSpeedMode(self, unit):
        assert (unit >= 1 and unit <= 3)
        cmd_id = '0192'
        nbytes = 1
        data = ([unit])
        response = b'\x06\x01\x01\x04'
        resp_n_bytes = 10
        ans = self.sendCommand(cmd_id, nbytes, data, response, resp_n_bytes)
        return struct.unpack('f', ans[4:8])[0]

    # COLLECTION/GROUP COMMANDS
    def switchXYZOff(self):
        cmd_id = 'A034'
        nbytes = 'A'
        group_flag = 'A0'
        data = ([group_flag, self.GROUPADDRESSXYZ])
        response = b'\x06\x01\x01\x04'
        resp_n_bytes = 6
        self.sendCommand(cmd_id, nbytes, data, response, resp_n_bytes)

    def switchXYZOn(self):
        cmd_id = 'A035'
        nbytes = 'A'
        group_flag = 'A0'
        data = ([group_flag, self.GROUPADDRESSXYZ])
        response = b'\x06\x01\x01\x04'
        resp_n_bytes = 6
        self.sendCommand(cmd_id, nbytes, data, response, resp_n_bytes)

    def resetZeroCounterOneXYZ(self):
        cmd_id = 'A0F0'
        nbytes = 0x0A
        group_flag = 0xA0
        data = ([group_flag] + self.GROUPADDRESSXYZ)
        response = None
        self.sendCommand(cmd_id, nbytes, data, response)

    def resetZeroCounterTwoXYZ(self):
        cmd_id = 'A132'
        nbytes = 'A'
        group_flag = 'A0'
        data = f'{group_flag}{self.GROUPADDRESSXYZ}'
        self.sendCommand(cmd_id, nbytes, data)

    def fastPositiveMovementXYZ(self, velocity):
        assert (velocity > 0 and velocity <= 15)
        cmd_id = 'A012'
        nbytes = 'B'
        group_flag = 'A0'
        velocity = str(velocity)
        data = f'{group_flag}{self.GROUPADDRESSXYZ}{velocity}'
        self.sendCommand(cmd_id, nbytes, data)

    def fastNegativeMovementXYZ(self, velocity):
        assert (velocity > 0 and velocity <= 15)
        cmd_id = 'A013'
        nbytes = 'B'
        group_flag = 'A0'
        velocity = str(velocity)
        data = f'{group_flag}{self.GROUPADDRESSXYZ}{velocity}'
        self.sendCommand(cmd_id, nbytes, data)

    def slowPositiveMovementXYZ(self, velocity):
        assert (velocity > 0 and velocity <= 15)
        cmd_id = 'A014'
        nbytes = 'B'
        group_flag = 'A0'
        velocity = str(velocity)
        data = f'{group_flag}{self.GROUPADDRESSXYZ}{velocity}'
        self.sendCommand(cmd_id, nbytes, data)

    def slowNegativeMovementXYZ(self, velocity):
        assert (velocity > 0 and velocity <= 15)
        cmd_id = 'A015'
        nbytes = 'B'
        group_flag = 'A0'
        velocity = str(velocity)
        data = f'{group_flag}{self.GROUPADDRESSXYZ}{velocity}'
        self.sendCommand(cmd_id, nbytes, data)

    def stopXYZ(self):
        cmd_id = 'A0FF'
        nbytes = 'A'
        group_flag = 'A0'
        data = f'{group_flag}{self.GROUPADDRESSXYZ}'
        self.sendCommand(cmd_id, nbytes, data)

    def moveXYZToZero(self, velocity):
        assert (velocity > 0 and velocity <= 15)
        cmd_id = 'A024'
        nbytes = 'B'
        group_flag = 'A0'
        velocity = str(velocity)
        data = f'{group_flag}{self.GROUPADDRESSXYZ}{velocity}'
        self.sendCommand(cmd_id, nbytes, data)

    def storeXYZPosition(self, slot_number):
        assert (slot_number > 0 and slot_number <= 5)
        cmd_id = 'A10A'
        nbytes = 'B'
        group_flag = 'A0'
        slot_number = str(slot_number)
        data = f'{group_flag}{self.GROUPADDRESSXYZ}{slot_number}'
        self.sendCommand(cmd_id, nbytes, data)

    def approachXYZPosition(self, slot_number, velocity):
        assert (slot_number > 0 and slot_number <= 5)
        assert (velocity > 0 and velocity <= 15)
        cmd_id = 'A110'
        nbytes = 'C'
        group_flag = 'A0'
        slot_number = str(slot_number)
        velocity = str(velocity)
        data = f'{group_flag}{self.GROUPADDRESSXYZ}{slot_number}{velocity}'
        self.sendCommand(cmd_id, nbytes, data)

    def stepXYZPositive(self, velocity, distance):
        """Step all three axes in the positive direction.

        Parameters
        ----------
        velocity : int
            How fast the motors will step
        distance : int
            How much distance each step will travel, in um
        """
        assert (velocity > 0 and velocity <= 15)
        cmd_id = 'A140'
        nbytes = '0F'
        group_flag = 'A0'
        velocity = str(velocity)
        distance = str(distance)
        data = f'{group_flag}{self.GROUPADDRESSXYZ}{velocity}{distance}'
        self.sendCommand(cmd_id, nbytes, data)

    def stepXYZNegative(self, velocity, distance):
        """Step all three axes in the negative direction.

        Parameters
        ----------
        velocity : int
            How fast the motors will step
        distance : int
            How much distance each step will travel, in um
        """
        assert (velocity > 0 and velocity <= 15)
        cmd_id = 'A141'
        nbytes = '0F'
        group_flag = 'A0'
        velocity = str(velocity)
        distance = str(distance)
        data = f'{group_flag}{self.GROUPADDRESSXYZ}{velocity}{distance}'
        self.sendCommand(cmd_id, nbytes, data)

    def storeXYZHome(self):
        cmd_id = 'A104'
        nbytes = 'B'
        group_flag = 'A0'
        data = f'{group_flag}{self.GROUPADDRESSXYZ}'
        self.sendCommand(cmd_id, nbytes, data)

    def returnXYZHome(self, velocity):
        assert (velocity > 0 and velocity <= 15)
        cmd_id = 'A022'
        nbytes = 'B'
        group_flag = 'A0'
        velocity = str(velocity)
        data = f'{group_flag}{self.GROUPADDRESSXYZ}{velocity}'
        self.sendCommand(cmd_id, nbytes, data)

    def abortXYZHome(self):
        cmd_id = 'A13F'
        nbytes = 'A'
        group_flag = 'A0'
        data = f'{group_flag}{self.GROUPADDRESSXYZ}'
        self.sendCommand(cmd_id, nbytes, data)

    # GROUP QUERIES
    def readXYZManipulator(self):
        cmd_id = 'A101'
        nbytes = 4
        group_flag = 0xA0
        unit1 = 1
        unit2 = 2
        unit3 = 3
        data = ([group_flag, unit1, unit2, unit3])
        response = b'\x06\xa1\x01\x14'
        # response: <ACK><ID1><ID2><14><UNIT1><UNIT2><UNIT3><flPOS1><flPOS2><flPOS3><CRC>
        # bytes   : <1>  <1>  <1>  <1> <1>    <1>    <1>    <4>     <4>     <4>     <total: 20>
        resp_n_bytes = 28
        ans = self.sendCommand(cmd_id, nbytes, data, response, resp_n_bytes)

        if self._verbose:
            print(ans)

        try:
            ans_decoded = [struct.unpack('f', ans[8:12])[0],
                           struct.unpack('f', ans[12:16])[0],
                           struct.unpack('f', ans[16:20])[0]]
            return ans_decoded
        except:
            pass

    def queryXYZState(self):
        cmd_id = 'A120'
        nbytes = 4
        group_flag = 0xA0
        unit1 = 1
        unit2 = 2
        unit3 = 3
        data = f'{group_flag}{unit1}{unit2}{unit3}'
        self.sendCommand(cmd_id, nbytes, data)


    # CRC Calculation
    @staticmethod
    def calculateCRC(data_bytes, length):
        crc_polynom = 0x1021
        crc = 0
        n = 0
        print('data bytes', data_bytes)
        while length > 0:
            crc = crc ^ data_bytes[n] << 8
            for i in np.arange(8):
                if (crc & 0x8000):
                    crc = crc << 1 ^ crc_polynom
                else:
                    crc = crc << 1
            
            length -= 1
            n += 1

        crcMSB = ctypes.c_ubyte(crc >> 8)
        crcLSB = ctypes.c_ubyte(crc)

        return (crcMSB.value, crcLSB.value)


