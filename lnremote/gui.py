""""""
"""
File: d:/GitHub/LN-Remote/lnremote/gui.py

Created on: 12/01/2022 14:17:02
Author: rmojica
"""

import csv
import datetime
import time
from pathlib import Path
import numpy

from __init__ import __about__
from config_loader import LoadConfig
from PySide6 import QtCore, QtWidgets
from PySide6.QtCore import QSize, Qt, Signal, Slot
from PySide6.QtGui import QAction, QColor, QFont, QPalette
from PySide6.QtWidgets import (QButtonGroup, QCheckBox, QGridLayout, QGroupBox,
                               QHBoxLayout, QLabel, QLineEdit, QMainWindow,
                               QMenuBar, QMessageBox, QPushButton,
                               QRadioButton, QTableWidget, QTableWidgetItem,
                               QWidget)


class PositionPanel(QGroupBox):

    def __init__(self, manipulator, interface):
        super().__init__("Position", parent=None)
        self.manipulator = manipulator
        self.interface = interface

        layout = QGridLayout()
        self.setLayout(layout)

        self.createContents()
        self.addToLayout(layout)

    def createContents(self):
        self.createPositionBoxes()
        self.createStopButton()
        self.createResetAxesButton()

    def addToLayout(self, layout):
        layout.addWidget(self.createAxisLabel('X'), 0, 0)
        layout.addWidget(self.createAxisLabel('Y'), 1, 0)
        layout.addWidget(self.createAxisLabel('Z'), 2, 0)

        layout.addWidget(self.read_x, 0, 1, 1, 2, alignment=QtCore.Qt.AlignLeft)
        layout.addWidget(self.read_y, 1, 1, 1, 2, alignment=QtCore.Qt.AlignLeft)
        layout.addWidget(self.read_z, 2, 1, 1, 2, alignment=QtCore.Qt.AlignLeft)

        layout.addWidget(self.createUnitLabel(), 0, 3, alignment=QtCore.Qt.AlignLeft)
        layout.addWidget(self.createUnitLabel(), 1, 3, alignment=QtCore.Qt.AlignLeft)
        layout.addWidget(self.createUnitLabel(), 2, 3, alignment=QtCore.Qt.AlignLeft)

        layout.addWidget(self.zero_btn, 3, 0, 1, 2)
        layout.addWidget(self.stop_axes_btn, 3, 2, 1, 2)

    def createPositionBoxes(self):
        self.read_x = QLineEdit('')
        self.read_x.setStyleSheet('padding:15px')
        self.read_x.setToolTip('Position of X Axis')
        self.read_x.setFont(QFont('Helvetica', 14))
        self.read_x.setReadOnly(True)
        self.read_x.setMaximumWidth(150)

        self.read_y = QLineEdit('')
        self.read_y.setStyleSheet('padding:15px')
        self.read_y.setToolTip('Position of Y Axis')
        self.read_y.setFont(QFont('Helvetica', 14))
        self.read_y.setReadOnly(True)
        self.read_y.setMaximumWidth(150)

        self.read_z = QLineEdit('')
        self.read_z.setStyleSheet('padding:15px')
        self.read_z.setToolTip('Position of Z Axis')
        self.read_z.setFont(QFont('Helvetica', 14))
        self.read_z.setReadOnly(True)
        self.read_z.setMaximumWidth(150)
    
    def createStopButton(self):
        self.stop_axes_btn = QPushButton('STOP')
        self.stop_axes_btn.setStyleSheet('padding:15px')
        self.stop_axes_btn.setToolTip('Immediately stop movement')
        self.stop_axes_btn.clicked.connect(
            lambda: self.manipulator.stopAxes([1, 2, 3]))

    def createResetAxesButton(self):
        self.zero_btn = QPushButton('Zero Axes')
        self.zero_btn.setStyleSheet('padding:15px')
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

    def __init__(self, position_panel, save_dir):
        super().__init__("Cells", parent=None)
        self.position_panel = position_panel
        self.save_dir = save_dir
        self.date = datetime.datetime.now().date().strftime("%Y%m%d")
        self.current_pipette = 1

        layout = QGridLayout()
        self.setLayout(layout)

        self.createContents()
        self.addToLayout(layout)

        self.enablePipetteCount()

        self.loadTableData()

    def createContents(self):
        self.createTable()
        self.createAddPipetteButton()
        self.createRemovePipetteButton()
        self.createSavePositionButton()
        self.createPipetteCheckBox()
        self.createPipetteCountBox()
        self.createIncreasePipetteCountButton()
        self.createAddPipetteButton()

    def addToLayout(self, layout):
        layout.addWidget(self.table, 0, 0, 1, 6)
        layout.addWidget(self.pipette_checkbox, 1, 1, 1, 2, QtCore.Qt.AlignRight)
        layout.addWidget(self.pipette_count, 1, 3, 1, 1, QtCore.Qt.AlignLeft)
        layout.addWidget(self.pipette_count_add_btn, 1, 4)
        layout.addWidget(self.add_pipette_btn, 2, 0, 1, 2)
        layout.addWidget(self.remove_pipette_btn, 2, 2, 1, 2)
        layout.addWidget(self.save_position_btn, 2, 4, 1, 2)

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
        self.add_pipette_btn.setStyleSheet('padding:15px')
        self.add_pipette_btn.setToolTip('Add row to table')
        self.add_pipette_btn.clicked.connect(self.addRow)

    def createRemovePipetteButton(self):
        self.remove_pipette_btn = QPushButton('Remove')
        self.remove_pipette_btn.setStyleSheet('padding:15px')
        self.remove_pipette_btn.setToolTip('Remove row from table')
        self.remove_pipette_btn.clicked.connect(self.removeRow)

    def createSavePositionButton(self):
        self.save_position_btn = QPushButton('Save Position')
        self.save_position_btn.setStyleSheet('padding:15px')
        self.save_position_btn.setToolTip('Save current position')
        self.save_position_btn.clicked.connect(self.addPatchedCell)

    def createPipetteCheckBox(self):
        self.pipette_checkbox = QCheckBox('Cell:')
        self.pipette_checkbox.setToolTip('Enable automatic pipette number addition')
        self.pipette_checkbox.stateChanged.connect(self.enablePipetteCount)

    def createPipetteCountBox(self):
        self.pipette_count = QLineEdit(str(self.current_pipette))
        self.pipette_count.setFixedWidth(50)

    def createIncreasePipetteCountButton(self):
        self.pipette_count_add_btn = QPushButton('+')
        self.pipette_count_add_btn.setFixedSize(25,25)
        self.pipette_count_add_btn.clicked.connect(self.increasePipetteCount)

    def increasePipetteCount(self):
        count = int(self.pipette_count.text()) + 1
        self.pipette_count.setText(str(count))

    def enablePipetteCount(self):
        if self.pipette_checkbox.isChecked():
            self.pipette_count.setEnabled(True)
            self.pipette_count_add_btn.setEnabled(True)
        else:
            self.pipette_count.setEnabled(False)
            self.pipette_count_add_btn.setEnabled(False)

    def addRow(self):
        total_rows = self.table.rowCount()
        self.table.insertRow(total_rows)

    def removeRow(self):
        total_rows = self.table.rowCount()
        self.table.removeRow(total_rows-1)

    def addPatchedCell(self):
        current_row = self.table.rowCount()
        current_pipette = self.pipette_count.text()
        if self.pipette_checkbox.isChecked():
            self.table.setItem(current_row - 1, 0,
                               QTableWidgetItem(f'p{current_pipette}'))
            self.pipette_count.setText(str(int(current_pipette)+1))
        else:
            pass

        current_position = self.position_panel.read_x.text()
        self.table.setItem(current_row - 1, 1,
                           QTableWidgetItem(current_position))

    def getTableData(self):
        self.pipettes = []
        total_rows = self.table.rowCount()
        total_columns = self.table.columnCount()
        for row in range(total_rows):
            self.pipettes.append([])
            for column in range(total_columns):
                _item = self.table.item(row, column)
                if _item:
                    self.pipettes[row].append(str(_item.text()))
                else:
                    self.pipettes[row].append('NA')

    def saveTableData(self):
        print('Saving pipettes...')
        self.getTableData()
        
        save_dir = Path(f'{self.save_dir}/{self.date}')
        save_dir.mkdir(parents=True, exist_ok=True)
        filepath = Path(f'{save_dir}/pipettes.csv')
        with open(filepath, 'w') as f:
            numpy.savetxt(f,
                            self.pipettes,
                            delimiter=",",
                            comments="",
                            header="pipette,depth",
                            fmt='%s')

    def overwritePipetteCount(self):
        prev_pipette = self.pipettes[len(self.pipettes) - 1][0]
        last_count = int(prev_pipette[1:])
        self.pipette_count.setText(str(last_count + 1))

    def setTableData(self):
        row_count = len(self.pipettes)
        col_count = len(self.pipettes[0])

        self.table.setRowCount(row_count - 1)
        self.table.setColumnCount(col_count)

        for row in range(1, row_count):
            for col in range(col_count):
                item = QTableWidgetItem(str(self.pipettes[row][col]))
                self.table.setItem(row - 1, col, item)
        
        self.overwritePipetteCount()
        self.pipette_count.setEnabled(True)
        self.pipette_checkbox.setChecked(True)
        self.pipette_count_add_btn.setEnabled(True)

    def loadTableData(self):
        load_dir = Path(f'{self.save_dir}/{self.date}/pipettes.csv') 
        if load_dir.exists():
            print('Loading pipettes...')
            self.pipettes = []
            with open(load_dir, newline='') as csvfile:
                for row in csv.reader(csvfile, delimiter=','):
                    self.pipettes.append(row)
            self.setTableData()


class ControlsPanel(QGroupBox):

    def __init__(self, manipulator, position_panel):
        super().__init__('Controls')

        self.manipulator = manipulator
        self.position_panel = position_panel
        self.approach_win = None

        layout = QGridLayout()
        self.setLayout(layout)

        self.createApproachButton()
        self.createExitBrainButton()
        self.createMoveAwayButton()
        self.createReturnButton()

        layout.addWidget(self.approach_btn, 0, 0)
        layout.addWidget(self.exit_brain_btn, 0, 1)
        layout.addWidget(self.move_away_btn, 1, 0)
        layout.addWidget(self.return_btn, 1, 1)

    def createApproachButton(self):
        self.approach_btn = QPushButton('Approach')
        self.approach_btn.setStyleSheet('padding:15px')
        self.approach_btn.setToolTip('Go to absolute coordinates')
        self.approach_btn.clicked.connect(self.approachPositionDialog)

    def createExitBrainButton(self):
        self.exit_brain_btn = QPushButton('Exit Tissue')
        self.exit_brain_btn.setStyleSheet('padding:15px')
        self.exit_brain_btn.setToolTip('Slowly exit tissue to 100 um')
        self.exit_brain_btn.clicked.connect(self.exitBrain)

    def createMoveAwayButton(self):
        self.move_away_btn = QPushButton('Move Away')
        self.move_away_btn.setStyleSheet('padding:15px')
        self.move_away_btn.setToolTip('Move stages away from the sample')
        self.move_away_btn.clicked.connect(self.moveAway)

    def createReturnButton(self):
        self.return_btn = QPushButton('Return')
        self.return_btn.setStyleSheet('padding:15px')
        self.return_btn.setToolTip('Return pipette to the craniotomy')
        self.return_btn.clicked.connect(self.returnToCraniotomy)

    def approachPositionDialog(self):
        if self.approach_win is None:
            self.approach_win = ApproachWindow()
        self.approach_win.submitGoTo.connect(
            self.manipulator.approachAxesPosition)
        self.approach_win.submitSpeed.connect(
            self.manipulator.setPositioningVelocity)
        self.approach_win.show()

    def exitBrain(self):
        self.manipulator.approachAxesPosition(axes=[1],
                                              approach_mode=0,
                                              positions=[100],
                                              speed_mode=0)

    def moveAway(self):
        if self.inBrain():
            msg = 'Looks like the pipette is still in the brain.\nAborting command.'
            result = self.errorDialog(msg, kind='choice')
            if result == 524288:
                # first exit brain
                self.exitBrain()
                time.sleep(1)
                self.manipulator.approachAxesPosition(axes=[2, 3],
                                                      approach_mode=0,
                                                      positions=[-26000, 26000],
                                                      speed_mode=1)
            else:
                pass

        else:
            self.manipulator.moveAxis(axis=1, speed_mode=1, direction=1, velocity=None)
            time.sleep(0.5)
            self.manipulator.approachAxesPosition(axes=[2, 3],
                                                  approach_mode=0,
                                                  positions=[-26000, 26000],
                                                  speed_mode=1)

    def returnToCraniotomy(self):
        if self.inBrain():
            msg = 'Looks like the pipette is still in the brain.\nAborting command.'
            result = self.errorDialog(msg, kind='warning')
            pass
        else:
            self.manipulator.approachAxesPosition(axes=[2, 3],
                                                  approach_mode=0,
                                                  positions=[500, 1000],
                                                  speed_mode=1)

    def inBrain(self):
        if float(self.position_panel.read_x.text()) < 100.0:
            return True
        else:
            return False

    def errorDialog(self, error_message, kind='choice'):
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

        if kind == 'choice':
            error_box.setStandardButtons(QMessageBox.Retry | QMessageBox.Cancel)
            error_box.setDefaultButton(QMessageBox.Cancel)

            proceed_btn = error_box.button(QMessageBox.Retry)
            proceed_btn.setText('Proceed Anyway')
        elif kind == 'warning':
            error_box.setStandardButtons(QMessageBox.Ok)
            error_box.setDefaultButton(QMessageBox.Ok)

        return error_box.exec()


class ApproachWindow(QWidget):
    submitGoTo = Signal(list, float, list, int)
    submitSpeed = Signal(list, int, int)

    def __init__(self):
        super().__init__()
        self.setWindowTitle('Approach')

        # default speed to 'slow'
        self.speed = 'slow'
        self.setToggledSpeed()

        layout = QGridLayout()
        self.setLayout(layout)
        self.speed_group = QButtonGroup(layout)

        self.createPositionBoxes()
        self.createRadioButtons()
        self.createRadioBox()
        self.createGoButton()

        layout.addWidget(self.createAxisLabel('X'), 0, 0)
        layout.addWidget(self.goto_x, 0, 1, alignment=QtCore.Qt.AlignLeft)
        layout.addWidget(self.createUnitLabel(), 0, 2, alignment=QtCore.Qt.AlignLeft)

        layout.addWidget(self.speed_selection_group, 1, 1)
        layout.addWidget(self.go_btn, 2, 1)

    def createPositionBoxes(self):
        self.goto_x = QLineEdit('')
        self.goto_x.setStyleSheet('padding:15px')
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
        self.go_btn.setStyleSheet('padding:15px')
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
        xcoord = self.goto_x.text()
        try:
            self.submitGoTo.emit([1], 0, [float(xcoord)], 0)
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


class AboutWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle('About')

        self.label = QLabel(__about__)
        self.label.setWordWrap(True)
        # label.setText(__about__)
        self.label.show()


class MainWindow(QMainWindow):

    CONFIG = LoadConfig().Gui()
    PATH = CONFIG['data_path']
    DEBUG = CONFIG['debug'] == 'True'
    WAVESURFER = CONFIG['wavesurfer'] == 'True'

    def __init__(self, interface):
        super().__init__()

        self.interface = interface
        self.setupGui()

    def setupGui(self):
        self.setWindowTitle('Manipulator GUI')
        self.setMinimumSize(QSize(400, 300))
        self.setMinimumWidth(400)
        self.setFont(QFont('Helvetica', 14))
        self.setWindowFlags(Qt.WindowStaysOnTopHint)

        # self.manipulator = LuigsAndNeumannSM10()
        # self.manipulator.initializeManipulator()
        self.position_panel = PositionPanel(self.interface.manipulator, self.interface)
        self.cells_panel = CellsPanel(self.position_panel, self.PATH)
        self.controls_panel = ControlsPanel(self.interface.manipulator,
                                            self.position_panel)

        self.content_layout = QGridLayout()
        self.content_layout.addWidget(self.position_panel, 0, 0)
        self.content_layout.addWidget(self.cells_panel, 0, 1)
        self.content_layout.addWidget(self.controls_panel, 1, 0, 1, 2)

        self.setCentralWidget(QWidget())
        self.centralWidget().setLayout(self.content_layout)

        self._createActions()
        self._connectActions()
        self._createMenuBar()

        # self.applyDarkTheme()

    def _createActions(self):
        self.saveAction = QAction('&Save', self)
        self.exitAction = QAction('&Exit', self)

        # self.helpAction = QAction('&Help', self)
        self.aboutAction = QAction('&About...', self)

    def _createMenuBar(self):
        menu_bar = QMenuBar(self)
        self.setMenuBar(menu_bar)

        file_menu = menu_bar.addMenu('&File')
        file_menu.addAction(self.saveAction)
        file_menu.addAction(self.exitAction)

        help_menu = menu_bar.addMenu('&Help')
        # help_menu.addAction(self.helpAction)
        help_menu.addAction(self.aboutAction)

    def _connectActions(self):
        self.saveAction.triggered.connect(self.cells_panel.saveTableData)
        self.exitAction.triggered.connect(self.close)
        # self.helpAction.triggered.connect(self.helpContent)
        self.aboutAction.triggered.connect(self.about)

    def about(self):
        self.about_window = AboutWindow()

    def applyDarkTheme(self):
        palette = QPalette()
        palette.setColor(QPalette.Window, QColor(53, 53, 53))
        palette.setColor(QPalette.WindowText, Qt.white)
        palette.setColor(QPalette.Base, QColor(25, 25, 25))
        palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
        palette.setColor(QPalette.ToolTipBase, Qt.black)
        palette.setColor(QPalette.ToolTipText, Qt.white)
        palette.setColor(QPalette.Text, Qt.white)
        palette.setColor(QPalette.Button, QColor(53, 53, 53))
        palette.setColor(QPalette.ButtonText, Qt.white)
        palette.setColor(QPalette.BrightText, Qt.red)
        palette.setColor(QPalette.Link, QColor(42, 130, 218))
        palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
        palette.setColor(QPalette.HighlightedText, Qt.black)
        self.setPalette(palette)
