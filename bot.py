import json
import logging
import os
import sys
import traceback
from collections import Counter
from datetime import datetime
from hashlib import sha256
from random import shuffle
from threading import Lock, Thread
from time import sleep, time

import telebot
from codicefiscale import codicefiscale
from dotenv import load_dotenv
from telebot import apihelper, types

from agent import (
    RecoverableException,
    UnknownPayload,
    check,
    format_locations,
    format_state,
)

logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
log = logging.getLogger()
load_dotenv()
db_lock = Lock()


ADMIN_ID = os.getenv("ADMIN_ID")
TOKEN = os.getenv("TELEGRAM_TOKEN")
bot = telebot.TeleBot(TOKEN, parse_mode=None)


def send_message(chat_id, *messages, reply_markup=None, parse_mode="HTML"):
    bot.send_message(
        chat_id, "\n".join(messages), reply_markup=reply_markup, parse_mode=parse_mode
    )


def reply_to(message, *messages):
    bot.reply_to(message, "\n".join(messages))


@bot.message_handler(commands=["start", "ricomincia"])
@bot.message_handler(
    func=lambda message: message.text and message.text.strip().lower() == "ricomincia"
)
def send_welcome(message):
    chat_id = str(message.chat.id)
    if chat_id in db:
        del db[chat_id]
        save_db(db)
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
        chat_id,
        "Ciao, me ciamo Serenissimo e i me gà programmà par darte na man coa prenotasiòn del vacino, queo anti-covid se intende.",
        "",
        "Praticamente controeo ogni 30 minuti se ghe xe posto par prenotarte.",
        "",
        "Per comunicazioni ufficiali riguardo ai vaccini controlla il sito https://vaccinicovid.regione.veneto.it/. "
        "Il bot è stato creato da Alberto Granzotto, per informazioni digita /info",
    )
    send_message(chat_id, "Seleziona la tua ULSS 👇", reply_markup=markup)


@bot.message_handler(commands=["controlla"])
@bot.message_handler(
    func=lambda message: message.text and message.text.strip().lower() == "controlla"
)
def check_message(message):
    chat_id = str(message.chat.id)
    state, notified = notify_locations(chat_id, verbose=True)


@bot.message_handler(commands=["cancella"])
@bot.message_handler(
    func=lambda message: message.text and message.text.strip().lower() == "cancella"
)
def delete_message(message):
    chat_id = str(message.chat.id)
    if chat_id in db:
        del db[chat_id]
        save_db(db)
    send_message(
        chat_id,
        "Ho cancellato i tuoi dati, non riceverai più nessuna notifica.",
        "Se vuoi ricominciare digita /ricomincia",
    )


@bot.message_handler(commands=["vaccinato"])
@bot.message_handler(
    func=lambda message: message.text and message.text.strip().lower() == "vaccinato"
)
def vaccinated_message(message):
    chat_id = str(message.chat.id)
    send_message(
        chat_id,
        "🎉 Complimenti! 🎉",
        "",
        "Ho cancellato i tuoi dati, non riceverai più nessuna notifica.",
        "Se vuoi ricominciare digita /ricomincia",
    )
    if chat_id in db:
        cf = db[chat_id].get("cf")
        if cf:
            hash = sha256(cf.encode("utf-8")).hexdigest()
            db["vaccinated:" + hash] = {"vaccinated": True}
        del db[chat_id]
        save_db(db)
        send_stats()


@bot.message_handler(regexp="^ULSS[1-9] .+$")
def ulss_message(message):
    chat_id = str(message.chat.id)
    ulss = message.text.split()[0][-1]
    db[chat_id] = {
        "chat_id": chat_id,
        "ulss": ulss,
    }
    markup = types.ReplyKeyboardRemove(selective=False)
    send_message(
        chat_id,
        "Oro benon. Ultimo passo, mandami il tuo codice fiscale 👇",
        reply_markup=markup,
    )
    save_db(db)


def clean_cf(s):
    return "".join(s.split()).upper()


INFO_MESSAGE = "\n".join(
    [
        "Per cambiare Codice Fiscale o ULSS, digita /ricomincia",
        "Per cancellarti, digita /cancella",
        "Se vuoi più informazioni o vuoi segnalare un errore, digita /info",
        "Per informazioni ufficiali https://vaccinicovid.regione.veneto.it/",
    ]
)


@bot.message_handler(
    func=lambda message: message.text and codicefiscale.is_valid(clean_cf(message.text))
)
def code_message(message):
    cf = clean_cf(message.text)
    chat_id = str(message.chat.id)

    if chat_id not in db:
        send_welcome(message)
        return

    db[chat_id]["cf"] = cf
    save_db(db)
    ulss = db[chat_id].get("ulss")

    if not ulss:
        send_welcome(message)
        return

    state, notified = notify_locations(chat_id)
    if state == "not_eligible":
        send_message(
            chat_id,
            "Non appartieni alle categorie che attualmente possono prenotare.",
            "Ogni 4 ore controllerò se si liberano posti per {} nella ULSS {} "
            "<b>Ti notifico solo se ci sono novità.</b>".format(cf, ulss),
        )
    if state == "not_registered":
        send_message(
            chat_id,
            "Il codice fiscale {} non risulta tra quelli "
            "registrati presso la ULSS {}".format(cf, ulss),
            "Controlla comunque nel sito ufficiale e se ho sbagliato per favore contattami!",
            "Per adesso non c'è altro che posso fare per te.",
        )
    elif state == "already_vaccinated":
        send_message(
            chat_id,
            "Per il codice fiscale inserito è già iniziato il percorso vaccinale.",
            "Controlla comunque nel sito ufficiale e se ho sbagliato per favore contattami!",
            "Per adesso non c'è altro che posso fare per te.",
        )
    elif state == "already_booked":
        send_message(
            chat_id, 
            "Per il codice fiscale inserito è già registrata una prenotazione.",
            "Controlla comunque nel sito ufficiale e se ho sbagliato per favore contattami!",
            "Per adesso non c'è altro che posso fare per te.",
        )
    else:
        send_message(
            chat_id,
            "Ogni 30 minuti controllerò se si liberano posti per {} nella ULSS {} "
            "<b>Ti notifico solo se ci sono novità.</b>".format(cf, ulss),
        )
    send_message(chat_id, INFO_MESSAGE)
    send_stats()
    save_db(db)


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
        "    - La ULSS di riferimento.",
        "- I tuoi dati sono memorizzati in un server in Germania.",
        '- Se digiti "cancella", i tuoi dati vengono eliminati completamente.',
        "- Il codice del bot è pubblicato su https://github.com/vrde/serenissimo e chiunque può verificarne il funzionamento.",
    )


#########
# ADMIN #
#########


def from_admin(message):
    return ADMIN_ID == str(message.chat.id)


def send_stats():
    c = Counter({"people": 0, "vaccinated": 0, "registered": 0})
    for k, v in db.copy().items():
        c["people"] += 1
        if k.startswith("vaccinated"):
            c["vaccinated"] += 1
        if v.get("cf"):
            c["registered"] += 1
    send_message(
        ADMIN_ID,
        "People: {people}\nRegistered: {registered}\nVaccinated: {vaccinated}".format(
            **c
        ),
    )


@bot.message_handler(commands=["stats"])
def stats_message(message):
    if from_admin(message):
        send_stats()


@bot.message_handler(commands=["broadcast"])
def broadcast_message(message):
    if from_admin(message):
        c = Counter()
        start = time()
        chat_ids = list(db.copy().keys())
        text = message.text[11:]
        if not text:
            return
        for chat_id in chat_ids:
            user = db.get(chat_id, {})
            cf = user.get("cf")
            ulss = user.get("ulss")
            if not cf or not ulss:
                continue
            c["total"] += 1
            log.info("Broadcast message to %s", chat_id)
            try:
                send_message(chat_id, text)
            except Exception as e:
                stack = traceback.format_exception(*sys.exc_info())
                send_message(ADMIN_ID, "🤬🤬🤬\n" + "".join(stack))
                print("".join(stack))
        end = time()
        send_message(
            ADMIN_ID, "Sent {} messages in {:.2f}s".format(c["total"], end - start)
        )


@bot.message_handler(func=lambda message: True)
def fallback_message(message):
    reply_to(
        message,
        "No go capìo.",
        "Per cambiare codice fiscale o ULSS, digita /ricomincia",
        "Per cancellarti, digita /cancella",
        "Se vuoi più informazioni o vuoi segnalare un errore, digita /info",
    )


######
# DB #
######


def load_db():
    try:
        with open("db.json", "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def save_db(db):
    with db_lock:
        with open("db.json", "w") as f:
            json.dump(db.copy(), f, indent=2)


def notify_locations(chat_id, verbose=False):
    # Load user
    user = db.get(chat_id)

    # Check if user exists
    if not user:
        return None, None

    cf = user.get("cf")
    ulss = user.get("ulss")
    state = user.get("state")
    now = time()

    # Check if user has all fields required to book an appointment
    if not cf or not ulss:
        return None, None

    attempt = 0
    while True:
        attempt += 1
        try:
            state, available_locations, unavailable_locations = check(cf, ulss)
            break
        except RecoverableException:
            if attempt == 3:
                log.error("HTTP Error while checking chat_id %s", chat_id)
                return None, None
        except UnknownPayload:
            log.exeption("Error for chat_id %s, CF %s, ULSS %s", chat_id, cf, ulss)
            stack = traceback.format_exception(*sys.exc_info())
            send_message(ADMIN_ID, "🤬🤬🤬\n" + "".join(stack))

    old_locations = user.get("locations", [])
    formatted_available = format_locations(available_locations)
    formatted_unavailable = format_locations(unavailable_locations)
    formatted_old = format_locations(old_locations)

    should_notify = formatted_available != formatted_old and available_locations

    log.info("Check chat_id %s, CF %s, ULSS %s, state %s", chat_id, cf, ulss, state)

    if verbose:
        log.info(
            "Notify Verbose chat_id %s, CF %s, ULSS %s, locations %s",
            chat_id,
            cf,
            ulss,
            formatted_available,
        )
        send_message(
            chat_id,
            "<b>Sedi disponibili:</b>",
            "",
            formatted_available or "Non ci sono risultati",
            "",
            "",
            "<b>Sedi NON disponibili:</b>" "",
            "",
            formatted_unavailable or "Non ci sono risultati",
            "",
            "",
            "Prenotati su https://vaccinicovid.regione.veneto.it/",
            "Se riesci a vaccinarti, scrivi /vaccinato per non ricevere più notifiche.",
            "",
            "<i>Per alcune categorie è richiesta l'autocertificazione.</i>"
        )
        user["locations"] = available_locations
        user["last_message"] = now

    # If something changed, we send all available locations to the user
    elif should_notify:
        log.info(
            "Notify chat_id %s, CF %s, ULSS %s, locations %s",
            chat_id,
            cf,
            ulss,
            formatted_available,
        )
        send_message(
            chat_id,
            "Sedi disponibili:",
            "",
            formatted_available,
            "",
            "Prenotati su https://vaccinicovid.regione.veneto.it/",
            "",
            "<i>Per alcune categorie è richiesta l'autocertificazione.</i>"
        )
        user["locations"] = available_locations
        user["last_message"] = now
    user["state"] = state
    user["last_check"] = now
    return state, should_notify


ELIGIBLE_DELTA = 30 * 60  # Wait 30 min for eligible
NON_ELIGIBLE_DELTA = 4 * 60 * 60  # Wait 4 hours for other categories
ALREADY_BOOKED_DELTA = 24 * 60 * 60  # Wait 24 hours for already booked


def should_check(chat_id):
    user = db.get(chat_id, {})
    cf = user.get("cf")
    ulss = user.get("ulss")
    if not user or not cf or not ulss:
        return False
    now = time()
    state = user.get("state")
    last_check = user.get("last_check", 0)
    delta = now - last_check
    return (
        (state == "eligible" and delta > ELIGIBLE_DELTA)
        or (state == "maybe_eligible" and delta > ELIGIBLE_DELTA)
        or (state == "not_eligible" and delta > NON_ELIGIBLE_DELTA)
        or (state == "already_booked" and delta > ALREADY_BOOKED_DELTA)
    )


def check_loop():
    sleep(600)
    while True:
        c = Counter()
        start = time()
        chat_ids = list(db.copy().keys())
        shuffle(chat_ids)
        for chat_id in chat_ids:
            if not should_check(chat_id):
                continue
            c["total"] += 1
            try:
                state, notified = notify_locations(chat_id)
                if state:
                    c[state] += 1
                    if notified:
                        c["success"] += 1
                        save_db(db)
            except KeyboardInterrupt:
                sys.exit()
            except Exception as e:
                stack = traceback.format_exception(*sys.exc_info())
                send_message(ADMIN_ID, "🤬🤬🤬\n" + "".join(stack))
                print("".join(stack))
        end = time()
        save_db(db)
        if c["total"] > 0:
            send_message(
                ADMIN_ID,
                "🏁 Done checking for locations",
                "\n".join("{} {}".format(k, v) for k, v in c.items()),
                "Total time: {:.2f}s".format(end - start),
            )
        sleep(600)


db = load_db()
save_db(db)

if __name__ == "__main__":
    log.info("Start Serenissimo bot, viva el doge, viva el mar!")
    Thread(target=check_loop, daemon=True).start()
    apihelper.SESSION_TIME_TO_LIVE = 5 * 60
    try:
        bot.polling()
    except KeyboardInterrupt:
        print("Ciao")
        sys.exit()
    except Exception as e:
        stack = traceback.format_exception(*sys.exc_info())
        send_message(ADMIN_ID, "🤬🤬🤬\n" + "".join(stack))
        print("".join(stack))
