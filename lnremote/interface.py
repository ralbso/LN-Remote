""""""
"""
File: d:/GitHub/LN-Remote/lnremote/interface.py

Created on: 01/17/2023 14:27:00
Author: rmojica
"""

from config_loader import LoadConfig
from gui import MainWindow
from manipulator import LuigsAndNeumannSM10

import time
from PySide6 import QtCore, QtGui, QtWidgets
from PySide6.QtCore import (QMutex, QObject, QRect, QRunnable, QSize, QThread,
                            QWaitCondition, Signal, Slot)
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (QApplication, QButtonGroup, QComboBox, QDialog,
                               QFileDialog, QFormLayout, QGridLayout,
                               QGroupBox, QHBoxLayout, QLabel, QLineEdit,
                               QListView, QListWidget, QMainWindow,
                               QMessageBox, QPushButton, QRadioButton,
                               QTableWidget, QTableWidgetItem, QVBoxLayout,
                               QWidget)


class Interface:

    CONFIG = LoadConfig().Manipulator()
    IP = CONFIG['ip']
    PORT = CONFIG['port']
    SERIAL = CONFIG['serial']
    DEBUG = CONFIG['debug'] == 'True'
    CONNECTION = CONFIG['connection']

    def __init__(self):
        self.gui = QApplication([])
        self.main_window = MainWindow(interface=self)

        self.manipulator = LuigsAndNeumannSM10()
        self.manipulator.initializeManipulator(connection_type=self.CONNECTION.lower())

        self.worker_wait_condition = QWaitCondition()
        self.acquisition_worker = AcquisitionWorker(self.worker_wait_condition, manipulator=self.manipulator)
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

    def connectToManipulator(self):
        self.manipulator.initializeManipulator(connection_type=self.CONNECTION)

    def getCurrentPosition(self):
        self.worker_wait_condition.wakeOne()

    def dataReadyCallback(self):
        self.main_window.position_panel.read_x.setText(f'{self.acquisition_worker.data[0]:.2f}')
        self.main_window.position_panel.read_y.setText(f'{self.acquisition_worker.data[1]:.2f}')
        self.main_window.position_panel.read_z.setText(f'{self.acquisition_worker.data[2]:.2f}')
        self.worker_wait_condition.wakeOne()

    def onExit(self):
        self.main_window.cells_panel.saveTableData()
        print('Closing GUI...')

class AcquisitionWorker(QObject):

    finished = Signal()
    data_ready = Signal()

    def __init__(self, wait_condition, manipulator):
        super().__init__()
        self.wait_condition = wait_condition
        self.manipulator = manipulator
        self.mutex = QMutex()

    @Slot()
    def run(self):
        while True:
            self.mutex.lock()
            self.wait_condition.wait(self.mutex)
            self.mutex.unlock()

            time.sleep(0.25)
            self.data = self.manipulator.readManipulator([1, 2, 3])
            self.data_ready.emit()

        self.finished.emit()
    
