# wheel.py

from confiq import WHEEL_COST
from data_base import get_balance, reduce_balance, add_balance
from xp_status import get_display_name
import random

def register(bot):
    @bot.message_handler(commands=['wheel'])
    def spin_wheel(message):
        user_id = message.from_user.id
        balance = get_balance(user_id)

        if balance < WHEEL_COST:
            return bot.send_message(message.chat.id, f"💸 У вас недостаточно Виртов. Нужно хотя бы {WHEEL_COST} для вращения.")

        reduce_balance(user_id, WHEEL_COST)

        # Возможные призы (включая минусовые)
        prizes = [-3000, -300, 0, 100, 200, 500, 1000, 5000]
        weights = [10, 15, 25, 20, 15, 10, 4, 1]  # Общая сумма = 100

        prize = random.choices(prizes, weights=weights)[0]

        if prize > 0:
            add_balance(user_id, prize)
            bot.send_message(
                message.chat.id,
                f"🎉 {get_display_name(message.from_user)} крутил колесо и выиграл *{prize}* Виртов!",
                parse_mode="Markdown"
            )
        elif prize == 0:
            bot.send_message(
                message.chat.id,
                f"😐 {get_display_name(message.from_user)} крутил колесо... и ничего не произошло.",
                parse_mode="Markdown"
            )
        else:
            loss = abs(prize)
            reduce_balance(user_id, loss)
            bot.send_message(
                message.chat.id,
                f"💀 {get_display_name(message.from_user)} крутил колесо и *потерял {loss}* Виртов...",
                parse_mode="Markdown"
            )
