from telebot import TeleBot, types
from confiq import TOKEN, MIN_BET, TEAM_MIN_BET, TEAM_SIZE, TEAM_DUEL_TIMEOUT_SEC
from data_base import get_balance, add_balance, reduce_balance
from helpers import get_display_name, can_duel
from xp_status import add_xp, update_stats, get_rank, get_xp
import random
from datetime import datetime
from admin import is_chat_disabled  # <- импортируем функцию проверки чата

bot = TeleBot(TOKEN)

pending_team_duels = {}

def register(bot):
    # Обычные дуэли (1×1)
    @bot.message_handler(func=lambda msg: msg.reply_to_message and msg.text.lower().startswith("кости"))
    def duel_handler(message):
        if is_chat_disabled(message.chat.id):  # <- проверка чата
            return  # чат выключен — не выполняем команду

        try:
            bet = int(message.text.split()[1])
        except (IndexError, ValueError):
            return bot.reply_to(message, "❌ Укажите сумму: `кости 500`", parse_mode="Markdown")

        player1 = message.from_user
        player2 = message.reply_to_message.from_user

        if player1.id == player2.id:
            return bot.reply_to(message, "❌ Вы не можете играть сами с собой.")
        if bet < MIN_BET:
            return bot.reply_to(message, f"❌ Минимальная ставка — {MIN_BET} Виртов.")
        if get_balance(player1.id) < bet or get_balance(player2.id) < bet:
            return bot.reply_to(message, "❌ У одного из игроков недостаточно Виртов.")
        if not can_duel(player1.id):
            return bot.reply_to(message, "⌛ Вы слишком часто играете. Подождите немного.")

        markup = types.InlineKeyboardMarkup()
        markup.add(
            types.InlineKeyboardButton("✅ Принять", callback_data=f"accept_duel:{player1.id}:{player2.id}:{bet}"),
            types.InlineKeyboardButton("❌ Отклонить", callback_data=f"decline_duel:{player1.id}:{player2.id}")
        )

        bot.send_message(
            message.chat.id,
            f"🎯 {get_display_name(player2)}, вас вызвал на дуэль *{get_display_name(player1)}* на сумму {bet} Виртов.\nПринять вызов?",
            reply_markup=markup,
            parse_mode="Markdown"
        )

    # Командные дуэли (2×2)
    @bot.message_handler(
        func=lambda msg: msg.text and (msg.text.lower().startswith('кости2') or msg.text.lower().startswith('дуэль2')) )
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
            types.InlineKeyboardButton("🅰️ В команду A", callback_data=f"team_join:A:{lobby_id}"),
            types.InlineKeyboardButton("🅱️ В команду B", callback_data=f"team_join:B:{lobby_id}")
        )
        markup.add(
            types.InlineKeyboardButton("✅ Старт", callback_data=f"team_start:{lobby_id}"),
            types.InlineKeyboardButton("❌ Отмена", callback_data=f"team_cancel:{lobby_id}")
        )

        text = (f"🎲 *Командная дуэль 2×2* на {bet} Виртов!\n\n"
                f"🅰️ Команда A: {get_display_name(initiator)}\n"
                f"🅱️ Команда B: —\n\n"
                f"Присоединяйтесь! Нужно по {TEAM_SIZE} игрока в каждой команде.\n"
                f"⏳ Лоби закроется через {TEAM_DUEL_TIMEOUT_SEC // 60} мин.")

        msg = bot.send_message(message.chat.id, text, reply_markup=markup, parse_mode="Markdown")
        pending_team_duels[lobby_id]["msg_id"] = msg.message_id

    # Обработка командных дуэлей (колбэки)
    @bot.callback_query_handler(func=lambda call: call.data.startswith(("team_join:", "team_start:", "team_cancel:")))
    def team_duel_callback(call):
        if is_chat_disabled(call.message.chat.id):  # <- проверка чата
            return  # чат выключен — не выполняем команду

        data = call.data.split(":")
        action = data[0]
        arg = data[1] if len(data) > 1 else None
        lobby_id = data[2] if len(data) > 2 else None

        if lobby_id not in pending_team_duels:
            return bot.answer_callback_query(call.id, "❌ Лоби не найдено или истекло.")

        lobby = pending_team_duels[lobby_id]
        user_id = call.from_user.id
        lobby["names"][user_id] = get_display_name(call.from_user)

        # Таймаут
        if datetime.now().timestamp() - lobby["created_at"] > TEAM_DUEL_TIMEOUT_SEC:
            bot.edit_message_text("⌛ Время лоби истекло.", lobby["chat_id"], lobby["msg_id"])
            pending_team_duels.pop(lobby_id, None)
            return

        def update_lobby_text():
            team_a = ", ".join([lobby["names"][uid] for uid in lobby["teams"]["A"]])
            team_b = ", ".join([lobby["names"][uid] for uid in lobby["teams"]["B"]])
            return (f"🎲 *Командная дуэль 2×2* на {lobby['bet']} Виртов!\n\n"
                    f"🅰️ Команда A: {team_a or '—'}\n"
                    f"🅱️ Команда B: {team_b or '—'}\n\n"
                    f"Присоединяйтесь! Нужно по {TEAM_SIZE} игрока в каждой команде.\n"
                    f"⏳ Лоби закроется через {TEAM_DUEL_TIMEOUT_SEC // 60} мин.")

        if action == "team_join":
            team = arg
            other_team = "B" if team == "A" else "A"
            if user_id in lobby["teams"][other_team]:
                lobby["teams"][other_team].remove(user_id)
            if user_id not in lobby["teams"][team] and len(lobby["teams"][team]) < TEAM_SIZE:
                if get_balance(user_id) < lobby["bet"]:
                    return bot.answer_callback_query(call.id, "❌ Недостаточно Виртов!")
                lobby["teams"][team].append(user_id)
            bot.edit_message_text(update_lobby_text(), lobby["chat_id"], lobby["msg_id"],
                                  reply_markup=call.message.reply_markup, parse_mode="Markdown")
            bot.answer_callback_query(call.id, f"Вы в команде {team}")

        elif action == "team_start":
            if user_id != lobby["initiator_id"]:
                return bot.answer_callback_query(call.id, "❌ Только создатель может начать игру.")
            if len(lobby["teams"]["A"]) != TEAM_SIZE or len(lobby["teams"]["B"]) != TEAM_SIZE:
                return bot.answer_callback_query(call.id, f"❌ Нужно по {TEAM_SIZE} игрока в каждой команде.")
            for team in ["A", "B"]:
                for pid in lobby["teams"][team]:
                    if get_balance(pid) < lobby["bet"]:
                        return bot.answer_callback_query(call.id, f"❌ У {lobby['names'][pid]} недостаточно Виртов.")
            rolls = {pid: random.randint(1, 6) for team in ["A", "B"] for pid in lobby["teams"][team]}
            sum_a = sum(rolls[pid] for pid in lobby["teams"]["A"])
            sum_b = sum(rolls[pid] for pid in lobby["teams"]["B"])

            result_text = "🎲 *Результаты командной дуэли*\n\n"
            for t, name in [("A", "🅰️ Команда A"), ("B", "🅱️ Команда B")]:
                result_text += f"{name}:\n"
                for pid in lobby["teams"][t]:
                    result_text += f"{lobby['names'][pid]}: 🎲 {rolls[pid]}\n"
            result_text += f"Сумма команды A: {sum_a}\nСумма команды B: {sum_b}\n\n"

            if sum_a == sum_b:
                result_text += "🤝 *Ничья!* Вирты возвращены."
                bot.edit_message_text(result_text, lobby["chat_id"], lobby["msg_id"], parse_mode="Markdown")
            else:
                winner_team = "A" if sum_a > sum_b else "B"
                loser_team = "B" if winner_team == "A" else "A"
                for pid in lobby["teams"][winner_team]:
                    add_balance(pid, lobby["bet"])
                    add_xp(pid, 30)
                for pid in lobby["teams"][loser_team]:
                    reduce_balance(pid, lobby["bet"])
                    add_xp(pid, 10)
                result_text += f"🏆 Победила команда {winner_team} и получает {lobby['bet']} Виртов!"
                bot.edit_message_text(result_text, lobby["chat_id"], lobby["msg_id"], parse_mode="Markdown")

            pending_team_duels.pop(lobby_id, None)

        elif action == "team_cancel":
            if user_id != lobby["initiator_id"]:
                return bot.answer_callback_query(call.id, "❌ Только создатель может отменить игру.")

            bot.edit_message_text("❌ Дуэль отменена создателем.", lobby["chat_id"], lobby["msg_id"])
            pending_team_duels.pop(lobby_id, None)

    # Обработка обычных дуэлей (колбэки)
    @bot.callback_query_handler(func=lambda call: call.data.startswith(("accept_duel:", "decline_duel:")))
    def handle_duel_response(call):
        if is_chat_disabled(call.message.chat.id):  # <- проверка чата
            return  # чат выключен — не выполняем команду

        data = call.data.split(":")
        action = data[0]
        player1_id = int(data[1])
        player2_id = int(data[2])

        if call.from_user.id != player2_id:
            bot.answer_callback_query(call.id, "⛔ Только вызванный игрок может принять дуэль.")
            return

        if action == "decline_duel":
            bot.edit_message_text("❌ Дуэль отклонена.", call.message.chat.id, call.message.message_id)
            return

        if player1_id == player2_id:
            bot.edit_message_text("❌ Вы не можете играть сами с собой.", call.message.chat.id, call.message.message_id)
            return

        bet = int(data[3])

        if get_balance(player1_id) < bet or get_balance(player2_id) < bet:
            return bot.edit_message_text("❌ У одного из игроков недостаточно Виртов.", call.message.chat.id,
                                         call.message.message_id)

        roll1 = random.randint(1, 6)
        roll2 = random.randint(1, 6)

        reduce_balance(player1_id, bet)
        reduce_balance(player2_id, bet)

        user1 = bot.get_chat(player1_id)
        name1 = get_display_name(user1)
        name2 = get_display_name(call.from_user)

        text = (
            f"🎲 Дуэль между *{name1}* и *{name2}*\n"
            f"• {name1}: 🎲 {roll1}\n"
            f"• {name2}: 🎲 {roll2}\n\n"
        )

        if roll1 > roll2:
            add_balance(player1_id, bet * 2)
            add_xp(player1_id, 20)
            update_stats(player1_id, won=bet * 2, win=True)
            update_stats(player2_id, lost=bet, loss=True)
            rank = get_rank(get_xp(player1_id))
            text += f"🏆 Победитель: *{name1}* и получает {bet * 2} Виртов!\n🎖️ Новый ранг: *{rank}*"
        elif roll2 > roll1:
            add_balance(player2_id, bet * 2)
            add_xp(player2_id, 20)
            update_stats(player2_id, won=bet * 2, win=True)
            update_stats(player1_id, lost=bet, loss=True)
            rank = get_rank(get_xp(player2_id))
            text += f"🏆 Победитель: *{name2}* и получает {bet * 2} Виртов!\n🎖️ Новый ранг: *{rank}*"
        else:
            add_balance(player1_id, bet)
            add_balance(player2_id, bet)
            text += "🤝 Ничья! Ставки возвращены."

        bot.edit_message_text(text, call.message.chat.id, call.message.message_id, parse_mode="Markdown")
