import logging
_LOGGER = logging.getLogger(__name__)

from aiohttp import ClientSession
import asyncio
from getpass import getpass

from yandex_session import YandexSession, LoginResponse

class CaptchaRequiredException(Exception):
    def __init__(self, message, captcha_url):
        super().__init__(message)
            
        self.captcha_url = captcha_url

class CaptchaNotOpenedException(Exception):
    pass

class WrongPasswordException(Exception):
    pass


class YandexTokenRetriever:
    async def get_token(self, username: str):
        session = ClientSession()
        yandex = YandexSession(session)

        tasks = ['login']
        captcha_url = None
        password = ''

        try: 
            for task in tasks:
                if task == 'login':
                    requestText = 'Provide your password'
                    if password:
                        requestText += ' [ENTER to use the previous one]'

                    print()
                    newPassword = getpass(requestText + ': ')
                    if newPassword:
                        password = newPassword

                    try:
                        # Workaround for the bug:
                        # https://github.com/aio-libs/aiohttp/issues/4549
                        await asyncio.sleep(0.1)

                        resp = await yandex.login_username(
                            username,
                            password
                        )
                        
                        return self._check_yandex_response(resp)
               
                    except CaptchaRequiredException as err:
                        captcha_url = err.captcha_url
                        tasks.append('captcha')
               
                    except WrongPasswordException:
                        print('Wrong password, try again.')
                        tasks.append('login')
                
                elif task == 'captcha':
                    try:
                        print()
                        print("Please, open the following URL in the browser and type the CAPTCHA below:")
                        print(captcha_url)
                        captcha_answer = input("CAPTCHA answer: ")

                        print()
                        print("In case of one-time passwords don't use the same, wait for a new one generated.")
                        newPassword = getpass('Provide your password [ENTER to use the previous one]: ')
                        if newPassword:
                            password = newPassword

                        # Workaround for the bug:
                        # https://github.com/aio-libs/aiohttp/issues/4549
                        await asyncio.sleep(0.1)

                        resp = await yandex.login_captcha(captcha_answer, password)
                        
                        return self._check_yandex_response(resp)
                    
                    except WrongPasswordException:
                        print('Wrong password, try again.')
                        tasks.append('login')
                    
                    except CaptchaNotOpenedException:
                        print('You need to open url in the browser to read the CAPTCHA.')
                        tasks.append('captcha')
                    
                    except CaptchaRequiredException as err:
                        print('Incorrect CAPTCHA!')
                        captcha_url = err.captcha_url
                        tasks.append('captcha')
        finally:
            await session.close()

    def _check_yandex_response(self, resp: LoginResponse):
        """Check Yandex response. Do not create entry for the same login. Show
        captcha form if captcha required. Show auth form with error if error.
        """
        if resp.ok:
            # set unique_id or return existing entry
            return resp.x_token

        elif resp.captcha_image_url:
            _LOGGER.debug(f"Captcha required: {resp.captcha_image_url}")
            raise CaptchaRequiredException("Captcha is required", resp.captcha_image_url)
            return

        elif resp.error == 'captcha.not_shown':
            _LOGGER.debug(f"Captcha was not opened")
            raise CaptchaNotOpenedException("Captcha was not opened")
            return

        elif resp.error == 'password.not_matched' or resp.error == 'password.empty':
            _LOGGER.debug(f"Wrong password")
            raise WrongPasswordException("Wrong password")
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

        retriever = YandexTokenRetriever()
        r = retriever.get_token(username)
        token = asyncio.get_event_loop().run_until_complete(r)
        print()
        print("Your token: " + token)
    except KeyboardInterrupt:
        print()
        print("Received exit, exiting")
    except Exception as error:
        print()
        print("Error occurred: " + str(error))
        
