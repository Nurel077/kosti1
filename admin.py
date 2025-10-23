import json
import os
from confiq import ADMIN_ID
from data_base import add_balance, reduce_balance, reset_all_balances

DISABLED_CHATS_FILE = "disabled_chats.json"


def load_disabled_chats():
    if not os.path.exists(DISABLED_CHATS_FILE):
        return []
    with open(DISABLED_CHATS_FILE, "r", encoding="utf-8") as f:
        return json.load(f)


def save_disabled_chats(data):
    with open(DISABLED_CHATS_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def is_chat_disabled(chat_id: int) -> bool:
    disabled = load_disabled_chats()
    return chat_id in disabled


def register(bot):

    # ⚙️ Игнорирует ВСЕ сообщения из отключённых чатов
    @bot.message_handler(func=lambda message: (
        message.text and is_chat_disabled(message.chat.id)
        and not message.text.lower().startswith(("/boton", "/botoff"))
    ))
    def ignore_disabled_chat(message):
        print(f"🔇 Игнорирую сообщение из отключённого чата {message.chat.id}")
        return

    # === /botoff ===
    @bot.message_handler(commands=['botoff'])
    def disable_chat(message):
        if message.from_user.id != ADMIN_ID:
            return bot.reply_to(message, "⛔ У вас нет прав на выполнение этой команды.")

        chat_id = message.chat.id
        disabled = load_disabled_chats()

        if chat_id in disabled:
            return bot.reply_to(message, "⚠️ Этот чат уже отключён.")

        disabled.append(chat_id)
        save_disabled_chats(disabled)
        bot.reply_to(message, "🚫 Бот выключен в этом чате. Чтобы включить обратно — /boton")
        print(f"🚫 Бот выключен в чате {chat_id}")

    # === /boton ===
    @bot.message_handler(commands=['boton'])
    def enable_chat(message):
        if message.from_user.id != ADMIN_ID:
            return bot.reply_to(message, "⛔ У вас нет прав на выполнение этой команды.")

        chat_id = message.chat.id
        disabled = load_disabled_chats()

        if chat_id not in disabled:
            return bot.reply_to(message, "⚠️ Этот чат уже активен.")

        disabled.remove(chat_id)
        save_disabled_chats(disabled)
        bot.reply_to(message, "✅ Бот снова активен в этом чате.")
        print(f"✅ Бот снова активен в чате {chat_id}")

    # === Остальные админ-команды ===
    @bot.message_handler(commands=['give'])
    def give_coins(message):
        if is_chat_disabled(message.chat.id):
            return
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
        if is_chat_disabled(message.chat.id):
            return
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

    @bot.message_handler(commands=['resetall'])
    def reset_all(message):
        if is_chat_disabled(message.chat.id):
            return
        if message.from_user.id != ADMIN_ID:
            return bot.reply_to(message, "⛔ У вас нет прав на выполнение этой команды.")
        try:
            reset_all_balances()
            bot.send_message(message.chat.id, "🔄 Все балансы успешно обнулены!")
        except Exception as e:
            bot.send_message(message.chat.id, f"⚠️ Ошибка при обнулении: {e}")
