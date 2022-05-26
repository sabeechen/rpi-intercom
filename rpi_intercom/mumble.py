import queue
import pymumble_py3
import time
from threading import Thread
from pymumble_py3.channels import Channel
from pymumble_py3.callbacks import PYMUMBLE_CLBK_SOUNDRECEIVED, PYMUMBLE_CLBK_CONNECTED, PYMUMBLE_CLBK_DISCONNECTED, PYMUMBLE_CLBK_PERMISSIONDENIED, PYMUMBLE_CLBK_CHANNELUPDATED, PYMUMBLE_CLBK_USERUPDATED
from pymumble_py3.errors import UnknownChannelError, ConnectionRejectedError
from .config import Config
from .control import Control
from .logger import getLogger
from .shutdown import Shutdown


logger = getLogger(__name__)

# The maximum duration of audio from the microphone we're 
# allowed to buffer before audio gets dropped 
SEND_BUFFER_MAX = 5 # 500ms


class Mumble():
    '''
    Handles staying connected to a mumble server (using pymumble) and 
    sending/recieving audio to/from the mumble server.
    '''
    def __init__(self, control: Control, config: Config, shutdown: Shutdown):
        self._connected = False
        self._config = config
        self._control = control
        self._shutdown = shutdown
        
        self._mumble = None

        # Transmitting audio over the network is handled in a seperate thread to avoid 
        # locking up the recieving audio buffer form the local microphone.
        self._transmit_queue = queue.Queue(maxsize=5)
        self._transmit_thread = None
        self._run_thread = None
        self._sound_callback = None
        self._stopping = False
        self._channel: Channel = None
        self._joined_channel = False

    def _onConnect(self):
        logger.info(f"Connected to Mumble server {self._config.server}:{self._config.port} as '{self._config.nickname}'")

        # If configured to do so, also join a channel after connecting.
        if self._config.channel is not None:
            try:
                self._channel: Channel = self._mumble.channels.find_by_name(self._config.channel)
                logger.info(f'Joining channel \'{self._config.channel}\'')
                self._channel.move_in()
                self._channel.get_users()
            except UnknownChannelError:
                logger.info(f"Channel '{self._config.channel}' is unknown")
        self._connected = True
        self._control._set_connected()

    def _onDisconnect(self):
        self._joined_channel = False
        self._connected = False
        logger.warn("Disconnected from mumble server")
        self._control._set_disconnected()

    def _onDenied(self, data):
        logger.error("Permission denied")

    def _channelUpdated(self, data):
        logger.info("Channel update")
        logger.info(f"{data}")

    def _userUpdate(self, user, update):
        if (user.get("name") == self._config.nickname and self._channel.get_id() == update.get("channel_id")):
            self._joined_channel = True
            logger.info(f"Moved into channel '{self._config.channel}'")


    def _onSound(self, user, soundchunk):
        if self._sound_callback:
            self._sound_callback(user, soundchunk.pcm)

    def transmit(self, chunk):
        try:
            for sample in chunk:
                if sample > 0:
                    self._transmit_queue.put(chunk, block=False)
                    break
        except:
            pass

    def _transmit_loop(self):
        while(not self._stopping):
            try:
                chunk = self._transmit_queue.get(block=True, timeout=0.5)
                if self._connected and self._control.transmitting and self._mumble is not None:
                    output = self._mumble.sound_output
                    backlog = output.get_buffer_size()
                    if backlog > self._config._send_buffer_latency:
                        # Audio from the microphone can slowly get sent to us faster than we can 
                        # trasmit it.  Dropping the buffer avoids a buildup of audio delay over 
                        # time by sacraficing some quality when it happens.  It would be better 
                        # to compress and re-sample the audio to catch up.
                        output.clear_buffer()
                        logger.warn(f"Clearing audio send buffer due to latency.  Backlog: {backlog}")
                    self._mumble.sound_output.add_sound(chunk)
                else:
                    time.sleep(1)
            except IndexError:
                # there wasn't any audio in the trasmit queue.
                time.sleep(0.005)
            except Exception as e:
                if isinstance(e, queue.Empty):
                    # Such pythonic, so clean. wow.
                    continue
                logger.printException(e)

    def start(self):
        '''
        Connects to the mumble server and starst sending/recieving audio.  Also retrys connecting to mumble if a disconnect happens.
        '''
        self._mumble = pymumble_py3.Mumble(
            self._config.server,
            self._config.nickname,
            password=self._config.password,
            port=self._config.port,
            reconnect=True,
            certfile=self._config.cert_file,
            keyfile=self._config.key_file,
            tokens=self._config.tokens)
        # Bind to some server events so we can be notified and react accordingly.
        self._mumble.callbacks.set_callback(PYMUMBLE_CLBK_SOUNDRECEIVED, self._onSound)
        self._mumble.callbacks.set_callback(PYMUMBLE_CLBK_CONNECTED, self._onConnect)
        self._mumble.callbacks.set_callback(PYMUMBLE_CLBK_DISCONNECTED, self._onDisconnect)
        self._mumble.callbacks.set_callback(PYMUMBLE_CLBK_PERMISSIONDENIED, self._onDenied)
        self._mumble.callbacks.set_callback(PYMUMBLE_CLBK_CHANNELUPDATED, self._channelUpdated)
        self._mumble.callbacks.set_callback(PYMUMBLE_CLBK_USERUPDATED, self._userUpdate)
        self._mumble.set_receive_sound(True)

        self._run_thread = Thread(target=self._run_mumble, name="Mumble Run Thread", daemon=True)
        self._run_thread.start()
        self._stopping = False
        self._transmit_thread = Thread(target=self._transmit_loop, name="Transmit Thread", daemon=True)
        self._transmit_thread.start()

    def _run_mumble(self):
        while True:
            sleep = 5
            try:
                logger.info(f"Connecting to mumble server {self._config.server}:{self._config.port}")
                self._mumble.run()
            except ConnectionRejectedError:
                logger.error("Mumble server rejected login")
                # avoid mumble throttling us
                sleep = 30
            except Exception as e:
                logger.printException(e)
                sleep = 10
            if self._shutdown.shutting_down:
                return
            logger.info(f"I'll retry in {sleep} seconds")
            time.sleep(sleep)
        

    def stop(self):
        '''
        Disconnects from the mumble server and stops processing audio.
        '''
        if self._mumble is not None:
            try:
                self._mumble.stop()
            except:
                # eat the error
                pass
            self._mumble = None
        self._connected = False
        self._stopping = True
        if self._transmit_thread is not None:        
            self._transmit_thread.join()
