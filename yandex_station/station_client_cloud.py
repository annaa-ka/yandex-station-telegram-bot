from dataclasses import dataclass
import asyncio
from asyncio.events import AbstractEventLoop
from os import name
from typing import List, TypedDict, Union
from .yandex_session import YandexSession
from .yandex_quasar import YandexQuasar
from .utils import fix_cloud_text
from aiohttp import ClientSession

EXCEPTION_100 = Exception("Нельзя произнести более 100 симоволов :(")


@dataclass
class SpeakerConfig:
    id: str
    name: str
    scenario_id: Union[str, None]


class SyncCloudClient:
    session: ClientSession 
    yandex: YandexSession
    loop: AbstractEventLoop
    
    def __init__(self): 
        self.loop = asyncio.get_event_loop()
        self.session = ClientSession(loop = self.loop)

    def start(self):
        self.loop.run_forever()

    def get_speakers(self, token: str) -> List[SpeakerConfig]:
        r = self.__get_speakers_async(token)
        return asyncio.run_coroutine_threadsafe(r, self.loop).result()

    async def __get_speakers_async(self, token: str) -> List[SpeakerConfig]:
        quasar = await self.__get_quasar(token)
        await quasar.load_devices()

        return [
            SpeakerConfig(item['id'], item['name'], item['scenario_id'])
            for item in quasar.speakers
        ]

    def prepare_speaker(self, token: str, speaker: SpeakerConfig) -> SpeakerConfig:
        r = self.__prepare_speaker_async(token, speaker)
        return asyncio.run_coroutine_threadsafe(r, self.loop).result()

    async def __prepare_speaker_async(self, token: str, speaker: SpeakerConfig) -> SpeakerConfig:
        quasar = await self.__get_quasar(token)
        speaker_data = self.__convert_speaker_config_to_quasar_object(speaker)
        
        await quasar.prepare_speaker(speaker_data)
        
        return SpeakerConfig(
            speaker_data['id'], 
            speaker_data['name'], 
            speaker_data['scenario_id']
        )

    def say(self, token: str, device: SpeakerConfig, phrase: str):
        r = self.say_async(token, device, phrase)
        asyncio.run_coroutine_threadsafe(r, self.loop).result()


    async def say_async(self, token: str, speaker: SpeakerConfig, phrase: str):
        phrase = fix_cloud_text(phrase)
        if len(phrase) > 100:
            raise EXCEPTION_100
        
        quasar = await self.__get_quasar(token)
        speaker_data = self.__convert_speaker_config_to_quasar_object(speaker)

        await quasar.send(speaker_data, phrase, is_tts=True)
        return

    def __convert_speaker_config_to_quasar_object(self, speaker: SpeakerConfig) -> dict:
        return {
            'id': speaker.id,
            'scenario_id': speaker.scenario_id,
            'name': speaker.name
        }
    
    async def __get_quasar(self, token: str) -> YandexQuasar:
        yandex = YandexSession(self.session, x_token = token)
        quasar = YandexQuasar(yandex)
        await yandex.login_token(token)

        return quasar

