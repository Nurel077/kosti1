from telebot import TeleBot, types
from confiq import TOKEN, TEAM_MIN_BET, TEAM_SIZE, TEAM_DUEL_TIMEOUT_SEC
from data_base import get_balance, add_balance, reduce_balance
from helpers import get_display_name
from shop import is_vip  # Для VIP-бонуса
import random
from datetime import datetime
import threading
from admin import is_chat_disabled

bot = TeleBot(TOKEN)

# Глобальные переменные для хранения ожидающих командных дуэлей
pending_team_duels = {}

def register(bot):
    # Обычные дуэли (1×1) — оставлено для совместимости, но можно убрать если не нужно
    @bot.message_handler(func=lambda msg: msg.text and (msg.text.lower().startswith('кости2') or msg.text.lower().startswith('дуэль2')))
    def team_duel_handler(message):
        if is_chat_disabled(message.chat.id):
            return

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
            "names": {initiator.id: get_display_name(initiator)},
            "auto_start_timer": None  # Для авто-старта
        }

        markup = kb(lobby_id)
        text = render_text(pending_team_duels[lobby_id])
        msg = bot.send_message(message.chat.id, text, reply_markup=markup, parse_mode="Markdown")
        pending_team_duels[lobby_id]["msg_id"] = msg.message_id

        # Проверяем авто-старт
        check_auto_start(lobby_id)

    def kb(lobby_id):
        m = types.InlineKeyboardMarkup()
        m.add(
            types.InlineKeyboardButton("🅰️ Встать в A", callback_data=f"team2:join:A:{lobby_id}"),
            types.InlineKeyboardButton("🅱️ Встать в B", callback_data=f"team2:join:B:{lobby_id}")
        )
        m.add(
            types.InlineKeyboardButton("🚪 Покинуть", callback_data=f"team2:leave:{lobby_id}"),
            types.InlineKeyboardButton("✅ Старт (капитан)", callback_data=f"team2:start:{lobby_id}")
        )
        m.add(types.InlineKeyboardButton("❌ Отмена (капитан)", callback_data=f"team2:cancel:{lobby_id}"))
        return m

    def render_text(lobby):
        def names(ids):
            arr = []
            for uid in ids:
                name = lobby["names"].get(uid, f"User {uid}")
                if is_vip(uid):
                    name = f"👑 {name}"
                arr.append(name)
            return ", ".join(arr) if arr else "—"

        bet = lobby["bet"]
        return (f"🎲 *Командная дуэль 2×2* на {bet} Виртов!\n\n"
                f"Команда A ({len(lobby['teams']['A'])}/{TEAM_SIZE}): {names(lobby['teams']['A'])}\n"
                f"Команда B ({len(lobby['teams']['B'])}/{TEAM_SIZE}): {names(lobby['teams']['B'])}\n\n"
                f"⏳ Лоби истечёт через {int((TEAM_DUEL_TIMEOUT_SEC - (datetime.now().timestamp() - lobby['created_at'])) // 60)} мин.")

    def check_auto_start(lobby_id):
        lobby = pending_team_duels.get(lobby_id)
        if not lobby:
            return
        if len(lobby["teams"]["A"]) == TEAM_SIZE and len(lobby["teams"]["B"]) == TEAM_SIZE:
            # Авто-старт через 30 сек
            def auto_start():
                if lobby_id in pending_team_duels:
                    start_duel(lobby_id)
            timer = threading.Timer(30, auto_start)
            timer.start()
            lobby["auto_start_timer"] = timer

    def start_duel(lobby_id):
        lobby = pending_team_duels.get(lobby_id)
        if not lobby:
            return
        teams = lobby["teams"]
        if len(teams["A"]) != TEAM_SIZE or len(teams["B"]) != TEAM_SIZE:
            return  # Не полные команды

        # Финальная проверка балансов
        for uid in teams["A"] + teams["B"]:
            if get_balance(uid) < lobby["bet"]:
                bot.send_message(lobby["chat_id"], "❌ У кого-то недостаточно Виртов — дуэль отменена.")
                pending_team_duels.pop(lobby_id, None)
                return

        # Броски с VIP-бонусом
        rolls = {}
        for uid in teams["A"] + teams["B"]:
            roll = random.randint(1, 6)
            if is_vip(uid):
                roll += 1  # VIP +1 к броску
            rolls[uid] = roll

        sumA = sum(rolls[uid] for uid in teams["A"])
        sumB = sum(rolls[uid] for uid in teams["B"])

        bet = lobby["bet"]
        if sumA == sumB:
            text = ("🤝 Ничья!\n"
                    f"Команда A: {', '.join(f'{lobby['names'][uid]} ({rolls[uid]})' for uid in teams['A'])} = {sumA}\n"
                    f"Команда B: {', '.join(f'{lobby['names'][uid]} ({rolls[uid]})' for uid in teams['B'])} = {sumB}\n"
                    "Вирты возвращены.")
        else:
            winners = teams["A"] if sumA > sumB else teams["B"]
            losers = teams["B"] if sumA > sumB else teams["A"]
            for uid in losers:
                reduce_balance(uid, bet)
            for uid in winners:
                add_balance(uid, bet)
            text = ("🏆 Результаты 2×2:\n"
                    f"Команда A: {', '.join(f'{lobby['names'][uid]} ({rolls[uid]})' for uid in teams['A'])} = {sumA}\n"
                    f"Команда B: {', '.join(f'{lobby['names'][uid]} ({rolls[uid]})' for uid in teams['B'])} = {sumB}\n\n"
                    f"Победила команда {'A' if sumA > sumB else 'B'}! Каждый победитель получил {bet} Виртов.")

        try:
            bot.edit_message_text(text, lobby["chat_id"], lobby["msg_id"], parse_mode="Markdown")
        except:
            bot.send_message(lobby["chat_id"], text)
        pending_team_duels.pop(lobby_id, None)

    # Обработка колбэков
    @bot.callback_query_handler(func=lambda call: call.data.startswith("team2:"))
    def team2_callbacks(call):
        if is_chat_disabled(call.message.chat.id):
            return

        parts = call.data.split(":", 3)
        action = parts[1]
        arg = parts[2] if len(parts) > 2 else None
        lobby_id = parts[3] if len(parts) > 3 else None

        lobby = pending_team_duels.get(lobby_id)
        if not lobby:
            return bot.answer_callback_query(call.id, "Лоби не найдено.")

        chat_id = lobby["chat_id"]
        msg_id = lobby["msg_id"]
        teams = lobby["teams"]
        user_id = call.from_user.id

        # Таймаут
        if datetime.now().timestamp() - lobby["created_at"] > TEAM_DUEL_TIMEOUT_SEC:
            bot.edit_message_text("⌛️ Лоби истекло.", chat_id, msg_id)
            pending_team_duels.pop(lobby_id, None)
            return

        if user_id not in lobby["names"]:
            lobby["names"][user_id] = get_display_name(call.from_user)

        if action == "join":
            team_key = arg
            if team_key not in ("A", "B"):
                return bot.answer_callback_query(call.id, "Неверная команда.")
            other = "B" if team_key == "A" else "A"
            if user_id in teams[other]:
                teams[other].remove(user_id)
            if user_id not in teams[team_key]:
                if len(teams[team_key]) >= TEAM_SIZE:
                    return bot.answer_callback_query(call.id, f"Команда {team_key} полная.")
                if get_balance(user_id) < lobby["bet"]:
                    return bot.answer_callback_query(call.id, "Недостаточно Виртов.")
                teams[team_key].append(user_id)
                check_auto_start(lobby_id)  # Проверяем авто-старт
            bot.edit_message_text(render_text(lobby), chat_id, msg_id, reply_markup=kb(lobby_id), parse_mode="Markdown")
            return

        if action == "leave":
            for team in teams.values():
                if user_id in team:
                    team.remove(user_id)
                    break
            if lobby["auto_start_timer"]:
                lobby["auto_start_timer"].cancel()
                lobby["auto_start_timer"] = None
            bot.edit_message_text(render_text(lobby), chat_id, msg_id, reply_markup=kb(lobby_id), parse_mode="Markdown")
            return

        if action == "cancel":
            if user_id != lobby["initiator_id"]:
                return bot.answer_callback_query(call.id, "Только капитан может отменить.")
            bot.edit_message_text("❌ Лоби отменено.", chat_id, msg_id)
            if lobby["auto_start_timer"]:
                lobby["auto_start_timer"].cancel()
            pending_team_duels.pop(lobby_id, None)
            return

        if action == "start":
            if user_id != lobby["initiator_id"]:
                return bot.answer_callback_query(call.id, "Только капитан может запустить.")
            start_duel(lobby_id)
            return
# ...existing code...