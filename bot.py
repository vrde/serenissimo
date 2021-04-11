from time import sleep
from dotenv import load_dotenv
from threading import Thread
from datetime import datetime
from collections import Counter
import traceback
import json
import sys
import telebot
from telebot import types, apihelper
import os
import requests
from bs4 import BeautifulSoup
from codicefiscale import codicefiscale
import logging
logging.basicConfig(level=logging.INFO,
                    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
log = logging.getLogger()
load_dotenv()


class InvalidCodeException(Exception):
    pass


ADMIN_ID = os.getenv('ADMIN_ID')
TOKEN = os.getenv('TELEGRAM_TOKEN')
bot = telebot.TeleBot(TOKEN, parse_mode=None)


@bot.message_handler(commands=['start', 'ricomincia'])
@bot.message_handler(func=lambda message: message.text and message.text.strip().lower() == 'ricomincia')
def send_welcome(message):
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
        message.chat.id, "Ciao, me ciamo Serenissimo e i me gà programmà par darte na man coa prenotasiòn del vacino, queo anti-covid se intende."
    )
    bot.send_message(
        message.chat.id, "Praticamente te me dixi ła ULSS e el to codice fiscałe, e mi controeo ogni ora se ghe xe posto par prenotarte."
    )
    bot.send_message(
        message.chat.id, "Per qualsiasi informazione controlla il sito ufficiale https://vaccinicovid.regione.veneto.it/")
    bot.send_message(
        message.chat.id, "Seleziona la tua ULSS.",
        reply_markup=markup)


@bot.message_handler(commands=['cancella'])
@bot.message_handler(func=lambda message: message.text and message.text.strip().lower() == 'cancella')
def delete_message(message):
    chat_id = str(message.chat.id)
    bot.send_message(
        message.chat.id, "Ho cancellato i tuoi dati, non riceverai più nessuna notifica. Se vuoi ricominciare digita /ricomincia"
    )
    del db[chat_id]
    save_db(db)


@bot.message_handler(regexp="^ULSS[1-9] .+$")
def ulss_message(message):
    chat_id = str(message.chat.id)
    ulss = message.text.split()[0][-1]
    db[chat_id] = {'cf': None, 'chat_id': chat_id,
                   'ulss': ulss, 'known_spots': []}
    markup = types.ReplyKeyboardRemove(selective=False)
    bot.send_message(
        message.chat.id, "Oro benon. Ultimo passo, mandami il tuo codice fiscale",
        reply_markup=markup)
    save_db(db)


@bot.message_handler(func=lambda message: message.text and codicefiscale.is_valid(message.text.strip()))
def code_message(message):
    cf = message.text.strip().upper()
    chat_id = str(message.chat.id)
    db[chat_id]['cf'] = cf
    try:
        check(cf, chat_id)
    except InvalidCodeException:
        bot.send_message(
            chat_id, "Non appartieni alle categorie che attualmente possono prenotare.")
        bot.send_message(
            chat_id, 'Controllerò comunque se si liberano posti per {} nella ULSS {} (controllo ogni ora).'.format(
                cf, db[chat_id]['ulss']))
    else:
        bot.send_message(
            message.chat.id, "Sei nella categoria di persone che possono prenotare! Ti avverto non appena si liberano posti per la vaccinazione (controllo ogni ora).")
    bot.send_message(
        chat_id, "Se vuoi cambiare codice fiscale o ULSS, digita /ricomincia")
    bot.send_message(chat_id, "Se vuoi cancellarti, digita /cancella")
    bot.send_message(ADMIN_ID, "New user")
    send_stats()
    save_db(db)


@bot.message_handler(commands=['info', 'informazioni', 'aiuto'])
@bot.message_handler(func=lambda message: message.text and message.text.strip().lower() in ['info', 'aiuto'])
def send_welcome(message):
    bot.send_message(
        message.chat.id, '\n'.join(['Questo bot è stato creato da <a href="https://www.granzotto.net/">Alberto Granzotto</a> (agranzot@mailbox.org).',
                                    "Il codice sorgente è rilasciato come software libero ed è disponibile su GitHub: https://github.com/vrde/serenissimo"]),
        parse_mode='HTML'
    )

#########
# ADMIN #
#########


def from_admin(message):
    return ADMIN_ID == str(message.chat.id)


def send_stats():
    c = Counter()
    for k, v in db.items():
        c['people'] += 1
        if v.get('cf'):
            c['registered'] += 1
    bot.send_message(
        ADMIN_ID, "People: {people}\nRegistered: {registered}".format(**c))


@ bot.message_handler(commands=['stats'])
def stats_message(message):
    if from_admin(message):
        send_stats()


@ bot.message_handler(func=lambda message: True)
def fallback_message(message):
    bot.reply_to(message, '\n'.join([
        "No go capìo.",
        "Se vuoi cambiare codice fiscale o ULSS, digita /ricomincia",
        "Se vuoi cancellarti, digita /cancella"]))


def check_availability(cf, ulss):
    log.info('Check availability for %s, ULSS %s', cf, ulss)
    data = {'cod_fiscale': cf}
    s = requests.Session()
    s.post('https://vaccinicovid.regione.veneto.it/ulss{}'.format(ulss))
    s.post('https://vaccinicovid.regione.veneto.it/ulss{}/azione/controllocf'.format(ulss), data=data)
    r = s.post(
        'https://vaccinicovid.regione.veneto.it/ulss{}/azione/sceglisede/servizio/2'.format(ulss), data=data)
    soup = BeautifulSoup(r.text, 'html.parser')
    spots = []
    for b in soup.find_all('button'):
        if 'disabled' not in b.attrs:
            spots.append(b.text.strip())
    if len(spots) == 1 and spots[0].strip() == 'Torna indietro':
        raise InvalidCodeException()
    return spots


def load_db():
    try:
        with open('db.json', 'r') as f:
            return json.load(f)
    except FileNotFoundError:
        return {}


def save_db(db):
    with open('db.json', 'w') as f:
        json.dump(db, f, indent=2)


def check(cf, chat_id):
    known_spots = db[chat_id]['known_spots']
    ulss = db[chat_id]['ulss']
    available_spots = check_availability(cf, ulss)

    spots = list(filter(lambda s: s not in known_spots, available_spots))
    if spots:
        log.info('Notify %s, ULSS %s, spots %s', cf, ulss, ', '.join(spots))
        bot.send_message(
            chat_id, "Sedi disponibili:\n{}\n\nPrenotati su https://vaccinicovid.regione.veneto.it/".format('\n'.join(spots)))
    db[chat_id]['known_spots'] = available_spots


def check_loop():
    sleep(60)
    while True:
        for chat_id, s in db.items():
            if s['cf'] and s['ulss']:
                try:
                    check(s['cf'], s['chat_id'])
                except InvalidCodeException:
                    pass
                save_db(db)
        sleep(3600)


if __name__ == "__main__":
    log.info('Start Serenissimo bot, viva el doge, viva el mar!')
    db = load_db()
    save_db(db)
    Thread(target=check_loop).start()
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
