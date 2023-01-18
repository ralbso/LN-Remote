import sys
from interface import Interface

def main():
    interface = Interface()
    sys.exit(interface.runGui())

if __name__ == '__main__':
    main()