from typing import List, Union
from dataclasses import dataclass
import asyncio
from asyncio.events import AbstractEventLoop
from aiohttp import ClientSession
import logging

from .yandex_session import LoginResponse, YandexSession
from .yandex_quasar import YandexQuasar
from .utils import fix_cloud_text

_LOGGER = logging.getLogger(__name__)

EXCEPTION_100 = Exception("Нельзя произнести более 100 симоволов :(")


@dataclass
class SpeakerConfig:
    id: str
    name: str
    scenario_id: Union[str, None]

class CaptchaRequiredException(Exception):
    def __init__(self, message, captcha_url: str, track_id: str = None):
        super().__init__(message)
            
        self.captcha_url = captcha_url
        self.track_id = track_id

class CaptchaNotOpenedException(Exception):
    pass

class WrongPasswordException(Exception):
    pass


class SyncCloudClient:
    session: ClientSession 
    yandex: YandexSession
    loop: AbstractEventLoop
    
    def __init__(self): 
        self.loop = asyncio.get_event_loop()
        self.session = ClientSession(loop = self.loop)

    def start(self):
        try:
            self.loop.run_forever()
        finally:
            self.loop.run_until_complete(self.session.close())

    def get_token(self, username: str, password: str) -> str:
        r = self.__get_token_async(username, password)
        return asyncio.run_coroutine_threadsafe(r, self.loop).result()

    async def __get_token_async(self, username: str, password: str) -> str:
        yandex = YandexSession(self.session)
        response = await yandex.login_username(username, password)

        return self.__check_login_response(response)

    def get_token_captcha(self, username: str, password: str, captcha: str, track_id: str) -> str:
        r = self.__get_token_captcha_async(username, password, captcha, track_id)
        return asyncio.run_coroutine_threadsafe(r, self.loop).result()

    async def __get_token_captcha_async(self, username: str, password: str, captcha: str, track_id: str) -> str:
        yandex = YandexSession(self.session)
        response = await yandex.login_captcha(captcha, password, username, track_id)

        return self.__check_login_response(response)

    def __check_login_response(self, resp: LoginResponse) -> str:
        if resp.ok:
            return resp.x_token

        elif resp.captcha_image_url:
            _LOGGER.debug(f"Captcha required: {resp.captcha_image_url}")
            raise CaptchaRequiredException("Captcha is required", resp.captcha_image_url, resp.track_id)

        elif resp.error == 'captcha.not_shown':
            _LOGGER.debug(f"Captcha was not opened")
            raise CaptchaNotOpenedException("Captcha was not opened")

        elif resp.error == 'password.not_matched' or resp.error == 'password.empty':
            _LOGGER.debug(f"Wrong password")
            raise WrongPasswordException("Wrong password")

        elif resp.external_url:
            raise RuntimeError("External url returned")

        elif resp.error:
            _LOGGER.debug(f"Config error: {resp.error}")
            raise ValueError(resp.error)

        else:
            _LOGGER.debug(f"Unknown error")
            raise RuntimeError("Unknown error")

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

