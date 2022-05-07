import math
import alsaaudio as alsa
from .config import Config, DEFAULTS, Options
from typing import Dict, List


FORMAT = alsa.PCM_FORMAT_S16_LE  # pymumble soundchunk.pcm is 16 bits little endian
CHANNELS = 1  # No need for stereo in an intercom
RATE = 48000  # pymumble soundchunk.pcm is 48000Hz
PCM_STRINGS = ['sysdefault:CARD=', 'default:CARD=']

class Devices():
    def __init__(self, config: Config):
        self._config = config
        self._speaker: alsa.PCM = None
        self._microphone: alsa.PCM = None
        self._devices:Dict[int, List[str]] = {}
        for i in alsa.card_indexes():
            (name, longname) = alsa.card_name(i)
            self._devices[i] = [name, str(i), longname]
        self._input_pcms: List[str] = alsa.pcms(alsa.PCM_CAPTURE)
        self._output_pcms: List[str] = alsa.pcms(alsa.PCM_PLAYBACK)

        # determine chunk size
        self._chunk_size = int(math.pow(2, int(math.log2(self._config.chunk_size))))
        if self._chunk_size < 128:
            self._chunk_size = 128

    def list(self):
        print("Identified speaker devices:")
        print("    default")
        for device in self._output_pcms:
            for identifier in PCM_STRINGS:
                if device.startswith(identifier):
                    print("    " + device.replace(identifier, ""))
        print()
        print("Identified microphone devices:")
        print("    default")
        for device in self._input_pcms:
            for identifier in PCM_STRINGS:
                if device.startswith(identifier):
                    print("    " + device.replace(identifier, ""))

        print()
        print("Only recommended devices are show here.  To see the list of ALL input/output devices ALSA provides, please run:")
        print("    python -m rpi_intercom list-devices-raw")


    def list_raw(self):
        print("Identified ouput devices:")
        print("    default")
        for device in self._output_pcms:
            print("    " + device)
        print()
        print("Identified input devices:")
        print("    default")
        for device in self._input_pcms:
            print("    " + device)

        print()
        print("Please note that not all available devices will work with this library, as they must support 16bit 48kHz mono audio input/output.  Its recommended to stick with the devices starting with 'sysdefault' or 'default' where ALSA does the necessary re-sampling, otherwise the device may distort the audio")

    def start(self):
        print("Configuring sound devices")
        print(f"Using a device chunk size of {self._chunk_size} bytes")
        if isinstance(self._config.microphone, int) or len(self._config.microphone) > 0:
            name = self._validate_device(self._config.microphone, self._input_pcms)
            print(f"Using microphone device '{name}' for audio input")
            self._microphone = alsa.PCM(type=alsa.PCM_CAPTURE, mode=alsa.PCM_NORMAL, channels=CHANNELS, rate=RATE, format=alsa.PCM_FORMAT_S16_LE, periodsize=self._chunk_size, device=name)
        
        if isinstance(self._config.speaker, int) or len(self._config.speaker) > 0:
            name = self._validate_device(self._config.speaker, self._output_pcms)
            print(f"Using speaker device '{name}' for audio output")
            self._speaker = alsa.PCM(type=alsa.PCM_PLAYBACK, mode=alsa.PCM_NORMAL, channels=CHANNELS, rate=RATE, format=alsa.PCM_FORMAT_S16_LE, periodsize=self._chunk_size, device=name)

    def stop(self):
        if self._speaker is not None:
            self._speaker.close()
            print("Closed speaker")
        if self._microphone is not None:
            self._microphone.pause()
            self._microphone.close()
            print("Closed microphone")
        self._microphone = None
        self._speaker = None

    def speaker_write(self, data) -> None:
        if self._speaker is None:
            return
        try:
            self._speaker.write(data)
        except (Exception, alsa.ALSAAudioError) as e:
            print("Speaker reported an exception:")
            print(e)
             # Restart the speaker
            try:
                self._speaker.close()
            except:
                # Just ignore if it can't close
                pass
            name = self._validate_device(self._config.speaker, self._output_pcms)
            print(f"Using speaker device '{name}' for audio output")
            self._speaker = alsa.PCM(type=alsa.PCM_PLAYBACK, mode=alsa.PCM_NORMAL, channels=CHANNELS, rate=RATE, format=alsa.PCM_FORMAT_S16_LE, periodsize=self._chunk_size, device=name)
            self.speaker_write(data)

    def microphone_read(self):
        if self._microphone is None:
            return
        try:
            return self._microphone.read()
        except (Exception, alsa.ALSAAudioError) as e:
            print("Microphone reported an exception:")
            print(e)

            # Restart the microphone
            try:
                self._microphone.pause()
                self._microphone.close()
            except:
                # Just ignore if it can't close
                pass
            name = self._validate_device(self._config.microphone, self._input_pcms)
            print(f"Using microphone device '{name}' for audio input")
            self._microphone = alsa.PCM(type=alsa.PCM_CAPTURE, mode=alsa.PCM_NORMAL, channels=CHANNELS, rate=RATE, format=alsa.PCM_FORMAT_S16_LE, periodsize=self._chunk_size, device=name)
            return self.microphone_read()

    @property
    def microphone(self):
        return self._microphone

    @property
    def speaker(self):
        return self._speaker

    @property
    def chunk_size(self):
        return self._chunk_size

    @property
    def frame_length(self):
        """The size in bytes of a frame given the configured chunk_size"""
        #16bit mono PCM is 2 bytes per frame
        return self.chunk_size * 2

    def _validate_device(self, name, device_list):
        name = str(name)
        if name in device_list:
            # easiest case, a fully named pcm device
            return name

        if f"sysdefault:CARD={name}" in device_list:
            return f"sysdefault:CARD={name}"
        if f"default:CARD={name}" in device_list:
            return f"default:CARD={name}"

        for index in self._devices:
            if name in self._devices[index]:
                return f"sysdefault:{index}"
        print(f"'{name}' does not identify a valid sound device.  You can use 'list-devices' to see what devices are available on your machine. Eg:")
        print("    python -m rpi_intercom list-devices")

        # TODO: this exception should be more descriptive
        raise Exception()
