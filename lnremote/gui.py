import csv
import datetime
import logging
import time
from pathlib import Path

import numpy
import qdarkstyle
from __init__ import __about__
from config_loader import LoadConfig
from PySide6 import QtCore, QtGui, QtWidgets
from PySide6.QtCore import QSize, Qt, Signal, Slot
from PySide6.QtGui import QAction, QFont
from PySide6.QtWidgets import (QButtonGroup, QCheckBox, QComboBox, QGridLayout,
                               QGroupBox, QHBoxLayout, QLabel, QLineEdit,
                               QMainWindow, QMenuBar, QMessageBox, QPushButton,
                               QRadioButton, QTableWidget, QTableWidgetItem,
                               QVBoxLayout, QWidget)
from qdarkstyle.light.palette import LightPalette

# create logger
logger = logging.getLogger(__name__)


class PositionPanel(QGroupBox):
    """Create the position panel, which contains the live position read-out
    from the manipulator, the Zero Axes button and the Stop button
    """
    def __init__(self, manipulator, interface):
        super().__init__("Position", parent=None)
        self.manipulator = manipulator
        self.interface = interface

        self._axis_colors = {
            'X': 'color: #ffb91d',
            'Y': 'color: #06a005',
            'Z': 'color: #fa0606'
        }

        layout = QGridLayout()
        self.setLayout(layout)

        self.createContents()
        self.addToLayout(layout)
        logger.info('Position panel created')

    def createContents(self):
        """Create the contents of the panel
        """
        self.createPositionBoxes()
        self.createStopButton()
        self.createResetAxesButton()

    def addToLayout(self, layout):
        """Add contents to the given layout
        """
        layout.addWidget(self.createAxisLabel('X'),
                         0,
                         0,
                         alignment=QtCore.Qt.AlignRight)
        layout.addWidget(self.createAxisLabel('Y'),
                         1,
                         0,
                         alignment=QtCore.Qt.AlignRight)
        layout.addWidget(self.createAxisLabel('Z'),
                         2,
                         0,
                         alignment=QtCore.Qt.AlignRight)

        layout.addWidget(self.read_x,
                         0,
                         1,
                         1,
                         2,
                         alignment=QtCore.Qt.AlignLeft)
        layout.addWidget(self.read_y,
                         1,
                         1,
                         1,
                         2,
                         alignment=QtCore.Qt.AlignLeft)
        layout.addWidget(self.read_z,
                         2,
                         1,
                         1,
                         2,
                         alignment=QtCore.Qt.AlignLeft)

        layout.addWidget(self.createUnitLabel(),
                         0,
                         3,
                         alignment=QtCore.Qt.AlignLeft)
        layout.addWidget(self.createUnitLabel(),
                         1,
                         3,
                         alignment=QtCore.Qt.AlignLeft)
        layout.addWidget(self.createUnitLabel(),
                         2,
                         3,
                         alignment=QtCore.Qt.AlignLeft)

        layout.addWidget(self.zero_btn, 3, 0, 1, 2)
        layout.addWidget(self.stop_axes_btn, 3, 2, 1, 2)

    def createPositionBoxes(self):
        """Create boxes to hold the axes positions, as well as their
        corresponding labels
        """
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
        """Create button to stop all axes movement
        """
        self.stop_axes_btn = QPushButton('STOP')
        self.stop_axes_btn.setStyleSheet('padding:15px')
        self.stop_axes_btn.setToolTip('Immediately stop movement')
        self.stop_axes_btn.clicked.connect(
            lambda: self.manipulator.stopAxes([1, 2, 3, 7, 8, 9]))

    def createResetAxesButton(self):
        """Create button to reset all axes to zero on counter 1
        """
        self.zero_btn = QPushButton('Zero Axes')
        self.zero_btn.setStyleSheet('padding:15px')
        self.zero_btn.setToolTip('Zero all axes')
        self.zero_btn.clicked.connect(
            lambda: self.manipulator.resetAxesZero([1, 2, 3, 7, 8, 9]))

    def createUnitLabel(self):
        """Create reusable label for axes units (um)
        """
        micron_label = QLabel('um')
        micron_label.setFont(QFont('Helvetica', 14))
        micron_label.setStyleSheet('padding:2px')
        return micron_label

    def createAxisLabel(self, axis: str):
        """Create label for the given axis
        """
        axis_label = QLabel(axis)
        axis_label.setFont(QFont('Helvetica', 18, QFont.Bold))
        axis_label.setStyleSheet(f'{self._axis_colors[axis]}; padding:2px')
        return axis_label

    def updatePositionBoxes(self, positions: list):
        """Update position labels based off given positions list
        """
        try:
            x_axis = f'{positions[0]:.2f}'
            y_axis = f'{positions[1]:.2f}'
            z_axis = f'{positions[2]:.2f}'
        except Exception as e:
            logger.error(f'Error updating position boxes: {e}')
            pass
        else:
            self.read_x.setText(x_axis)
            self.read_y.setText(y_axis)
            self.read_z.setText(z_axis)


class CellsPanel(QGroupBox):
    """Create the cells panel, which contains the pipette table and all
    related buttons"""
    def __init__(self, position_panel, save_dir):
        super().__init__("Cells", parent=None)
        self.position_panel = position_panel
        self.save_dir = save_dir
        self.date = datetime.datetime.now().date().strftime("%Y%m%d")
        self.current_pipette = 1
        self._cols = 9

        layout = QGridLayout()
        self.setLayout(layout)

        self.createContents()
        self.addToLayout(layout)

        self.enablePipetteCount()

        self.loadTableData()

        logger.info('Cells panel created')

    def styleLayout(self, layout):
        """Set all columns to be of equal width
        """
        for i in range(self._cols):
            layout.setColumnStretch(i, 1)

    def createContents(self):
        """Create panel contents
        """
        self.createTable()
        self.createAddPipetteButton()
        self.createRemovePipetteButton()
        self.createSavePositionButton()
        self.createPipetteCheckBox()
        self.createPipetteCountBox()
        self.createIncreasePipetteCountButton()
        self.createAddPipetteButton()

    def addToLayout(self, layout):
        """Add contents to the specified layout
        """
        self.styleLayout(layout)

        layout.addWidget(self.table, 0, 0, 1, self._cols)
        layout.addWidget(self.pipette_checkbox, 1, 2, 1, 3,
                         QtCore.Qt.AlignRight)
        layout.addWidget(self.pipette_count, 1, 5, 1, 1, QtCore.Qt.AlignLeft)
        layout.addWidget(self.pipette_count_add_btn, 1, 6, 1, 1)
        layout.addWidget(self.add_pipette_btn, 2, 0, 1, 3)
        layout.addWidget(self.remove_pipette_btn, 2, 3, 1, 3)
        layout.addWidget(self.save_position_btn, 2, 6, 1, 3)

    def createTable(self):
        """Create table that holds all pipettes and their corresponding depths
        """
        self.table = QTableWidget()
        self.table.setFont(QFont('Helvetica', 10))
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(['Pipette', 'Depth'])
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)
        self.table.verticalHeader().setVisible(False)

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QtWidgets.QHeaderView.Stretch)
        header.setSectionResizeMode(1, QtWidgets.QHeaderView.Stretch)

    def createAddPipetteButton(self):
        """Create button to add rows to the table
        """
        self.add_pipette_btn = QPushButton('Add')
        self.add_pipette_btn.setStyleSheet('padding:10px')
        self.add_pipette_btn.setToolTip('Add row to table')
        self.add_pipette_btn.clicked.connect(self.addRow)

    def createRemovePipetteButton(self):
        """Create button to remove the last row/pipette from the table
        """
        self.remove_pipette_btn = QPushButton('Del')
        self.remove_pipette_btn.setStyleSheet('padding:10px')
        self.remove_pipette_btn.setToolTip('Remove row from table')
        self.remove_pipette_btn.clicked.connect(self.removeRow)

    def createSavePositionButton(self):
        """Create button to save the current pipette's position
        """
        self.save_position_btn = QPushButton('Store')
        self.save_position_btn.setStyleSheet('padding:10px')
        self.save_position_btn.setToolTip('Save current position')
        self.save_position_btn.clicked.connect(self.addPatchedCell)

    def createPipetteCheckBox(self):
        """Create checkbox to enable pipette count
        """
        self.pipette_checkbox = QCheckBox('Cell:')
        self.pipette_checkbox.setToolTip(
            'Enable automatic pipette number addition')
        self.pipette_checkbox.stateChanged.connect(self.enablePipetteCount)

    def createPipetteCountBox(self):
        """Create box that holds the current pipette/cell count, which the
        table will use
        """
        self.pipette_count = QLineEdit(str(self.current_pipette))
        self.pipette_count.setFixedWidth(30)

    def createIncreasePipetteCountButton(self):
        """Create button to increase pipette count by 1
        """
        self.pipette_count_add_btn = QPushButton('+')
        self.pipette_count_add_btn.setFixedSize(25, 25)
        self.pipette_count_add_btn.clicked.connect(self.increasePipetteCount)

    def increasePipetteCount(self):
        """Increase pipette count by 1
        """
        count = int(self.pipette_count.text()) + 1
        self.pipette_count.setText(str(count))

    def enablePipetteCount(self):
        """Enable pipettes to be counted automatically
        """
        if self.pipette_checkbox.isChecked():
            self.pipette_count.setEnabled(True)
            self.pipette_count_add_btn.setEnabled(True)
        else:
            self.pipette_count.setEnabled(False)
            self.pipette_count_add_btn.setEnabled(False)

    def addRow(self):
        """Add row to table
        """
        total_rows = self.table.rowCount()
        self.table.insertRow(total_rows)

    def removeRow(self):
        """Remove row from table
        """
        total_rows = self.table.rowCount()
        self.table.removeRow(total_rows - 1)

    def addPatchedCell(self):
        """Store the current pipette/cell number and its current position to
        the previously-created row on the table. If the automatic pipette
        count is enabled, it will be used. Otherwise, the user can add any
        value to the 'Pipette' column. The current position will always be
        stored.
        """
        current_row = self.table.rowCount()
        current_pipette = self.pipette_count.text()
        if self.pipette_checkbox.isChecked():
            self.table.setItem(current_row - 1, 0,
                               QTableWidgetItem(f'p{current_pipette}'))
            self.pipette_count.setText(str(int(current_pipette) + 1))
        else:
            pass

        current_position = self.position_panel.read_x.text()
        self.table.setItem(current_row - 1, 1,
                           QTableWidgetItem(current_position))

    def getTableData(self):
        """Extract data from table
        """
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
                    self.pipettes[row].append('')

    def saveTableData(self):
        """Save data on table to csv
        """
        logger.info('Saving pipettes...')
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
        """If loading a previously-stored pipettes file to display on the
        table, we also get the last saved pipette number and add 1 so that
        the automatic counter starts from where we left off
        """
        i = 1
        while True:
            try:
                if len(self.pipettes) < 1:
                    last_count = 0
                else:
                    prev_pipette = self.pipettes[-i][0]
                    last_count = int(prev_pipette[1:])
                self.pipette_count.setText(str(last_count + 1))
                break
            except Exception:
                i += 1
                continue

    def setTableData(self):
        """If loading pipettes from file, set the table data from the file
        """
        row_count = len(self.pipettes)
        col_count = len(self.pipettes[0])

        self.table.setRowCount(row_count - 1)
        self.table.setColumnCount(col_count)

        for row in range(1, row_count):
            for col in range(col_count):
                item = QTableWidgetItem(str(self.pipettes[row][col]))
                self.table.setItem(row - 1, col, item)

        if row_count > 1:
            self.overwritePipetteCount()
            self.pipette_count.setEnabled(True)
            self.pipette_checkbox.setChecked(True)
            self.pipette_count_add_btn.setEnabled(True)

    def loadTableData(self):
        """Load previously-saved pipettes file and populate the table
        """
        load_dir = Path(f'{self.save_dir}/{self.date}/pipettes.csv')
        if load_dir.exists():
            self.pipettes = []
            with open(load_dir, newline='') as csvfile:
                for row in csv.reader(csvfile, delimiter=','):
                    self.pipettes.append(row)
            self.setTableData()
            logger.info('Loaded pipettes.')


class NavigationPanel(QGroupBox):
    """Create the navigation panel, which contains all navigation-related
    buttons and menus
    """
    def __init__(self, manipulator):
        super().__init__('Navigation')
        self.manipulator = manipulator

        self._speed_modes = {'L': 0, 'H': 1}
        self.speed_mode = int(list(self._speed_modes.values())[0])

        self._velocities = {'slow': 6, 'med': 10, 'fast': 15}
        self.velocity = int(list(self._velocities.values())[0])

        layout = QGridLayout()
        self.setLayout(layout)

        self.createContents()
        self.addToLayout(layout)

        self.toggleNavigation()

        logger.info('Navigation panel created')

    def styleLayout(self, layout):
        """Ensure that all columns have the same width
        """
        layout.setColumnStretch(0, 1)
        layout.setColumnStretch(1, 1)
        layout.setColumnStretch(2, 1)
        layout.setColumnStretch(3, 1)
        layout.setColumnStretch(4, 1)

    def createContents(self):
        """Create navigation panel contents (buttons & menus)
        """
        self.createNavigationCheckBox()
        self.createNavigationSpeedDropdown()
        self.createNavigationVelocityDropdown()
        self.createNavigateXInButton()
        self.createNavigateXOutButton()
        self.createNavigateYForwardButton()
        self.createNavigateYBackwardButton()
        self.createNavigateZUpButton()
        self.createNavigateZDownButton()

    def addToLayout(self, layout):
        """Add all contents to the panel's layout
        """
        self.styleLayout(layout)

        layout.addWidget(self.navigation_checkbox, 0, 0, 1, 2)
        layout.addWidget(self.navigation_speed_dropdown, 0, 2, 1, 2)
        layout.addWidget(self.navigation_velocity_dropdown, 0, 4, 1, 2)
        layout.addWidget(self.navigate_x_in_btn, 2, 0)
        layout.addWidget(self.navigate_x_out_btn, 2, 2)
        layout.addWidget(self.navigate_y_fwd_btn, 1, 1)
        layout.addWidget(self.navigate_y_bwd_btn, 3, 1)
        layout.addWidget(self.navigate_z_up_btn, 1, 5)
        layout.addWidget(self.navigate_z_down_btn, 3, 5)

    def createNavigationCheckBox(self):
        """Create checkbox to enable or disable manual navigation in the GUI
        """
        self.navigation_checkbox = QCheckBox('Enable')
        self.navigation_checkbox.setToolTip('Enable navigation keys')
        self.navigation_checkbox.stateChanged.connect(self.toggleNavigation)

    def toggleNavigation(self):
        """Enable/disable manual navigation buttons
        """
        if self.navigation_checkbox.isChecked():
            self.navigation_speed_dropdown.setEnabled(True)
            self.navigation_velocity_dropdown.setEnabled(True)
            self.navigate_x_in_btn.setEnabled(True)
            self.navigate_x_out_btn.setEnabled(True)
            self.navigate_y_fwd_btn.setEnabled(True)
            self.navigate_y_bwd_btn.setEnabled(True)
            self.navigate_z_up_btn.setEnabled(True)
            self.navigate_z_down_btn.setEnabled(True)

            self.setMovementParameters(self.speed_mode, self.velocity)
        else:
            self.navigation_speed_dropdown.setEnabled(False)
            self.navigation_velocity_dropdown.setEnabled(False)
            self.navigate_x_in_btn.setEnabled(False)
            self.navigate_x_out_btn.setEnabled(False)
            self.navigate_y_fwd_btn.setEnabled(False)
            self.navigate_y_bwd_btn.setEnabled(False)
            self.navigate_z_up_btn.setEnabled(False)
            self.navigate_z_down_btn.setEnabled(False)

    def createNavigationSpeedDropdown(self):
        """Create dropdown with navigation speeds
        """
        self.navigation_speed_dropdown = QComboBox()
        self.navigation_speed_dropdown.addItems(list(self._speed_modes.keys()))
        self.navigation_speed_dropdown.currentTextChanged.connect(
            self.speedChanged)

    def speedChanged(self, speed_mode):
        """Get the selected speed mode
        """
        self.speed_mode = self._speed_modes[speed_mode]
        self.setMovementParameters(self.speed_mode, self.velocity)

    def createNavigationVelocityDropdown(self):
        """Create dropdown with navigation velocities. This may look similar
        to the speed dropdown, but isn't. In general, Luigs and Nuemann
        manipulators have two speeds, low (L) or high (H). A high speed with
        slow velocity is faster than a low speed with slow velocity.
        """
        self.navigation_velocity_dropdown = QComboBox()
        self.navigation_velocity_dropdown.addItems(
            list(self._velocities.keys()))
        self.navigation_velocity_dropdown.currentTextChanged.connect(
            self.velocityChanged)

    def velocityChanged(self, velocity):
        """Get the selected speed mode
        """
        self.velocity = self._velocities[velocity]
        self.setMovementParameters(self.speed_mode, self.velocity)

    def createNavigateXInButton(self):
        """Create button to move X in
        """
        icon = QtGui.QIcon(":/icons/circle-left-yellow.svg")
        self.navigate_x_in_btn = QPushButton()
        self.navigate_x_in_btn.setIcon(icon)
        self.navigate_x_in_btn.setStyleSheet('padding:10px')

        ax = 1
        self.navigate_x_in_btn.pressed.connect(
            lambda: self.onPress(ax, self.speed_mode, -1))
        self.navigate_x_in_btn.released.connect(lambda: self.onRelease(ax))

    def createNavigateXOutButton(self):
        """Create button to move X out
        """
        icon = QtGui.QIcon(":/icons/circle-right-yellow.svg")
        self.navigate_x_out_btn = QPushButton()
        self.navigate_x_out_btn.setIcon(icon)
        self.navigate_x_out_btn.setStyleSheet('padding:10px')

        ax = 1
        self.navigate_x_out_btn.pressed.connect(
            lambda: self.onPress(ax, self.speed_mode, 1))
        self.navigate_x_out_btn.released.connect(lambda: self.onRelease(ax))

    def createNavigateYForwardButton(self):
        """Create button to move Y forwards
        """
        icon = QtGui.QIcon(":/icons/circle-up-green.svg")
        self.navigate_y_fwd_btn = QPushButton()
        self.navigate_y_fwd_btn.setIcon(icon)
        self.navigate_y_fwd_btn.setStyleSheet('padding:10px')

        ax = 2
        self.navigate_y_fwd_btn.pressed.connect(
            lambda: self.onPress(ax, self.speed_mode, 1))
        self.navigate_y_fwd_btn.released.connect(lambda: self.onRelease(ax))

    def createNavigateYBackwardButton(self):
        """Create button to move Y backwards
        """
        icon = QtGui.QIcon(":/icons/circle-down-green.svg")
        self.navigate_y_bwd_btn = QPushButton()
        self.navigate_y_bwd_btn.setIcon(icon)
        self.navigate_y_bwd_btn.setStyleSheet('padding:10px')

        ax = 2
        self.navigate_y_bwd_btn.pressed.connect(
            lambda: self.onPress(ax, self.speed_mode, -1))
        self.navigate_y_bwd_btn.released.connect(lambda: self.onRelease(ax))

    def createNavigateZUpButton(self):
        """Create button to move Z up
        """
        icon = QtGui.QIcon(":/icons/circle-up-red.svg")
        self.navigate_z_up_btn = QPushButton()
        self.navigate_z_up_btn.setIcon(icon)
        self.navigate_z_up_btn.setStyleSheet('padding:10px')

        ax = 3
        self.navigate_z_up_btn.pressed.connect(
            lambda: self.onPress(ax, self.speed_mode, 1))
        self.navigate_z_up_btn.released.connect(lambda: self.onRelease(ax))

    def createNavigateZDownButton(self):
        """Create button to move Z down
        """
        icon = QtGui.QIcon(":/icons/circle-down-red.svg")
        self.navigate_z_down_btn = QPushButton()
        self.navigate_z_down_btn.setIcon(icon)
        self.navigate_z_down_btn.setStyleSheet('padding:10px')

        ax = 3
        self.navigate_z_down_btn.pressed.connect(
            lambda: self.onPress(ax, self.speed_mode, -1))
        self.navigate_z_down_btn.released.connect(lambda: self.onRelease(ax))

    def onPress(self, axis, speed_mode, direction, velocity=None):
        """If button is pressed, move the `axis` at the specified `speed_mod`
        towards `direction`
        """
        self.manipulator.moveAxis(axis, speed_mode, direction, velocity)

    def onRelease(self, axis):
        """If button is released, stop the `axis`
        """
        self.manipulator.stopMovement(axis)

    def setMovementParameters(self, speed_mode, velocity):
        """Set the selected movement parameters for each axis
        """
        logger.info('Setting default movement parameters')
        for axis in range(1, 4):
            self.manipulator.setMovementVelocity(axis, speed_mode, velocity)


class ControlsPanel(QGroupBox):
    """Create the controls panel, which contains all other manipulator
    controls, with a focus on automation.
    """
    def __init__(self, manipulator, position_panel, style):
        super().__init__('Controls')

        self.manipulator = manipulator
        self.position_panel = position_panel
        self.approach_win = None
        self.style = style

        layout = QGridLayout()
        self.setLayout(layout)

        self.createContents()
        self.addToLayout(layout)

        logger.info('Controls panel created')

    def createContents(self):
        """Create controls panel contents
        """
        self.createApproachButton()
        self.createExitBrainButton()
        self.createMoveAwayButton()
        self.createReturnButton()
        self.createUnitSelectionLabel()
        self.createUnitSelectionDropdown()

    def addToLayout(self, layout):
        """Add contents to layout
        """
        layout.addWidget(self.unit_selection_label, 0, 0)
        layout.addWidget(self.unit_selection_dropdown, 0, 1)
        layout.addWidget(self.approach_btn, 1, 0)
        layout.addWidget(self.exit_brain_btn, 1, 1)
        layout.addWidget(self.move_away_btn, 2, 0)
        layout.addWidget(self.return_btn, 2, 1)

    def createUnitSelectionLabel(self):
        """Create label to select unit to visualize and move
        """
        self.unit_selection_label = QLabel('Manipulator:')
        self.unit_selection_label.setFont(QFont('Helvetica', 12))
        self.unit_selection_label.setStyleSheet(
            'padding:2px; qproperty-alignment:AlignCenter;')

    def createUnitSelectionDropdown(self):
        """Create dropdown to select unit to visualize and move
        """
        self.unit_selection_dropdown = QComboBox()
        self.unit_selection_dropdown.addItems(['Intracellular', 'LFP'])
        self.unit_selection_dropdown.setToolTip('Select unit')
        self.unit_selection_dropdown.currentTextChanged.connect(
            self.unitChanged)
        self._current_unit = 1
        self._current_axes = [1, 2, 3]

    def createApproachButton(self):
        """Create approach button, which opens the approach position dialog
        """
        self.approach_btn = QPushButton('Approach')
        self.approach_btn.setStyleSheet('padding:15px')
        self.approach_btn.setToolTip('Go to absolute coordinates')
        self.approach_btn.clicked.connect(self.approachPositionDialog)

    def createExitBrainButton(self):
        """Create exit brain button
        """
        self.exit_brain_btn = QPushButton('Retract')
        self.exit_brain_btn.setStyleSheet('padding:15px')
        self.exit_brain_btn.setToolTip('Slowly retract to 100 um')
        self.exit_brain_btn.clicked.connect(self.exitBrain)

    def createMoveAwayButton(self):
        """Create move away button
        """
        self.move_away_btn = QPushButton('Move Away')
        self.move_away_btn.setStyleSheet('padding:15px')
        self.move_away_btn.setToolTip('Move stages away from the sample')
        self.move_away_btn.clicked.connect(self.moveAway)

    def createReturnButton(self):
        """Create return button
        """
        self.return_btn = QPushButton('Return')
        self.return_btn.setStyleSheet('padding:15px')
        self.return_btn.setToolTip('Return pipette to the craniotomy')
        self.return_btn.clicked.connect(self.returnToCraniotomy)

    def unitChanged(self):
        """Change unit to visualize and move
        """
        if self.unit_selection_dropdown.currentText() == 'Intracellular':
            self._current_unit = 1
            self._current_axes = [1, 2, 3]
        else:
            self._current_unit = 2
            self._current_axes = [7, 8, 9]

        self.manipulator.setUnit(self._current_unit)

    def approachPositionDialog(self):
        """Open approach position dialog
        """
        if self.approach_win is None:
            self.approach_win = ApproachWindow(self.style, self._current_axes)
        self.approach_win.submitGoTo.connect(
            self.manipulator.approachAxesPosition)
        self.approach_win.submitSpeed.connect(
            self.manipulator.setPositioningVelocity)
        self.approach_win.show()

    def exitBrain(self):
        """Slowly exit tissue to a safe distance (100 um away from the tissue)
        """
        logger.info('Exiting brain, moving to 100 um')
        self.manipulator.approachAxesPosition(axes=[self._current_axes[0]],
                                              approach_mode=0,
                                              positions=[100],
                                              speed_mode=0)

    def moveAway(self):
        """Move away from the tissue. If the pipette position indicates it
        might still be in the tissue, a dialog box pops up and allows the
        user to cancel or proceed anyway.\n
        If the proceed anyway button is pressed, the pipette is first safely
        removed and then
        quickly moved away.
        """
        logger.info('Moving away from the craniotomy')
        if self.inBrain():
            msg = "Looks like the pipette is still in the brain."
            "\nAborting command."
            result = self.errorDialog(msg, kind='choice')
            if result == 524288:
                self.exitBrain()  # first exit brain
                time.sleep(1)
                if not self.inBrain():
                    self.manipulator.approachAxesPosition(
                        axes=[self._current_axes[1:3]],
                        approach_mode=0,
                        positions=[-26000, 26000],
                        speed_mode=1)
            else:
                pass

        else:
            self.manipulator.moveAxis(axis=1,
                                      speed_mode=1,
                                      direction=1,
                                      velocity=None)
            time.sleep(0.5)
            self.manipulator.approachAxesPosition(
                axes=[self._current_axes[1:3]],
                approach_mode=0,
                positions=[-26000, 26000],
                speed_mode=1)

    def returnToCraniotomy(self):
        """Return the pipette to the vicinity of the craniotomy. Similar to
        the `moveAway()` method, if the pipette is still in the tissue, a
        dialog box is displayed. This one however cannot be overridden,
        for safety.
        """
        logger.info('Returning to the craniotomy')
        if self.inBrain():
            msg = 'Looks like the pipette is still in the brain.'
            '\nAborting command.'
            self.errorDialog(msg, kind='warning')
            pass
        else:
            self.manipulator.approachAxesPosition(
                axes=[self._current_axes[1:3]],
                approach_mode=0,
                positions=[500, 1000],
                speed_mode=1)

    def inBrain(self):
        """Check whether the pipette is still in the brain (Position < 100 um)
        """
        logger.info('Checking if pipette is still in the brain...')
        if float(self.position_panel.read_x.text()) < 100.0:
            logger.info('Pipette is still in the brain')
            return True
        else:
            logger.info('Pipette is not in the brain')
            return False

    def errorDialog(self, error_message, kind='choice'):
        """Generate error dialog to notify user of a problem

        Parameters
        ----------
        error_message : str
            Error message to display on dialog box
        """
        logger.warning(error_message)

        error_box = QMessageBox()
        error_box.setIcon(QtWidgets.QMessageBox.Critical)
        error_box.setWindowTitle('Error')
        error_box.setText(error_message)

        if kind == 'choice':
            error_box.setStandardButtons(QMessageBox.Retry
                                         | QMessageBox.Cancel)
            error_box.setDefaultButton(QMessageBox.Cancel)

            proceed_btn = error_box.button(QMessageBox.Retry)
            proceed_btn.setText('Proceed Anyway')
        elif kind == 'warning':
            error_box.setStandardButtons(QMessageBox.Ok)
            error_box.setDefaultButton(QMessageBox.Ok)

        return error_box.exec()


class ApproachWindow(QWidget):
    """Create window that allows the user to navigate to a specific
    X coordinate.
    """

    submitGoTo = Signal(list, float, list, int)
    submitSpeed = Signal(list, int, int)

    def __init__(self, style, axes):
        super().__init__()
        self.setWindowTitle('Approach')
        self.setWindowFlags(Qt.WindowStaysOnTopHint)

        self.axes = axes

        self.setStyleSheet(style)
        # default speed to 'slow'
        self.speed = 'slow'
        self.setToggledSpeed()

        layout = QGridLayout()
        self.setLayout(layout)
        self.speed_group = QButtonGroup(layout)

        self.createContents()
        self.addToLayout(layout)

        logger.info('Approach window created')

    def createContents(self):
        """Create window contents
        """
        self.createPositionBox()
        self.createRadioButtons()
        self.createRadioBox()
        self.createGoButton()

    def addToLayout(self, layout):
        """Add contents to layout
        """
        layout.addWidget(self.createAxisLabel('X'), 0, 0)
        layout.addWidget(self.goto_x, 0, 1, alignment=QtCore.Qt.AlignLeft)
        layout.addWidget(self.createUnitLabel(),
                         0,
                         2,
                         alignment=QtCore.Qt.AlignLeft)

        layout.addWidget(self.speed_selection_group, 1, 1)
        layout.addWidget(self.go_btn, 2, 1)

    def createPositionBox(self):
        """Create boxes for user input on the positions
        """
        self.goto_x = QLineEdit('')
        self.goto_x.setStyleSheet('padding:15px')
        self.goto_x.setFont(QFont('Helvetica', 16))
        self.goto_x.setToolTip('Position of X Axis')
        self.goto_x.setMaximumWidth(150)

    def createRadioBox(self):
        """Create box to group radio buttons
        """
        self.speed_selection_group = QGroupBox('Speed')
        self.button_layout = QHBoxLayout()
        self.speed_selection_group.setLayout(self.button_layout)

        self.speed_group.setExclusive(True)

        self.speed_group.addButton(self.slow_speed_btn)
        self.speed_group.addButton(self.fast_speed_btn)

        self.button_layout.addWidget(self.slow_speed_btn)
        self.button_layout.addWidget(self.fast_speed_btn)

    def createRadioButtons(self):
        """Create radio buttons for speed selection
        """
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
        """Create go button
        """
        self.go_btn = QPushButton('Go')
        self.go_btn.setStyleSheet('padding:15px')
        self.go_btn.setToolTip('Go to absolute position')
        self.go_btn.setMaximumWidth(150)
        self.go_btn.clicked.connect(self.getInputPosition)

    def createUnitLabel(self):
        """Create unit label (um)
        """
        micron_label = QLabel('um')
        micron_label.setFont(QFont('Helvetica', 14))
        micron_label.setStyleSheet('padding:2px')
        return micron_label

    def createAxisLabel(self, axis: str):
        """Create axis label
        """
        axis_label = QLabel(axis)
        axis_label.setFont(QFont('Helvetica', 18, QFont.Bold))
        axis_label.setStyleSheet('padding:5px')
        return axis_label

    @Slot(list, float, list, int)
    def getInputPosition(self):
        """Get the input position
        """
        xcoord = self.goto_x.text()
        try:
            self.submitGoTo.emit([self.axes[0]], 0, [float(xcoord)], 0)
        except ValueError:
            logger.error('Invalid input for X coordinate')
            pass
        self.close()

    def getToggledButton(self):
        """Get the toggled radio button
        """
        toggled_radio = self.sender()
        self.speed = toggled_radio.speed
        self.setToggledSpeed()

    @Slot(list, int, int)
    def setToggledSpeed(self):
        """Set the speed to whichever one was selected
        """
        if self.speed == 'slow':
            logger.info('Setting velocity to 5 (1.5 um/s)')
            # vel = 6 --> 3 um/s, 0.002630 rps
            # vel = 5 --> 1.5 um/s, 0.001280 rps
            velocity = 6
        elif self.speed == 'fast':
            logger.info('Setting velocity to 7 (6 um/s)')
            velocity = 7  # 6 um/s, 0.005070 rps

        self.submitSpeed.emit([self.axes[0]], 0, velocity)


class AboutWindow(QWidget):
    """Create a simple About window, for the curious ones
    """
    def __init__(self, style):
        super().__init__()
        self.setFixedSize(275, 175)
        self.setWindowTitle('About')
        self.setStyleSheet(style)
        self.setWindowFlags(Qt.WindowStaysOnTopHint)

        layout = QVBoxLayout()
        self.setLayout(layout)

        label = QLabel(__about__)
        label.setWordWrap(True)
        layout.addWidget(label)

        logger.info('About window created')


class MainWindow(QMainWindow):

    CONFIG = LoadConfig().General()
    PATH = CONFIG['data_path']

    def __init__(self, interface):
        super().__init__()

        self.interface = interface
        self.setupGui()

        logger.info('Main window initialized')

    def __del__(self):
        logger.info('Main window destroyed')

    def setupGui(self):
        icon = QtGui.QIcon(":/icons/LN-icon1.svg")
        self.setWindowIcon(icon)
        self.setWindowTitle('Manipulator GUI')
        self.setMinimumSize(QSize(400, 300))
        self.setMinimumWidth(400)
        self.setFont(QFont('Helvetica', 14))
        # self.setWindowFlags(Qt.WindowStaysOnTopHint)
        self.dark_mode = True

        self.setDisplayMode()

        self.position_panel = PositionPanel(self.interface.manipulator,
                                            self.interface)
        self.cells_panel = CellsPanel(self.position_panel, MainWindow.PATH)
        self.navigation_panel = NavigationPanel(self.interface.manipulator)
        self.controls_panel = ControlsPanel(self.interface.manipulator,
                                            self.position_panel, self.style)

        self.content_layout = QGridLayout()
        self.content_layout.addWidget(self.position_panel, 0, 0)
        self.content_layout.addWidget(self.cells_panel, 0, 1)
        self.content_layout.addWidget(self.navigation_panel, 1, 0)
        self.content_layout.addWidget(self.controls_panel, 1, 1)

        self.setCentralWidget(QWidget())
        self.centralWidget().setLayout(self.content_layout)

        self._createActions()
        self._connectActions()
        self._createMenuBar()

    def setDisplayMode(self):
        self.light_stylesheet = qdarkstyle.load_stylesheet(
            palette=LightPalette)
        self.dark_stylesheet = qdarkstyle.load_stylesheet(qt_api='pyside6')
        if self.dark_mode:
            logger.info('Setting dark mode')
            self.style = self.dark_stylesheet
        else:
            logger.info('Setting light mode')
            self.style = self.light_stylesheet

        self.setStyleSheet(self.style)
        return self.style

    def toggleDarkMode(self):
        self.dark_mode = self.modeAction.isChecked()
        self.setDisplayMode()

    def _createActions(self):
        # File actions
        self.saveAction = QAction('&Save', self)
        self.exitAction = QAction('&Exit', self)

        # View actions
        self.modeAction = QAction('&Dark mode', self, checkable=True)
        self.modeAction.setChecked(True)

        # About actions
        # self.helpAction = QAction('&Help', self)
        self.aboutAction = QAction('&About...', self)

    def _createMenuBar(self):
        menu_bar = QMenuBar(self)
        self.setMenuBar(menu_bar)

        file_menu = menu_bar.addMenu('&File')
        file_menu.addAction(self.saveAction)
        file_menu.addAction(self.exitAction)

        view_menu = menu_bar.addMenu('&View')
        view_menu.addAction(self.modeAction)

        help_menu = menu_bar.addMenu('&Help')
        # help_menu.addAction(self.helpAction)
        help_menu.addAction(self.aboutAction)

    def _connectActions(self):
        self.saveAction.triggered.connect(self.cells_panel.saveTableData)
        self.exitAction.triggered.connect(self.close)

        self.modeAction.triggered.connect(self.toggleDarkMode)

        # self.helpAction.triggered.connect(self.helpContent)
        self.aboutAction.triggered.connect(self.aboutWindowCallback)

    def aboutWindowCallback(self):
        self.about_window = AboutWindow(self.style)
        self.about_window.show()
