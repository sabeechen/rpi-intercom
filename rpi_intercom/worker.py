import queue
from threading import Event, Lock, Thread
from .logger import getLogger

logger = getLogger(__name__)

class Worker:
    def __init__(self, name="Worker"):
        self._name = name
        self._queue = queue.Queue()
        self._thread = Thread(target=self._work, name=name, daemon=True)
        self._active = False
        self._wake_event = Event()

    def start(self):
        self._active = True
        self._thread.start()

    def trigger(self):
        self._wake_event.set()

    def stop(self):
        self._active = False

    def submit(self, delay: float, work):
        self._queue.put((delay,work))

    def _work(self):
        while self._active:
            try:
                delay, work = self._queue.get(timeout=1)
                if delay != 0:
                    self._wake_event.wait(delay)
                self._wake_event.clear()
                work()
            except queue.Empty:
                # Queue just times on "get" out to avoid a locked thread
                pass
            except BaseException as e:
                logger.error(f"Worker {self._name} got an exception")
                logger.printException(e)