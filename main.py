from telegram.ext import Updater, CommandHandler, MessageHandler, ConversationHandler, PicklePersistence
from telegram.ext import  Filters, InlineQueryHandler, TypeHandler, DispatcherHandlerStop
import logging
from telegram import InlineQueryResultArticle, InputTextMessageContent, Update
from dotenv import load_dotenv
import os
from yandex_station.station_client_cloud import SyncCloudClient, CaptchaRequiredException, WrongPasswordException
from yandex_station.station_client import YandexDeviceConfig


_LOGGER = logging.getLogger(__name__)

load_dotenv()
botToken = os.environ.get('TELEGRAM_BOT_TOKEN')

my_persistence = PicklePersistence(filename='my_file.txt')
updater = Updater(token=botToken,  persistence=my_persistence,  use_context=True)
dispatcher = updater.dispatcher
whitelist = os.environ.get('USERS_WHITELIST', "").split(',')


logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                     level=logging.INFO)



def access_check(update, context):
    if len(whitelist) == 0:
        return
    if str(update.effective_user.id) not in whitelist:
            context.bot.send_message(chat_id=update.effective_chat.id, text="Sorry, the bot is in the "
                                        "development mode. You don't have access permission.")
            _LOGGER.info('User with ID: ' + str(update.effective_user.id) + ' is not included into the whitelist.')
            raise DispatcherHandlerStop
    return


access_check_handler = TypeHandler(Update, access_check)
dispatcher.add_handler(access_check_handler, 0)


USERNAME, PASSWORD, CAPTCHA = range(3)


def start(update, context):
    update.message.reply_text("Hello. Nice to meet you! The command /cancel is to stop the conversation.")
    context.bot.send_message(chat_id=update.effective_chat.id, text="Please, enter station username.")
    return USERNAME


def username_(update, context):
    context.user_data['username_'] = update.message.text
    update.message.delete()
    context.bot.send_message(chat_id=update.effective_chat.id, text="Please, enter station password.")
    return PASSWORD


def password_(update, context):
    context.user_data['password_'] = update.message.text
    update.message.delete()
    try:
        if context.user_data.get('captcha_answer_') is None:
            context.user_data['token_'] = station_client.get_token(context.user_data['username_'],
                                                                   context.user_data['password_'])
            update.message.reply_text("Your yandex_station token: " + context.user_data['token_'])
        else:
            context.user_data['token_'] = station_client.get_token_captcha(context.user_data['username_'],
                                        context.user_data['password_'], context.user_data['captcha_answer_'],
                                                                           context.user_data['track_id_'])
            update.message.reply_text("Your yandex_station token: " + context.user_data['token_'])
    except CaptchaRequiredException as err:
        context.user_data['track_id_'] = err.track_id
        context.bot.send_message(chat_id=update.effective_chat.id,
                                 text="Please, open the following URL in the browser and type the "
                                      "CAPTCHA answer below: " +
                                 err.captcha_url)
        return CAPTCHA
    except WrongPasswordException:
        update.message.reply_text("The password is wrong. Try again.")
    except Exception:
        update.message.reply_text("Try again.")


def capthcha_(update, context):
    context.user_data['captcha_answer_'] = update.message.text
    context.bot.send_message(chat_id=update.effective_chat.id,
                             text="Please, enter station password.")
    return PASSWORD


def cancel(update, _):
    return ConversationHandler.END


conv_handler = ConversationHandler(
        entry_points=[CommandHandler('start', start)],
        states={
            USERNAME: [MessageHandler(Filters.text & (~Filters.command), username_)],
            PASSWORD: [MessageHandler(Filters.text & (~Filters.command), password_)],
            CAPTCHA: [MessageHandler(Filters.text & (~Filters.command), capthcha_)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
        allow_reentry=True
    )
dispatcher.add_handler(conv_handler, 1)


# def say_via_alice(update, context):
#   station_client.say(update.message.text)
#
#
# say_via_alice_handler = MessageHandler(Filters.text & (~Filters.command), say_via_alice)
# dispatcher.add_handler(say_via_alice_handler, 1)


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


station_client = SyncCloudClient()
updater.start_polling()
try:
    station_client.start()
except KeyboardInterrupt:
    print("Received exit, exiting")
updater.stop()
