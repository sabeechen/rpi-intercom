from asyncio import Event
from typing import Any, Dict, List
from aiohttp import web
from aiohttp.web import Request
from os.path import join, abspath
import aiohttp
import asyncio
import json
import logging

from .devices import Devices
from .logger import getLogger, getHistory, ATTACHABLE
from .shutdown import Shutdown

logger = getLogger(__name__)
class ClientConnection():
    def __init__(self, ws: web.WebSocketResponse, welcome_message, handler):
        self._closed = Event()
        self._ws = ws
        self._welcome_message = welcome_message
        self._write_queue = asyncio.Queue()
        self._read_loop_task = asyncio.create_task(self.read_loop())
        self._write_loop_task = asyncio.create_task(self.write_loop())
        self._running = True
        self._handler = handler

    async def read_loop(self):
        await self.queue({'type': 'init', 'data': self._welcome_message})
        for item in getHistory(0):
            await self.log(item[1])
        async for msg in self._ws:
            if msg.type == aiohttp.WSMsgType.TEXT:
                try:
                    data = json.loads(msg.data)
                    await self._handler(self, data)
                except BaseException as e:
                    logger.error("Error handling websocket message")
                    logger.printException(e)
            elif msg.type == aiohttp.WSMsgType.ERROR:
                logger.info(f'ws connection closed with exception {self._ws.exception()}')
        self._running = False
        self._write_loop_task.cancel()
        self._closed.set()

    async def write_loop(self):
        while self._running:
            item = await self._write_queue.get()
            await self._ws.send_str(item)

    async def log(self, message):
        await self.queue({'type': 'log', 'log': message})

    async def send(self, message):
        await self.queue(message)

    async def queue(self, message: Any):
        await self._write_queue.put(json.dumps(message))
        while self._write_queue.qsize() > 1000:
            # drop messages, just being defensive
            await self._write_queue.get()

    async def closed(self):
        await self._read_loop_task

class Server():
    def __init__(self, devices: Devices, shutdown: Shutdown):
        self._connections: List[ClientConnection] = []
        self._devices = devices
        self._shutdown = shutdown
        self._update = None

    async def start(self):
        app = web.Application()
        app.add_routes([
            web.get('/ws', self.websocket_handler),
            web.get('/', self.index),
            web.static('/static', abspath(join(__file__, "..", "static")))
            ])
        runner = web.AppRunner(app)
        await runner.setup()
        site = web.TCPSite(runner, "0.0.0.0", 8000)
        await site.start()
        self._loop = asyncio.get_running_loop()
        ATTACHABLE.attach(self.write_log)
        self._update = asyncio.create_task(self.update_loop())

    def welcomeMessage(self):
        return {
            'input_devices': self._devices._input_pcms,
            'output_devices': self._devices._output_pcms,
            'devices': self._devices._devices
        }

    async def update_loop(self):
        while True:
            update = {
                'type': 'status',
                'vad': self._devices.vad
            }
            for conn in self._connections:
                await conn.send(update)
            await asyncio.sleep(0.5)
    
    def write_log(self, message):
        asyncio.run_coroutine_threadsafe(self._write_log(message), self._loop)

    async def _write_log(self, message):
        for conn in self._connections:
            await conn.log(message)

    async def index(self, request: web.Request):
        return web.FileResponse(abspath(join(__file__, "..", "static", "index.html")))

    async def websocket_handler(self, request: web.Request):
        ws = web.WebSocketResponse()
        await ws.prepare(request)
        conn = ClientConnection(ws, self.welcomeMessage(), self.client_message)
        self._connections.append(conn)
        await conn.closed()
        self._connections.remove(conn)
        return ws

    async def client_message(self, ws, message: Dict[str, Any]):
        data_type = message.get("type")
        if data_type == "shutdown":
            logger.info("Web client requested a shutdown")
            self._shutdown.shutdown()
        elif data_type == "ping":
            # do nothing, just a heartbeat
            pass
        elif data_type == "reset":
            logger.info("Resetting sound devices")
            self._devices.resetSpeaker()
            self._devices.resetMic()
        elif data_type == "volume":
            # Handle volume control
            pass
