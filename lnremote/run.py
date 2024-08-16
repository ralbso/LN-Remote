import sys
from interface import Interface

import logging
from logging.handlers import RotatingFileHandler

root_logger = logging.getLogger()
root_logger.setLevel(logging.DEBUG)

# create formatter
stream_format = logging.Formatter(
    "[%(asctime)s] %(name)s:%(funcName)s:%(lineno)-3d :: "
    "%(levelname)-8s - %(message)s"
)

# create console handler and set level to debug
stream_handler = logging.StreamHandler(sys.stdout)
stream_handler.setLevel(logging.INFO)
stream_handler.setFormatter(stream_format)

# create file handler and set level to debug
file_handler = RotatingFileHandler('interface.log',
                                   maxBytes=int(1.024e6),
                                   backupCount=3)
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(stream_format)

# add handlers to root_logger
root_logger.addHandler(stream_handler)
root_logger.addHandler(file_handler)


def run_lnremote():
    interface = Interface()
    sys.exit(interface.runGui())


if __name__ == '__main__':
    run_lnremote()
