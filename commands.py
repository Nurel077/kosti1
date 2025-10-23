from datetime import datetime
from telebot import types
from confiq import DAILY_FILE, DAILY_REWARD, BOOST_FILE
from data_base import get_balance, add_balance, load_json, save_json
from helpers import get_display_name
from admin import is_chat_disabled  # <- импортируем функцию проверки чата

def is_vip(user_id: int) -> bool:
    """Проверка на VIP статус"""
    data = load_json(BOOST_FILE)
    return str(user_id) in data.get("vip", [])

def register(bot):
    # ================= START ==================
    @bot.message_handler(commands=['start'])
    def start(message):
        if is_chat_disabled(message.chat.id):  # <- проверка чата
            return  # чат выключен — не выполняем команду

        get_balance(message.from_user.id)  # создаём баланс если нет
        keyboard = types.InlineKeyboardMarkup(row_width=2)
        keyboard.add(
            types.InlineKeyboardButton("💰 Баланс", callback_data="balance"),
            types.InlineKeyboardButton("📆 Daily", callback_data="get_daily"),
            types.InlineKeyboardButton("🏆 Топ", callback_data="top"),
            types.InlineKeyboardButton("👤 Статус", callback_data="status"),
        )
        bot.send_message(
            message.chat.id,
            "👋 *Добро пожаловать в игру «Кости»!*\n\n"
            "🎮 Доступные команды через кнопки ниже:",
            parse_mode="Markdown",
            reply_markup=keyboard
        )

    # ================= HELP ==================
    @bot.message_handler(commands=['help'])
    def help_cmd(message):
        if is_chat_disabled(message.chat.id):  # <- проверка чата
            return  # чат выключен — не выполняем команду

        if message.chat.type != 'private':
            return
        bot.send_message(
            message.chat.id,
            "📜 *Правила игры в кости:*\n\n"
            "🔹 Ответь на сообщение игрока:\n"
            "  — `кости 400` — вызов на дуэль\n"
            "  — `Вирты 300` — передать виртов\n\n"
            "🔹 Команды:\n"
            "  — /balance — ваш баланс\n"
            "  — /daily — ежедневная награда\n"
            "  — /top — топ игроков\n"
            "  — /status — ваш статус\n\n"
            "💡 Минимальная ставка: 300 Виртов",
            parse_mode="Markdown"
        )

    # ================= BALANCE ==================
    def send_balance(chat_id, user):
        if is_chat_disabled(chat_id):  # <- проверка чата
            return  # чат выключен — не выполняем команду

        bal = get_balance(user.id)
        name = get_display_name(user)
        if is_vip(user.id):
            name = f"👑✨ {name} ✨👑"
        bot.send_message(chat_id, f"💰 Баланс {name}: *{bal} Виртов*", parse_mode="Markdown")

    @bot.message_handler(commands=['balance'])
    def balance_cmd(message):
        send_balance(message.chat.id, message.from_user)

    # ================= DAILY ==================
    def process_daily(user_id: str, user_obj, call=None, chat_id=None):
        if is_chat_disabled(chat_id):  # <- проверка чата
            return  # чат выключен — не выполняем команду

        daily_data = load_json(DAILY_FILE)
        today = datetime.now().strftime('%Y-%m-%d')

        if daily_data.get(user_id) == today:
            text = "📆 Награда уже получена сегодня. Приходите завтра!"
            if call:
                bot.answer_callback_query(call.id, text=text, show_alert=True)
            else:
                bot.send_message(chat_id, text)
            return

        # VIP ×4 награда
        reward = DAILY_REWARD * 4 if is_vip(int(user_id)) else DAILY_REWARD
        add_balance(user_id, reward)

        daily_data[user_id] = today
        save_json(DAILY_FILE, daily_data)

        text = f"🎁 Вы получили *{reward} Виртов*! До встречи завтра 👋"
        if call:
            bot.answer_callback_query(call.id, text=text, show_alert=True)
        else:
            bot.send_message(chat_id, text, parse_mode="Markdown")

    @bot.message_handler(commands=['daily'])
    def daily_cmd(message):
        user_id = str(message.from_user.id)
        process_daily(user_id, message.from_user, chat_id=message.chat.id)

    @bot.callback_query_handler(func=lambda call: call.data == "get_daily")
    def daily_button(call):
        user_id = str(call.from_user.id)
        process_daily(user_id, call.from_user, call=call)

    # ================= TOP ==================
    def send_top(chat_id):
        if is_chat_disabled(chat_id):  # <- проверка чата
            return  # чат выключен — не выполняем команду

        balances = load_json('balances.json')
        top = sorted(balances.items(), key=lambda x: x[1], reverse=True)[:10]

        statuses = [
            "🥇 Депутат", "🥈 Образз", "🥉 Лудоман", "💰 Удачливый", "🎯 Опытный",
            "💸 При деньгах", "🎲 Рисковый", "🤑 Жадный", "🔥 Крутой", "🤞 Новичок"
        ]

        text = "🏆 *Топ игроков:*\n\n"
        for i, (user_id, bal) in enumerate(top, 1):
            try:
                user = bot.get_chat_member(chat_id, int(user_id)).user
                name = get_display_name(user)
            except Exception:
                name = f"User {user_id}"

            if is_vip(int(user_id)):
                name = f"👑✨ {name} ✨👑"
                status = "💎 VIP Игрок"
            else:
                status = statuses[i - 1] if bal >= 1000 else "💀 Бомж"

            text += f"{i}. {name}: {bal} Виртов — {status}\n"

        bot.send_message(chat_id, text, parse_mode="Markdown")

    @bot.message_handler(commands=['top'])
    def top_cmd(message):
        send_top(message.chat.id)

    # ================= STATUS ==================
    def send_status(chat_id, user):
        if is_chat_disabled(chat_id):  # <- проверка чата
            return  # чат выключен — не выполняем команду

        user_id = user.id
        balance = get_balance(user_id)
        name = get_display_name(user)

        if is_vip(user_id):
            name = f"👑✨ {name} ✨👑"
            status = "💎 VIP Игрок"
        else:
            if balance < 1000:
                status = "💀 Бомж"
            else:
                balances = load_json('balances.json')
                top = sorted(balances.items(), key=lambda x: x[1], reverse=True)[:10]

                statuses = [
                    "🥇 Депутат", "🥈 Образз", "🥉 Лудоман", "💰 Удачливый", "🎯 Опытный",
                    "💸 При деньгах", "🎲 Рисковый", "🤑 Жадный", "🔥 Крутой", "🤞 Новичок"
                ]
                status = "👤 Игрок"
                for i, (uid, _) in enumerate(top):
                    if str(user_id) == uid:
                        status = statuses[i]
                        break

        bot.send_message(
            chat_id,
            f"👤 Статус {name}: {status}\n💰 Баланс: {balance} Виртов",
            parse_mode="Markdown"
        )

    @bot.message_handler(commands=['status'])
    def status_cmd(message):
        send_status(message.chat.id, message.from_user)

    # ================= CALLBACK MENU ==================
    @bot.callback_query_handler(func=lambda call: call.data in ["balance", "get_daily", "top", "status"])
    def menu_buttons(call):
        if is_chat_disabled(call.message.chat.id):  # <- проверка чата
            return  # чат выключен — не выполняем команду

        if call.data == "balance":
            send_balance(call.message.chat.id, call.from_user)
        elif call.data == "get_daily":
            process_daily(str(call.from_user.id), call.from_user, call=call)
        elif call.data == "top":
            send_top(call.message.chat.id)
        elif call.data == "status":
            send_status(call.message.chat.id, call.from_user)

        bot.answer_callback_query(call.id)  # закрыть "часики"
