import json
import logging
import os
import sys
import re
import traceback
from collections import Counter
from threading import Thread
from time import sleep, time


from telebot import apihelper
from .bot import bot, send_message, reply_to

from . import snooze
from . import feedback
from . import stats
from . import db
from .agent import (
    HTTPException,
    ApplicationException,
    UnknownPayload,
    check,
    format_locations,
)

log = logging.getLogger()


DEV = os.getenv("DEV")
ADMIN_ID = os.getenv("ADMIN_ID")

@bot.message_handler(commands=["start", "ricomincia"])
@bot.message_handler(
    func=lambda message: message.text and message.text.strip().lower() == "ricomincia"
)
def send_welcome(message):
    telegram_id = str(message.from_user.id)
    send_message(
        telegram_id,
        "Ciao, Serenissimo è stato disattivato il 25 agosto.",
        "",
        "Per prenotarti per la vaccinazione visita il sito https://vaccinicovid.regione.veneto.it/.",
        "Il bot è gestito da Alberto Granzotto, per informazioni digita /info",
    )


@bot.message_handler(commands=["cancella"])
@bot.message_handler(
    func=lambda message: message.text and message.text.strip().lower() == "cancella"
)
def delete_message(message):
    telegram_id = str(message.from_user.id)
    with db.transaction() as t:
        user = db.user.by_telegram_id(t, telegram_id)
        if user:
            db.user.delete(t, user["id"])
    send_message(
        telegram_id,
        "Ho cancellato i tuoi dati, non riceverai più nessuna notifica.",
        "Se vuoi ricominciare digita /ricomincia",
    )



@bot.message_handler(commands=["info", "informazioni", "aiuto", "privacy"])
@bot.message_handler(
    func=lambda message: message.text
    and message.text.strip().lower() in ["info", "aiuto", "privacy"]
)
def send_info(message):
    chat_id = str(message.from_user.id)
    send_message(
        chat_id,
        'Questo bot è stato creato da <a href="https://www.granzotto.net/">Alberto Granzotto</a> (agranzot@mailbox.org). '
        "Ho creato il bot di mia iniziativa, se trovi errori o hai correzioni mandami una mail. "
        "Il codice sorgente è rilasciato come software libero ed è disponibile su GitHub: https://github.com/vrde/serenissimo",
        "",
        "Per cancellarti, digita /cancella",
        "",
        "Informativa sulla privacy:",
        "- Nel database i dati memorizzati sono:",
        "    - Il tuo identificativo di Telegram (NON il numero di telefono).",
        "    - Il suo codice fiscale.",
        "    - Le ultime sei cifre della tua tessera sanitaria.",
        "    - La ULSS di riferimento.",
        "- I tuoi dati sono memorizzati in un server in Germania.",
        '- Se digiti "cancella", i tuoi dati vengono eliminati completamente.',
        "- Il codice del bot è pubblicato su https://github.com/vrde/serenissimo e chiunque può verificarne il funzionamento.",
    )


@bot.message_handler(func=lambda message: True)
def fallback_message(message):
    telegram_id = str(message.from_user.id)
    if message.text:
        log.info("Unknown message: %s", message.text)
    reply_to(
        message,
        "Ciao, Serenissimo è stato disattivato il 25 agosto.",
        "",
        "Per prenotarti per la vaccinazione visita il sito https://vaccinicovid.regione.veneto.it/.",
        "Il bot è gestito da Alberto Granzotto, per informazioni digita /info",
    )


if __name__ == "__main__":
    log.info("Start Serenissimo bot, viva el doge, viva el mar!")
    with db.transaction() as t:
        db.init(t)
        db.init_data(t)
    apihelper.SESSION_TIME_TO_LIVE = 5 * 60
    try:
        bot.polling()
    except KeyboardInterrupt:
        sys.exit()
    except Exception as e:
        stack = traceback.format_exception(*sys.exc_info())
        send_message(ADMIN_ID, "🤬🤬🤬\n" + "".join(stack))
        print("".join(stack))
