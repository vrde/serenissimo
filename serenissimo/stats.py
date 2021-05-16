from io import BytesIO
import matplotlib.pyplot as plt
from .bot import bot, from_admin
from . import db


@bot.message_handler(commands=["stats"])
def message_handler(message):
    if not from_admin(message):
        return

    with db.connection(row_factory=None) as c:
        s = db.stats.group_subscribers_by_day(c)
        n = db.stats.group_notifications_by_day(c)
        e = db.stats.group_errors_by_day(c)

    fig, axs = plt.subplots(3)
    axs[0].set_title("New subscribers")
    axs[0].bar(*list(zip(*s)))
    axs[1].set_title("Notifications sent")
    axs[1].bar(*list(zip(*n)))
    axs[2].set_title("Errors")
    axs[2].bar(*list(zip(*e)))
    plt.tight_layout()

    buffer = BytesIO()
    plt.savefig(buffer, format="png")
    buffer.seek(0)
    bot.send_photo(message.chat.id, buffer)
