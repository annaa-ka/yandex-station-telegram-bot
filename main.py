import logging
import os

from dotenv import load_dotenv
from telegram import InlineQueryResultArticle, InputTextMessageContent, Update
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Updater,
    CommandHandler,
    MessageHandler,
    ConversationHandler,
    PicklePersistence,
    Filters,
    InlineQueryHandler,
    TypeHandler,
    DispatcherHandlerStop,
    CallbackQueryHandler
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


def help_func(update, context):
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="The list of the available commands you can find in the menu.")


help_handler = CommandHandler('help', help_func)
dispatcher.add_handler(help_handler, 1)


YANDEX_AUTH_USERNAME, YANDEX_AUTH_PASSWORD, YANDEX_AUTH_CAPTCHA = range(3)


def clean_out_info(context):
    lst = ['yandex_auth_username', 'yandex_auth_captcha_answer', 'yandex_auth_track_id']
    for key in lst:
        context.user_data.pop(key, None)


def start(update, context):
    clean_out_info(context)
    update.message.reply_text("Hi! \n\n"
                              "To start our work we will need to get your yandex station token. \n"
                              "For this step we will need your Yandex ID and password. \n\n"
                              "The command /cancel_authorization is to stop the conversation.")
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="Please, enter your Yandex ID.")
    return YANDEX_AUTH_USERNAME


def yandex_username(update, context):
    context.user_data['yandex_auth_username'] = update.message.text
    update.message.delete()
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="If 2FA is activated for your yandex account, "
        "enter a one-time password. Otherwise, enter your password.")
    return YANDEX_AUTH_PASSWORD


def yandex_password(update, context):
    yandex_auth_password = update.message.text
    update.message.delete()
    try:
        if context.user_data.get('yandex_auth_captcha_answer') is None:
            context.user_data['station_token'] = station_client.get_token(
                                                                            context.user_data['yandex_auth_username'],
                                                                            yandex_auth_password
                                                                            )
        else:
            context.user_data['station_token'] = station_client.get_token_captcha(
                context.user_data['yandex_auth_username'], yandex_auth_password,
                context.user_data['yandex_auth_captcha_answer'], context.user_data['yandex_auth_track_id'])

        update.message.reply_text("Authorization was successful! Use /set_speaker to choose which station we will use.")
        clean_out_info(context)
        return ConversationHandler.END
    except CaptchaRequiredException as err:
        context.user_data['yandex_auth_track_id'] = err.track_id
        context.bot.send_message(
            chat_id=update.effective_chat.id,
            text="Please, type CAPTCHA answer below: " + err.captcha_url)
        return YANDEX_AUTH_CAPTCHA
    except WrongPasswordException:
        update.message.reply_text("The password is wrong. Try again or restart the process with the /start command")
    except Exception:
        update.message.reply_text("Something went wrong. Restart the process with the /start command")
        clean_out_info(context)
        return ConversationHandler.END



def captcha_answer(update, context):
    context.user_data['captcha_auth_answer'] = update.message.text
    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="If 2FA is activated for your yandex account, "
             "enter a new one-time password from app 'Яключ'."
             "Otherwise, enter your password.")
    return YANDEX_AUTH_PASSWORD


def cancel_authorization(update, context):
    clean_out_info(context)
    update.message.reply_text("The authorization process is stopped. If you want to restart, use /start")
    return ConversationHandler.END


station_token_conv_handler = ConversationHandler(
    entry_points=[CommandHandler('start', start)],
    states={
        YANDEX_AUTH_USERNAME: [MessageHandler(Filters.text & (~Filters.command), yandex_username)],
        YANDEX_AUTH_PASSWORD: [MessageHandler(Filters.text & (~Filters.command), yandex_password)],
        YANDEX_AUTH_CAPTCHA: [MessageHandler(Filters.text & (~Filters.command), captcha_answer)],
    },
    fallbacks=[CommandHandler('cancel_authorization', cancel_authorization)],
    allow_reentry=True
)
dispatcher.add_handler(station_token_conv_handler, 1)

YANDEX_CHOOSING_STATION = range(1)


def start_station_choosing(update, context):
    if context.user_data.get('station_token') is None:
        update.message.reply_text("Sorry, you have not authorized yet. Use /start to start our work.")
        return ConversationHandler.END

    update.message.reply_text("Now you need to choose a station which we will use in our work. \n\n"
                              "The command /cancel_station_choosing is to stop the conversation.")

    list_of_speakers = station_client.get_speakers(context.user_data['station_token'])

    inline_keyboard_list = []
    dict_of_station_config = {}

    for elem in list_of_speakers:
        inline_keyboard_list.append(InlineKeyboardButton(elem.name, callback_data=elem.id))
        dict_of_station_config[elem.id] = elem

    keyboard = [inline_keyboard_list]

    context.user_data["dict_of_station_config"] = dict_of_station_config

    reply_markup = InlineKeyboardMarkup(keyboard)
    update.message.reply_text('Please choose:', reply_markup=reply_markup)

    return YANDEX_CHOOSING_STATION


def choose_station(update, context):
    query = update.callback_query
    query.answer()
    speaker_id = query.data


    new_speaker_config = station_client.prepare_speaker(
        context.user_data["station_token"],
        context.user_data["dict_of_station_config"][speaker_id]
    )
    context.user_data["selected_yandex_speaker"] = new_speaker_config

    query.edit_message_text(text=f"Selected option: {new_speaker_config.name}")

    context.bot.send_message(
        chat_id=update.effective_chat.id,
        text="The setup was successful. \n\n"
             "In your yandex cloud we have created a special service script. "
             "Please, do not delete it.")

    context.user_data.pop("dict_of_station_config", None)

    return ConversationHandler.END


def cancel_station_choosing(update, context):
    update.message.reply_text("The process of choosing station is stopped. If you want to restart, use /set_speaker")
    context.user_data.pop("dict_of_station_config", None)
    return ConversationHandler.END


choosing_station_conv_handler = ConversationHandler(
    entry_points=[CommandHandler('set_speaker', start_station_choosing)],
    states={
        YANDEX_CHOOSING_STATION: [CallbackQueryHandler(choose_station)],
    },
    fallbacks=[CommandHandler('cancel_station_choosing', cancel_station_choosing)],
    allow_reentry=True
)
dispatcher.add_handler(choosing_station_conv_handler, 1)


def say_via_alice(update, context):
    if context.user_data.get('station_token') is None:
        update.message.reply_text("Sorry, you have not authorized yet. Use /start to start our work.")
        return

    if context.user_data.get('selected_yandex_speaker') is None:
        update.message.reply_text("Sorry, you have not chosen the station yet. Use /set_speaker to start our work.")
        return

    station_client.say(
        context.user_data["station_token"],
        context.user_data["selected_yandex_speaker"],
        update.message.text
    )


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
