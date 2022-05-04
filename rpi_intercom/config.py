from dataclasses import dataclass
from enum import Enum
from typing import Any, Dict, List, Union
from numpy import fromfile
from schema import Schema, Optional, Or
import yaml
import sys
import uuid
import argparse

class Options(Enum):
    SERVER = "server"
    PORT = "port"
    NICKNAME = "nickname"
    PASSWORD = "password"
    CERT_FILE = "cert_file"
    KEY_FILE = "key_file"
    TOKENS = "tokens"
    SEND_BUFFER_LATENCY = "send_buffer_latency"
    CHANNEL = "channel"
    PINS = "pins"
    RESTART_SECONDS = "restart_seconds"
    CHUNK_SIZE = "chunk_size"
    SPEAKER = "speaker"
    MICROPHONE = "microphone"

class PinConfig(Enum):
    ACTION_TOOGLE_TRANSMIT = "toggle_transmit"
    ACTION_HOLD_TO_TRANSMIT = "transmit"
    ACTION_TOOGLE_DEAFEN = "toggle_deafen"
    ACTION_HOLD_TO_DEAFEN = "deafen"
    ACTION_VOLUME_UP = "volume_up"
    ACTION_VOLUME_DOWN = "volume_down"
    STATUS_TRANSMITTING = "transmitting"
    STATUS_CONNECTED = "connected"
    STATUS_RECIEVING = "receiving"
    STATUS_DEAFENED = "deafened"

PIN_SCHEMA = Schema(
    Or(*[value.value for value in PinConfig._member_map_.values()]))

CONFIG_SCHEMA = Schema({
    Options.SERVER.value: str,
    Optional(Options.PORT.value): int,
    Optional(Options.NICKNAME.value): str,
    Optional(Options.PASSWORD.value): str,
    Optional(Options.CERT_FILE.value): str,
    Optional(Options.KEY_FILE.value): str,
    Optional(Options.TOKENS.value): [str],
    Optional(Options.CHANNEL.value): str,
    Optional(Options.SEND_BUFFER_LATENCY.value): float,
    Optional(Options.PINS.value): {str: PIN_SCHEMA},
    Optional(Options.RESTART_SECONDS.value): int,
    Optional(Options.CHUNK_SIZE.value): int,
    Optional(Options.SPEAKER.value): Or(int, str),
    Optional(Options.MICROPHONE.value): Or(int, str),
})

DEFAULTS = {
    Options.SERVER: "unused",
    Options.NICKNAME: "intercom_" + hex(uuid.getnode())[-4:],
    Options.PORT: 64738,
    Options.PASSWORD: "",
    Options.CERT_FILE: None,
    Options.KEY_FILE: None,
    Options.CHANNEL: None,
    Options.SEND_BUFFER_LATENCY: 0.5,
    Options.TOKENS: [],
    Options.PINS: {},
    Options.RESTART_SECONDS: 0,
    Options.CHUNK_SIZE: 512,
    Options.SPEAKER: "default",
    Options.MICROPHONE: "default",
}


class Config:
    def __init__(self, server: str = None, port: int = None, nickname: str = None, password:str = None, cert_file: str = None, key_file: str = None, channel: str = None, send_buffer_latency:float = None, tokens: List[str] = None, pins: Dict[str, PinConfig] = None, restart_seconds:int=None, chunk_size: int=None, speaker:Union[str, int]=None, microphone:Union[str, int]=None):
        self._server = server if server is not None else DEFAULTS[Options.SERVER]
        self._port = port if port is not None else DEFAULTS[Options.PORT]
        self._nickname = nickname if nickname is not None else DEFAULTS[Options.NICKNAME]
        self._password = password if password is not None else DEFAULTS[Options.PASSWORD]
        self._cert_file = cert_file if cert_file is not None else DEFAULTS[Options.CERT_FILE]
        self._key_file = key_file if key_file is not None else DEFAULTS[Options.KEY_FILE]
        self._channel = channel if channel is not None else DEFAULTS[Options.KEY_FILE]
        self._send_buffer_latency = send_buffer_latency if send_buffer_latency is not None else DEFAULTS[Options.SEND_BUFFER_LATENCY]
        self._tokens = tokens if tokens is not None else DEFAULTS[Options.TOKENS]
        self._pins = pins if pins is not None else DEFAULTS[Options.PINS]
        self._restart_seconds = restart_seconds if restart_seconds is not None else DEFAULTS[Options.RESTART_SECONDS]
        self._chunk_size = chunk_size if chunk_size is not None else DEFAULTS[Options.CHUNK_SIZE]
        self._microphone = microphone if microphone is not None else DEFAULTS[Options.MICROPHONE]
        self._speaker = speaker if speaker is not None else DEFAULTS[Options.SPEAKER]

    @classmethod
    def fromFile(cls, path):
        with open(path) as f:
            config = yaml.safe_load(f)
        return Config(config)

    @property
    def server(self):
        return self._server

    @property
    def port(self):
        return self._port

    @property
    def nickname(self):
        return self._nickname

    @property
    def password(self):
        return self._password

    @property
    def cert_file(self):
        return self._cert_file

    @property
    def key_file(self):
        return self._key_file

    @property
    def channel(self):
        return self._channel
    
    @property
    def send_buffer_latency(self):
        return self._send_buffer_latency

    @property
    def tokens(self):
        return self._tokens

    @property
    def pins(self):
        return self._pins

    @property
    def restart_seconds(self) -> int:
        return self._restart_seconds

    @property
    def chunk_size(self) -> int:
        return self._chunk_size

    @property
    def microphone(self) -> Union[str, int]:
        return self._microphone
        
    @property
    def speaker(self) -> Union[str, int]:
        return self._speaker

    @classmethod
    def fromArgs(cls):
        parser = argparse.ArgumentParser()
        parser.add_argument("--config", required=False,
                            help="The config file to laod optiosn from.  All other aguments are ignored when thsi is specified", default=None)
        parser.add_argument("--server", required=False,
                            help="The address of the mumble server", default=None)
        parser.add_argument("--port", required=False,
                            help="The port of the mumble server", type=int, default=None)
        parser.add_argument("--nickname", required=False,
                            help="The nickname to use when connecting to mumble", default=None)
        parser.add_argument("--password", required=False,
                            help="The password to use when connecting to mumble", default=None)
        parser.add_argument("--cert_file", required=False,
                            help="The path of a certificate file to use when connecting to mumble", default=None)
        parser.add_argument("--key_file", required=False,
                            help="The path of a certificate key file to use when connecting to mumble", default=None)
        parser.add_argument("--channel", required=False,
                            help="The channel to join after connectiong to mumble", default=None)
        parser.add_argument("--send_buffer_latency", required=False,
                            help="How long to let audio sit in the send buffer before dropping it", default=None)
        parser.add_argument("--tokens", required=False, nargs="*",
                            help="One or more access tokens to be passed to the server", default=None)
        parser.add_argument("--restart_seconds", required=False, nargs="*",
                            help="If set, how often the client should restart istelf in seconds.", default=None)
        parser.add_argument("--speaker", required=False, nargs="*",
                            help="The speaker device to use for sound output.  Can be either the ALSA device name (a string) or a device index (an integer)", default=None)
        parser.add_argument("--microphone", required=False, nargs="*",
                            help="The microphone device to use for sound input.  Can be either the ALSA device name (a string) or a device index (an integer)", default=None)
        parser.add_argument("--chunk_size", required=False, nargs="*",
                            help="Size of the chunk in bytes that speaker or microphone output/input is processed.  Must be a power of 2.", default=None)
        args = parser.parse_args()

        if args.config is not None:
            with open(args.config) as f:
                config = yaml.safe_load(f)
                CONFIG_SCHEMA.validate(config)
                return Config(server=config.get(Options.SERVER.value), 
                            port=config.get(Options.PORT.value), 
                            nickname=config.get(Options.NICKNAME.value), 
                            password=config.get(Options.PASSWORD.value), 
                            cert_file=config.get(Options.CERT_FILE.value), 
                            key_file=config.get(Options.KEY_FILE.value), 
                            channel=config.get(Options.CHANNEL.value),
                            send_buffer_latency=config.get(Options.SEND_BUFFER_LATENCY.value),
                            pins=config.get(Options.PINS.value), 
                            tokens=config.get(Options.TOKENS.value),
                            restart_seconds=config.get(Options.RESTART_SECONDS.value),
                            chunk_size=config.get(Options.CHUNK_SIZE.value),
                            microphone=config.get(Options.MICROPHONE.value),
                            speaker=config.get(Options.SPEAKER.value))
        else:
            return Config(server=args.server, 
                port=args.port, 
                nickname=args.nickname, 
                password=args.password, 
                cert_file=args.cert_file, 
                key_file=args.key_file, 
                channel=args.channel, 
                send_buffer_latency=args.send_buffer_latency,
                tokens=args.tokens,
                restart_seconds=args.restart_seconds,
                chunk_size=args.chunk_size,
                microphone=args.microphone,
                speaker=args.speaker)

    def get(self, key):
        if key in self.data:
            return self.data[key]
        else:
            return DEFAULTS[key]
