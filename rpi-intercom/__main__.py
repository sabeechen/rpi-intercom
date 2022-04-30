from encodings import utf_8
import sys
from .install import InstallService
from .devices import Devices

if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == "install-service":
        InstallService().run()
    elif len(sys.argv) > 1 and sys.argv[1] == "list-devices":
        Devices().list()
    else:
        from .intercom import Intercom
        from .config import Config
        Intercom(Config.fromArgs()).run()
