def register(bot):
    @bot.message_handler(func=lambda msg: msg.reply_to_message and msg.text.lower().startswith("вирты"))
    def transfer_handler(message):
        if is_chat_disabled(message.chat.id):  # ← блокируем чат
            return
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
        confirm_button = types.InlineKeyboardButton(
            "Подтвердить",
            callback_data=f"confirm_transfer:{sender.id}:{receiver.id}:{amount}"
        )
        cancel_button = types.InlineKeyboardButton(
            "Отменить",
            callback_data=f"cancel_transfer:{sender.id}:{receiver.id}"
        )
        markup.add(confirm_button, cancel_button)

        bot.send_message(
            message.chat.id,
            f"💸 *{get_display_name(sender)}* собирается отправить *{amount}* Виртов игроку *{get_display_name(receiver)}*.\n\nПодтвердите действие.",
            reply_markup=markup,
            parse_mode="Markdown"
        )
