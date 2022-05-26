from hmac import compare_digest
import math
import threading
import time
import alsaaudio as alsa
from .config import Config, DEFAULTS, Options
from .shutdown import Shutdown
from typing import Dict, List
from datetime import datetime, timedelta
from .logger import getLogger
from .worker import Worker
import numpy as np
import samplerate
from datetime import datetime, timezone, timedelta
import collections

logger = getLogger(__name__)
FORMAT = alsa.PCM_FORMAT_S16_LE  # pymumble soundchunk.pcm is 16 bits little endian
CHANNELS = 1  # No need for stereo in an intercom
RATE = 48000  # pymumble soundchunk.pcm is 48000Hz
PCM_STRINGS = ['sysdefault:CARD=', 'default:CARD=']
DATA_LENGTH = 2 # Length of a single-channel sample in bytes
AUDIO_DATA_TYPE = np.dtype(np.int16).newbyteorder('<')
VAD_MINIMUM = 0.5
VAD_DELAY = 0.5

class Devices():
    def __init__(self, config: Config, shutdown: Shutdown):
        self._start = datetime.now()
        self._config = config
        self._speaker: alsa.PCM = None
        self._microphone: alsa.PCM = None
        self._devices:Dict[int, List[str]] = {}
        self._shutdown = shutdown
        for i in alsa.card_indexes():
            (name, longname) = alsa.card_name(i)
            self._devices[i] = [name, str(i), longname]
        self._input_pcms: List[str] = alsa.pcms(alsa.PCM_CAPTURE)
        self._output_pcms: List[str] = alsa.pcms(alsa.PCM_PLAYBACK)
        self._cards = alsa.cards()
        self._worker = Worker("Device Check")
        self._reset_speaker = False
        self._reset_microphone = False
        self._microphone_resampler = None
        self._microphone_sample_rate = None
        self._microphone_channels = None
        self._speaker_resampler = None
        self._speaker_sample_rate = None
        self._speaker_channels = None
        self._microphone_start = None
        self._mixer = None
        self._vad = 0
        self._vad_last_activated = datetime.now()
        self._vad_active = False
        self._vad_queue = collections.deque(maxlen=10)

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

    @property
    def vad(self):
        max = 0
        for item in self._vad_queue:
            if item > max:
                max = item
        return round(max, 1)

    def resetMic(self):
        self._reset_microphone = True
        self._worker.trigger()

    def resetSpeaker(self):
        self._reset_speaker = True
        self._worker.trigger()

    def _checkLoop(self):
        delay = 5
        try:
            mic_name, card = self._validateDeviceArgs(self._config.microphone, self._input_pcms)
            if self._microphone is None and mic_name is not None and not self._shutdown.shutting_down:
                logger.info(f"Connecting to the microphone:")
                device = alsa.PCM(
                    type=alsa.PCM_CAPTURE, 
                    mode=alsa.PCM_NORMAL,
                    channels=CHANNELS,
                    rate=RATE,
                    format=alsa.PCM_FORMAT_S16_LE,
                    periodsize=self._chunk_size,
                    device=mic_name)
                self._microphone_channels = device.setchannels(CHANNELS)
                self._microphone_sample_rate = device.setrate(RATE)
                self._microphone_resampler = samplerate.Resampler()
                logger.info(f"  Device name: {device.cardname()}")
                logger.info(f"  Channels:    {self._microphone_channels}")
                logger.info(f"  Sample rate: {self._microphone_sample_rate} Hz")
                self._microphone_start = datetime.now(timezone.utc)
                self._microphone = device           
            elif self._reset_microphone and self._microphone is not None:
                logger.info(f"Closing microphone {self._microphone.cardname()}")
                try:
                    logger.debug("Pausing")
                    self._microphone.pause()
                except:
                    pass
                try:
                    logger.debug("Closing")
                    self._microphone.close()
                except:
                    pass
                self._microphone = None
                logger.info("Closed microphone")
                delay = 0
            self._reset_microphone = None

            speaker_name, card = self._validateDeviceArgs(self._config.speaker, self._output_pcms)
            if self._speaker is None and speaker_name is not None and not self._shutdown.shutting_down:
                logger.info(f"Connecting to the speaker:")
                device = alsa.PCM(
                    type=alsa.PCM_PLAYBACK, 
                    mode=alsa.PCM_NORMAL, 
                    channels=CHANNELS,
                    rate=RATE,
                    format=alsa.PCM_FORMAT_S16_LE,
                    periodsize=self._chunk_size,
                    device=speaker_name)
                self._speaker_channels = device.setchannels(CHANNELS)
                self._speaker_sample_rate = device.setrate(RATE)
                self._speaker_resampler = samplerate.Resampler()
                logger.info(f"  Device name:  {device.cardname()}")
                logger.info(f"  Channels:     {self._speaker_channels}")
                logger.info(f"  Sample rate:  {self._speaker_sample_rate} Hz")
                self._speaker = device
                self._mixer = None
                try:
                    self._mixer = alsa.Mixer(control='PCM', device=speaker_name)
                except alsa.ALSAAudioError:
                    try:
                        self._mixer = alsa.Mixer(device=speaker_name)
                    except alsa.ALSAAudioError:
                        logger.warning("Unable to find a mixer device for this speaker.  Volume control will be unavailable.")
                if self._mixer is not None:
                    self._mixer.setvolume(50)
                    logger.info(f"  Volume:       {self._mixer.getvolume()}")
                    logger.info(f"  Volume Range: {self._mixer.getrange()}")

            elif self._reset_speaker and self._speaker is not None:
                logger.info(f"Closing speaker {self._speaker.cardname()}")
                dev = self._speaker
                self._speaker = None
                self._close(dev)
                logger.info("Closed speaker")
                delay = 0 
            self._reset_speaker = False
        finally:
            self._worker.submit(delay, self._checkLoop)

    def _close(self, device):
        if device is None:
            return
        try:
            logger.debug("Pausing")
            device.pause()
        except BaseException as e:
            logger.debug(f"{e}")
        try:
            logger.debug("Closing")
            device.close()
        except BaseException as e:
            logger.debug(f"{e}")

    def _validateDeviceArgs(self, dev_name, list: List[str]):
        if dev_name is None:
            return None
        for device in self._devices:
            for name in self._devices[device]:
                if str(dev_name) == name:
                    return f"hw:{device}", int(device)
        raise Exception(f"'{dev_name}' does not identify a valid sound device")

    def start(self):
        self._worker.start()
        self._worker.submit(0, self._checkLoop)
        logger.info(f"Using a device chunk size of {self._chunk_size} bytes")

    def stop(self):
        self._worker.stop()
        if self._speaker is not None:
            device = self._speaker
            self._speaker = None
            self._close(device)
            logger.info("Closed speaker")
        if self._microphone is not None:
            device = self._microphone
            self._microphone = None
            self._close(device)
            logger.info("Closed microphone")


    def speaker_write(self, data) -> None:
        if self._speaker is None or self._shutdown.shutting_down:
            return
        try:
            ratio = self._speaker_sample_rate / RATE
            processed = self._speaker_resampler.process(data, ratio, False)

            if self._speaker_channels != 1:
                # mix up to multiple channels
                output = np.zeros(len(processed) * self._speaker_channels)
                for x in range(self._speaker_channels):
                    output[x::self._speaker_channels] = processed
            else:
                output = processed
            self._speaker.write((output * 32768).astype(AUDIO_DATA_TYPE).tobytes())
        except (Exception, alsa.ALSAAudioError) as e:
            if not self._shutdown.shutting_down:
                logger.error("Speaker reported an exception:")
                logger.printException(e)
                self.resetSpeaker()

    def microphone_read(self):
        length, data = self._microphone_read()
        self._vad_queue.append(self._vad)
        return length, data

    def _microphone_read(self):
        if self._microphone is None or self._shutdown.shutting_down:
            self._vad = 0
            return None, None
        try:
            length = -1
            while length < 0:
                start = datetime.now(timezone.utc)
                length, data =  self._microphone.read()
                if length < 0 and datetime.now(timezone.utc) > self._microphone_start + timedelta(seconds=10):
                    logger.warn("Buffer overrun from the microphone")
                    length = -1
                    continue
                duration = datetime.now(timezone.utc) - start
                expected_seconds = length / (self._microphone_sample_rate * DATA_LENGTH * self._microphone_channels)
                if duration.total_seconds() < expected_seconds * 0.5:
                    logger.debug(f"Expected microphone read to take {int(expected_seconds*1000000)} us, but it took {int(duration.total_seconds()*1000000)} us")
                    length = -1
                    continue
            channels = int(len(data) / length / DATA_LENGTH)
            if channels < 1 or channels * DATA_LENGTH * length != len(data):
                logger.error(f"Reading from the soundcard got an invalid channel count of {channels}. length: {length} chunk_size: {len(data)}")
                self._vad = 0
                return None, None

            # Mix down multiple channels and resample if necessary
            data_float = np.frombuffer(data, dtype=AUDIO_DATA_TYPE).astype(float) / 32768
            current = np.zeros(length)
            for source in [data_float[x::channels] for x in range(channels)]:
                current = current + source - (current * source)
            if self._microphone_sample_rate != RATE:
                ratio = RATE / self._microphone_sample_rate
                current = self._microphone_resampler.process(current, ratio, False)
            self._vad = round(np.average(np.abs(current)) * 0.5 * 100, 2)
            max = np.max(np.abs(current))

            if self._vad > VAD_MINIMUM:
                self._vad_last_activated = datetime.now()
            if max > 1:
                # I'm not sure why this happens, but when it does the speaker just outputs
                # an ungly square wave sound.  Ignore it for now.
                data = np.zeros(len(current)).astype(AUDIO_DATA_TYPE).tobytes()
            elif datetime.now() - self._vad_last_activated < timedelta(seconds=VAD_DELAY):
                if not self._vad_active:
                    self._vad_active = True
                    logger.info("Sound detected")
                data = (current * 32768).astype(AUDIO_DATA_TYPE).tobytes()
            else:
                if self._vad_active:
                    self._vad_active = False
                    logger.info("No sound detected")
                data = np.zeros(len(current)).astype(AUDIO_DATA_TYPE).tobytes()
            return length, data
        except (Exception, alsa.ALSAAudioError) as e:
            if not self._shutdown.shutting_down:
                logger.error("Microphone reported an exception:")
                logger.printException(e)
                self.resetMic()
                self._vad = 0
                return None, None

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
