import pyaudio
import queue
import os
import sys
from contextlib import contextmanager
from .config import Config
from .mumble import Mumble
from .control import Control

CHUNK = 1024  # Seems like a decent chunk size.  Why not?
FORMAT = pyaudio.paInt16  # pymumble soundchunk.pcm is 16 bits
CHANNELS = 1  # No need for stereo in an intercom
RATE = 48000  # pymumble soundchunk.pcm is 48000Hz
FRAME_LENGTH = CHUNK * pyaudio.get_sample_size(FORMAT)

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
        with ignore_std_error():
            self._audio = pyaudio.PyAudio()
        self._mumble = mumble
        self._control = control
        self._speaker_queue = queue.Queue(maxsize=5)
        self._output_current = b''
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
            if self._speaker_queue.empty() or self._control.deafened:
                # There isn't any audio buffered from mumble, so just send
                # silent audio data to the speaker.
                self._control.recieving = False
                chunk = bytes(bytearray(FRAME_LENGTH))
                return (chunk, pyaudio.paContinue)
            else:
                self._control.recieving = True
                chunk = self._speaker_queue.get()
                self.last_output = chunk
                return (chunk, pyaudio.paContinue)
        except Exception as e:
            print(e)

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

    def _play(self, frame):
        '''
        Buffer audio data (eg from mumble) to be played locally
        '''
        if self._control.deafened:
            return
        self._output_current += frame

        # Data recieved from mumble doesn't necessarily align with the speaker's 
        # configured chunk size,  so we break it up as it arrives into FRAME_LENGTH
        # size peices.
        while len(self._output_current) > FRAME_LENGTH:
            self.last_output = self._output_current[0:FRAME_LENGTH]
            self._speaker_queue.put(self._output_current[0:FRAME_LENGTH])
            self._output_current = self._output_current[FRAME_LENGTH:]
