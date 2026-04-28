import sys
import argparse
from interface import Interface

import logging
from logging.handlers import RotatingFileHandler

root_logger = logging.getLogger()
root_logger.setLevel(logging.DEBUG)

stream_format = logging.Formatter(
    "[%(asctime)s] %(name)s:%(funcName)s:%(lineno)-3d :: "
    "%(levelname)-8s - %(message)s"
)

stream_handler = logging.StreamHandler(sys.stdout)
stream_handler.setLevel(logging.INFO)
stream_handler.setFormatter(stream_format)

file_handler = RotatingFileHandler(
    "interface.log",
    maxBytes=int(1.024e6),
    backupCount=3
)
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(stream_format)

root_logger.addHandler(stream_handler)
root_logger.addHandler(file_handler)


def parse_args(argv=None):
    parser = argparse.ArgumentParser(add_help=True)
    parser.add_argument(
        "--lightweight",
        action="store_true",
        help="Launch GUI with only Position + Controls panels",
    )
    return parser.parse_args(argv)


def run_lnremote(argv=None):
    args = parse_args(argv)
    interface = Interface(lightweight=args.lightweight)
    sys.exit(interface.runGui())


if __name__ == "__main__":
    run_lnremote()