""""""
"""
File: d:/GitHub/LN-Remote/lnremote/config_loader.py

Created on: 01/17/2023 14:31:51
Author: rmojica
"""
import pathlib
import configparser

class LoadConfig:
    def __init__(self):
        config_path = pathlib.Path(__file__).absolute().parent.parent / 'config.ini'
        self.config = configparser.ConfigParser()
        self.config.read(config_path)

    def Gui(self):
        # GUI SETTINGS
        return self.config._sections['GUI']

    def Manipulator(self):
        # MANIPULATOR SETTINGS
        return self.config._sections['MANIPULATOR']

if __name__ == "__main__":
    conf = LoadConfig().MANIPULATOR()
    print(conf)
