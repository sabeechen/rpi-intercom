from threading import Lock
from typing import Dict, List
import pyaudio
import queue
import os
import sys
from contextlib import contextmanager
from .config import Config
from .mumble import Mumble
from .control import Control
import numpy as np

CHUNK = 1024  # Seems like a decent chunk size.  Why not?
FORMAT = pyaudio.paInt16  # pymumble soundchunk.pcm is 16 bits
CHANNELS = 1  # No need for stereo in an intercom
RATE = 48000  # pymumble soundchunk.pcm is 48000Hz
FRAME_LENGTH = CHUNK * pyaudio.get_sample_size(FORMAT)

# The duration in seconds of one byte of PCM Data
LENGTH_TO_DURATION = 1.0 / (RATE * pyaudio.get_sample_size(FORMAT))

MAX_USER_BUFFER = 1


STREAM = True


@contextmanager
def ignore_std_error():
    '''
    Creates a context where std error message are ignored. This is used to 
    prevent pyaudio from spewing warning messages about finding audio devices when it first 
    starts
    '''
    devnull = os.open(os.devnull, os.O_WRONLY)
    old_stderr = os.dup(2)
    sys.stderr.flush()
    os.dup2(devnull, 2)
    os.close(devnull)
    try:
        yield
    finally:
        os.dup2(old_stderr, 2)
        os.close(old_stderr)


class Sound():
    '''
    Handles sending mumble sound to the speaker and recieving audio form the microphone using pyaudio.
    '''
    def __init__(self, mumble: Mumble, control: Control, config: Config):
        
        self._audio_data_type = np.dtype(np.int16)

        with ignore_std_error():
            self._audio = pyaudio.PyAudio()
        self._mumble = mumble
        self._control = control
        self._speaker_queue = queue.Queue(maxsize=5)
        self._output_current = b''
        self._buffer_lock = Lock()
        self._audio_buffers: Dict[str, bytes] = {}
        self._outgoing_buffer: Dict[str, queue.Queue] = {}
        self._microphone = self._audio.open(format=FORMAT,
                                          channels=CHANNELS,
                                          rate=RATE,
                                          input=True,
                                          output=False,
                                          frames_per_buffer=CHUNK,
                                          stream_callback=self._microphone_callback)
        self._speaker = self._audio.open(format=FORMAT,
                                        channels=CHANNELS,
                                        rate=RATE,
                                        input=False,
                                        output=True,
                                        frames_per_buffer=CHUNK,
                                        stream_callback=self._speaker_callback)
        self._mumble._sound_callback = self._play

    def _microphone_callback(self, in_data, frame_count, time_info, status_flags):
        self._mumble.transmit(in_data)
        return (None, pyaudio.paContinue)

    def _speaker_callback(self, in_data, frame_count, time_info, status_flags):
        try:
            toMix: List[bytes] = []
            for speaker in self._outgoing_buffer.values():
                if not speaker.empty():
                    toMix.append(speaker.get())
            
            
            if len(toMix) == 0 or self._control.deafened:
                # There isn't any audio buffered from mumble, so just send
                # silent audio data to the speaker.
                self._control.recieving = False
                chunk = bytes(bytearray(FRAME_LENGTH))
                return (chunk, pyaudio.paContinue)
            else:
                mixed = toMix[0]

                # Only go through the overhead of mixing audio if 
                # there is more than one source to deal with.
                if len(toMix) > 1:
                    mixed = self._mix(toMix)
                self._control.recieving = True
                return (mixed, pyaudio.paContinue)
        except Exception as e:
            print(e)
            self._control.recieving = False
            chunk = bytes(bytearray(FRAME_LENGTH))
            return (chunk, pyaudio.paContinue)
            

    def _mix(self, sources: List[bytes]):
        """
        This implements a very simple a widely recognized mixing method that also
        doesn't seem to have a name.  Two sources A and B get mixed together 
        into output M such that:
        M[i] = A[i] + B[i] - (A[i] * B[i])

        Additional sources get added in by iteratively substituting M for A (eg a reudction).
        I don't really know why this works or how it keeps the audio stable, but it seems to
        perform pretty well.  There is no way to mix audio without losing fidelity.
        """
        current = np.zeros(CHUNK)
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
        self._speaker.start_stream()

    def stop(self):
        '''
        Stop sending and recieving audio data from the speakers/microphone, and cleanup any used resources.
        '''
        self._speaker.stop_stream()
        self._audio.terminate()

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
            while len(self._audio_buffers[name]) > FRAME_LENGTH:
                if outgoing.full():
                    outgoing.get()
                outgoing.put(self._audio_buffers[name][0:FRAME_LENGTH])
                self._audio_buffers[name] = self._audio_buffers[name][FRAME_LENGTH:]
