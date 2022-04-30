import os
import sys
import pyaudio
from contextlib import contextmanager
from pprint import pprint

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

class Devices():
    def __init__(self):
        pass

    def list(self):
        audio = None
        try:
            with ignore_std_error():
                audio  = pyaudio.PyAudio()
            devices = audio.get_device_count()
            for x in range(0, devices):
                info = audio.get_device_info_by_index(x)
                print(f"{info['index']}: '{info['name']}'")
                pprint(info, indent=4)
                #pprint.pprint(audio.get_default_host_api_info())

            print(F"Count: {audio.get_host_api_count()}")
            pprint(audio.get_host_api_info_by_index(1))
            pprint(audio.get_default_input_device_info())
        finally:
            if audio is not None:
                audio.terminate()
