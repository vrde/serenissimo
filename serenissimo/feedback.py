from .bot import bot, send_message, edit_message_text, edit_message_reply_markup
from . import db
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton


BUTTON = "Ho prenotato la vaccinazione, cancellami"
MESSAGE = "Ottima notizia! <b>Serenissimo ti ha aiutato a trovare posto?</b>"
MESSAGE_UNDO = (
    "OK, non ho cancellato la tua iscrizione, continuerai a ricevere notifiche."
)
MESSAGE_REPLY = "Grazie. <b>Ho cancellato i tuoi dati e non riceverai più alcuna notifica.</b> Per ricominciare puoi usare il bottone qui sotto.\n\nSe hai un commento o un messaggio da condividere, scrivimi a agranzot@mailbox.org, altrimenti buon vaccino!"


def gen_markup_init(markup=None):
    if not markup:
        markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton(BUTTON, callback_data="feedback_init"))
    return markup


def gen_markup_feedback():
    markup = InlineKeyboardMarkup()
    markup.add(
        InlineKeyboardButton(
            "Sì 👍",
            callback_data="feedback_yes",
        ),
        InlineKeyboardButton(
            "No 👎",
            callback_data="feedback_no",
        ),
        row_width=2,
    )
    markup.add(InlineKeyboardButton("Annulla", callback_data="feedback_undo"))
    return markup


@bot.callback_query_handler(func=lambda call: call.data.startswith("feedback_"))
def callback_query(call):
    telegram_id = str(call.from_user.id)
    call_id = call.id
    message_id = call.message.id
    data = call.data

    with db.connection() as c:
        user = db.user.by_telegram_id(c, telegram_id)
        if not user:
            bot.answer_callback_query(call_id, show_alert=False)
            return

    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton("Ricomincia", callback_data="main_start"))

    # Empty reply to the original query
    bot.answer_callback_query(call_id, show_alert=False)
    if data == "feedback_init":
        # Create a new message to display the extra information
        send_message(telegram_id, MESSAGE, reply_markup=gen_markup_feedback())
    elif data == "feedback_undo":
        edit_message_reply_markup(telegram_id, message_id, reply_markup=False)
        send_message(telegram_id, MESSAGE_UNDO)
    elif data == "feedback_yes":
        with db.transaction() as t:
            user = db.user.by_telegram_id(t, telegram_id)
            if user:
                db.user.delete(t, user["id"])
                db.log.insert(t, "booked", True)
        send_message(telegram_id, MESSAGE_REPLY, reply_markup=markup)
    elif data == "feedback_no":
        with db.transaction() as t:
            user = db.user.by_telegram_id(t, telegram_id)
            if user:
                db.user.delete(t, user["id"])
                db.log.insert(t, "booked", False)
        send_message(telegram_id, MESSAGE_REPLY, reply_markup=markup)
