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
from .server import Server
import aiorun
import logging
from .logger import getLogger
import sys
import asyncio

logger = getLogger(__name__)

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
        self._sound = Sound(self._devices, self._mumble, self._control, config)
        self._server = Server(self._devices, self._shutdown)

    @property
    def controller(self):
        return self._control

    def start(self):
        self._shutdown.start()
        self._control.start()
        self._mumble.start()
        self._devices.start()
        self._sound.start()

    def stop(self):
        self._mumble.stop()
        self._sound.stop()
        self._devices.stop()
        self._control.stop()

    async def run(self):
        try:
            logger.info("Starting up rpi_intercom v" + pkg_resources.get_distribution("rpi_intercom").version)
            self.start()
            signal.signal(signal.SIGQUIT, self._do_shutdown)
            signal.signal(signal.SIGTERM, self._do_shutdown)
            await self._server.start()
            await self._shutdown.wait_for_shutdown()
        except KeyboardInterrupt:
            logger.info("Keyboard interupt")
            self._shutdown.shutdown()
        finally:
            logger.info("Shutting down")
            self.stop()

    def _do_shutdown(self, *args, **kwargs):
        self._shutdown.shutdown()
