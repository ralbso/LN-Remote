""""""
"""
File: d:/GitHub/LN-Remote/gui.py

Created on: 12/01/2022 14:17:02
Author: rmojica
"""

import sys
import time

from PySide6 import QtGui, QtWidgets, QtCore
from PySide6.QtCore import QObject, QRect, QSize, QThread, QRunnable, Signal, Slot
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (QApplication, QComboBox, QDialog, QFileDialog,
                             QGridLayout, QGroupBox, QLineEdit, QListView,
                             QListWidget, QMainWindow, QMessageBox,
                             QPushButton, QVBoxLayout, QHBoxLayout, QWidget, QLabel, QFormLayout,
                             QRadioButton, QButtonGroup)
from manipulator import LuigsAndNeumannSM10

class GUI(QMainWindow, LuigsAndNeumannSM10):

    def __init__(self, connection_type):
        super().__init__()

        # set up GUI
        self.setWindowTitle("Manipulator GUI")
        self.setMinimumSize(QSize(400, 300))
        self.setMinimumWidth(400)
        self.setFont(QFont('Helvetica', 14))
        self._verbose = False

        self.initializeManipulator(connection_type=connection_type)

        self.createGrid()
        # self.updatePositions()
        if connection_type == 'socket':
            self.startThread()

        self.approach_win = None

        # self.setPositioningSpeedMode(speed_selection=0)

    def startThread(self):
        self.thread = QThread()
        self.worker = Worker(lambda: self.updatePositions())
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
        micron_label.setStyleSheet('padding:2px')

        axis_label = QLabel('X')
        axis_label.setFont(QFont('Helvetica', 18, QFont.Bold))
        axis_label.setStyleSheet('padding:5px')
        subgrid.addWidget(axis_label, 0, 0)

        self.read_x = QLineEdit('')
        self.read_x.setStyleSheet('padding:20px')
        self.read_x.setToolTip('Position of X Axis')
        self.read_x.setFont(QFont('Helvetica', 14))
        self.read_x.setReadOnly(True)
        self.read_x.setMaximumWidth(150)
        # subgrid.addRow(axis_label, self.read_x)
        subgrid.addWidget(self.read_x, 0, 1, alignment=QtCore.Qt.AlignLeft)
        subgrid.addWidget(micron_label, 0, 2, alignment=QtCore.Qt.AlignLeft)

        micron_label = QLabel('um')
        micron_label.setFont(QFont('Helvetica', 14))
        micron_label.setStyleSheet('padding:2px')
        
        axis_label = QLabel('Y')
        axis_label.setFont(QFont('Helvetica', 18, QFont.Bold))
        axis_label.setStyleSheet('padding:5px')
        subgrid.addWidget(axis_label, 1, 0)

        self.read_y = QLineEdit('')
        self.read_y.setStyleSheet('padding:20px')
        self.read_y.setToolTip('Position of Y Axis')
        self.read_y.setFont(QFont('Helvetica', 14))
        self.read_y.setReadOnly(True)
        self.read_y.setMaximumWidth(150)
        # subgrid.addRow(axis_label, self.read_y)
        subgrid.addWidget(self.read_y, 1, 1, alignment=QtCore.Qt.AlignLeft)
        subgrid.addWidget(micron_label, 1, 2, alignment=QtCore.Qt.AlignLeft)

        micron_label = QLabel('um')
        micron_label.setFont(QFont('Helvetica', 14))
        micron_label.setStyleSheet('padding:2px')

        axis_label = QLabel('Z')
        axis_label.setFont(QFont('Helvetica', 18, QFont.Bold))
        axis_label.setStyleSheet('padding:5px')
        subgrid.addWidget(axis_label, 2, 0)

        self.read_z = QLineEdit('')
        self.read_z.setStyleSheet('padding:20px')
        self.read_z.setToolTip('Position of Z Axis')
        self.read_z.setFont(QFont('Helvetica', 14))
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

        self.goto_btn = QPushButton('GoTo')
        self.goto_btn.setStyleSheet('padding:20px')
        self.goto_btn.setToolTip('Go to absolute coordinates')
        subgrid.addWidget(self.goto_btn, 0, 1)

        self.zero_btn.clicked.connect(self.resetAxesZero)
        self.x_in_btn.clicked.connect(lambda: self.moveAxis(1, 0, -1))
        self.x_out_btn.clicked.connect(lambda: self.moveAxis(1, 0, 1))
        self.stop_movement_x_btn.clicked.connect(lambda: self.stopMovement(1))
        self.goto_btn.clicked.connect(self.approachPositionDialog)

    def updatePositions(self):
        positions = self.readManipulator([1,2,3])

        if positions != b'' and positions is not None:
            self.read_x.setText(f'{positions[0]:.2f}')
            self.read_y.setText(f'{positions[1]:.2f}')
            self.read_z.setText(f'{positions[2]:.2f}')

    def approachPositionDialog(self):
        if self.approach_win is None:
            self.approach_win = ApproachWindow()
        self.approach_win.submitGoTo.connect(self.approachAxesPosition)
        self.approach_win.submitSpeed.connect(self.setPositioningVelocity)
        self.approach_win.show()


class ApproachWindow(QWidget):
    submitGoTo = Signal(list, float, list, int)
    submitSpeed = Signal(list, int, int)

    def __init__(self):
        super().__init__()
        self.createGrid()
        self.populateGrid()

    def createGrid(self):
        # lay grid on panel
        self.grid = QGridLayout()
        self.setLayout(self.grid)

    def populateGrid(self):
        micron_label = QLabel('um')
        micron_label.setFont(QFont('Helvetica', 14))
        micron_label.setStyleSheet('padding:2px')

        axis_label = QLabel('X')
        axis_label.setFont(QFont('Helvetica', 18, QFont.Bold))
        axis_label.setStyleSheet('padding:20px')
        self.grid.addWidget(axis_label, 0, 0)

        self.goto_x = QLineEdit('')
        self.goto_x.setStyleSheet('padding:20px')
        self.goto_x.setFont(QFont('Helvetica', 16))
        self.goto_x.setToolTip('Position of X Axis')
        self.goto_x.setMaximumWidth(150)
        self.grid.addWidget(self.goto_x, 0, 1, alignment=QtCore.Qt.AlignLeft)
        self.grid.addWidget(micron_label, 0, 2, alignment=QtCore.Qt.AlignLeft)

        micron_label = QLabel('um')
        micron_label.setFont(QFont('Helvetica', 14))
        micron_label.setStyleSheet('padding:2px')

        speed_selection_group = QGroupBox('Speed')
        self.grid.addWidget(speed_selection_group, 1, 1)

        button_layout = QHBoxLayout()
        speed_selection_group.setLayout(button_layout)

        speed_group = QButtonGroup(self.grid)
        speed_group.setExclusive(True)
        self.slow_speed = QRadioButton('Slow')
        self.medium_speed = QRadioButton('Medium')
        self.fast_speed = QRadioButton('Fast')
        speed_group.addButton(self.slow_speed)
        speed_group.addButton(self.medium_speed)
        speed_group.addButton(self.fast_speed)
        button_layout.addWidget(self.slow_speed)
        button_layout.addWidget(self.medium_speed)
        button_layout.addWidget(self.fast_speed)

        self.go_btn = QPushButton('Go')
        self.go_btn.setStyleSheet('padding:20px')
        self.go_btn.setToolTip('Go to absolute position')
        self.go_btn.setMaximumWidth(150)
        self.grid.addWidget(self.go_btn, 2, 1)

        self.go_btn.clicked.connect(self.getInputPosition)
        speed_group.buttonClicked.connect(self.getButtonClicked)

    def getInputPosition(self):
        try:
            xcoord = float(self.goto_x.text())
            self.submitGoTo.emit([1], 0, [xcoord], 0)
        except ValueError:
            pass        
        self.close()

    def getButtonClicked(self, button):
        speed = button.text().lower()
        if speed == 'slow':
            velocity = 6    # 3 um/s 
        elif speed == 'medium':
            velocity = 7
        elif speed == 'fast':
            velocity = 8
        self.submitSpeed.emit([1], 0, velocity)


class Worker(QObject):

    finished = Signal()
    answer = Signal(str)

    def __init__(self, function):
        super().__init__()
        self.function = function

    @Slot()
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
    mainWin = GUI(connection_type='socket')
    mainWin.show()
    sys.exit(app.exec())