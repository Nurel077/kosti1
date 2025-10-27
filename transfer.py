from telebot import types
from data_base import get_balance, reduce_balance, add_balance
from helpers import get_display_name
from telebot.types import User
from admin import is_chat_disabled  # <- импортируем функцию проверки чата

def register(bot):
    @bot.message_handler(func=lambda msg: msg.reply_to_message and msg.text.lower().startswith("вирты"))
    def transfer_handler(message):
        if is_chat_disabled(message.chat.id):  # <- проверка чата
            return  # чат выключен — не выполняем команду

        try:
            amount = int(message.text.split()[1])
        except (IndexError, ValueError):
            return bot.reply_to(message, "❌ Укажите сумму: `Вирты 500`", parse_mode="Markdown")

        sender = message.from_user
        receiver = message.reply_to_message.from_user

        if sender.id == receiver.id:
            return bot.reply_to(message, "❌ Нельзя отправить себе.")

        if amount <= 0:
            return bot.reply_to(message, "❌ Сумма должна быть больше 0.")

        if get_balance(sender.id) < amount:
            return bot.reply_to(message, "❌ Недостаточно Виртов для перевода.")

        # Отправка сообщения с кнопками подтверждения
        markup = types.InlineKeyboardMarkup()
        confirm_button = types.InlineKeyboardButton("Подтвердить",
                                                    callback_data=f"confirm_transfer:{sender.id}:{receiver.id}:{amount}")
        cancel_button = types.InlineKeyboardButton("Отменить",
                                                   callback_data=f"cancel_transfer:{sender.id}:{receiver.id}")
        markup.add(confirm_button, cancel_button)

        bot.send_message(
            message.chat.id,
            f"💸 *{get_display_name(sender)}* собирается отправить *{amount}* Виртов игроку *{get_display_name(receiver)}*.\n\nПодтвердите действие.",
            reply_markup=markup,
            parse_mode="Markdown"
        )

    @bot.callback_query_handler(func=lambda call: call.data.startswith("confirm_transfer:"))
    def confirm_transaction(call):
        if is_chat_disabled(call.message.chat.id):  # <- проверка чата
            return  # чат выключен — не выполняем команду

        sender_id, receiver_id, amount = map(int, call.data.split(":")[1:])

        # Получаем объекты пользователей
        sender = bot.get_chat(sender_id)  # Получаем объект отправителя
        receiver = bot.get_chat(receiver_id)  # Получаем объект получателя

        if get_balance(sender_id) < amount:
            bot.answer_callback_query(call.id, text="❌ Недостаточно средств на балансе для выполнения транзакции.")
            return

        # Выполнение транзакции
        reduce_balance(sender_id, amount)
        add_balance(receiver_id, amount)

        bot.answer_callback_query(call.id, text="✅ Транзакция подтверждена!")

        # Отправка сообщения в группу
        bot.send_message(
            call.message.chat.id,
            f"💸 *{get_display_name(sender)}* отправил *{amount}* Виртов игроку *{get_display_name(receiver)}*.",
            parse_mode="Markdown"
        )
        bot.edit_message_text(
            "✅ Транзакция подтверждена!",
            call.message.chat.id,
            call.message.message_id
        )

    @bot.callback_query_handler(func=lambda call: call.data.startswith("cancel_transfer:"))
    def cancel_transaction(call):
        if is_chat_disabled(call.message.chat.id):  # <- проверка чата
            return  # чат выключен — не выполняем команду

        bot.answer_callback_query(call.id, text="❌ Транзакция отменена.")
        bot.edit_message_text(
            "❌ Транзакция отменена пользователем.",
            call.message.chat.id,
            call.message.message_id
        )
