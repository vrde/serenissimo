import os
from hashlib import sha256
from time import time, sleep
from dotenv import load_dotenv
from threading import Thread, Lock
from datetime import datetime
from collections import Counter
from random import shuffle
import traceback
import json
import sys
import telebot
from telebot import types, apihelper
from codicefiscale import codicefiscale
import logging
from check import check as check

logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
log = logging.getLogger()
load_dotenv()
db_lock = Lock()


ADMIN_ID = os.getenv('ADMIN_ID')
TOKEN = os.getenv('TELEGRAM_TOKEN')
bot = telebot.TeleBot(TOKEN, parse_mode=None)


@bot.message_handler(commands=['start', 'ricomincia'])
@bot.message_handler(func=lambda message: message.text and message.text.strip().lower() == 'ricomincia')
def send_welcome(message):
    chat_id = str(message.chat.id)
    if chat_id in db:
        del db[chat_id]
        save_db(db)
    markup = types.ReplyKeyboardMarkup(row_width=2)
    buttons = [
        types.KeyboardButton('ULSS1 Dolomiti'),
        types.KeyboardButton('ULSS2 Marca Trevigiana'),
        types.KeyboardButton('ULSS3 Serenissima'),
        types.KeyboardButton('ULSS4 Veneto Orientale'),
        types.KeyboardButton('ULSS5 Polesana'),
        types.KeyboardButton('ULSS6 Euganea'),
        types.KeyboardButton('ULSS7 Pedemontana'),
        types.KeyboardButton('ULSS8 Berica'),
        types.KeyboardButton('ULSS9 Scaligera'),
    ]
    markup.add(*buttons)
    bot.send_message(
        message.chat.id, '\n\n'.join([
            "🔔 AVVISO 🔔",
            "Il portale di prenotazione https://vaccinicovid.regione.veneto.it/ ha modificato la gestione delle categorie fragili. A causa di questo aggiornamento alcune funzionalità di Serenissimo non sono al momento disponibili. Sto lavorando per ripristinarle quanto prima.",
            "Invito comunque a controllare il sito ufficiale: https://vaccinicovid.regione.veneto.it/",
        ]))
    bot.send_message(
        message.chat.id, '\n\n'.join([
            "Ciao, me ciamo Serenissimo e i me gà programmà par darte na man coa prenotasiòn del vacino, queo anti-covid se intende.",
            "Praticamente controeo ogni 30 minuti se ghe xe posto par prenotarte.",
            "Per comunicazioni ufficiali riguardo ai vaccini controlla il sito https://vaccinicovid.regione.veneto.it/.",
            "Il bot è stato creato da Alberto Granzotto, per informazioni digita /info"]))
    bot.send_message(
        message.chat.id, "Seleziona la tua ULSS 👇",
        reply_markup=markup)


@bot.message_handler(commands=['cancella'])
@bot.message_handler(func=lambda message: message.text and message.text.strip().lower() == 'cancella')
def delete_message(message):
    chat_id = str(message.chat.id)
    bot.send_message(
        message.chat.id, '\n'.join(["Ho cancellato i tuoi dati, non riceverai più nessuna notifica.",
                                    "Se vuoi ricominciare digita /ricomincia"]))
    if chat_id in db:
        del db[chat_id]
        save_db(db)


@bot.message_handler(commands=['vaccinato'])
@bot.message_handler(func=lambda message: message.text and message.text.strip().lower() == 'vaccinato')
def vaccinated_message(message):
    chat_id = str(message.chat.id)
    bot.send_message(
        message.chat.id, '\n'.join(["🎉 Complimenti! 🎉",
                                    "Ho cancellato i tuoi dati, non riceverai più nessuna notifica.",
                                    "Se vuoi ricominciare digita /ricomincia"]))
    if chat_id in db:
        cf = db[chat_id].get('cf')
        if cf:
            hash = sha256(cf.encode('utf-8')).hexdigest()
            db['vaccinated:' + hash] = {"vaccinated": True}
        del db[chat_id]
        save_db(db)
        send_stats()


@bot.message_handler(regexp="^ULSS[1-9] .+$")
def ulss_message(message):
    chat_id = str(message.chat.id)
    ulss = message.text.split()[0][-1]
    db[chat_id] = {'chat_id': chat_id, 'ulss': ulss, }
    markup = types.ReplyKeyboardRemove(selective=False)
    bot.send_message(
        message.chat.id, "Oro benon. Ultimo passo, mandami il tuo codice fiscale 👇",
        reply_markup=markup)
    save_db(db)


def clean_cf(s):
    return ''.join(s.split()).upper()


@bot.message_handler(func=lambda message: message.text and codicefiscale.is_valid(clean_cf(message.text)))
def code_message(message):
    cf = clean_cf(message.text)
    chat_id = str(message.chat.id)
    if chat_id not in db:
        send_welcome(message)
        return
    db[chat_id]['cf'] = cf
    save_db(db)
    state, locations, notified = notify_locations(chat_id)
    if state == 'not_eligible':
        bot.send_message(
            message.chat.id, '\n'.join(["Non sei nella categoria di persone che attualmente si possono prenotare. "
                                        "Se pensi sia un errore prova a cambiare ULSS o controlla il sito ufficiale https://vaccinicovid.regione.veneto.it/."]))
    elif state == 'already_vaccinated':
        bot.send_message(
            message.chat.id, "Sei già stato vaccinato.")
    bot.send_message(
        chat_id, '\n'.join([
            "Per cambiare codice fiscale o ULSS, digita /ricomincia",
            "Per cancellarti, digita /cancella",
            "Se vuoi più informazioni o vuoi segnalare un errore, digita /info",
        ]))
    bot.send_message(
        chat_id, 'Se lasci tutto così, controllerò se si liberano posti per {} nella ULSS {} (controllo ogni 30 minuti).'.format(
            cf, db[chat_id]['ulss']))
    send_stats()
    save_db(db)


@ bot.message_handler(commands=['info', 'informazioni', 'aiuto', 'privacy'])
@ bot.message_handler(func=lambda message: message.text and message.text.strip().lower() in ['info', 'aiuto', 'privacy'])
def send_info(message):
    bot.send_message(
        message.chat.id, '\n'.join(['Questo bot è stato creato da <a href="https://www.granzotto.net/">Alberto Granzotto</a> (agranzot@mailbox.org). '
                                    "Ho creato il bot di mia iniziativa, se trovi errori o hai correzioni mandami una mail. "
                                    "Il codice sorgente è rilasciato come software libero ed è disponibile su GitHub: https://github.com/vrde/serenissimo",
                                    '', '',
                                    'Informativa sulla privacy:',
                                    '- I tuoi dati vengono usati esclusivamente per controllare la disponibilità di un appuntamento per la vaccinazione usando il sito https://vaccinicovid.regione.veneto.it/',
                                    '- Nel database i dati memorizzati sono:',
                                    '    - Il tuo identificativo di Telegram (NON il numero di telefono).',
                                    '    - Il suo codice fiscale.',
                                    '    - La ULSS di riferimento.',
                                    '- I tuoi dati sono memorizzati in un server in Germania.',
                                    '- Se digiti "cancella", i tuoi dati vengono eliminati completamente.',
                                    '- Il codice del bot è pubblicato su https://github.com/vrde/serenissimo e chiunque può verificarne il funzionamento.'
                                    ]),
        parse_mode='HTML'
    )


#########
# ADMIN #
#########

def from_admin(message):
    return ADMIN_ID == str(message.chat.id)


def send_stats():
    c = Counter({"people": 0, "vaccinated": 0, "registered": 0})
    for k, v in db.copy().items():
        c['people'] += 1
        if k.startswith("vaccinated"):
            c['vaccinated'] += 1
        if v.get('cf'):
            c['registered'] += 1
    bot.send_message(
        ADMIN_ID, "People: {people}\nRegistered: {registered}\nVaccinated: {vaccinated}".format(**c))


@bot.message_handler(commands=['stats'])
def stats_message(message):
    if from_admin(message):
        send_stats()


@bot.message_handler(commands=['broadcast'])
def broadcast_message(message):
    if from_admin(message):
        c = Counter()
        start = time()
        chat_ids = list(db.copy().keys())
        text = message.text[11:]
        if not text:
            return
        for chat_id in chat_ids:
            c['total'] += 1
            log.info('Broadcast message to %s', chat_id)
            try:
                bot.send_message(chat_id, text)
            except Exception as e:
                stack = traceback.format_exception(*sys.exc_info())
                bot.send_message(
                    ADMIN_ID, '🤬🤬🤬\n' + ''.join(stack))
                print(''.join(stack))
        end = time()
        bot.send_message(ADMIN_ID, "Sent {} messages in {:.2f}s".format(c['total'], end-start))

@bot.message_handler(func=lambda message: True)
def fallback_message(message):
    bot.reply_to(message, '\n'.join([
        "No go capìo.",
        "Per cambiare codice fiscale o ULSS, digita /ricomincia",
        "Per cancellarti, digita /cancella",
        "Se vuoi più informazioni o vuoi segnalare un errore, digita /info",
    ]))


######
# DB #
######


def load_db():
    try:
        with open('db.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def save_db(db):
    with db_lock:
        with open('db.json', 'w') as f:
            json.dump(db.copy(), f, indent=2)


def notify_locations(chat_id):
    # Load user
    user = db.get(chat_id)

    # Check if user exists
    if not user:
        return None, None, None

    cf = user.get('cf')
    ulss = user.get('ulss')
    now = time()

    # Check if user has all fields required to book an appointment
    if not cf or not ulss:
        return None, None, None

    old_locations = user.get('locations', [])
    state, available_locations = check(cf, ulss)
    new_locations = set(old_locations).symmetric_difference(
        set(available_locations))

    log.info('Check %s, ULSS %s, state %s', cf, ulss, state)

    # If we find some new locations, we send all available locations to the user
    if new_locations and available_locations:
        log.info('Notify %s, ULSS %s, locations %s',
                 cf, ulss, ', '.join(available_locations))
        bot.send_message(
            chat_id, '\n'.join(
                ["Sedi disponibili:",
                 "",
                 "\n".join('- ' + l for l in available_locations),
                 "",
                 "Prenotati su https://vaccinicovid.regione.veneto.it/",
                 "Se riesci a vaccinarti, scrivi /vaccinato per non ricevere più notifiche."
                 ]))
        user['locations'] = available_locations
        user['last_message'] = now
    user['state'] = state
    user['last_check'] = now
    return state, new_locations, new_locations and available_locations


ELIGIBLE_DELTA = 30*60 # Wait 30 min for eligible
ELIGIBLE_SPECIAL_DELTA = 30*60 # Wait 30 min for eligible special
NON_ELIGIBLE_DELTA = 4*60*60 # Wait 4 hours for other categories


def should_check(chat_id):
    user = db.get(chat_id)
    cf = user.get('cf')
    ulss = user.get('ulss')
    if not user or not cf or not ulss:
        return False
    now = time()
    state = user.get('state')
    last_check = user.get('last_check', 0)
    delta = now - last_check
    return (state == 'eligible' and delta > ELIGIBLE_DELTA) or\
            (state == 'eligible_special' and delta > ELIGIBLE_SPECIAL_DELTA) or\
            (delta > NON_ELIGIBLE_DELTA)


def check_loop():
    sleep(60)
    while True:
        c = Counter()
        start = time()
        chat_ids= list(db.copy().keys())
        shuffle(chat_ids)
        for chat_id in chat_ids:
            if not should_check(chat_id):
                continue
            c['total'] += 1
            try:
                state, locations, notified = notify_locations(chat_id)
                if state:
                    c[state] += 1
                    if notified:
                        c['success'] += 1
                        save_db(db)
            except KeyboardInterrupt:
                print("Ciao")
                sys.exit()
            except Exception as e:
                stack = traceback.format_exception(*sys.exc_info())
                bot.send_message(
                    ADMIN_ID, '🤬🤬🤬\n' + ''.join(stack))
                print(''.join(stack))
        end = time()
        save_db(db)
        if c['total'] > 0:
            bot.send_message(
                ADMIN_ID,
                '\n'.join(["🏁 Done checking for locations",
                        "Messages sent: {}".format(c['success']),
                        "Eligible: {}".format(c['eligible']),
                        "Eligible special: {}".format(c['eligible_special']),
                        "Not eligible: {}".format(c['not_eligible']),
                        "Already vaccinated: {}".format(
                            c['already_vaccinated']),
                        "Total time: {:.2f}s".format(end-start)])
            )
        sleep(10)


if __name__ == "__main__":
    log.info('Start Serenissimo bot, viva el doge, viva el mar!')
    db = load_db()
    save_db(db)
    Thread(target=check_loop, daemon=True).start()
    apihelper.SESSION_TIME_TO_LIVE = 5 * 60
    try:
        bot.polling()
    except KeyboardInterrupt:
        print("Ciao")
        sys.exit()
    except Exception as e:
        stack = traceback.format_exception(*sys.exc_info())
        bot.send_message(
            ADMIN_ID, '🤬🤬🤬\n' + ''.join(stack))
        print(''.join(stack))
