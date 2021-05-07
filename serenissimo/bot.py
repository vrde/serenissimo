import json
import logging
import os
import sys
import re
import traceback
from collections import Counter
from datetime import datetime
from hashlib import sha256
from random import shuffle
from threading import Lock, Thread
from time import sleep, time

import telebot
from codicefiscale import codicefiscale
from telebot import apihelper, types

from . import db
from .agent import (
    RecoverableException,
    UnknownPayload,
    check,
    format_locations,
    format_state,
)

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
    telegram_id = str(message.chat.id)
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


@bot.message_handler(commands=["start", "ricomincia"])
@bot.message_handler(
    func=lambda message: message.text and message.text.strip().lower() == "ricomincia"
)
def send_welcome(message):
    telegram_id = str(message.chat.id)

    # Remove all previous data
    with db.transaction() as t:
        user = db.user.by_telegram_id(t, telegram_id)
        if user:
            db.user.delete(t, user["id"])
        db.user.insert(t, telegram_id)

    markup = types.ReplyKeyboardMarkup(row_width=2)
    buttons = [
        types.KeyboardButton("ULSS1 Dolomiti"),
        types.KeyboardButton("ULSS2 Marca Trevigiana"),
        types.KeyboardButton("ULSS3 Serenissima"),
        types.KeyboardButton("ULSS4 Veneto Orientale"),
        types.KeyboardButton("ULSS5 Polesana"),
        types.KeyboardButton("ULSS6 Euganea"),
        types.KeyboardButton("ULSS7 Pedemontana"),
        types.KeyboardButton("ULSS8 Berica"),
        types.KeyboardButton("ULSS9 Scaligera"),
    ]
    markup.add(*buttons)
    send_message(
        telegram_id,
        "Ciao, me ciamo Serenissimo e i me gà programmà par darte na man coa prenotasiòn del vacino, queo anti-covid se intende.",
        "",
        "Praticamente controeo ogni ora se ghe xe posto par prenotarte.",
        "",
        "Per comunicazioni ufficiali riguardo ai vaccini controlla il sito https://vaccinicovid.regione.veneto.it/. "
        "Il bot è stato creato da Alberto Granzotto, per informazioni digita /info",
    )
    send_message(telegram_id, "Seleziona la tua ULSS 👇", reply_markup=markup)


@bot.message_handler(regexp="^ULSS[1-9] .+$")
def ulss_message(message):
    telegram_id = str(message.chat.id)
    ulss_id = int(message.text.split()[0][-1])

    with db.transaction() as t:
        user = db.user.by_telegram_id(t, telegram_id)
        if user:
            # Load the last subscription
            subscription = db.subscription.last_by_user(t, user["id"])

            # If there is one but it's incomplete, update it.
            if subscription and (
                not subscription["ulss_id"] or not subscription["fiscal_code"]
            ):
                db.subscription.update(t, subscription["id"], ulss_id=ulss_id)
            # If there isn't one or the one we loaded is complete, create a new one.
            else:
                db.subscription.insert(t, user["id"], ulss_id=ulss_id)

    if not user:
        return send_welcome(message)

    markup = types.ReplyKeyboardRemove(selective=False)
    send_message(
        telegram_id,
        "Oro benón. Mandami il tuo codice fiscale 👇",
        reply_markup=markup,
    )


def clean_fiscal_code(s):
    return "".join(s.split()).upper()


INFO_MESSAGE = (
    "- Per ricominciare digita /ricomincia",
    "- Per cancellarti digita /cancella",
    "- Se vuoi più informazioni o vuoi segnalare un errore digita /info",
)


@bot.message_handler(
    func=lambda message: message.text
    and codicefiscale.is_valid(clean_fiscal_code(message.text))
)
def fiscal_code_message(message):
    fiscal_code = clean_fiscal_code(message.text)
    telegram_id = str(message.chat.id)

    with db.transaction() as t:
        user = db.user.by_telegram_id(t, telegram_id)
        if user:
            subscription = db.subscription.last_by_user(t, user["id"])
            if (
                subscription
                and subscription["ulss_id"]
                and not subscription["fiscal_code"]
            ):
                # We do a sync check for locations right after. To avoid
                # overlapping with the worker (that might pick up this
                # subscription as well) we set the last check to now.
                db.subscription.update(
                    t, subscription["id"], fiscal_code=fiscal_code, set_last_check=True
                )

    if not user or not subscription or not subscription["ulss_id"]:
        return send_welcome(message)

    markup = types.ReplyKeyboardRemove(selective=False)
    send_message(
        telegram_id,
        'Ultimo sforso! Mandami le <u>ultime sei cifre</u> della tua <a href="https://it.wikipedia.org/wiki/Tessera_sanitaria">tessera sanitaria europea</a> 👇',
        reply_markup=markup,
    )


def clean_health_insurance_number(text):
    if text:
        text = text.replace(" ", "")
        if re.match("^\d{6}$", text):
            return text


@bot.message_handler(func=lambda m: clean_health_insurance_number(m.text))
def health_insurance_number_message(message):
    health_insurance_number = clean_health_insurance_number(message.text)
    telegram_id = str(message.chat.id)

    with db.transaction() as t:
        user = db.user.by_telegram_id(t, telegram_id)
        if user:
            subscription = db.subscription.last_by_user(t, user["id"])
            if subscription and subscription["ulss_id"] and subscription["fiscal_code"]:
                # We do a sync check for locations right after. To avoid
                # overlapping with the worker (that might pick up this
                # subscription as well) we set the last check to now.
                db.subscription.update(
                    t,
                    subscription["id"],
                    health_insurance_number=health_insurance_number,
                    set_last_check=True,
                )

    if (
        not user
        or not subscription
        or not subscription["ulss_id"]
        or not subscription["fiscal_code"]
    ):
        return send_welcome(message)

    state_id, notified = notify_locations(subscription["id"], sync=True)
    send_stats()


@bot.message_handler(commands=["controlla"])
@bot.message_handler(
    func=lambda message: message.text and message.text.strip().lower() == "controlla"
)
def check_message(message):
    telegram_id = str(message.chat.id)
    with db.connection() as c:
        user = db.user.by_telegram_id(c, telegram_id)
        subscription = db.subscription.last_by_user(c, user["id"])
    if subscription:
        state, notified = notify_locations(subscription["id"], sync=True)
    else:
        send_welcome(message)


@bot.message_handler(commands=["cancella"])
@bot.message_handler(
    func=lambda message: message.text and message.text.strip().lower() == "cancella"
)
def delete_message(message):
    telegram_id = str(message.chat.id)
    with db.transaction() as t:
        user = db.user.by_telegram_id(t, telegram_id)
        if user:
            db.user.delete(t, user["id"])
    send_message(
        telegram_id,
        "Ho cancellato i tuoi dati, non riceverai più nessuna notifica.",
        "Se vuoi ricominciare digita /ricomincia",
    )


@bot.message_handler(commands=["vaccinato"])
@bot.message_handler(
    func=lambda message: message.text and message.text.strip().lower() == "vaccinato"
)
def vaccinated_message(message):
    telegram_id = str(message.chat.id)
    with db.transaction() as t:
        user = db.user.by_telegram_id(t, telegram_id)
        if user:
            db.user.delete(t, user["id"])
            db.log.insert(t, "vaccinated")
    send_message(
        telegram_id,
        "🎉 Complimenti! 🎉",
        "",
        "Ho cancellato i tuoi dati, non riceverai più nessuna notifica.",
        "Se vuoi ricominciare digita /ricomincia",
    )


@bot.message_handler(commands=["info", "informazioni", "aiuto", "privacy"])
@bot.message_handler(
    func=lambda message: message.text
    and message.text.strip().lower() in ["info", "aiuto", "privacy"]
)
def send_info(message):
    chat_id = str(message.chat.id)
    send_message(
        chat_id,
        'Questo bot è stato creato da <a href="https://www.granzotto.net/">Alberto Granzotto</a> (agranzot@mailbox.org). '
        "Ho creato il bot di mia iniziativa, se trovi errori o hai correzioni mandami una mail. "
        "Il codice sorgente è rilasciato come software libero ed è disponibile su GitHub: https://github.com/vrde/serenissimo",
        "",
        "Per cambiare codice fiscale o ULSS, digita /ricomincia",
        "Per cancellarti, digita /cancella",
        "",
        "Informativa sulla privacy:",
        "- I tuoi dati vengono usati esclusivamente per controllare la disponibilità di un appuntamento per la vaccinazione usando il sito https://vaccinicovid.regione.veneto.it/",
        "- Nel database i dati memorizzati sono:",
        "    - Il tuo identificativo di Telegram (NON il numero di telefono).",
        "    - Il suo codice fiscale.",
        "    - Le ultime sei cifre della tua tessera sanitaria.",
        "    - La ULSS di riferimento.",
        "- I tuoi dati sono memorizzati in un server in Germania.",
        '- Se digiti "cancella", i tuoi dati vengono eliminati completamente.',
        "- Il codice del bot è pubblicato su https://github.com/vrde/serenissimo e chiunque può verificarne il funzionamento.",
    )


def from_admin(message):
    return ADMIN_ID == str(message.chat.id)


def send_stats():
    stats = db.stats.select(db.connect())
    send_message(
        ADMIN_ID,
        f"Users: {stats['users']}",
        f"Users (incomplete): {stats['users_incomplete']}",
        f"Vaccinated: {stats['vaccinated']}",
    )


@bot.message_handler(commands=["stats"])
def stats_message(message):
    if from_admin(message):
        send_stats()


@bot.message_handler(commands=["broadcast"])
def broadcast_message(message):
    if not from_admin(message):
        return
    text = message.text[11:]
    if not text:
        return
    total = 0
    start = time()
    with db.connection() as c:
        for user in db.user.select_active(c):
            total += 1
            telegram_id = user["telegram_id"]
            log.info("Broadcast message to %s", telegram_id)
            send_message(telegram_id, text)
    end = time()
    send_message(ADMIN_ID, f"Sent {total} messages in {end-start:.2}s")


@bot.message_handler(func=lambda message: True)
def fallback_message(message):
    reply_to(
        message,
        "No go capìo.",
        *INFO_MESSAGE,
    )


def notify_locations(subscription_id, sync=False):
    with db.connection() as c:
        s = db.subscription.by_id(c, subscription_id)

    if not s or not s["ulss_id"] or not s["fiscal_code"]:
        return None, None

    telegram_id = s["telegram_id"]
    fiscal_code = s["fiscal_code"]
    health_insurance_number = s["health_insurance_number"]
    ulss_id = s["ulss_id"]
    old_locations = json.loads(s["locations"])

    attempt = 0
    while True:
        attempt += 1
        try:
            status_id, available_locations, unavailable_locations = check(
                ulss_id, fiscal_code, health_insurance_number
            )
            break
        except RecoverableException:
            if attempt == 3:
                log.error(
                    "HTTP Error for telegram_id %s, ulss_id %s, fiscal_code %s",
                    telegram_id,
                    ulss_id,
                    fiscal_code,
                )
                stack = traceback.format_exception(*sys.exc_info())
                send_message(ADMIN_ID, "🤬🤬🤬\n" + "".join(stack))
                if sync:
                    send_message(
                        telegram_id,
                        "Errore: non riesco a contattare il portale della Regione. ",
                        "Il problema è temporaneo, riprova tra qualche minuto.",
                    )
                return None, None
        except UnknownPayload:
            log.exception(
                "Payload Error for telegram_id %s, ulss_id %s, fiscal_code %s",
                telegram_id,
                ulss_id,
                fiscal_code,
            )
            stack = traceback.format_exception(*sys.exc_info())
            send_message(ADMIN_ID, "🤬🤬🤬\n" + "".join(stack))
            if sync:
                send_message(
                    telegram_id,
                    "Errore: sembra che il portale della Regione sia cambiato. "
                    "Potrebbe essere una cosa temporanea, fai un paio di tentativi. "
                    "Se il problema persiste cercherò di sistemarlo al più presto.",
                )
            return None, None

    formatted_available = format_locations(available_locations)
    formatted_unavailable = format_locations(unavailable_locations, limit=500)
    formatted_old = format_locations(old_locations)

    should_notify = formatted_available != formatted_old and available_locations

    log.info(
        "Check telegram_id %s, CF %s, ULSS %s, state %s",
        telegram_id,
        fiscal_code,
        ulss_id,
        status_id,
    )

    if sync:
        log.info(
            "Notify sync telegram_id %s, CF %s, ULSS %s, state %s, locations %s",
            telegram_id,
            fiscal_code,
            ulss_id,
            status_id,
            formatted_available,
        )

        if formatted_available or formatted_unavailable:
            send_message(
                telegram_id,
                "<b>Sedi disponibili:</b>",
                "",
                formatted_available or "Al momento non ci sono sedi disponibili\n",
            )
            send_message(
                telegram_id,
                "<b>Sedi NON disponibili:</b>",
                "",
                formatted_unavailable or "Non ci sono risultati\n",
            )
            send_message(
                telegram_id,
                'Prenotati sul <a href="https://vaccinicovid.regione.veneto.it/">Portale della Regione</a> e ricorda che '
                "<i>per alcune prenotazioni è richiesta l'autocertificazione</i>.",
            )

        if status_id == "not_eligible":
            send_message(
                telegram_id,
                f"Ogni 4 ore controllerò se si liberano posti per {fiscal_code} nella ULSS {ulss_id}. "
                "<u>Ti notifico solo se ci sono novità.</u>",
                "",
                *INFO_MESSAGE,
            )
        elif status_id == "not_registered":
            send_message(
                telegram_id,
                f"<b>Il codice fiscale {fiscal_code} non risulta tra quelli registrati presso la ULSS {ulss_id}.</b>",
                "Controlla comunque nel sito ufficiale e se ho sbagliato per favore contattami!",
                "Per cambiare ULSS o Codice Fiscale, digita /ricomincia",
                "Per /ricomincia",
            )
        elif status_id == "wrong_health_insurance_number":
            send_message(
                telegram_id,
                f"<b>Il numero di tessera sanitaria {health_insurance_number} non è corretto.</b>",
                "Controlla comunque nel sito ufficiale e se ho sbagliato per favore contattami!",
                "Se vuoi ricominciare digita /ricomincia",
                'Se vuoi riprovare digita di nuovo le <u>ultime sei cifre</u> della tua <a href="https://it.wikipedia.org/wiki/Tessera_sanitaria">tessera sanitaria europea</a> (quella plastificata per intenderci) 👇',
            )
        elif status_id == "already_vaccinated":
            send_message(
                telegram_id,
                "<b>Per il codice fiscale inserito è già iniziato il percorso vaccinale.</b>",
                "Controlla comunque nel sito ufficiale e se ho sbagliato per favore contattami!",
                "Per adesso non c'è altro che posso fare per te.",
                "",
                *INFO_MESSAGE,
            )
        elif status_id == "already_booked":
            send_message(
                telegram_id,
                "<b>Per il codice fiscale inserito è già registrata una prenotazione.</b>",
                "Controlla comunque nel sito ufficiale e se ho sbagliato per favore contattami!",
                "Per adesso non c'è altro che posso fare per te.",
                "",
                *INFO_MESSAGE,
            )
        else:
            send_message(
                telegram_id,
                f"Ogni ora controllerò se si liberano posti per {fiscal_code} nella ULSS {ulss_id}. "
                "<u>Ti notifico solo se ci sono novità.</u>",
                "",
                *INFO_MESSAGE,
            )

    # If something changed, we send all available locations to the user
    elif should_notify:
        log.info(
            "Notify chat_id %s, CF %s, ULSS %s, locations %s",
            telegram_id,
            fiscal_code,
            ulss_id,
            formatted_available,
        )
        send_message(
            telegram_id,
            "<b>Sedi disponibili</b>",
            "",
            formatted_available,
            '<a href="https://serenissimo.granzotto.net/#perch%C3%A9-ricevo-notifiche-per-categorie-a-cui-non-appartengo">Come funzionano le notifiche?</a>',
            "",
            'Prenotati sul <a href="https://vaccinicovid.regione.veneto.it/">Portale della Regione</a> e ricorda che '
            "<i>per alcune prenotazioni è richiesta l'autocertificazione</i>.",
        )
    with db.transaction() as t:
        db.subscription.update(
            t,
            subscription_id,
            status_id=status_id,
            locations=json.dumps(available_locations),
            set_last_check=True,
        )
    return status_id, should_notify


def check_loop():
    if not DEV:
        sleep(60)
    while True:
        stats = Counter()
        start = time()
        with db.connection() as c:
            for s in db.subscription.select_stale(c):
                stats["total"] += 1
                state, notified = notify_locations(s["subscription_id"])
                stats[state] += 1
                if notified:
                    stats["notified"] += 1
                    with db.transaction() as t:
                        db.log.insert(t, "notification", s["ulss_id"])
        end = time()
        if stats["total"] > 0:
            send_message(
                ADMIN_ID,
                "🏁 Done checking for locations",
                "\n".join(f"{k} {v}" for k, v in stats.items()),
                f"Total time: {end-start:.2f}s",
            )
        sleep(60)


if __name__ == "__main__":
    log.info("Start Serenissimo bot, viva el doge, viva el mar!")
    with db.transaction() as t:
        db.init(t)
        db.init_data(t)
    Thread(target=check_loop, daemon=True).start()
    apihelper.SESSION_TIME_TO_LIVE = 5 * 60
    try:
        bot.polling()
    except KeyboardInterrupt:
        sys.exit()
    except Exception as e:
        stack = traceback.format_exception(*sys.exc_info())
        send_message(ADMIN_ID, "🤬🤬🤬\n" + "".join(stack))
        print("".join(stack))
