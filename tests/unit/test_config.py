import unittest
from lnremote.config_loader import LoadConfig


class TestConnection(unittest.TestCase):

    def __init__(self, methodName: str = "runTest") -> None:
        super().__init__(methodName)
        CONFIG = LoadConfig().Manipulator()
        self.IP = CONFIG['ip']
        self.PORT = int(CONFIG['port'])
        self.SERIAL = CONFIG['serial']
        self.BAUDRATE = int(CONFIG['baudrate'])
        self.CONNECTION = CONFIG['connection'].lower()

    def test_ip_exists(self):
        self.assertEqual(len(self.IP) > 0, True)

    def test_port_exists(self):
        self.assertEqual(self.PORT > 0, True)

    def test_serial_exists(self):
        self.assertEqual(len(self.SERIAL) > 0, True)

    def test_baudrate_exists(self):
        self.assertEqual(self.BAUDRATE > 0, True)

    def test_connection_exists(self):
        self.assertEqual(len(self.CONNECTION) > 0, True)


if __name__ == '__main__':
    unittest.main()
