# LN-Remote
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

`LN-Remote` is a remote control for Luigs and Neumann's micromanipulators. It allows the user to interface with the manipulator from a computer to build upon the functionality of the L&N Remote control units. 

## Table of contents
- [Features](#features)
- [Usage](#usage)
- [Requirements](#requirements)
- [Installation](#installation)
- [License](#license)

## Features
- Read the current position of the manipulator
- Gross movement of the manipulator
- Fine, slow traversal to specified depths
- Store pipette depths for each patched cell in a csv file
- Quick action buttons for common tasks, like moving to the surface, moving away from the sample, etc.

## Usage
The software is designed to be used with a Luigs and Neumann manipulator, a L&N control box. A remote control unit (like the SM10<sup>Touch</sup>) is not required, but highly recommended.

LN-Remote can operate using two communication modes: serial and TCP/IP. Depending on your setup, you might want to adjust this in the `config.ini` file, along with the device's `IP` and `PORT` (for TCP/IP) and `SERIAL` number (for serial). Note that the serial mode has not yet been thoroughly tested, and might not work as expected.

To start the software, run the `run.py` script. The [GUI](/doc/_static/LN-Remote.jpg) should open up, and automatically connect to the manipulator. 
- The current positions of the manipulator axes are displayed in the top left corner, in the 'Position' panel. 
- To grossly move the axes, you must first check the 'Enable' button in the 'Navigation' panel. The dropdown menus to the right allow you to set the speed mode and velocity of the axes. Below, the arrow buttons allow you to move the axes in the positive and negative direction, corresponding to the directional buttons in the SM10<sup>Touch</sup> remote control unit.
- To save the current position of the X axis as a patched cell, click the 'Add' button in the 'Cells' panel followed by the 'Store' button. If the 'Cell' checkbox is clicked, the program will automatically add the pipette/cell number to the 'Pipette' column, along with the current depth of the X axis. The 'Pipette' and 'Depth' columns can be edited manually by double-clicking on the fields. If a row was added by mistake, clicking the 'Del' button will remove the last row. Finally, the '+' button increases the pipette number by 1, and the text within the box is editable.
- Some quick actions are laid out in the 'Controls' panel.
  - 'Approach' allows you to specify an absolute depth to move to pipette to, and the 'Retract' button will move the pipette to the surface.
  - 'Move Away' will move the pipette away from the sample. If the pipette is still in the sample, a dialog box will warn you. Clicking 'Proceed anyway', the pipette will first move to the surface, and then move away from the sample.
  - After exchanging the pipette, 'Return' moves it to Y = 0 and Z = 0, without changing the X axis position. This way, we prevent the pipette from crashing onto the sample if there is a misalignment between the sample and the manipulator.

![](/doc/_static/LN-Remote.jpg)

## Requirements
It is written in Python and uses the *PySide6* framework for the GUI. It has been tested on Windows 10 and 11, but should work on Linux and Mac as well.
- Python 3.8 or higher
- PySide6
- PySerial
- qdarkstyle

## Installation
Installation is easy with `conda`:
1. Clone the repository to your local machine, and navigate to the directory.
2. Run `conda env create -n lnremote -f environment.yml` to create a new environment with all the required packages. 
3. Activate the environment with `conda activate lnremote`.
4. Run LN-Remote with `python run.py`.

## License
This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details