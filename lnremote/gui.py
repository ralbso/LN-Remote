""""""
"""
File: d:/GitHub/LN-Remote/gui.py

Created on: 12/01/2022 14:17:02
Author: rmojica
"""

import sys
import time
import configparser
import pathlib

from PySide6 import QtGui, QtWidgets, QtCore
from PySide6.QtCore import QObject, QRect, QSize, QThread, QRunnable, Signal, Slot
from PySide6.QtGui import QFont
from PySide6.QtWidgets import (QApplication, QComboBox, QDialog, QFileDialog,
                             QGridLayout, QGroupBox, QLineEdit, QListView,
                             QListWidget, QMainWindow, QMessageBox,
                             QPushButton, QVBoxLayout, QHBoxLayout, QWidget, QLabel, QFormLayout,
                             QRadioButton, QButtonGroup, QTableWidget, QTableWidgetItem)
from manipulator import LuigsAndNeumannSM10

class GUI(QMainWindow, LuigsAndNeumannSM10):

    config_path = pathlib.Path(__file__).absolute().parent.parent / "config.ini"
    CONFIG = configparser.ConfigParser()
    CONFIG.read(config_path)
    PATH = CONFIG['GUI']['DATA_PATH']
    DEBUG = CONFIG['GUI'].getboolean('DEBUG')

    def __init__(self, connection_type):
        super().__init__()

        # set up GUI
        self.setWindowTitle("Manipulator GUI")
        self.setMinimumSize(QSize(400, 300))
        self.setMinimumWidth(400)
        self.setFont(QFont('Helvetica', 14))

        self.initializeManipulator(connection_type=connection_type)

        self.createGrid()

        if connection_type == 'socket':
            self.positionThread()
        elif connection_type == 'dummy':
            self.updatePositions()

        self.approach_win = None

    def positionThread(self):
        self.thread = QThread()
        self.worker = Worker(lambda: self.updatePositions())
        self.worker.moveToThread(self.thread)

        self.thread.started.connect(self.worker.run)
        self.worker.finished.connect(self.thread.deleteLater)
        self.worker.answer.connect(self.worker.run)
        self.thread.finished.connect(self.thread.deleteLater)

        self.thread.start()
    
    def moveAxesThread(self):
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
        self.main_grid = QGridLayout()
        panel.setLayout(self.main_grid)

        # create panels for GUI
        self.createPositionPanel()
        self.createControlsPanel()
        self.createCellsPanel()

    def createPositionPanel(self):
        position_panel_box = QGroupBox('Position')
        self.main_grid.addWidget(position_panel_box, 0, 0)

        subgrid = QGridLayout()
        position_panel_box.setLayout(subgrid)

        # X POSITION LABEL
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
        subgrid.addWidget(self.read_x, 0, 1, alignment=QtCore.Qt.AlignLeft)
        subgrid.addWidget(micron_label, 0, 2, alignment=QtCore.Qt.AlignLeft)

        # Y POSITION LABEL
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
        subgrid.addWidget(self.read_y, 1, 1, alignment=QtCore.Qt.AlignLeft)
        subgrid.addWidget(micron_label, 1, 2, alignment=QtCore.Qt.AlignLeft)

        # Z POSITION LABEL
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
        subgrid.addWidget(self.read_z, 2, 1, alignment=QtCore.Qt.AlignLeft)
        subgrid.addWidget(micron_label, 2, 2, alignment=QtCore.Qt.AlignLeft)

        # ZERO AXES BUTTON
        self.zero_btn = QPushButton('Zero Axes')
        self.zero_btn.setStyleSheet('padding:20px')
        self.zero_btn.setToolTip('Zero all axes')        
        subgrid.addWidget(self.zero_btn, 3, 1)
        self.zero_btn.clicked.connect(lambda: self.resetAxesZero([1, 2, 3]))

    def createCellsPanel(self):
        cells_panel_box = QGroupBox('Cells')
        self.main_grid.addWidget(cells_panel_box, 0, 1)

        # lay boxes on panel
        grid_layout = QGridLayout()
        cells_panel_box.setLayout(grid_layout)

        # create table
        self.table = QTableWidget()
        grid_layout.addWidget(self.table, 0, 0, 1, 0)

        self.table.setFont(QFont('Helvetica', 10))
        self.table.setColumnCount(2)
        self.table.setHorizontalHeaderLabels(['Pipette', 'Depth'])
        self.table.setSelectionBehavior(QtWidgets.QAbstractItemView.SelectRows)

        header = self.table.horizontalHeader()
        header.setSectionResizeMode(0, QtWidgets.QHeaderView.Stretch)
        header.setSectionResizeMode(1, QtWidgets.QHeaderView.Stretch)

        # ADD PIPETTE BUTTON
        self.add_pipette_btn = QPushButton('Add')
        self.add_pipette_btn.setStyleSheet('padding:20px')
        self.add_pipette_btn.setToolTip('Add row to table')        
        grid_layout.addWidget(self.add_pipette_btn, 1, 0)
        self.add_pipette_btn.clicked.connect(self.addRow)

        # SAVE POSITION BUTTON
        self.save_position_btn = QPushButton('Save Position')
        self.save_position_btn.setStyleSheet('padding:20px')
        self.save_position_btn.setToolTip('Save current position')        
        grid_layout.addWidget(self.save_position_btn, 1, 1)
        self.save_position_btn.clicked.connect(self.addPatchedCell)

    def addRow(self):
        rows = self.table.rowCount()
        self.table.insertRow(rows)

    def addPatchedCell(self):
        current_table_row = self.table.rowCount()
        current_position = self.read_x.text()
        self.table.setItem(current_table_row-1, 1, QTableWidgetItem(current_position))

    def createControlsPanel(self):
        controls_panel_box = QGroupBox('Controls')
        self.main_grid.addWidget(controls_panel_box, 1, 0, 1, 2)

        # lay boxes on panel
        subgrid = QGridLayout()
        controls_panel_box.setLayout(subgrid)

        # STOP ALL AXES BUTTON
        self.stop_movement_x_btn = QPushButton('STOP')
        self.stop_movement_x_btn.setStyleSheet('padding:20px')
        self.stop_movement_x_btn.setToolTip('Immediately stop movement in X axis')
        subgrid.addWidget(self.stop_movement_x_btn, 0, 0)

        # GO TO POSITION BUTTON
        self.goto_btn = QPushButton('Approach')
        self.goto_btn.setStyleSheet('padding:20px')
        self.goto_btn.setToolTip('Go to absolute coordinates')
        subgrid.addWidget(self.goto_btn, 0, 1)

        # EXIT BRAIN BUTTON
        self.exit_brain_btn = QPushButton('Exit Tissue')
        self.exit_brain_btn.setStyleSheet('padding:20px')
        self.exit_brain_btn.setToolTip('Slowly exit tissue to 100 um')
        subgrid.addWidget(self.exit_brain_btn, 1, 0)

        # MOVE AWAY BUTTON
        self.move_away_btn = QPushButton('Move Away')
        self.move_away_btn.setStyleSheet('padding:20px')
        self.move_away_btn.setToolTip('Move stages away from the sample')
        subgrid.addWidget(self.move_away_btn, 1, 1)

        # BUTTON CONNECTIONS
        self.stop_movement_x_btn.clicked.connect(lambda: self.stopAxes([1, 2, 3]))
        self.goto_btn.clicked.connect(self.approachPositionDialog)
        self.exit_brain_btn.clicked.connect(self.exitBrain)
        self.move_away_btn.clicked.connect(self.moveAway)

    def exitBrain(self):
        self.approachAxesPosition(axes=[1], approach_mode=0, positions=[100], speed_mode=0)
    
    def moveAway(self):
        if float(self.read_x.text()) < 100.0:
            result = self.errorDialog('Looks like the pipette is still in the brain.\nAborting command.')
            if result == 524288:
                # first move stage X (1) all the way out
                self.moveAxis(1, 0, 1)
                time.sleep(1)
                self.approachAxesPosition(axes=[2,3], approach_mode=0, positions=[500, 500], speed_mode=1)
            else:
                pass

        else:
            self.moveAxis(1, 1, 1)
            self.approachAxesPosition(axes=[2,3], approach_mode=0, positions=[500, 500], speed_mode=1)

    def updatePositions(self):
        if self.type == 'socket':
            positions = self.readManipulator([1,2,3])

        elif self.type == 'dummy':
            positions = [50, 317, 810]

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
        self.createGrid()
        self.populateGrid()

    def createGrid(self):
        # lay grid on panel
        self.main_grid = QGridLayout()
        self.setLayout(self.main_grid)

    def populateGrid(self):
        micron_label = QLabel('um')
        micron_label.setFont(QFont('Helvetica', 14))
        micron_label.setStyleSheet('padding:2px')

        axis_label = QLabel('X')
        axis_label.setFont(QFont('Helvetica', 18, QFont.Bold))
        axis_label.setStyleSheet('padding:20px')
        self.main_grid.addWidget(axis_label, 0, 0)

        self.goto_x = QLineEdit('')
        self.goto_x.setStyleSheet('padding:20px')
        self.goto_x.setFont(QFont('Helvetica', 16))
        self.goto_x.setToolTip('Position of X Axis')
        self.goto_x.setMaximumWidth(150)
        self.main_grid.addWidget(self.goto_x, 0, 1, alignment=QtCore.Qt.AlignLeft)
        self.main_grid.addWidget(micron_label, 0, 2, alignment=QtCore.Qt.AlignLeft)

        micron_label = QLabel('um')
        micron_label.setFont(QFont('Helvetica', 14))
        micron_label.setStyleSheet('padding:2px')

        speed_selection_group = QGroupBox('Speed')
        self.main_grid.addWidget(speed_selection_group, 1, 1)

        button_layout = QHBoxLayout()
        speed_selection_group.setLayout(button_layout)

        speed_group = QButtonGroup(self.main_grid)
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
        self.main_grid.addWidget(self.go_btn, 2, 1)

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
    mainWin = GUI(connection_type='dummy')
    mainWin.show()
    sys.exit(app.exec())
