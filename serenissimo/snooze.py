from .bot import bot, send_message, edit_message_text
from . import db
from telebot.types import InlineKeyboardMarkup, InlineKeyboardButton


MESSAGE_CLOSED = (
    "Le notifiche notturne ti disturbano?\nSe sì, schiaccia il pulsante qui sotto 👇"
)
BUTTON_CLOSED = "🌜 Modifica gli orari delle notifiche 🦉"
MESSAGE_OPEN = "⏰ se vuoi disattivare le notifiche di notte, seleziona l'intervallo orario che preferisci e non ti disturberò!"


def init_message(telegram_id):
    send_message(telegram_id, MESSAGE_CLOSED, reply_markup=gen_markup_settings())


def gen_markup_settings():
    markup = InlineKeyboardMarkup()
    markup.add(InlineKeyboardButton(BUTTON_CLOSED, callback_data="snooze_show"))
    return markup


def gen_markup_snooze(snooze_from, snooze_to):
    markup = InlineKeyboardMarkup()
    keys = [
        ["👇 Dalle ore 👇", "noop"],
        ["👇 Alle ore 👇", "noop"],
        ["20:00", "snooze_from_20"],
        ["6:00", "snooze_to_06"],
        ["22:00", "snooze_from_22"],
        ["8:00", "snooze_to_08"],
        ["24:00", "snooze_from_24"],
        ["10:00", "snooze_to_10"],
    ]

    from_key = None if snooze_from is None else f"snooze_from_{snooze_from:02}"
    to_key = None if snooze_to is None else f"snooze_to_{snooze_to:02}"

    buttons = [
        InlineKeyboardButton(
            f"{label} ✅" if key in [from_key, to_key] else label,
            callback_data=key,
        )
        for label, key in keys
    ]

    label_no_thanks = "No grazie, lascia le notifiche attive"

    markup.add(*buttons, row_width=2)
    markup.add(
        InlineKeyboardButton(
            f"{label_no_thanks} ✅"
            if from_key is None and to_key is None
            else label_no_thanks,
            callback_data="snooze_none",
        ),
        row_width=1,
    )
    # Show save button only if the user selected a valid interval or an empty interval
    if bool(snooze_from is None) == bool(snooze_to is None):
        markup.add(
            InlineKeyboardButton("Salva e chiudi", callback_data="snooze_hide"),
        )
    return markup


@bot.callback_query_handler(func=lambda call: True)
def callback_query(call):
    # print(call)
    telegram_id = str(call.from_user.id)
    call_id = call.id
    message_id = call.message.id
    data = call.data
    with db.connection() as c:
        user = db.user.by_telegram_id(c, telegram_id)
        if not user:
            return
        snooze_from_current = user["snooze_from"]
        snooze_to_current = user["snooze_to"]
        snooze_from = snooze_from_current
        snooze_to = snooze_to_current

    if data == "noop":
        bot.answer_callback_query(call_id, show_alert=False)
    elif data.startswith("snooze_"):
        # Show snooze markup
        if data == "snooze_show":
            interval = ""
            if snooze_from is not None and snooze_to is not None:
                interval = f"Non ti mando notifiche tra le <b>{snooze_from}:00</b> e le <b>{snooze_to}:00</b>"
            edit_message_text(
                f"{MESSAGE_OPEN}\n\n{interval}",
                telegram_id,
                message_id,
                reply_markup=gen_markup_snooze(snooze_from_current, snooze_to_current),
                parse_mode="HTML",
            )
            bot.answer_callback_query(call_id, show_alert=False)
        # Hide snooze markup
        elif data == "snooze_hide":
            edit_message_text(
                MESSAGE_CLOSED,
                telegram_id,
                message_id,
                reply_markup=gen_markup_settings(),
            )
            bot.answer_callback_query(call_id, "Impostazioni salvate")
        else:
            if data.startswith("snooze_from"):
                snooze_from = int(data.split("_").pop())
                with db.transaction() as t:
                    db.user.update(t, user["id"], snooze_from=snooze_from)
            if data.startswith("snooze_to"):
                snooze_to = int(data.split("_").pop())
                with db.transaction() as t:
                    db.user.update(t, user["id"], snooze_to=snooze_to)
            if data.startswith("snooze_none"):
                snooze_from = None
                snooze_to = None
                with db.transaction() as t:
                    db.user.reset_snooze(t, user["id"])

            interval = ""
            if snooze_from is not None and snooze_to is not None:
                interval = f"\n\nNon ti mando notifiche tra le <b>{snooze_from}:00</b> e le <b>{snooze_to}:00</b>"

            # If the bot tries to edit a message but the content is the same, it gets a 400,
            # so we check if there are actual changes to push
            if snooze_from != snooze_from_current or snooze_to != snooze_to_current:
                edit_message_text(
                    f"{MESSAGE_OPEN}{interval}",
                    telegram_id,
                    message_id,
                    reply_markup=gen_markup_snooze(snooze_from, snooze_to),
                    parse_mode="HTML",
                )
            bot.answer_callback_query(call_id, show_alert=False)
