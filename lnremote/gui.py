""""""
"""
File: d:/GitHub/LN-Remote/gui.py

Created on: 12/01/2022 14:17:02
Author: rmojica
"""

import sys

from PyQt5 import QtGui, QtWidgets, QtCore
from PyQt5.QtCore import QObject, QRect, QSize, QThread, pyqtSignal, pyqtSlot
from PyQt5.QtGui import QFont
from PyQt5.QtWidgets import (QApplication, QComboBox, QDialog, QFileDialog,
                             QGridLayout, QGroupBox, QLineEdit, QListView,
                             QListWidget, QMainWindow, QMessageBox,
                             QPushButton, QVBoxLayout, QHBoxLayout, QWidget, QLabel, QFormLayout)
from manipulator import LuigsAndNeumannSM10

class GUI(QMainWindow, LuigsAndNeumannSM10):

    def __init__(self):
        super().__init__()

        # set up GUI
        self.setWindowTitle("Data Visualizator 3000")
        self.setMinimumSize(QSize(400, 300))
        self.setMinimumWidth(400)
        self.setFont(QFont('Helvetica', 14))

        self.createGrid()
        # self.updatePositions()
        # self.startThread()

    def startThread(self):
        self.thread = QThread()
        self.worker = Worker(self.updatePositions)
        self.worker.moveToThread(self.thread)

        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.thread.deleteLater)
        self.worker.answer.connect(self.worker.run)
        self.thread.finished.connect(self.thread.deleteLater)

        self.thread.start()

    def createGrid(self):
        """Create grid that tiles the entire window
        """
        # create central panel that spans the whole window
        panel = QWidget(self)
        self.setCentralWidget(panel)

        # lay grid on panel
        self.grid = QGridLayout()
        panel.setLayout(self.grid)

        # create panels for GUI
        self.createPositionPanel()
        self.createControlsPanel()

    def createPositionPanel(self):
        position_panel_box = QGroupBox('Position')
        self.grid.addWidget(position_panel_box, 0, 0)

        subgrid = QGridLayout()
        position_panel_box.setLayout(subgrid)

        # subgrid = QFormLayout()
        # position_panel_box.setLayout(subgrid)

        micron_label = QLabel('um')
        micron_label.setFont(QFont('Helvetica', 14))
        micron_label.setStyleSheet('padding:5px')

        axis_label = QLabel('X')
        axis_label.setFont(QFont('Helvetica', 18, QFont.Bold))
        axis_label.setStyleSheet('padding:20px')
        subgrid.addWidget(axis_label, 0, 0)

        self.read_x = QLineEdit('')
        self.read_x.setStyleSheet('padding:20px')
        self.read_x.setToolTip('Position of X Axis')
        self.read_x.setReadOnly(True)
        self.read_x.setMaximumWidth(150)
        # subgrid.addRow(axis_label, self.read_x)
        subgrid.addWidget(self.read_x, 0, 1, alignment=QtCore.Qt.AlignLeft)
        subgrid.addWidget(micron_label, 0, 2, alignment=QtCore.Qt.AlignLeft)

        micron_label = QLabel('um')
        micron_label.setFont(QFont('Helvetica', 14))
        micron_label.setStyleSheet('padding:5px')
        
        axis_label = QLabel('Y')
        axis_label.setFont(QFont('Helvetica', 18, QFont.Bold))
        axis_label.setStyleSheet('padding:20px')
        subgrid.addWidget(axis_label, 1, 0)

        self.read_y = QLineEdit('')
        self.read_y.setStyleSheet('padding:20px')
        self.read_y.setToolTip('Position of Y Axis')
        self.read_y.setReadOnly(True)
        self.read_y.setMaximumWidth(150)
        # subgrid.addRow(axis_label, self.read_y)
        subgrid.addWidget(self.read_y, 1, 1, alignment=QtCore.Qt.AlignLeft)
        subgrid.addWidget(micron_label, 1, 2, alignment=QtCore.Qt.AlignLeft)

        micron_label = QLabel('um')
        micron_label.setFont(QFont('Helvetica', 14))
        micron_label.setStyleSheet('padding:5px')

        axis_label = QLabel('Z')
        axis_label.setFont(QFont('Helvetica', 18, QFont.Bold))
        axis_label.setStyleSheet('padding:20px')
        subgrid.addWidget(axis_label, 2, 0)

        self.read_z = QLineEdit('')
        self.read_z.setStyleSheet('padding:20px')
        self.read_z.setToolTip('Position of Z Axis')
        self.read_z.setReadOnly(True)
        self.read_z.setMaximumWidth(150)
        # subgrid.addRow(axis_label, self.read_z)
        subgrid.addWidget(self.read_z, 2, 1, alignment=QtCore.Qt.AlignLeft)
        subgrid.addWidget(micron_label, 2, 2, alignment=QtCore.Qt.AlignLeft)

    def createControlsPanel(self):
        controls_panel_box = QGroupBox('Controls')
        self.grid.addWidget(controls_panel_box, 0, 1)

        # lay boxes on panel
        subgrid = QGridLayout()
        controls_panel_box.setLayout(subgrid)

        self.zero_btn = QPushButton('Zero Axes')
        self.zero_btn.setStyleSheet('padding:20px')
        self.zero_btn.setToolTip('Zero all axes')
        subgrid.addWidget(self.zero_btn, 0, 0)

        # create buttons to move X axis in and out
        self.x_in_btn = QPushButton('X In')
        self.x_in_btn.setStyleSheet('padding:20px')
        self.x_in_btn.setToolTip('Move X axis into tissue')
        subgrid.addWidget(self.x_in_btn, 1, 0)

        self.x_out_btn = QPushButton('X Out')
        self.x_out_btn.setStyleSheet('padding:20px')
        self.x_out_btn.setToolTip('Move X axis into tissue')
        subgrid.addWidget(self.x_out_btn, 2, 0)

        self.stop_movement_x_btn = QPushButton('Stop X')
        self.stop_movement_x_btn.setStyleSheet('padding:20px')
        self.stop_movement_x_btn.setToolTip('Immediately stop movement in X axis')
        subgrid.addWidget(self.stop_movement_x_btn, 3, 0)

        self.zero_btn.clicked.connect(self.resetZeroCounterOneXYZ)
        self.x_in_btn.clicked.connect(self.moveXIn)
        self.x_out_btn.clicked.connect(self.moveXOut)
        self.stop_movement_x_btn.clicked.connect(self.stopMovement)

    def updatePositions(self):
        positions = self.readXYZManipulator()
        self.read_x.selectAll()
        self.read_y.selectAll()
        self.read_z.selectAll()
        try:
            self.read_x.insert(str(round(positions[0], 2)))
            self.read_y.insert(str(round(positions[1], 2)))
            self.read_z.insert(str(round(positions[2], 2)))
            self.positions_cache = positions
        except:
            self.read_x.insert(str(round(self.positions_cache[0], 2)))
            self.read_y.insert(str(round(self.positions_cache[1], 2)))
            self.read_z.insert(str(round(self.positions_cache[2], 2)))


class Worker(QObject):

    finished = pyqtSignal()
    answer = pyqtSignal(str)

    def __init__(self, function):
        super().__init__()
        self.function = function

    @pyqtSlot()
    def run(self):
        # print('Slot getting position in thread:', QThread.currentThread())
        ans = self.function()
        self.answer.emit(ans)
        self.finished.emit()
        

if __name__ == "__main__":
    # try:
    #     from ctypes import windll
    #     windll.shcore.SetProcessDpiAwareness(0)
    # except ImportError:
    #     pass

    app = QtWidgets.QApplication([])
    mainWin = GUI()
    mainWin.show()
    sys.exit(app.exec())
