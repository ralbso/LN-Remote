import unittest
from unittest.mock import patch, MagicMock
import socket
from lnremote.devices import LNSM10


class TestConnection(unittest.TestCase):

    def __init__(self, methodName: str = "runTest") -> None:
        super().__init__(methodName)

    @patch('socket.socket')
    def test_mock_connection(self, mock_socket):
        # Arrange
        mock_socket_instance = MagicMock()
        mock_socket.return_value = mock_socket_instance

        # Act
        lnsm10 = LNSM10()
        lnsm10_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        lnsm10_socket.connect((lnsm10.IP, 12345))

        # Assert
        mock_socket_instance.connect.assert_called_with((lnsm10.IP, 12345))
        lnsm10_socket.close()

    def test_real_connection(self):
        # Arrange
        lnsm10 = LNSM10()
        lnsm10_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)

        # Act
        lnsm10_socket.settimeout(2)
        lnsm10_socket.connect((lnsm10.IP, lnsm10.PORT))

        # Assert
        self.assertTrue(lnsm10_socket.fileno() != -1)

        # Clean up
        lnsm10_socket.close()


if __name__ == '__main__':
    unittest.main()
