# chest_event.py

import random
import time
import threading
from helpers import get_display_name
from data_base import add_balance
from confiq import DICE_PHRASES
active_chest = None  # глобальная переменная

CHAT_ID = -1002858139670  # ← замени на свой ID группы

def register(bot):
    @bot.message_handler(func=lambda message: message.text and 'забрать' in message.text.lower())
    def grab_chest(message):
        global active_chest
        if active_chest and message.chat.id == active_chest['chat_id']:
            winner_id = message.from_user.id
            amount = active_chest['amount']
            add_balance(winner_id, amount)
            bot.send_message(
                message.chat.id,
                f"🎉 {get_display_name(message.from_user)} забрал сундук и получил {amount} Виртов!"
            )
            active_chest = None

    def chest_event():
        global active_chest
        while True:
            wait_time = random.randint(1200, 3600)  # 20–60 минут
            time.sleep(wait_time)
            amount = random.randint(100, 300)
            active_chest = {'chat_id': CHAT_ID, 'amount': amount}
            bot.send_message(
                CHAT_ID,
                f"🎁 Найден сундук! Напиши 'забрать' первым, чтобы получить {amount} Виртов!"
            )

    def philosophy_event():
        while True:
            wait_time = random.randint(1600, 3600)  # 30–60 минут
            time.sleep(wait_time)
            phrase = random.choice(DICE_PHRASES)
            bot.send_message(CHAT_ID, f"📜 Философия дня: {phrase}")

    # запускаем оба потока
    threading.Thread(target=chest_event, daemon=True).start()
    threading.Thread(target=philosophy_event, daemon=True).start()
