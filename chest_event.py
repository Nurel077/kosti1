import random
import time
import threading
from helpers import get_display_name
from data_base import add_balance
from confiq import DICE_PHRASES
from admin import is_chat_disabled  # <- импортируем функцию проверки чата

active_chests = {}  # словарь для хранения активных сундуков по ID группы

CHAT_IDS = [-1002858139670, -1003173623720]  # список с двумя ID групп (замени на свои)


def register(bot):
    @bot.message_handler(func=lambda message: message.text and 'забрать' in message.text.lower())
    def grab_chest(message):
        if is_chat_disabled(message.chat.id):  # <- проверка чата
            return  # чат выключен — не выполняем команду

        global active_chests
        chat_id = message.chat.id

        # Проверяем, есть ли активный сундук для текущей группы
        if chat_id in active_chests and active_chests[chat_id]:
            active_chest = active_chests[chat_id]
            winner_id = message.from_user.id
            amount = active_chest['amount']
            add_balance(winner_id, amount)
            bot.send_message(
                chat_id,
                f"🎉 {get_display_name(message.from_user)} забрал сундук и получил {amount} Виртов!"
            )
            # После того как сундук забрали, очищаем активный сундук для этой группы
            active_chests[chat_id] = None

    def chest_event():
        global active_chests
        while True:
            for chat_id in CHAT_IDS:
                if is_chat_disabled(chat_id):  # <- проверка чата
                    continue  # если чат выключен, переходим к следующему

                wait_time = random.randint(1200, 3600)  # 20–60 минут
                time.sleep(wait_time)
                amount = random.randint(100, 300)
                active_chests[chat_id] = {'chat_id': chat_id, 'amount': amount}
                bot.send_message(
                    chat_id,
                    f"🎁 Найден сундук! Напиши 'забрать' первым, чтобы получить {amount} Виртов!"
                )

    def philosophy_event():
        while True:
            for chat_id in CHAT_IDS:
                if is_chat_disabled(chat_id):  # <- проверка чата
                    continue  # если чат выключен, пропускаем отправку философии

                wait_time = random.randint(1600, 3600)  # 30–60 минут
                time.sleep(wait_time)
                phrase = random.choice(DICE_PHRASES)
                bot.send_message(chat_id, f"📜 Философия дня: {phrase}")

    # запускаем оба потока
    threading.Thread(target=chest_event, daemon=True).start()
    threading.Thread(target=philosophy_event, daemon=True).start()
