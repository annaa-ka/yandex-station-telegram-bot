from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, InlineQueryHandler
import logging
from telegram import InlineQueryResultArticle, InputTextMessageContent
from dotenv import load_dotenv
import os

load_dotenv()
botToken = os.environ.get('TELEGRAM_BOT_TOKEN')


updater = Updater(token=botToken, use_context=True)
dispatcher = updater.dispatcher


logging.basicConfig(format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
                     level=logging.INFO)


def start(update, context):
    context.bot.send_message(chat_id=update.effective_chat.id, text="I'm a bot, please talk to me!")
start_handler = CommandHandler('start', start)
dispatcher.add_handler(start_handler)


def echo(update, context):
    context.bot.send_message(chat_id=update.effective_chat.id, text=update.message.text)


echo_handler = MessageHandler(Filters.text & (~Filters.command), echo)
dispatcher.add_handler(echo_handler)


def caps(update, context):
    text_caps = ' '.join(context.args).upper()
    context.bot.send_message(chat_id=update.effective_chat.id, text=text_caps)
caps_handler = CommandHandler('caps', caps)
dispatcher.add_handler(caps_handler)


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
dispatcher.add_handler(inline_caps_handler)
#Использование: в используемом вами клиенте Телеграмм наберите
# @логин_бота и через пробел какое либо сообщение.  Далее появится
# контекстное меню с выбором преобразования сообщения: UPPER, BOLD, ITALIC.
# Выберете требуемое преобразование.


def unknown(update, context):
    context.bot.send_message(chat_id=update.effective_chat.id, text="Sorry, I didn't understand that command.")
unknown_handler = MessageHandler(Filters.command, unknown)
dispatcher.add_handler(unknown_handler)


updater.start_polling()
updater.idle()















