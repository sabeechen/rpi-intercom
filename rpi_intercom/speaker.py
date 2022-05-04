import datetime
from threading import Lock
from .circular_buffer import Buffer
import numpy as np

class Speaker:
    """Represents a speaker, as in a channel of audio from one person on Mumble"""
    def __init__(self, name: str, max_buffer, ideal_buffer):
        self._name = name
        self._buffer = Buffer(max_buffer)
        self._lock = Lock()
        self._ideal_buffer = ideal_buffer
        self._missed = True
        self._started_talking = False
        self._audio_data_type = np.dtype(np.int16).newbyteorder('<')

    def buffer(self, data: bytes):
        with self._lock:
            # Convert 16 bit int data to floats in the range (-1, 1)
            self._buffer.push(np.frombuffer(data, dtype=self._audio_data_type).astype(float) / 32768)
            if self._buffer.length >= self._ideal_buffer:
                self._missed = False

    def read(self, size):
        with self._lock:
            if not self._missed and self._buffer.length > 0:
                if not self._started_talking:
                    print(f"{self._name} started talking")
                    self._started_talking = True
                ret = self._buffer.pop(size)
                if len(ret) < size:
                    ret = np.concatenate((ret, np.zeros(size - len(ret))), axis=None)
                return ret
            if not self._missed:
                print(f"{self._name} stopped talking")
            self._missed = True
            self._started_talking = False
            return None