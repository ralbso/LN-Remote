""""""
"""
File: d:/GitHub/LN-Remote/gui.py

Created on: 12/01/2022 14:17:02
Author: rmojica
"""

import time

from config_loader import LoadConfig
from manipulator import LuigsAndNeumannSM10

from PySide6 import QtCore, QtGui, QtWidgets
from PySide6.QtCore import QSize, Signal, Slot
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (QApplication, QButtonGroup, QComboBox, QDialog,
                               QFileDialog, QGridLayout, QGroupBox,
                               QHBoxLayout, QLabel, QLineEdit, QListView,
                               QListWidget, QMainWindow, QMessageBox,
                               QPushButton, QRadioButton, QTableWidget,
                               QTableWidgetItem, QVBoxLayout, QWidget)


class PositionPanel(QGroupBox):

    def __init__(self, manipulator, interface):
        super().__init__("Position", parent=None)
        self.manipulator = manipulator
        self.interface = interface

        # self.interface.getCurrentPosition()

        layout = QGridLayout()
        self.setLayout(layout)

        self.createPositionBoxes()
        self.createResetAxesButton()

        layout.addWidget(self.createAxisLabel('X'), 0, 0)
        layout.addWidget(self.createAxisLabel('Y'), 1, 0)
        layout.addWidget(self.createAxisLabel('Z'), 2, 0)

        layout.addWidget(self.read_x, 0, 1, alignment=QtCore.Qt.AlignLeft)
        layout.addWidget(self.read_y, 1, 1, alignment=QtCore.Qt.AlignLeft)
        layout.addWidget(self.read_z, 2, 1, alignment=QtCore.Qt.AlignLeft)

        layout.addWidget(self.createUnitLabel(),
                         0,
                         2,
                         alignment=QtCore.Qt.AlignLeft)
        layout.addWidget(self.createUnitLabel(),
                         1,
                         2,
                         alignment=QtCore.Qt.AlignLeft)
        layout.addWidget(self.createUnitLabel(),
                         2,
                         2,
                         alignment=QtCore.Qt.AlignLeft)

        layout.addWidget(self.zero_btn, 3, 1)

    def createPositionBoxes(self):
        self.read_x = QLineEdit('')
        self.read_x.setStyleSheet('padding:20px')
        self.read_x.setToolTip('Position of X Axis')
        self.read_x.setFont(QFont('Helvetica', 14))
        self.read_x.setReadOnly(True)
        self.read_x.setMaximumWidth(150)

        self.read_y = QLineEdit('')
        self.read_y.setStyleSheet('padding:20px')
        self.read_y.setToolTip('Position of X Axis')
        self.read_y.setFont(QFont('Helvetica', 14))
        self.read_y.setReadOnly(True)
        self.read_y.setMaximumWidth(150)

        self.read_z = QLineEdit('')
        self.read_z.setStyleSheet('padding:20px')
        self.read_z.setToolTip('Position of X Axis')
        self.read_z.setFont(QFont('Helvetica', 14))
        self.read_z.setReadOnly(True)
        self.read_z.setMaximumWidth(150)

    def createResetAxesButton(self):
        self.zero_btn = QPushButton('Zero Axes')
        self.zero_btn.setStyleSheet('padding:20px')
        self.zero_btn.setToolTip('Zero all axes')
        self.zero_btn.clicked.connect(
            lambda: self.manipulator.resetAxesZero([1, 2, 3]))

    def createUnitLabel(self):
        micron_label = QLabel('um')
        micron_label.setFont(QFont('Helvetica', 14))
        micron_label.setStyleSheet('padding:2px')
        return micron_label

    def createAxisLabel(self, axis: str):
        axis_label = QLabel(axis)
        axis_label.setFont(QFont('Helvetica', 18, QFont.Bold))
        axis_label.setStyleSheet('padding:5px')
        return axis_label


class CellsPanel(QGroupBox):

    def __init__(self, position_panel):
        super().__init__("Cells", parent=None)
        self.position_panel = position_panel

        layout = QGridLayout()
        self.setLayout(layout)

        self.createTable()
        self.createAddPipetteButton()
        self.createSavePositionButton()

        layout.addWidget(self.table, 0, 0, 1, 0)
        layout.addWidget(self.add_pipette_btn, 1, 0)
        layout.addWidget(self.save_position_btn, 1, 1)

    def createTable(self):
        self.table = QTableWidget()
        self.table.setFont(QFont('Helvetica', 10))
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(['Pipette', 'Depth'])
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QtWidgets.QHeaderView.Stretch)
        header.setSectionResizeMode(1, QtWidgets.QHeaderView.Stretch)

    def createAddPipetteButton(self):
        self.add_pipette_btn = QPushButton('Add')
        self.add_pipette_btn.setStyleSheet('padding:20px')
        self.add_pipette_btn.setToolTip('Add row to table')
        self.add_pipette_btn.clicked.connect(self.addRow)

    def createSavePositionButton(self):
        self.save_position_btn = QPushButton('Save Position')
        self.save_position_btn.setStyleSheet('padding:20px')
        self.save_position_btn.setToolTip('Save current position')
        self.save_position_btn.clicked.connect(self.addPatchedCell)

    def addRow(self):
        total_rows = self.table.rowCount()
        self.table.insertRow(total_rows)

    def addPatchedCell(self):
        current_row = self.table.rowCount()
        current_position = self.position_panel.read_x.text()
        self.table.setItem(current_row - 1, 1,
                           QTableWidgetItem(current_position))


class ControlsPanel(QGroupBox):

    def __init__(self, manipulator, position_panel):
        super().__init__('Controls')

        self.manipulator = manipulator
        self.position_panel = position_panel
        self.approach_win = None

        layout = QGridLayout()
        self.setLayout(layout)

        self.createStopButton()
        self.createApproachButton()
        self.createExitBrainButton()
        self.createMoveAwayButton()

        layout.addWidget(self.stop_axes_btn, 0, 0)
        layout.addWidget(self.approach_btn, 0, 1)
        layout.addWidget(self.exit_brain_btn, 1, 0)
        layout.addWidget(self.move_away_btn, 1, 1)

    def createStopButton(self):
        self.stop_axes_btn = QPushButton('STOP')
        self.stop_axes_btn.setStyleSheet('padding:20px')
        self.stop_axes_btn.setToolTip('Immediately stop movement')
        self.stop_axes_btn.clicked.connect(
            lambda: self.manipulator.stopAxes([1, 2, 3]))

    def createApproachButton(self):
        self.approach_btn = QPushButton('Approach')
        self.approach_btn.setStyleSheet('padding:20px')
        self.approach_btn.setToolTip('Go to absolute coordinates')
        self.approach_btn.clicked.connect(self.approachPositionDialog)

    def createExitBrainButton(self):
        self.exit_brain_btn = QPushButton('Exit Tissue')
        self.exit_brain_btn.setStyleSheet('padding:20px')
        self.exit_brain_btn.setToolTip('Slowly exit tissue to 100 um')
        self.exit_brain_btn.clicked.connect(self.exitBrain)

    def createMoveAwayButton(self):
        self.move_away_btn = QPushButton('Move Away')
        self.move_away_btn.setStyleSheet('padding:20px')
        self.move_away_btn.setToolTip('Move stages away from the sample')
        self.move_away_btn.clicked.connect(self.moveAway)

    def approachPositionDialog(self):
        if self.approach_win is None:
            self.approach_win = ApproachWindow()
        self.approach_win.submitGoTo.connect(
            self.manipulator.approachAxesPosition)
        self.approach_win.submitSpeed.connect(lambda:
            self.manipulator.setPositioningVelocity())
        self.approach_win.show()

    def exitBrain(self):
        self.manipulator.approachAxesPosition(axes=[1],
                                              approach_mode=0,
                                              positions=[100],
                                              speed_mode=0)

    def moveAway(self):
        if float(self.position_panel.read_x.text()) < 100.0:
            result = self.errorDialog(
                'Looks like the pipette is still in the brain.\nAborting command.'
            )
            if result == 524288:
                # first move stage X (1) all the way out
                self.manipulator.moveAxis(1, 0, 1)
                time.sleep(1)
                self.manipulator.approachAxesPosition(axes=[2, 3],
                                                      approach_mode=0,
                                                      positions=[500, 500],
                                                      speed_mode=1)
            else:
                pass

        else:
            self.manipulator.moveAxis(1, 1, 1)
            self.maniuplator.approachAxesPosition(axes=[2, 3],
                                                  approach_mode=0,
                                                  positions=[500, 500],
                                                  speed_mode=1)

    def errorDialog(self, error_message):
        """Generate error dialog to notify user of a problem

        Parameters
        ----------
        error_message : str
            Error message to display on dialog box
        """
        error_box = QMessageBox()
        error_box.setIcon(QtWidgets.QMessageBox.Critical)
        error_box.setWindowTitle('Error')
        error_box.setText(error_message)
        error_box.setStandardButtons(QMessageBox.Retry | QMessageBox.Cancel)
        error_box.setDefaultButton(QMessageBox.Cancel)

        proceed_btn = error_box.button(QMessageBox.Retry)
        proceed_btn.setText('Proceed Anyway')

        return error_box.exec()


class ApproachWindow(QWidget):
    submitGoTo = Signal(list, float, list, int)
    submitSpeed = Signal(list, int, int)

    def __init__(self):
        super().__init__()

        layout = QGridLayout()
        self.setLayout(layout)
        self.speed_group = QButtonGroup(layout)

        self.createPositionBox()
        self.createRadioButtons()
        self.createRadioBox()
        self.createGoButton()

        layout.addWidget(self.createAxisLabel('X'), 0, 0)
        layout.addWidget(self.goto_x, 0, 1, alignment=QtCore.Qt.AlignLeft)
        layout.addWidget(self.createUnitLabel(),
                         0,
                         2,
                         alignment=QtCore.Qt.AlignLeft)

        layout.addWidget(self.speed_selection_group, 1, 1)
        layout.addWidget(self.go_btn, 2, 1)

    def createPositionBox(self):
        self.goto_x = QLineEdit('')
        self.goto_x.setStyleSheet('padding:20px')
        self.goto_x.setFont(QFont('Helvetica', 16))
        self.goto_x.setToolTip('Position of X Axis')
        self.goto_x.setMaximumWidth(150)

    def createRadioBox(self):
        self.speed_selection_group = QGroupBox('Speed')
        self.button_layout = QHBoxLayout()
        self.speed_selection_group.setLayout(self.button_layout)

        self.speed_group.setExclusive(True)

        self.speed_group.addButton(self.slow_speed_btn)
        self.speed_group.addButton(self.fast_speed_btn)

        self.button_layout.addWidget(self.slow_speed_btn)
        self.button_layout.addWidget(self.fast_speed_btn)

    def createRadioButtons(self):
        # set default speed
        self.speed = 'slow'
        self.setToggledSpeed()

        self.slow_speed_btn = QRadioButton('Slow')
        self.slow_speed_btn.speed = 'slow'
        self.slow_speed_btn.setChecked(True)
        self.slow_speed_btn.toggled.connect(self.getToggledButton)

        self.fast_speed_btn = QRadioButton('Fast')
        self.fast_speed_btn.speed = 'fast'
        self.fast_speed_btn.setChecked(False)
        self.fast_speed_btn.toggled.connect(self.getToggledButton)

    def createGoButton(self):
        self.go_btn = QPushButton('Go')
        self.go_btn.setStyleSheet('padding:20px')
        self.go_btn.setToolTip('Go to absolute position')
        self.go_btn.setMaximumWidth(150)
        self.go_btn.clicked.connect(self.getInputPosition)

    def createUnitLabel(self):
        micron_label = QLabel('um')
        micron_label.setFont(QFont('Helvetica', 14))
        micron_label.setStyleSheet('padding:2px')
        return micron_label

    def createAxisLabel(self, axis: str):
        axis_label = QLabel(axis)
        axis_label.setFont(QFont('Helvetica', 18, QFont.Bold))
        axis_label.setStyleSheet('padding:5px')
        return axis_label

    @Slot(list, float, list, int)
    def getInputPosition(self):
        try:
            xcoord = float(self.goto_x.text())
            self.submitGoTo.emit([1], 0, [xcoord], 0)
        except ValueError:
            pass
        self.close()

    def getToggledButton(self):
        toggled_radio = self.sender()
        self.speed = toggled_radio.speed
        self.setToggledSpeed()

    @Slot(list, int, int)
    def setToggledSpeed(self):
        if self.speed == 'slow':
            velocity = 6  # 3 um/s, 0.002630 rps
        elif self.speed == 'fast':
            velocity = 7  # 6 um/s, 0.005070 rps

        self.submitSpeed.emit([1], 0, velocity)


class MainWindow(QMainWindow):

    CONFIG = LoadConfig().Gui()
    PATH = CONFIG['data_path']
    DEBUG = CONFIG['debug']

    def __init__(self, interface):
        super().__init__()

        self.interface = interface
        self.setupGui()
        
    def setupGui(self):
        self.setWindowTitle('Manipulator GUI')
        self.setMinimumSize(QSize(400, 300))
        self.setMinimumWidth(400)
        self.setFont(QFont('Helvetica', 14))

        self.manipulator = LuigsAndNeumannSM10()
        self.position_panel = PositionPanel(self.manipulator, self.interface)
        self.cells_panel = CellsPanel(self.position_panel)
        self.controls_panel = ControlsPanel(self.manipulator, self.position_panel)

        self.content_layout = QGridLayout()
        self.content_layout.addWidget(self.position_panel, 0, 0)
        self.content_layout.addWidget(self.cells_panel, 0, 1)
        self.content_layout.addWidget(self.controls_panel, 1, 0, 1, 2)

        self.setCentralWidget(QWidget())
        self.centralWidget().setLayout(self.content_layout)
