import signal, os
import pkg_resources
from threading import Event
from time import sleep
from .control import Control
from .config import Config
from .sound  import Sound
from .mumble import Mumble
from .devices import Devices
from .echotest import EchoTest
from .shutdown import Shutdown


class Intercom:
    '''
    The primary class for runnign an intercom.  It listens on the default recording device 
    for audio to send to mumble server and play any audio recieved on the default playback
    device.  Simply calling run() will start the intercom and block indefinitely while
    listening for process signals to stop, as would be approriate for a runnign this as a
    service.  You may instead call start() and stop() to asynchronously run the intercom
    in the background while your script does something else.  Accessing the 'controller'
    property gives access to an object the manages the intercom's behavior such as 
    to start/stop playback, mute, or defen.
    '''
    def __init__(self, config: Config):
        self._shutdown = Shutdown(config)
        self._config = config
        self._wait_forever = Event()
        self._control = Control(config)
        self._devices = Devices(self._config, self._shutdown)
        self._mumble = Mumble(self._control, config)
        #self.mumble = EchoTest()
        self._sound = Sound(self._devices, self._mumble, self._control, config)

    @property
    def controller(self):
        return self._control

    def start(self):
        self._shutdown.start()
        self._control.start()
        self._devices.start()
        self._mumble.start()
        self._sound.start()

    def stop(self):
        self._mumble.stop()
        self._sound.stop()
        self._devices.stop()
        self._control.stop()

    def run(self):
        try:
            print("Starting up rpi_intercom v" + pkg_resources.get_distribution("rpi_intercom").version)
            self.start()
            signal.signal(signal.SIGQUIT, self._shutdown.shutdown)
            signal.signal(signal.SIGTERM, self._shutdown.shutdown)
            self._shutdown.wait_for_shutdown()
        except KeyboardInterrupt:
            print("Keyboard interupt")
            self._shutdown.shutdown()
        finally:
            print("Shutting down")
            self.stop()
