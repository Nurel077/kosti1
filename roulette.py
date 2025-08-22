import random
import threading
import datetime
from telebot import types
from data_base import get_balance, add_balance, reduce_balance

TIMEOUT_SECONDS = 60   # время ожидания выбора кнопки
MIN_BET = 300          # минимальная ставка
MAX_DAILY_ROULETTE = 10 # максимум игр в день

RED_SET = {1,3,5,7,9,12,14,16,18,19,21,23,25,27,30,32,34,36}
BLACK_SET = {2,4,6,8,10,11,13,15,17,20,22,24,26,28,29,31,33,35}


def register(bot):
    # user_id -> {amount, chat_id, msg_id, timer, ask_msg_id}
    active_bets = {}
    # user_id -> {"date": "2025-08-22", "count": int}
    daily_limits = {}

    def check_limit(user_id: int) -> bool:
        today = datetime.date.today().isoformat()
        data = daily_limits.get(user_id)

        if not data or data["date"] != today:
            # сбрасываем счётчик на новый день
            daily_limits[user_id] = {"date": today, "count": 0}

        if daily_limits[user_id]["count"] >= MAX_DAILY_ROULETTE:
            return False
        return True

    def increment_limit(user_id: int):
        today = datetime.date.today().isoformat()
        daily_limits[user_id]["date"] = today
        daily_limits[user_id]["count"] += 1

    # 🎰 Запуск рулетки
    @bot.message_handler(commands=["roulette"])
    def roulette(message):
        user_id = message.from_user.id
        username = message.from_user.first_name

        if not check_limit(user_id):
            bot.send_message(message.chat.id, f"❌ {username},лудик запомни казино никогда не проигрывает .")
            return

        if user_id in active_bets:
            bot.send_message(
                message.chat.id,
                f"❗ {username}, у тебя уже есть активная ставка. "
                "Нажми кнопки под прошлым сообщением или /cancel_roulette для отмены."
            )
            return

        ask_msg = bot.send_message(
            message.chat.id,
            f"🎰 {username}, ответь на это сообщение и введи сумму ставки (минимум {MIN_BET}):"
        )
        active_bets[user_id] = {"ask_msg_id": ask_msg.message_id}

    # ❌ Отмена рулетки
    @bot.message_handler(commands=["cancel_roulette"])
    def cancel_roulette(message):
        user_id = message.from_user.id
        username = message.from_user.first_name
        data = active_bets.pop(user_id, None)
        if not data or "amount" not in data:
            bot.send_message(message.chat.id, f"ℹ️ {username}, у тебя нет активной рулетки.")
            return
        add_balance(user_id, data["amount"])  # вернуть ставку
        if data.get("timer"):
            data["timer"].cancel()
        if data.get("msg_id"):
            try:
                bot.edit_message_reply_markup(chat_id=data["chat_id"], message_id=data["msg_id"], reply_markup=None)
            except Exception:
                pass
        bot.send_message(message.chat.id, f"❌ {username}, рулетка отменена, деньги возвращены.")

    # 📝 Проверка и принятие суммы ставки (только ответом на сообщение)
    @bot.message_handler(func=lambda m: True, content_types=["text"])
    def ask_bet_amount(message):
        user_id = message.from_user.id
        username = message.from_user.first_name

        data = active_bets.get(user_id)
        if not data or "ask_msg_id" not in data:
            return  # не связано с рулеткой

        if not message.reply_to_message or message.reply_to_message.message_id != data["ask_msg_id"]:
            return  # игрок не ответил на нужное сообщение

        # проверка числа
        try:
            amount = int(message.text.strip())
        except Exception:
            bot.send_message(message.chat.id, f"❌ {username}, введи корректное число.")
            return

        if amount < MIN_BET:
            bot.send_message(message.chat.id, f"❌ {username}, минимальная ставка — {MIN_BET}.")
            return

        balance = get_balance(user_id)
        if amount > balance:
            bot.send_message(message.chat.id, f"❌ {username}, недостаточно средств. Баланс: {balance}.")
            return

        # заморозка ставки
        reduce_balance(user_id, amount)

        msg = show_bet_options(message.chat.id, user_id, username)
        t = threading.Timer(TIMEOUT_SECONDS, on_timeout, args=(user_id,))
        active_bets[user_id].update({
            "amount": amount,
            "chat_id": msg.chat.id,
            "msg_id": msg.message_id,
            "timer": t,
        })
        t.start()

    # 🔘 Кнопки для выбора ставки
    def show_bet_options(chat_id: int, user_id: int, username: str):
        def cb(suffix): return f"roulette:{user_id}:{suffix}"

        markup = types.InlineKeyboardMarkup()
        markup.row(
            types.InlineKeyboardButton("🔴 Красное (x2)", callback_data=cb("color_red")),
            types.InlineKeyboardButton("⚫ Чёрное (x2)",  callback_data=cb("color_black")),
            types.InlineKeyboardButton("🟢 Зеро (x14)",   callback_data=cb("color_green")),
        )
        markup.row(
            types.InlineKeyboardButton("Чёт (x2)",   callback_data=cb("parity_even")),
            types.InlineKeyboardButton("Нечёт (x2)", callback_data=cb("parity_odd")),
        )
        markup.row(
            types.InlineKeyboardButton("1–18 (x2)",  callback_data=cb("range_low")),
            types.InlineKeyboardButton("19–36 (x2)", callback_data=cb("range_high")),
        )
        return bot.send_message(chat_id, f"🎲 {username}, выбери ставку:", reply_markup=markup)

    # ⏳ Если не выбрал за 60 сек — вернуть деньги
    def on_timeout(user_id: int):
        data = active_bets.pop(user_id, None)
        if not data or "amount" not in data:
            return
        add_balance(user_id, data["amount"])
        try:
            bot.edit_message_text(
                "⌛ Время вышло. Ставка отменена, деньги возвращены.",
                chat_id=data["chat_id"],
                message_id=data["msg_id"],
                reply_markup=None
            )
        except Exception:
            pass

    # 🎲 Обработка кнопок
    @bot.callback_query_handler(func=lambda call: call.data.startswith("roulette:"))
    def handle_spin(call):
        try:
            _, owner_id_str, bet_type = call.data.split(":", 2)
            owner_id = int(owner_id_str)
        except Exception:
            bot.answer_callback_query(call.id)
            return

        # только владелец может нажимать кнопки
        if call.from_user.id != owner_id:
            bot.answer_callback_query(call.id, "Это не твоя ставка.", show_alert=True)
            return

        data = active_bets.pop(owner_id, None)
        if not data or "amount" not in data:
            bot.answer_callback_query(call.id, "Сначала начни /roulette.")
            return

        if data.get("timer"):
            data["timer"].cancel()

        bet = data["amount"]
        username = call.from_user.first_name

        # крутим рулетку
        number = random.randint(0, 36)
        if number == 0:
            color = "green"
        elif number in RED_SET:
            color = "red"
        else:
            color = "black"

        mult = 0
        if bet_type == "color_red" and color == "red":
            mult = 2
        elif bet_type == "color_black" and color == "black":
            mult = 2
        elif bet_type == "color_green" and color == "green":
            mult = 14
        elif bet_type == "parity_even" and number != 0 and number % 2 == 0:
            mult = 2
        elif bet_type == "parity_odd" and number % 2 == 1:
            mult = 2
        elif bet_type == "range_low" and 1 <= number <= 18:
            mult = 2
        elif bet_type == "range_high" and 19 <= number <= 36:
            mult = 2

        if mult > 0:
            add_balance(owner_id, bet * mult)
            result_text = (f"🎲 {username}, выпало {number} ({color.upper()})\n"
                           f"✅ Победа! Выплата: {bet} × {mult} = {bet * mult}.")
        else:
            result_text = (f"🎲 {username}, выпало {number} ({color.upper()})\n"
                           f"❌ Проигрыш. Ставка {bet} не возвращается.")

        # ✅ засчитываем игру
        increment_limit(owner_id)

        try:
            bot.edit_message_text(
                result_text,
                call.message.chat.id,
                call.message.message_id,
                reply_markup=None
            )
        except Exception:
            bot.send_message(call.message.chat.id, result_text)

        bot.answer_callback_query(call.id)
