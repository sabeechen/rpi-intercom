from datetime import timedelta
from .config import Config
from threading import Event, Thread
from datetime import datetime, timedelta
from time import sleep
import os
import psutil

class Shutdown():
    def __init__(self, config: Config):
        self._config = config
        self._shutdown_indicator = Event()
        self._shutdown_requested = None
        self._shutdown_thread = Thread(name="Shutdown watcher", daemon=True, target=self.watch_for_shutdown)

    @property
    def shutting_down(self):
        return self._shutdown_indicator.is_set()

    def start(self):
        self._shutdown_thread.start()

    def wait_for_shutdown(self):
        self._shutdown_indicator.wait()

    def shutdown(self):
        print("Shutdown was requested")
        self._shutdown_requested = datetime.utcnow()
        self._shutdown_indicator.set()

    def watch_for_shutdown(self):
        self.wait_for_shutdown()

        # Wait 3 seconds for a clean exit, then exit garcelessly.
        sleep(3)
        print("Things couldn't get cleaned up, exiting gracelessly")
        psutil.Process(os.getpid()).kill()

