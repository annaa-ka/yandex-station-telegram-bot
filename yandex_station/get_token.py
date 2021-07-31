"""
1. User can enter login/pass from GUI
2. User can set login/pass in YAML
3. If the password requires updating, user need to configure another component
   with the same login.
4. Captcha will be requested if necessary
5. If authorization through YAML does not work, user can continue it through
   the GUI.
"""

#import voluptuous as vol
import logging
_LOGGER = logging.getLogger(__name__)

from aiohttp import ClientSession
import asyncio
from getpass import getpass

from yandex_session import YandexSession, LoginResponse


class YandexTokenRetriever:
    async def get_token(self, username: str, password: str):
        session = ClientSession()
        yandex = YandexSession(session)

        try:
        
            resp = await yandex.login_username(
                username,
                password
            )

            return await self._check_yandex_response(resp)
        finally:
            await session.close()

    async def _check_yandex_response(self, resp: LoginResponse):
        """Check Yandex response. Do not create entry for the same login. Show
        captcha form if captcha required. Show auth form with error if error.
        """
        if resp.ok:
            # set unique_id or return existing entry
            return resp.x_token

        elif resp.captcha_image_url:
            _LOGGER.debug(f"Captcha required: {resp.captcha_image_url}")
            raise RuntimeError("Captcha is required")
            return

        elif resp.external_url:
            raise RuntimeError("External url returned")
            return

        elif resp.error:
            _LOGGER.debug(f"Config error: {resp.error}")
            raise ValueError(resp.error)

if __name__ == "__main__":        
    try:    
        username = input('Provide your username: ')
        password = getpass('Provide your password: ')

        retriever = YandexTokenRetriever()
        r = retriever.get_token(username, password)
        token = asyncio.run(r)
        print()
        print("Your token: " + token)
    except Exception as error:
        print("Error occured: " + str(error))
        
