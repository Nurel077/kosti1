from telebot import TeleBot, types
from confiq import TOKEN, MIN_BET
from data_base import get_balance, add_balance, reduce_balance
from helpers import get_display_name, can_duel
from xp_status import add_xp, update_stats, get_rank, get_xp
from shop import is_vip  # Для VIP-бонуса
import random
import time
from admin import is_chat_disabled

bot = TeleBot(TOKEN)

# Cooldown для дуэлей (5 сек между вызовами)
duel_cooldown = {}

def register(bot):
    @bot.message_handler(func=lambda msg: msg.reply_to_message and msg.text.lower().startswith("кости"))
    def duel_handler(message):
        if is_chat_disabled(message.chat.id):
            return

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

        # Cooldown
        now = time.time()
        if player1.id in duel_cooldown and now - duel_cooldown[player1.id] < 5:
            return bot.reply_to(message, "⏳ Подождите 5 сек перед новой дуэлью.")
        duel_cooldown[player1.id] = now

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

    @bot.callback_query_handler(func=lambda call: call.data.startswith(("accept_duel:", "decline_duel:")))
    def handle_duel_response(call):
        if is_chat_disabled(call.message.chat.id):
            return

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
            return bot.edit_message_text("❌ У одного из игроков недостаточно Виртов.", call.message.chat.id, call.message.message_id)

        # Броски с VIP-бонусом
        roll1 = random.randint(1, 6)
        roll2 = random.randint(1, 6)
        if is_vip(player1_id):
            roll1 += 1
        if is_vip(player2_id):
            roll2 += 1

        reduce_balance(player1_id, bet)
        reduce_balance(player2_id, bet)

        name1 = get_display_name(types.User(id=player1_id, is_bot=False, first_name="Player1"))  # Заглушка, лучше хранить имена
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
# ...existing code...