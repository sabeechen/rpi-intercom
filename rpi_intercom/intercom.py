import signal, os
from threading import Event
from time import sleep
from .control import Control
from .config import Config
from .sound  import Sound
from .mumble import Mumble
from .devices import Devices
from .echotest import EchoTest


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
        self._config = config
        self._wait_forever = Event()
        self._control = Control(config)
        self._devices = Devices(self._config)
        self._mumble = Mumble(self._control, config)
        #self.mumble = EchoTest()
        self._sound = Sound(self._devices, self._mumble, self._control, config)

    @property
    def controller(self):
        return self._control

    def start(self):
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
            print("Starting up")
            self.start()
            signal.signal(signal.SIGQUIT, self._signal_handler)
            signal.signal(signal.SIGTERM, self._signal_handler)
            if self._config.restart_seconds > 0:
                print(f"I will shut down in {self._config.restart_seconds} seconds")
                self._wait_forever.wait(timeout=self._config.restart_seconds)
            else:
                self._wait_forever.wait()
        except TimeoutError:
            # normal, just restart like normal
            print("Shutting down due to the configured timeout")
            pass
        except KeyboardInterrupt:
            pass
        finally:
            print("Shutting down")
            self.stop()

    def _signal_handler(self, signum, frame):
        self._wait_forever.set()
