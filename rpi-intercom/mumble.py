import queue
import pymumble_py3
import time
from threading import Thread
from pymumble_py3.channels import Channel
from pymumble_py3.callbacks import PYMUMBLE_CLBK_SOUNDRECEIVED, PYMUMBLE_CLBK_CONNECTED, PYMUMBLE_CLBK_DISCONNECTED, PYMUMBLE_CLBK_PERMISSIONDENIED
from pymumble_py3.errors import UnknownChannelError
from .config import Config
from .control import Control

# The maximum duration of audio from the microphone we're 
# allowed to buffer before audio gets dropped 
SEND_BUFFER_MAX = 5 # 500ms


class Mumble():
    '''
    Handles staying connected to a mumble server (using pymumble) and 
    sending/recieving audio to/from the mumble server.
    '''
    def __init__(self, control: Control, config: Config):
        self._connected = False
        self._config = config
        self._control = control
        
        self._mumble = None

        # Transmitting audio over the network is handled in a seperate thread to avoid 
        # locking up the recieving audio buffer form the local microphone.
        self._transmit_queue = queue.Queue(maxsize=5)
        self._transmit_thread = None
        self._sound_callback = None
        self._stopping = False


    def _onConnect(self):
        print(f"Connected to Mumble server {self._config.server}:{self._config.port} as '{self._config.nickname}'")

        # If configured to do so, also join a channel after connecting.
        if self._config.channel is not None:
            try:
                channel: Channel = self._mumble.channels.find_by_name(self._config.channel)
                channel.move_in()
                print(f'Joined channel \'{self._config.channel}\'')
            except UnknownChannelError:
                print(f"Channel '{self._config.channel}' is unknown")
        self._connected = True
        self._control._set_connected()

    def _onDisconnect(self):
        self._connected = False
        print("Disconnected from server")
        self._control._set_disconnected()

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
                        print(f"Clearing audio send buffer due to latency.  Backlog: {backlog}")
                    self._mumble.sound_output.add_sound(chunk)
            except IndexError:
                # there wasn't any audio in the trasmit queue.
                time.sleep(0.005)
            except Exception as e:
                if isinstance(e, queue.Empty):
                    # Such pythonic, so clean. wow.
                    continue
                print(e)

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
        self._mumble.set_receive_sound(True)
        self._mumble.start()
        self._stopping = False
        self._transmit_thread = Thread(target=self._transmit_loop, name="Transmit Thread", daemon=True)
        self._transmit_thread.start()

    def stop(self):
        '''
        Disconnects from the mumble server and stops processing audio.
        '''
        if self._mumble is not None:
            self._mumble.stop()
            self._mumble = None
        self._connected = False
        self._stopping = True
        if self._transmit_thread is not None:        
            self._transmit_thread.join()
