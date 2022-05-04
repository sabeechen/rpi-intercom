from encodings import utf_8
import sys
from .install import InstallService
from .devices import Devices
from .config import Config

if __name__ == '__main__':
    if len(sys.argv) > 1 and sys.argv[1] == "install-service":
        InstallService().run()
    elif len(sys.argv) > 1 and sys.argv[1] == "list-devices":
        Devices(Config()).list()
    elif len(sys.argv) > 1 and sys.argv[1] == "list-devices-raw":
        Devices(Config()).list_raw()
    else:
        from .intercom import Intercom
        from .config import Config
        Intercom(Config.fromArgs()).run()
