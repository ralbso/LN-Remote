import logging

from gui import MainWindow
from devices import LNSM10

import time
from PySide6.QtCore import (QMutex, QObject, QThread, QWaitCondition, Signal,
                            Slot)
from PySide6.QtWidgets import QApplication

# create logger
logger = logging.getLogger(__name__)


class Interface:
    """The `Interface` class serves as the messenger between the GUI and
    the device. Through it, we start the `QApplication` and initialize a
    worker thread (`AcquisitionWorker`) that continuously updates the
    manipulator's current position.
    """
    def __init__(self):
        self.gui = QApplication([])

        self.manipulator = LNSM10()
        self.manipulator.checkDevice()

        self.main_window = MainWindow(interface=self)

        self.worker_wait_condition = QWaitCondition()
        self.acquisition_worker = AcquisitionWorker(
            self.worker_wait_condition,
            manipulator=self.manipulator)
        self.acquisition_thread = QThread()

        self.acquisition_worker.moveToThread(self.acquisition_thread)
        self.acquisition_thread.started.connect(self.acquisition_worker.run)
        self.acquisition_worker.finished.connect(self.acquisition_thread.quit)
        self.acquisition_worker.data_ready.connect(self.dataReadyCallback)
        self.acquisition_thread.start()

        self.gui.aboutToQuit.connect(self.onExit)

    def runGui(self):
        self.main_window.show()
        self.getCurrentPosition()
        return self.gui.exec_()

    def getCurrentPosition(self):
        self.worker_wait_condition.wakeOne()

    def dataReadyCallback(self):
        try:
            self.main_window.position_panel.updatePositionBoxes(
                self.acquisition_worker.data)
        except Exception as e:
            logger.error(f'Hit a snag: {e}')
            logger.error(f'Last read data: {self.acquisition_worker.data}')
        finally:
            self.worker_wait_condition.wakeOne()

    def onExit(self):
        self.acquisition_worker.stop()
        self.acquisition_thread.terminate()
        self.main_window.cells_panel.saveTableData()
        logger.info('Closing GUI...')


class AcquisitionWorker(QObject):
    """The `AcquisitionWorker` class serves as a worker thread for the
    `Interface` class. This is where the magic happens: it continuously
    reads the manipulator's current position and emits a signal when
    new data is available.
    """

    finished = Signal()
    data_ready = Signal()

    def __init__(self, wait_condition, manipulator):
        super().__init__()
        self.wait_condition = wait_condition
        self.manipulator = manipulator
        self.mutex = QMutex()

        self.keep_running = True

    def __del__(self):
        # adding method somehow reduces the chances of a crash
        logger.info('AcquisitionWorker deleted')

    @Slot()
    def run(self):
        while self.keep_running:
            self.mutex.lock()
            self.wait_condition.wait(self.mutex, 1500)  # 1.5 second timeout
            self.mutex.unlock()

            if not self.keep_running:
                break

            try:
                time.sleep(0.1)  # read every 100 ms
                self.data = self.manipulator.readManipulator()
                self.data_ready.emit()
            except Exception as e:
                logger.error(f'Error in AcquisitionWorker: {e}')

                # still emit a signal with None to keep loop going
                # if there's an error, position data will just not update
                self.data = [None, None, None, None]
                self.data_ready.emit()

        self.finished.emit()

    def stop(self):
        logger.info('Stopping AcquisitionWorker...')
        self.keep_running = False
