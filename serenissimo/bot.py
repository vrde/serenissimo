import logging
import os

import telebot
from telebot import apihelper

from . import db

log = logging.getLogger()


DEV = os.getenv("DEV")
ADMIN_ID = os.getenv("ADMIN_ID")
TOKEN = os.getenv("TELEGRAM_TOKEN")

bot = telebot.TeleBot(TOKEN, parse_mode=None)


def send_message(telegram_id, *messages, reply_markup=None, parse_mode="HTML"):
    if DEV:
        telegram_id = ADMIN_ID
    try:
        bot.send_message(
            telegram_id,
            "\n".join(messages),
            reply_markup=reply_markup,
            parse_mode=parse_mode,
            disable_web_page_preview=True,
        )
    except apihelper.ApiTelegramException as e:
        log.exception("Error sending message %s", "\n".join(messages))
        if e.error_code == 403:
            # User blocked us, remove them
            log.info("User %s blocked us, delete all their data", telegram_id)
            with db.transaction() as t:
                user = db.user.by_telegram_id(t, telegram_id)
                if user:
                    db.user.delete(t, user["id"])


def reply_to(message, *messages):
    telegram_id = str(message.from_user.id)
    try:
        bot.reply_to(message, "\n".join(messages))
    except apihelper.ApiTelegramException as e:
        log.exception("Error sending message %s", "\n".join(messages))
        if e.error_code == 403:
            # User blocked us, remove them
            log.info("User %s blocked us, delete all their data", telegram_id)
            with db.transaction() as t:
                user = db.user.by_telegram_id(t, telegram_id)
                if user:
                    db.user.delete(t, user["id"])


def edit_message_text(
    text,
    chat_id=None,
    message_id=None,
    inline_message_id=None,
    parse_mode=None,
    disable_web_page_preview=None,
    reply_markup=None,
):
    try:
        bot.edit_message_text(
            text,
            chat_id=chat_id,
            message_id=message_id,
            inline_message_id=inline_message_id,
            parse_mode=parse_mode,
            disable_web_page_preview=disable_web_page_preview,
            reply_markup=reply_markup,
        )
    except apihelper.ApiTelegramException as e:
        if e.error_code == 400:
            log.warning("Error editing message")
        else:
            raise
