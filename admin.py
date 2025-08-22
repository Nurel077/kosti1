from confiq import ADMIN_ID
from data_base import add_balance, reduce_balance

def register(bot):
    @bot.message_handler(commands=['give'])
    def give_coins(message):
        if message.from_user.id != ADMIN_ID:
            return

        try:
            user_id, amount = message.text.split()[1:]
            amount = int(amount)
            add_balance(user_id, amount)
            bot.send_message(message.chat.id, f"✅ Пользователю {user_id} добавлено {amount} виртов.")
        except:
            bot.send_message(message.chat.id, "❌ Используй: `/give user_id amount`", parse_mode="Markdown")

    @bot.message_handler(commands=['removevirts'])
    def remove_bits(message):
        if message.from_user.id != ADMIN_ID:
            return bot.reply_to(message, "⛔ У вас нет прав на выполнение этой команды.")
        try:
            parts = message.text.split()
            user_id = int(parts[1])
            amount = int(parts[2])
            reduce_balance(user_id, amount)
            bot.reply_to(message, f"✅ Удалено {amount} виртов у пользователя {user_id}.")
        except:
            bot.reply_to(message, "⚠️ Формат: /removevirts user_id amount")