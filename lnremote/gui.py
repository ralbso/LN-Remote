import csv
import datetime
import logging
import time
from pathlib import Path
import resources

import numpy
import qdarkstyle
from __init__ import __about__
from config_loader import LoadConfig
import configparser
from PySide6 import QtCore, QtGui, QtWidgets
from PySide6.QtCore import QSize, Qt, Signal, Slot
from PySide6.QtGui import QAction, QFont
from PySide6.QtWidgets import (QButtonGroup, QCheckBox, QComboBox, QGridLayout,
                               QGroupBox, QHBoxLayout, QLabel, QLineEdit,
                               QMainWindow, QMenuBar, QMessageBox, QPushButton,
                               QRadioButton, QTableWidget, QTableWidgetItem,
                               QVBoxLayout, QWidget, QSpinBox, QFrame)
from qdarkstyle.light.palette import LightPalette

# create logger
logger = logging.getLogger(__name__)


class SelectedAxes():
    def __init__(self):
        self.selected = [1, 2, 3]


class PositionPanel(QGroupBox):
    """Create the position panel, which contains the live position read-out
    from the manipulator, the Zero Axes button and the Stop button
    """
    def __init__(self, manipulator, axes):
        super().__init__("Position", parent=None)
        self.manipulator = manipulator

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
        self.zero_btn = QPushButton('ZERO ALL')
        self.zero_btn.setStyleSheet('padding:15px')
        self.zero_btn.setToolTip('Zero all axes')
        self.zero_btn.clicked.connect(
            lambda: self.manipulator.resetAxesZero())

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
    def __init__(self, manipulator, axes):
        super().__init__('Navigation')
        self.manipulator = manipulator
        self.AXES = axes

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
            logger.info('Enabling navigation buttons')
            self.navigation_speed_dropdown.setEnabled(True)
            self.navigation_velocity_dropdown.setEnabled(True)
            self.navigate_x_in_btn.setEnabled(True)
            self.navigate_x_out_btn.setEnabled(True)
            self.navigate_y_fwd_btn.setEnabled(True)
            self.navigate_y_bwd_btn.setEnabled(True)
            self.navigate_z_up_btn.setEnabled(True)
            self.navigate_z_down_btn.setEnabled(True)

            self.setMovementParameters(self.AXES.selected, self.speed_mode,
                                       self.velocity)
        else:
            logger.info('Disabling navigation buttons')
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
        self.setMovementParameters(self.AXES.selected, self.speed_mode,
                                   self.velocity)

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
        self.setMovementParameters(self.AXES.selected, self.speed_mode,
                                   self.velocity)

    def createNavigateXInButton(self):
        """Create button to move X in
        """
        icon = QtGui.QIcon(":/icons/circle-left-yellow.svg")
        self.navigate_x_in_btn = QPushButton()
        self.navigate_x_in_btn.setIcon(icon)
        self.navigate_x_in_btn.setStyleSheet('padding:10px')

        ax = 0
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

        ax = 0
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

        ax = 1
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

        ax = 1
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

        ax = 2
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

        ax = 2
        self.navigate_z_down_btn.pressed.connect(
            lambda: self.onPress(ax, self.speed_mode, -1))
        self.navigate_z_down_btn.released.connect(lambda: self.onRelease(ax))

    def onPress(self, axis, speed_mode, direction, velocity=None):
        """If button is pressed, move the `axis` at the specified `speed_mod`
        towards `direction`
        """
        ax_to_move = self.AXES.selected[axis]
        self.manipulator.moveAxis(ax_to_move, speed_mode, direction, velocity)

    def onRelease(self, axis):
        """If button is released, stop the `axis`
        """
        ax_to_stop = self.AXES.selected[axis]
        self.manipulator.stopMovement(ax_to_stop)

    def setMovementParameters(self, axis, speed_mode, velocity):
        """Set the selected movement parameters for each axis
        """
        logger.info('Setting default movement parameters')
        for axis in self.AXES.selected:
            self.manipulator.setMovementVelocity(axis, speed_mode, velocity)


class ControlsPanel(QGroupBox):
    """Create the controls panel, which contains all other manipulator
    controls, with a focus on automation.
    """
    def __init__(self, manipulator, position_panel, style, axes):
        super().__init__('Controls')

        self.manipulator = manipulator
        self.position_panel = position_panel
        self.approach_win = None
        self.style = style

        self.AXES = axes

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

    def createApproachButton(self):
        """Create approach button, which opens the approach position dialog
        """
        self.approach_btn = QPushButton('Approach')
        self.approach_btn.setStyleSheet('padding:15px')
        self.approach_btn.setToolTip('Go to absolute coordinates')
        self.approach_btn.clicked.connect(self.openApproachWindow)

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
            # self._current_unit = 1
            self.AXES.selected = [1, 2, 3]
            self.move_away_btn.setEnabled(True)
            self.return_btn.setEnabled(True)
        else:
            # self._current_unit = 2
            self.AXES.selected = [7, 8, 9]
            self.move_away_btn.setEnabled(False)
            self.return_btn.setEnabled(False)

        # self.manipulator.setUnit(self._current_unit)
        self.manipulator.setCurrentAxes(self.AXES.selected)

    def openApproachWindow(self):
        """Open approach position window
        """
        main_window = self.window()
        style, dark_mode = main_window.getCurrentStyle()

        # create window with current style
        self.approach_win = ApproachWindow(style, dark_mode, self.AXES.selected)

        # register with main window for style updates
        main_window.registerChildWindow(self.approach_win)

        # connect cleanup on close
        self.approach_win.destroyed.connect(
            lambda: main_window.unregisterChildWindow(self.approach_win)
        )

        # connect signals
        self.approach_win.submitGoTo.connect(self.manipulator.approachAxesPosition)
        self.approach_win.submitSpeed.connect(self.manipulator.setPositioningVelocity)
        self.approach_win.show()

    # def approachPositionDialog(self):
    #     """Open approach position dialog
    #     """
    #     if self.approach_win is None:
    #         self.approach_win = ApproachWindow(self.style, self.AXES.selected)

    #     self.approach_win.submitGoTo.connect(
    #         self.manipulator.approachAxesPosition)
    #     self.approach_win.submitSpeed.connect(
    #         self.manipulator.setPositioningVelocity)
        
    #     self.approach_win.show()

    def exitBrain(self):
        """Slowly exit tissue to a safe distance (100 um away from the tissue)
        """
        logger.info('Exiting brain, moving to 100 um')
        if self.AXES.selected == [7, 8, 9]:
            msg = 'Retracting LFP probe. Are you sure?'
            result = self.confirmDialog(msg)
            if result == 1024:
                self.manipulator.approachAxesPosition(
                    axes=[self.AXES.selected[0]],
                    approach_mode=0,
                    positions=[100, 100],
                    speed_mode=0)
        else:
            self.manipulator.approachAxesPosition(axes=[self.AXES.selected[0]],
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
                        axes=[self.AXES.selected[1:3]],
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
                axes=[self.AXES.selected[1:3]],
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
                axes=[self.AXES.selected[1:3]],
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

    def confirmDialog(self, message):
        """Generate confirmation dialog to notify user of a problem

        Parameters
        ----------
        message : str
            Message to display on dialog box
        """
        logger.info(message)

        confirm_box = QMessageBox()
        confirm_box.setIcon(QMessageBox.Information)
        confirm_box.setWindowTitle('Moving LFP')
        confirm_box.setText(message)
        confirm_box.setStandardButtons(QMessageBox.Ok | QMessageBox.Cancel)
        confirm_box.setDefaultButton(QMessageBox.Cancel)

        return confirm_box.exec()


class ApproachWindow(QWidget):
    """Create window that allows the user to navigate to a specific
    X coordinate.
    """

    submitGoTo = Signal(list, float, list, int)
    submitSpeed = Signal(list, int, int)

    def __init__(self, style, dark_mode, axes):
        super().__init__()
        self.setWindowTitle('Approach')
        self.setWindowFlags(Qt.WindowStaysOnTopHint)

        self.axes = axes
        self.dark_mode = dark_mode

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

    @Slot(str, bool)
    def updateStyle(self, style, dark_mode):
        """Update window style
        """
        self.setStyleSheet(style)
        self.dark_mode = dark_mode

    def closeEvent(self, event):
        """Handle window close event"""
        event.accept()

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
    def __init__(self, style, dark_mode):
        super().__init__()
        self.setFixedSize(275, 175)
        self.setWindowTitle('About')
        self.setStyleSheet(style)
        self.setWindowFlags(Qt.WindowStaysOnTopHint)
        self.dark_mode = dark_mode

        layout = QVBoxLayout()
        self.setLayout(layout)

        label = QLabel(__about__)
        label.setWordWrap(True)
        layout.addWidget(label)

        logger.info('About window created')

    @Slot(str, bool)
    def updateStyle(self, style, dark_mode):
        """Update window style
        """
        self.setStyleSheet(style)
        self.dark_mode = dark_mode


class SettingsWindow(QWidget):
    """Settings window for configuration options
    """

    # signal to notify when settings are saved
    settingsSaved = Signal()

    def __init__(self, style, dark_mode):
        super().__init__()
        self.setWindowTitle('Settings')
        self.setWindowFlags(Qt.WindowStaysOnTopHint)
        self.setStyleSheet(style)
        self.setMinimumSize(QSize(400, 200))
        self.dark_mode = dark_mode

        self.config_loader = LoadConfig()
        self.config_path = Path(__file__).absolute().parent.parent / 'config.ini'

        # main layout
        main_layout = QVBoxLayout()
        self.setLayout(main_layout)

        # create tab widget for different settings categories
        self.tabs = QtWidgets.QTabWidget()
        main_layout.addWidget(self.tabs)

        # create tabs
        self.createGeneralTab()
        self.createManipulatorTab()

        # add a separator line
        separator = QFrame()
        separator.setFrameShape(QFrame.HLine)
        separator.setFrameShadow(QFrame.Sunken)
        main_layout.addWidget(separator)

        # button layout
        button_widget = QWidget()
        button_layout = QHBoxLayout()
        button_widget.setLayout(button_layout)
        button_widget.setFixedHeight(50)

        # create buttons with explicity styling
        self.save_btn = QPushButton('Save')
        self.save_btn.setMinimumWidth(100)
        self.save_btn.setStyleSheet('padding: 8px;')

        self.apply_btn = QPushButton('Apply')
        self.apply_btn.setMinimumWidth(100)
        self.apply_btn.setStyleSheet('padding: 8px;')

        self.cancel_btn = QPushButton('Cancel')
        self.cancel_btn.setMinimumWidth(100)
        self.cancel_btn.setStyleSheet('padding: 8px;')

        self.save_btn.clicked.connect(self.saveAndClose)
        self.cancel_btn.clicked.connect(self.close)
        self.apply_btn.clicked.connect(self.applySettings)

        button_layout.addStretch()
        button_layout.addWidget(self.save_btn)
        button_layout.addWidget(self.apply_btn)
        button_layout.addWidget(self.cancel_btn)

        main_layout.addWidget(button_widget, 0)

        logger.info('Settings window created')

    def createGeneralTab(self):
        """Create the General settings tab
        """
        general_widget = QWidget()
        general_layout = QGridLayout()
        general_widget.setLayout(general_layout)

        # load current settings
        general_config = self.config_loader.General()

        # data path setting
        row = 0
        general_layout.addWidget(QLabel('Data Path:'), row, 0)
        self.data_path_edit = QLineEdit(general_config.get('data_path', ''))
        self.data_path_edit.setToolTip('Directory where data will be saved')
        general_layout.addWidget(self.data_path_edit, row, 1)

        browse_btn = QPushButton('Browse...')
        browse_btn.setMaximumWidth(100)
        browse_btn.clicked.connect(self.browsePath)
        general_layout.addWidget(browse_btn, row, 2)

        row += 1
        general_layout.addWidget(QLabel('GUI Settings:'), row, 0, 1, 3)

        row += 1
        self.dark_mode_checkbox = QCheckBox('Enable Dark Mode')
        self.dark_mode_checkbox.setChecked(general_config.get('dark_mode', 'True').lower() == 'true')
        general_layout.addWidget(self.dark_mode_checkbox, row, 1)

        # add spacer to push everything to top
        general_layout.setRowStretch(row + 1, 1)

        self.tabs.addTab(general_widget, 'General')

    def createManipulatorTab(self):
        """Create the Manipulator settings tab
        """
        manipulator_widget = QWidget()
        manipulator_layout = QGridLayout()
        manipulator_widget.setLayout(manipulator_layout)

        # load current settings
        manipulator_config = self.config_loader.Manipulator()

        row = 0

        # connection type
        manipulator_layout.addWidget(QLabel('Connection Type:'), row, 0)
        self.connection_combo = QComboBox()
        self.connection_combo.addItems(['Ethernet', 'USB', 'Demo'])
        current_connection = manipulator_config.get('connection', 'Ethernet').lower()
        self.connection_combo.setCurrentText(current_connection.capitalize())
        self.connection_combo.currentTextChanged.connect(self.onConnectionChanged)
        manipulator_layout.addWidget(self.connection_combo, row, 1)

        row += 1
        manipulator_layout.addWidget(QLabel(''), row, 0)  # spacer

        # serial settings group
        row += 1
        serial_label = QLabel('Serial Settings:')
        serial_label.setStyleSheet('font-weight: bold;')
        manipulator_layout.addWidget(serial_label, row, 0, 1, 2)

        row += 1
        manipulator_layout.addWidget(QLabel('Serial Port:'), row, 0)
        self.serial_edit = QLineEdit(manipulator_config.get('serial_port', ''))
        self.serial_edit.setToolTip('Serial port for the manipulator')
        manipulator_layout.addWidget(self.serial_edit, row, 1)

        row += 1
        manipulator_layout.addWidget(QLabel('Baud Rate:'), row, 0)
        self.baudrate_combo = QComboBox()
        self.baudrate_combo.addItems(['9600', '19200', '38400', '57600', '115200'])
        self.baudrate_combo.setCurrentText(str(manipulator_config.get('baudrate', '115200')))
        self.baudrate_combo.setEditable(True)
        manipulator_layout.addWidget(self.baudrate_combo, row, 1)

        row += 1
        manipulator_layout.addWidget(QLabel(''), row, 0)  # spacer

        # network settings group
        row += 1
        network_label = QLabel('Network Settings:')
        network_label.setStyleSheet('font-weight: bold;')
        manipulator_layout.addWidget(network_label, row, 0, 1, 2)

        row += 1
        manipulator_layout.addWidget(QLabel('IP Address:'), row, 0)
        self.ip_edit = QLineEdit(manipulator_config.get('ip', '192.168.178.30'))
        self.ip_edit.setToolTip('IP address for network connection')
        manipulator_layout.addWidget(self.ip_edit, row, 1)

        row += 1
        manipulator_layout.addWidget(QLabel('Port:'), row, 0)
        self.port_spin = QSpinBox()
        self.port_spin.setRange(1, 65535)
        self.port_spin.setValue(int(manipulator_config.get('port', '1001')))
        self.port_spin.setToolTip('Port number for network connection')
        manipulator_layout.addWidget(self.port_spin, row, 1)

        # enable/disable fields based on connection type
        self.onConnectionChanged(current_connection)

        # add spacer to push everything to top
        manipulator_layout.setRowStretch(row + 1, 1)

        self.tabs.addTab(manipulator_widget, 'Manipulator')

    @Slot(str, bool)
    def updateStyle(self, style, dark_mode):
        """Update window style
        """
        self.setStyleSheet(style)
        self.dark_mode = dark_mode

    def onConnectionChanged(self, connection_type):
        """Enable/disable fields based on connection type
        """
        is_serial = connection_type.lower() == 'usb'
        is_network = connection_type.lower() == 'ethernet'

        self.serial_edit.setEnabled(is_serial)
        self.baudrate_combo.setEnabled(is_serial)
        self.ip_edit.setEnabled(is_network)
        self.port_spin.setEnabled(is_network)

    def browsePath(self):
        """Open file browser to select data path
        """
        from PySide6.QtWidgets import QFileDialog

        directory = QFileDialog.getExistingDirectory(
            self,
            "Select data directory",
            self.data_path_edit.text()
        )

        if directory:
            self.data_path_edit.setText(directory)

    def applySettings(self):
        """Apply settings without closing the window
        """
        try:
            # read the config file
            config = configparser.ConfigParser()
            config.read(self.config_path)

            # update GENERAL section
            if not config.has_section('GENERAL'):
                config.add_section('GENERAL')

            config.set('GENERAL', 'data_path', self.data_path_edit.text())
            config.set('GENERAL', 'dark_mode', str(self.dark_mode_checkbox.isChecked()))

            # update MANIPULATOR section
            if not config.has_section('MANIPULATOR'):
                config.add_section('MANIPULATOR')

            config.set('MANIPULATOR', 'connection', self.connection_combo.currentText())
            config.set('MANIPULATOR', 'serial_port', self.serial_edit.text())
            config.set('MANIPULATOR', 'baudrate', self.baudrate_combo.currentText())
            config.set('MANIPULATOR', 'ip', self.ip_edit.text())
            config.set('MANIPULATOR', 'port', str(self.port_spin.value()))

            # write to config file
            with open(self.config_path, 'w') as configfile:
                config.write(configfile)

            logger.info('Settings saved successfully')

            # show confirmation
            msg = QMessageBox()
            msg.setIcon(QMessageBox.Information)
            msg.setWindowTitle('Settings Saved')
            msg.setText('Settings have been saved successfully.')
            msg.setStandardButtons(QMessageBox.Ok)
            msg.setWindowFlags(Qt.WindowStaysOnTopHint)
            msg.exec()

            # emit signal
            self.settingsSaved.emit()

            return True
        
        except Exception as e:
            logger.error(f'Error saving settings: {e}')

            msg = QMessageBox()
            msg.setIcon(QMessageBox.Critical)
            msg.setWindowTitle('Error')
            msg.setText(f'Failed to save settings:\n{e}')
            msg.setStandardButtons(QMessageBox.Ok)
            msg.exec()

            return False
        
    def saveAndClose(self):
        """Save settings and close the window
        """
        if self.applySettings():
            self.close()

    def closeEvent(self, event):
        """Handle window close event
        """
        logger.info('Settings window closed')
        event.accept()


class MainWindow(QMainWindow):

    CONFIG = LoadConfig().General()
    PATH = CONFIG['data_path']

    # signal to notify when stylesheet or dark mode changes
    styleChanged = Signal(str, bool)  # stylesheet, dark_mode

    def __init__(self, interface):
        super().__init__()

        self.manipulator = interface.manipulator
        self.axes = SelectedAxes()

        # track child windows
        self.child_windows = []

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

        self.position_panel = PositionPanel(self.manipulator, self.axes)
        self.cells_panel = CellsPanel(self.position_panel, MainWindow.PATH)
        self.navigation_panel = NavigationPanel(self.manipulator,
                                                self.axes)
        self.controls_panel = ControlsPanel(self.manipulator,
                                            self.position_panel, self.style,
                                            self.dark_mode, self.axes)

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

        # emit signal to update all child windows
        self.styleChanged.emit(self.style, self.dark_mode)

        return self.style

    def toggleDarkMode(self):
        self.dark_mode = self.modeAction.isChecked()
        self.setDisplayMode()

        if hasattr(self, 'controls_panel'):
            self.controls_panel.dark_mode = self.dark_mode

        logger.info(f'Dark mode set to {self.dark_mode}')

    def registerChildWindow(self, window):
        """Register a child window to receive style updates
        """
        self.child_windows.append(window)

        # connect to style changes
        self.styleChanged.connect(window.updateStyle)
        
        logger.info(f'Registered child window: {window.windowTitle()}')

    def unregisterChildWindow(self, window):
        """Unregister a child window
        """
        if window in self.child_windows:
            self.child_windows.remove(window)
            try:
                self.styleChanged.disconnect(window.updateStyle)
            except Exception as e:
                pass
            logger.info(f'Unregistered child window: {window.windowTitle()}')

    def getCurrentStyle(self):
        """Get the current style and dark mode setting
        """
        return self.style, self.dark_mode

    def _createActions(self):
        # File actions
        self.saveAction = QAction('&Save', self)
        self.settingsAction = QAction('Se%ttings...', self)
        self.exitAction = QAction('&Exit', self)

        # View actions
        self.modeAction = QAction('&Dark mode', self, checkable=True)
        self.modeAction.setChecked(True)

        # About actions
        # help action not yet defined, but will link to help documentation
        # self.helpAction = QAction('&Help', self)
        self.aboutAction = QAction('&About...', self)

    def _createMenuBar(self):
        menu_bar = QMenuBar(self)
        self.setMenuBar(menu_bar)

        file_menu = menu_bar.addMenu('&File')
        file_menu.addAction(self.saveAction)
        file_menu.addAction(self.settingsAction)
        file_menu.addSeparator()
        file_menu.addAction(self.exitAction)

        view_menu = menu_bar.addMenu('&View')
        view_menu.addAction(self.modeAction)

        help_menu = menu_bar.addMenu('&Help')
        # help_menu.addAction(self.helpAction)
        help_menu.addAction(self.aboutAction)

    def _connectActions(self):
        self.saveAction.triggered.connect(self.cells_panel.saveTableData)
        self.settingsAction.triggered.connect(self.openSettingsWindow)
        self.exitAction.triggered.connect(self.close)

        self.modeAction.triggered.connect(self.toggleDarkMode)

        # self.helpAction.triggered.connect(self.helpContent)
        self.aboutAction.triggered.connect(self.aboutWindowCallback)

    def aboutWindowCallback(self):
        self.about_window = AboutWindow(self.style, self.dark_mode)
        self.registerChildWindow(self.about_window)
        self.about_window.destroyed.connect(
            lambda: self.unregisterChildWindow(self.about_window)
        )
        self.about_window.show()
        logger.info('About window opened')
    
    def openSettingsWindow(self):
        """Open settings window
        """
        self.settings_window = SettingsWindow(self.style, self.dark_mode)
        self.registerChildWindow(self.settings_window)
        self.settings_window.destroyed.connect(
            lambda: self.unregisterChildWindow(self.settings_window)
        )
        self.settings_window.show()
        logger.info('Settings window opened')
