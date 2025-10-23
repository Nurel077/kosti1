from telebot import TeleBot, types
from confiq import TOKEN, TEAM_MIN_BET, TEAM_SIZE, TEAM_DUEL_TIMEOUT_SEC
from data_base import get_balance, add_balance, reduce_balance
from helpers import get_display_name
import random
from datetime import datetime
from admin import is_chat_disabled  # <- импортируем функцию проверки чата

bot = TeleBot(TOKEN)

# Глобальные переменные для хранения ожидающих командных дуэлей
pending_team_duels = {}

def register(bot):
    @bot.message_handler(func=lambda msg: msg.text and (msg.text.lower().startswith('кости2') or msg.text.lower().startswith('дуэль2')))
    def team_duel_handler(message):
        if is_chat_disabled(message.chat.id):  # <- проверка чата
            return  # чат выключен — не выполняем команду

        try:
            bet = int(message.text.split()[1])
        except (IndexError, ValueError):
            return bot.reply_to(message, "❌ Укажите сумму: `кости2 500`", parse_mode="Markdown")

        initiator = message.from_user

        if bet < TEAM_MIN_BET:
            return bot.reply_to(message, f"❌ Минимальная ставка для команд — {TEAM_MIN_BET} Виртов.")
        if get_balance(initiator.id) < bet:
            return bot.reply_to(message, "❌ У вас недостаточно Виртов для создания лоби.")

        lobby_id = f"{message.chat.id}:{message.message_id}:{initiator.id}"
        if lobby_id in pending_team_duels:
            return bot.reply_to(message, "❌ Лоби уже создано, дождитесь набора команд.")

        # Создаем лоби и сразу записываем инициатора в команду A
        pending_team_duels[lobby_id] = {
            "bet": bet,
            "chat_id": message.chat.id,
            "msg_id": None,
            "created_at": datetime.now().timestamp(),
            "initiator_id": initiator.id,
            "teams": {"A": [initiator.id], "B": []},
            "names": {initiator.id: get_display_name(initiator)}
        }

        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("🅰️ Встать в команду A", callback_data=f"team2:join:A:{lobby_id}"),
            types.InlineKeyboardButton("🅱️ Встать в команду B", callback_data=f"team2:join:B:{lobby_id}")
        )
        markup.add(
            types.InlineKeyboardButton("✅ Старт (капитан)", callback_data=f"team2:start:{lobby_id}"),
            types.InlineKeyboardButton("❌ Отмена (капитан)", callback_data=f"team2:cancel:{lobby_id}")
        )

        text = (f"🎲 *Командная дуэль 2×2* на {bet} виртов!\n\n"
                f"Команда A: {get_display_name(initiator)}\n"
                f"Команда B: —\n\n"
                f"Нажмите кнопки, чтобы присоединиться. Требуется по {TEAM_SIZE} игрока в каждой команде.\n"
                f"⏳ Лоби истечёт через {TEAM_DUEL_TIMEOUT_SEC//60 if TEAM_DUEL_TIMEOUT_SEC>=60 else TEAM_DUEL_TIMEOUT_SEC} мин.")
        msg = bot.send_message(message.chat.id, text, reply_markup=markup)
        pending_team_duels[lobby_id]["msg_id"] = msg.message_id

    # Функция для поиска лоби по сообщению
    def _find_lobby_by_message(call):
        chat_id = call.message.chat.id
        msg_id = call.message.message_id
        for lobby_id, lobby in pending_team_duels.items():
            if lobby["chat_id"] == chat_id and lobby["msg_id"] == msg_id:
                return lobby_id, lobby
        return None, None

    # Обработка командных дуэлей (колбэки)
    @bot.callback_query_handler(func=lambda call: call.data.startswith("team2:"))
    def team2_callbacks(call):
        if is_chat_disabled(call.message.chat.id):  # <- проверка чата
            return  # чат выключен — не выполняем команду

        parts = call.data.split(":", 3)  # team2:action:arg:lobby_id
        action = parts[1] if len(parts) > 1 else None
        arg = parts[2] if len(parts) > 2 else None
        lobby_id = parts[3] if len(parts) > 3 else None

        if action in ("start", "cancel") and lobby_id is None:
            lobby_id = arg
            arg = None

        lobby = None
        if lobby_id and lobby_id in pending_team_duels:
            lobby = pending_team_duels[lobby_id]
        else:
            # Фолбэк: ищем лобби по сообщению с кнопками (фикс)
            found_key, found_lobby = _find_lobby_by_message(call)
            if found_key:
                lobby_id = found_key
                lobby = found_lobby

        if not lobby:
            return bot.answer_callback_query(call.id, "Лоби не найдено или истекло.")

        chat_id = lobby["chat_id"]
        msg_id = lobby["msg_id"]
        bet = lobby["bet"]
        teams = lobby["teams"]
        initiator_id = lobby["initiator_id"]

        # Таймаут лоби
        if datetime.now().timestamp() - lobby["created_at"] > TEAM_DUEL_TIMEOUT_SEC:
            try:
                bot.edit_message_text("⌛️ Время лоби истекло.", chat_id, msg_id)
            except:
                pass
            pending_team_duels.pop(lobby_id, None)
            return

        def render_text():
            def names(ids):
                arr = []
                for uid in ids:
                    if uid not in lobby["names"]:
                        try:
                            user = bot.get_chat_member(chat_id, uid).user
                            lobby["names"][uid] = get_display_name(user)
                        except:
                            lobby["names"][uid] = f"User {uid}"
                    arr.append(lobby["names"][uid])
                return ", ".join(arr) if arr else "—"

            return (f"🎲 *Командная дуэль 2×2* на {bet} виртов!\n\n"
                    f"Команда A: {names(teams['A'])}\n"
                    f"Команда B: {names(teams['B'])}\n\n"
                    f"Нужно по {TEAM_SIZE} игрока в каждой команде.")

        def kb():
            m = types.InlineKeyboardMarkup()
            m.add(
                types.InlineKeyboardButton("🅰️ Встать в A", callback_data=f"team2:join:A:{lobby_id}"),
                types.InlineKeyboardButton("🅱️ Встать в B", callback_data=f"team2:join:B:{lobby_id}")
            )
            m.add(
                types.InlineKeyboardButton("✅ Старт (капитан)", callback_data=f"team2:start:{lobby_id}"),
                types.InlineKeyboardButton("❌ Отмена (капитан)", callback_data=f"team2:cancel:{lobby_id}")
            )
            return m

        user_id = call.from_user.id
        if user_id not in lobby["names"]:
            lobby["names"][user_id] = get_display_name(call.from_user)

        if action == "join":
            team_key = arg  # "A" или "B"
            if team_key not in ("A", "B"):
                return bot.answer_callback_query(call.id, "Неверная команда.")
            other = "B" if team_key == "A" else "A"
            if user_id in teams[other]:
                teams[other].remove(user_id)
            if user_id not in teams[team_key]:
                if len(teams[team_key]) >= TEAM_SIZE:
                    return bot.answer_callback_query(call.id, f"Команда {team_key} уже укомплектована.")
                if get_balance(user_id) < bet:
                    return bot.answer_callback_query(call.id, "Недостаточно виртов для участия.")
                teams[team_key].append(user_id)
            try:
                bot.edit_message_text(render_text(), chat_id, msg_id, reply_markup=kb())
            except:
                bot.edit_message_caption(render_text(), chat_id, msg_id, reply_markup=kb())
            return

        if action == "cancel":
            if user_id != initiator_id:
                return bot.answer_callback_query(call.id, "Отменить может только капитан (создатель лоби).")
            try:
                bot.edit_message_text("❌ Лоби отменено капитаном.", chat_id, msg_id)
            except:
                pass
            pending_team_duels.pop(lobby_id, None)
            return

        if action == "start":
            if user_id != initiator_id:
                return bot.answer_callback_query(call.id, "Запустить может только капитан (создатель лоби).")

            if len(teams["A"]) != TEAM_SIZE or len(teams["B"]) != TEAM_SIZE:
                return bot.answer_callback_query(call.id, "Нужно по 2 игрока в каждой команде.")

            # финальная проверка балансов
            for uid in teams["A"] + teams["B"]:
                if get_balance(uid) < bet:
                    return bot.answer_callback_query(call.id, "У кого-то из игроков недостаточно виртов.")

            # Броски
            rolls = {}
            for uid in teams["A"] + teams["B"]:
                rolls[uid] = random.randint(1, 6)

            sumA = sum(rolls[uid] for uid in teams["A"])
            sumB = sum(rolls[uid] for uid in teams["B"])

            if sumA == sumB:
                # Ничья — возврат
                text = ("🎲 Ничья!\n"
                        "Команда A: " + ", ".join(f"{lobby['names'][uid]} ({rolls[uid]})" for uid in teams["A"]) + f" = {sumA}\n"
                        "Команда B: " + ", ".join(f"{lobby['names'][uid]} ({rolls[uid]})" for uid in teams["B"]) + f" = {sumB}\n"
                        "Вирты возвращены.")
                try:
                    bot.edit_message_text(text, chat_id, msg_id)
                except:
                    bot.send_message(chat_id, text)
                pending_team_duels.pop(lobby_id, None)
                return

            winners = teams["A"] if sumA > sumB else teams["B"]
            losers = teams["B"] if sumA > sumB else teams["A"]

            for uid in losers:
                reduce_balance(uid, bet)
            for uid in winners:
                add_balance(uid, bet)

            text = ("🎲 Результаты 2×2:\n"
                    "Команда A: " + ", ".join(f"{lobby['names'][uid]} ({rolls[uid]})" for uid in teams["A"]) + f" = {sumA}\n"
                    "Команда B: " + ", ".join(f"{lobby['names'][uid]} ({rolls[uid]})" for uid in teams["B"]) + f" = {sumB}\n\n"
                    f"🏆 Победила команда {'A' if sumA > sumB else 'B'}! "
                    f"Каждый победитель получил {bet} виртов, проигравшие заплатили по {bet}.")
            try:
                bot.edit_message_text(text, chat_id, msg_id)
            except:
                bot.send_message(chat_id, text)

            pending_team_duels.pop(lobby_id, None)
            return
