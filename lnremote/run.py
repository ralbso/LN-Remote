""""""
"""
File: d:/GitHub/LN-Remote/lnremote/run.py

Created on: 01/17/2023 21:01:56
Author: rmojica
"""
import sys
from interface import Interface

def main():
    interface = Interface()
    sys.exit(interface.runGui())

if __name__ == '__main__':
    main()