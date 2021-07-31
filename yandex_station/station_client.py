from .yandex_session import YandexSession, LoginResponse
from .yandex_glagol import YandexGlagol
import asyncio

from aiohttp import ClientSession

class YandexDeviceConfig:
    def __init__(self, name: str, host: str, device_id: str, platform: str, port: int = 1961):
        self.name = name
        self.host = host
        self.device_id = device_id
        self.platform = platform
        self.port = port

class SyncClient:
    session: ClientSession 
    yandex: YandexSession
    glagol: YandexGlagol
    loop = None

    def __init__(self, device: YandexDeviceConfig, x_token: str): 
        self.loop = asyncio.get_event_loop()

        self.session = ClientSession(loop = self.loop)
        self.yandex = YandexSession(self.session, x_token = x_token)

        device_spec = {
            'name': device.name,
            'host': device.host,
            'port': device.port,
            'quasar_info': {
                'device_id': device.device_id,
                'platform': device.platform
            }
        }
        
        self.glagol = YandexGlagol(self.yandex, device_spec)

    def start(self):
        self.loop.run_until_complete(self.yandex.refresh_cookies())
        self.loop.run_until_complete(self.glagol.start_or_restart())
        self.loop.run_forever()

    def say(self, phrase: str):
        r = self.say_async(phrase)
        asyncio.run_coroutine_threadsafe(r, self.loop)
    
    async def say_async(self, phrase: str):
        await self.glagol.send({
            "command" : "sendText",
            "text" : "Повторяй за мной '" + phrase + "'"
        })

        wait_time  = len(phrase) * 0.07
        if (wait_time < 1):
            wait_time = 1

        await asyncio.sleep(wait_time)

        await self.glagol.send({
            "command": "serverAction",
            "serverActionEventPayload": {
                "type": "server_action",
                "name": "on_suggest"
            }
        })

        await asyncio.sleep(1)
