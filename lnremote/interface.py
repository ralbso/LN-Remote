import logging
import argparse

from gui import MainWindow           # keep this import if you replaced gui.py with the new version
# OR, if you kept gui.py intact and are using the separate file I generated:
# from gui_lightweight import MainWindow

from devices import LNSM10

import time
from PySide6.QtCore import (QMutex, QObject, QThread, QWaitCondition, Signal, Slot)
from PySide6.QtWidgets import QApplication

logger = logging.getLogger(__name__)


def parse_args():
    parser = argparse.ArgumentParser(add_help=True)
    parser.add_argument(
        "--lightweight",
        action="store_true",
        help="Launch GUI with only Position + Controls panels"
    )
    return parser.parse_args()


class Interface:
    """Messenger between GUI and the device."""
    def __init__(self, lightweight: bool = False):
        self.gui = QApplication([])

        self.manipulator = LNSM10()
        self.manipulator.checkDevice()

        # Pass mode explicitly
        self.main_window = MainWindow(interface=self, lightweight=lightweight)

        self.worker_wait_condition = QWaitCondition()
        self.acquisition_worker = AcquisitionWorker(
            self.worker_wait_condition,
            manipulator=self.manipulator
        )
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
                self.acquisition_worker.data
            )
        except Exception as e:
            logger.error(f'Hit a snag: {e}')
            logger.error(f'Last read data: {self.acquisition_worker.data}')
        finally:
            self.worker_wait_condition.wakeOne()

    def onExit(self):
        self.acquisition_worker.stop()
        self.acquisition_thread.terminate()

        # Guard: cells_panel doesn't exist in lightweight mode
        if hasattr(self.main_window, "cells_panel") and self.main_window.cells_panel is not None:
            try:
                self.main_window.cells_panel.saveTableData()
            except Exception as e:
                logger.error(f"Failed to save table data on exit: {e}")

        logger.info('Closing GUI...')


class AcquisitionWorker(QObject):
    finished = Signal()
    data_ready = Signal()

    def __init__(self, wait_condition, manipulator):
        super().__init__()
        self.wait_condition = wait_condition
        self.manipulator = manipulator
        self.mutex = QMutex()
        self.keep_running = True

    def __del__(self):
        logger.info('AcquisitionWorker deleted')

    @Slot()
    def run(self):
        while self.keep_running:
            self.mutex.lock()
            self.wait_condition.wait(self.mutex, 1500)
            self.mutex.unlock()

            if not self.keep_running:
                break

            try:
                time.sleep(0.1)
                self.data = self.manipulator.readManipulator()
                self.data_ready.emit()
            except Exception as e:
                logger.error(f'Error in AcquisitionWorker: {e}')
                self.data = [None, None, None, None]
                self.data_ready.emit()

        self.finished.emit()

    def stop(self):
        logger.info('Stopping AcquisitionWorker...')
        self.keep_running = False


if __name__ == "__main__":
    args = parse_args()
    interface = Interface(lightweight=args.lightweight)
    raise SystemExit(interface.runGui())