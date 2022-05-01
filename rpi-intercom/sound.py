from threading import Lock, Thread
from typing import Dict, List
import queue
from contextlib import contextmanager
from .config import Config
from .mumble import Mumble
from .control import Control
from .devices import Devices
import numpy as np

class Sound():
    '''
    Handles buffering audio between the speaker, microphone, and mumble.  Also mixes audio form Mumble in case there is more than oen speaker
    '''
    def __init__(self, devices: Devices, mumble: Mumble, control: Control, config: Config):
        
        self._audio_data_type = np.dtype(np.int16).newbyteorder('<')
        self._devices = devices
        self._mumble = mumble
        self._control = control
        self._speaker_queue = queue.Queue(maxsize=5)
        self._buffer_lock = Lock()
        self._audio_buffers: Dict[str, bytes] = {}
        self._outgoing_buffer: Dict[str, queue.Queue] = {}
        self._microphone_thread: Thread = None
        self._speaker_thread: Thread = None
        self._mumble._sound_callback = self._play
        self._running = False

    def _microphone_loop(self):
        while(self._running):
            _length, chunk = self._devices.microphone.read()
            self._mumble.transmit(chunk)


    def _speaker_loop(self):
        while(self._running):
            try:
                toMix: List[bytes] = []
                for speaker in self._outgoing_buffer.values():
                    if not speaker.empty():
                        toMix.append(speaker.get())
                if len(toMix) == 0 or self._control.deafened:
                    # There isn't any audio buffered from mumble, so just send
                    # silent audio data to the speaker.
                    self._control.recieving = False
                    chunk = bytes(bytearray(self._devices.frame_length))
                    self._devices.speaker.write(chunk)
                else:
                    mixed = toMix[0]
                    # Only go through the overhead of mixing audio if 
                    # there is more than one source to deal with.
                    if len(toMix) > 1:
                        mixed = self._mix(toMix)
                    self._control.recieving = True
                    self._devices.speaker.write(mixed)
            except Exception as e:
                print(e)
                self._control.recieving = False
                chunk = bytes(bytearray(self._devices.frame_length))
                self._devices.speaker.write(chunk)
            

    def _mix(self, sources: List[bytes]):
        """
        This implements a very simple and widely recognized mixing method that also
        doesn't seem to have a name.  Two sources A and B get mixed together 
        into output M such that:
        M[i] = A[i] + B[i] - (A[i] * B[i])

        Additional sources get added in by iteratively substituting M for A (eg a reudction).
        I don't really know why this works or how it keeps the audio stable, but it seems to
        perform pretty well.  There is no way to mix audio without losing fidelity.
        """
        current = np.zeros(self._devices.chunk_size)
        for raw_data in sources:
            # This algorithm only works for floats in the range (-1, 1), so first convert mumble's
            # 16 bit PCM into that format.
            source = np.frombuffer(raw_data, dtype=self._audio_data_type).astype(float) / 32768

            # Then mix them together as described above
            current = current + source - (current * source)
        # Convert back into 16bit PCM
        current = (current * 32768).astype(self._audio_data_type)
        return current.tobytes()

    def start(self):
        '''
        Start sending and recieving data from the speaker/microphone.
        '''
        self._running = True
        if self._devices.microphone is not None:
            self._microphone_thread = Thread(target=self._microphone_loop, name="Microphone Thread", daemon=True)
            self._microphone_thread.start()
        if self._devices.speaker is not None:
            self._speaker_thread = Thread(target=self._speaker_loop, name="Speaker Thread", daemon=True)
            self._speaker_thread.start()

    def stop(self):
        '''
        Stop sending and recieving audio data from the speakers/microphone, and cleanup any used resources.
        '''
        self._running = False
        if self._microphone_thread is not None:
            self._microphone_thread.join()
            self._microphone_thread = None
        if self._speaker_thread is not None:
            self._speaker_thread.join()
            self._speaker_thread = None
        

    def _play(self, user, frame):
        '''
        Buffer audio data (eg from mumble) to be played locally
        '''
        if self._control.deafened:
            return

        # Keep track of audio chunks recieved per user so we can mix together 
        # audio sources later if necessary
        name = user['name']
        if name not in self._audio_buffers:
            self._audio_buffers[name] = b''
            self._outgoing_buffer[name] = queue.Queue(maxsize=5)

        with self._buffer_lock:
            self._audio_buffers[name] += frame
            outgoing = self._outgoing_buffer[name]

            # Data recieved from mumble doesn't necessarily align with the speaker's 
            # configured chunk size,  so we break it up as it arrives into FRAME_LENGTH
            # size peices.
            while len(self._audio_buffers[name]) > self._devices.frame_length:
                if outgoing.full():
                    outgoing.get()
                outgoing.put(self._audio_buffers[name][0:self._devices.frame_length])
                self._audio_buffers[name] = self._audio_buffers[name][self._devices.frame_length:]
