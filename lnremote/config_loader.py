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
