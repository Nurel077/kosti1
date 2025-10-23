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

    # Далее идет код для обработки командных дуэлей и обычных дуэлей...
