from telegram.ext import Updater, CommandHandler, MessageHandler
from telegram.ext import  Filters, InlineQueryHandler, TypeHandler, DispatcherHandlerStop
import logging
from telegram import InlineQueryResultArticle, InputTextMessageContent, Update
from dotenv import load_dotenv
import os
from yandex_station.station_client import SyncClient, YandexDeviceConfig


_LOGGER = logging.getLogger(__name__)

load_dotenv()
botToken = os.environ.get('TELEGRAM_BOT_TOKEN')


updater = Updater(token=botToken, use_context=True)
dispatcher = updater.dispatcher


logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                     level=logging.INFO)


def access_check(update, context):
    whitelist = list(os.environ.get('USERS_WHITELIST').split(','))
    if len(whitelist) == 0:
        return
    else:
        if str(update.effective_user.id) in whitelist:
            return
        else:
            context.bot.send_message(chat_id=update.effective_chat.id, text="Sorry, the bot is in the development mode. You don't have access permission.")
            _LOGGER.info('User with ID: ' + str(update.effective_user.id) + ' is not included into the whitelist.')
            raise DispatcherHandlerStop

access_check_handler = TypeHandler(Update, access_check)
dispatcher.add_handler(access_check_handler, 0)

def start(update, context):
    context.bot.send_message(chat_id=update.effective_chat.id, text="I'm a bot, please talk to me!")


start_handler = CommandHandler('start', start)
dispatcher.add_handler(start_handler, 1)


def say_via_alice(update, context):
    station_client.say(update.message.text)


say_via_alice_handler = MessageHandler(Filters.text & (~Filters.command), say_via_alice)
dispatcher.add_handler(say_via_alice_handler, 1)


def caps(update, context):
    text_caps = ' '.join(context.args).upper()
    context.bot.send_message(chat_id=update.effective_chat.id, text=text_caps)


caps_handler = CommandHandler('caps', caps)
dispatcher.add_handler(caps_handler, 1)


def inline_caps(update, context):
    query = update.inline_query.query
    if not query:
        return
    results = list()
    results.append(
        InlineQueryResultArticle(
            id=query.upper(),
            title='Caps',
            input_message_content=InputTextMessageContent(query.upper())
        )
    )
    context.bot.answer_inline_query(update.inline_query.id, results)


inline_caps_handler = InlineQueryHandler(inline_caps)
dispatcher.add_handler(inline_caps_handler, 1)
# Использование: в используемом вами клиенте Телеграмм наберите
# @логин_бота и через пробел какое либо сообщение.  Далее появится
# контекстное меню с выбором преобразования сообщения: UPPER, BOLD, ITALIC.
# Выберете требуемое преобразование.


def unknown(update, context):
    context.bot.send_message(chat_id=update.effective_chat.id, text="Sorry, I didn't understand that command.")


unknown_handler = MessageHandler(Filters.command, unknown)
dispatcher.add_handler(unknown_handler, 1)

name = os.environ.get('NAME')
host = os.environ.get('HOST')
device_id = os.environ.get('DEVICE_ID')
platform = os.environ.get('PLATFORM')

device_config = YandexDeviceConfig(
    name=name,  # Произвольное
    host=host,
    device_id=device_id,
    platform=platform
)

station_client = SyncClient(device_config, os.environ.get('YANDEX_TOKEN'))
updater.start_polling()
try:
    station_client.start()
except KeyboardInterrupt:
    print("Received exit, exiting")
updater.stop()
