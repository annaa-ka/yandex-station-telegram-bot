import logging
import os

from dotenv import load_dotenv
from telegram import InlineQueryResultArticle, InputTextMessageContent, Update
from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    PicklePersistence,
    Filters,
    InlineQueryHandler,
    TypeHandler,
    DispatcherHandlerStop
)

from yandex_station.station_client_cloud import (
    SyncCloudClient,
    CaptchaRequiredException,
    WrongPasswordException
)

_LOGGER = logging.getLogger(__name__)

load_dotenv()
botToken = os.environ.get('TELEGRAM_BOT_TOKEN')

my_persistence = PicklePersistence(filename='bot_data.bin')
updater = Updater(token=botToken, persistence=my_persistence, use_context=True)
dispatcher = updater.dispatcher
whitelist = os.environ.get('USERS_WHITELIST', "").split(',')

logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                    level=logging.INFO)


def access_check(update, context):
    if len(whitelist) == 0:
        return
    if str(update.effective_user.id) not in whitelist:
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Sorry, the bot is in the development mode. "
                 "You don't have access permission.")
        _LOGGER.info('User with ID: ' + str(update.effective_user.id) + ' is not included into the whitelist.')
        raise DispatcherHandlerStop
    return


access_check_handler = TypeHandler(Update, access_check)
dispatcher.add_handler(access_check_handler, 0)

USERNAME_, PASSWORD_, CAPTCHA_ = range(3)


def clean_out_info(context):
    lst = {'yandex_username_', 'yandex_captcha_answer_', 'yandex_track_id_'}
    for key in lst:
        context.user_data.pop(key, None)


def start(update, context):
    clean_out_info(context)
    update.message.reply_text("Hi! \n"
                              "To start our work we will need to get your yandex station token. \n"
                              "For this step we will need your Yandex ID and password. \n"
                              "The command /cancel is to stop the conversation.")
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Please, enter your Yandex ID.")
    return USERNAME_


def yandex_username_(update, context):
    context.user_data['yandex_username_'] = update.message.text
    update.message.delete()
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="If 2FA is activated for your yandex account, "
        "enter a one-time password. Otherwise, enter your password.")
    return PASSWORD_


def yandex_password_(update, context):
    yandex_password = update.message.text
    update.message.delete()
    try:
        if context.user_data.get('yandex_captcha_answer_') is None:
            context.user_data['station_token_'] = station_client.get_token(
                                                                            context.user_data['yandex_username_'],
                                                                            yandex_password
                                                                            )
        else:
            context.user_data['station_token_'] = station_client.get_token_captcha(
                context.user_data['yandex_username_'], yandex_password,
                context.user_data['yandex_captcha_answer_'], context.user_data['yandex_track_id_'])

        update.message.reply_text("Authorization was successful!!!")
        clean_out_info(context)
    except CaptchaRequiredException as err:
        context.user_data['yandex_track_id_'] = err.track_id
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Please, type CAPTCHA answer below: " + err.captcha_url)
        return CAPTCHA_
    except WrongPasswordException:
        update.message.reply_text("The password is wrong. Try again using /start.")
    except Exception:
        update.message.reply_text("Something went wrong. Try again using /start.")


def captcha_answer_(update, context):
    context.user_data['captcha_answer_'] = update.message.text
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="If 2FA is activated for your yandex account, "
             "enter a one-time password from app 'Яключ'."
             "You might need a new one in case the previous one ran out of time."
             "Otherwise, enter your password.")
    return PASSWORD_


def cancel(update, context):
    clean_out_info(context)
    update.message.reply_text("The authorization process is stopped. If you want to restart, use /start")
    return ConversationHandler.END


conv_handler = ConversationHandler(
    entry_points=[CommandHandler('start', start)],
    states={
        USERNAME_: [MessageHandler(Filters.text & (~Filters.command), yandex_username_)],
        PASSWORD_: [MessageHandler(Filters.text & (~Filters.command), yandex_password_)],
        CAPTCHA_: [MessageHandler(Filters.text & (~Filters.command), captcha_answer_)],
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

station_client = SyncCloudClient()
updater.start_polling()
try:
    station_client.start()
except KeyboardInterrupt:
    print("Received exit, exiting")
updater.stop()
