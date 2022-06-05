from datetime import timedelta
from .config import Config
from threading import Thread
from datetime import datetime, timedelta
from time import sleep
import os
import psutil
import asyncio
from .logger import getLogger

logger = getLogger(__name__)

class Shutdown():
    def __init__(self, config: Config):
        self._config = config
        self._shutdown_indicator = None
        self._shutdown_requested = None
        self._shutdown_taks = None

    @property
    def shutting_down(self):
        return self._shutdown_indicator.is_set()

    def start(self):
        self._shutdown_task = asyncio.create_task(self.watch_for_shutdown())
        self._shutdown_indicator = asyncio.Event()

    async def wait_for_shutdown(self):
        await self._shutdown_indicator.wait()

    def shutdown(self):
        logger.info("Shutdown was requested")
        self._shutdown_requested = datetime.utcnow()
        self._shutdown_indicator.set()

    async def watch_for_shutdown(self):
        await self.wait_for_shutdown()
        # Wait some time for a clean exit, then exit full stop.
        await asyncio.sleep(10)
        logger.error("Things couldn't get cleaned up, exiting gracelessly")
        psutil.Process(os.getpid()).kill()

