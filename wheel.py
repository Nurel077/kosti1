from data_base import get_balance, reduce_balance, add_balance, load_json, save_json
from helpers import get_display_name
from admin import is_chat_disabled
from shop import is_luck_active, is_boost_active
from confiq import MIN_BET, STATS_FILE
from telebot import types
import random
import time

# Cooldown между играми (5 сек)
last_play = {}

def register(bot):
    @bot.message_handler(commands=['games'])
    def cmd_games(message):
        if is_chat_disabled(message.chat.id):
            return
        markup = types.InlineKeyboardMarkup(row_width=1)
        markup.add(
            types.InlineKeyboardButton("🪙 Монета (/coin)", callback_data="game_coin"),
            types.InlineKeyboardButton("🎰 Слоты (/slots)", callback_data="game_slots"),
            types.InlineKeyboardButton("✂️ КНБ (/rps)", callback_data="game_rps")
        )
        bot.send_message(message.chat.id, "🎡 *Мини-игры:*\nВыберите игру или используйте команды напрямую.", reply_markup=markup, parse_mode="Markdown")

    @bot.callback_query_handler(func=lambda call: call.data.startswith("game_"))
    def game_menu(call):
        game = call.data.split("_")[1]
        if game == "coin":
            bot.send_message(call.message.chat.id, "🪙 Использование: /coin <орёл|решка> <ставка>")
        elif game == "slots":
            bot.send_message(call.message.chat.id, "🎰 Использование: /slots <ставка>")
        elif game == "rps":
            bot.send_message(call.message.chat.id, "✂️ Использование: /rps <камень|ножницы|бумага> [ставка]")
        bot.answer_callback_query(call.id)

    @bot.message_handler(commands=['coin'])
    def cmd_coin(message):
        if is_chat_disabled(message.chat.id):
            return
        user = message.from_user.id
        now = time.time()
        if user in last_play and now - last_play[user] < 5:
            return bot.send_message(message.chat.id, "⏳ Подожди 5 сек перед следующей игрой.")
        last_play[user] = now

        parts = message.text.split()
        if len(parts) < 3:
            return bot.send_message(message.chat.id, "Использование: /coin <орёл|решка> <ставка>")
        choice = parts[1].lower()
        try:
            bet = int(parts[2])
            if bet < MIN_BET or bet <= 0:
                return bot.send_message(message.chat.id, f"Ставка должна быть от {MIN_BET} Виртов.")
        except:
            return bot.send_message(message.chat.id, "Ставка должна быть числом.")
        if get_balance(user) < bet:
            return bot.send_message(message.chat.id, "Недостаточно Виртов.")
        if choice not in ('орёл','решка','orel','reshka'):
            return bot.send_message(message.chat.id, "Выберите 'орёл' или 'решка'.")
        reduce_balance(user, bet)
        # Применение luck: шанс 60% вместо 50%
        luck = is_luck_active(user)
        win_chance = 0.6 if luck else 0.5
        outcome = 'орёл' if random.random() < win_chance else 'решка'
        boost = is_boost_active(user)
        multiplier = 1.1 if boost else 1.0
        if outcome == choice:
            win = int(bet * 2 * multiplier)
            add_balance(user, win)
            msg = f"🎉 {get_display_name(message.from_user)} угадал ({outcome}) и выиграл {win}!"
            if luck: msg += " 🍀"
            if boost: msg += " ⚡"
            update_stats(user, 'coin', 'win')
        else:
            msg = f"💤 Вышло {outcome}. {get_display_name(message.from_user)} проиграл {bet}."
            update_stats(user, 'coin', 'lose')
        msg += f"\n💰 Баланс: {get_balance(user)} Виртов"
        bot.send_message(message.chat.id, msg)

    @bot.message_handler(commands=['slots'])
    def cmd_slots(message):
        if is_chat_disabled(message.chat.id):
            return
        user = message.from_user.id
        now = time.time()
        if user in last_play and now - last_play[user] < 5:
            return bot.send_message(message.chat.id, "⏳ Подожди 5 сек перед следующей игрой.")
        last_play[user] = now

        parts = message.text.split()
        if len(parts) < 2:
            return bot.send_message(message.chat.id, "Использование: /slots <ставка>")
        try:
            bet = int(parts[1])
            if bet < MIN_BET or bet <= 0:
                return bot.send_message(message.chat.id, f"Ставка должна быть от {MIN_BET} Виртов.")
        except:
            return bot.send_message(message.chat.id, "Ставка должна быть числом.")
        if get_balance(user) < bet:
            return bot.send_message(message.chat.id, "Недостаточно Виртов.")
        reduce_balance(user, bet)
        symbols = ['🍒','🍋','🔔','⭐','7️⃣']
        luck = is_luck_active(user)
        boost = is_boost_active(user)
        multiplier = 1.1 if boost else 1.0
        # Luck: повышенный шанс на выигрыш
        if luck and random.random() < 0.3:
            res = [random.choice(symbols[:3])] * 3
        else:
            res = [random.choice(symbols) for _ in range(3)]
        board = ' '.join(res)
        jackpot = random.random() < 0.01  # 1% шанс на джекпот
        if jackpot:
            win = int(bet * 50 * multiplier)
            add_balance(user, win)
            msg = f"{board}\n🎰 СУПЕР ДЖЕКПОТ! {get_display_name(message.from_user)} выиграл {win} Виртов! 🎉"
            update_stats(user, 'slots', 'win')
        elif res.count(res[0]) == 3:
            win = int(bet * 10 * multiplier)
            add_balance(user, win)
            msg = f"{board}\n🎰 Джекпот! {get_display_name(message.from_user)} выиграл {win} Виртов!"
            update_stats(user, 'slots', 'win')
        elif len(set(res)) <= 2:
            win = int(bet * 2 * multiplier)
            add_balance(user, win)
            msg = f"{board}\n🙂 Неплохо — выигрыш {win} Виртов."
            update_stats(user, 'slots', 'win')
        else:
            msg = f"{board}\n💔 Увы, ты проиграл {bet} Виртов."
            update_stats(user, 'slots', 'lose')
        if luck: msg += " 🍀"
        if boost: msg += " ⚡"
        msg += f"\n💰 Баланс: {get_balance(user)} Виртов"
        bot.send_message(message.chat.id, msg)

    @bot.message_handler(commands=['rps'])
    def cmd_rps(message):
        if is_chat_disabled(message.chat.id):
            return
        user = message.from_user.id
        now = time.time()
        if user in last_play and now - last_play[user] < 5:
            return bot.send_message(message.chat.id, "⏳ Подожди 5 сек перед следующей игрой.")
        last_play[user] = now

        parts = message.text.split()
        if len(parts) < 2:
            return bot.send_message(message.chat.id, "Использование: /rps <камень|ножницы|бумага> [ставка]")
        pick = parts[1].lower()
        bet = 0
        if len(parts) >= 3:
            try:
                bet = int(parts[2])
                if bet < MIN_BET or bet <= 0:
                    return bot.send_message(message.chat.id, f"Ставка должна быть от {MIN_BET} Виртов.")
            except:
                return bot.send_message(message.chat.id, "Ставка должна быть числом.")
        if bet and get_balance(user) < bet:
            return bot.send_message(message.chat.id, "Недостаточно Виртов.")
        if bet:
            reduce_balance(user, bet)
        bot_pick = random.choice(['камень','ножницы','бумага'])
        win_map = {'камень':'ножницы','ножницы':'бумага','бумага':'камень'}
        luck = is_luck_active(user)
        boost = is_boost_active(user)
        multiplier = 1.1 if boost else 1.0
        # Luck: 10% шанс на автопобеду
        if luck and random.random() < 0.1:
            reward = int(bet * 2 * multiplier)
            if reward:
                add_balance(user, reward)
            msg = f"🍀 Удача! Автопобеда: {pick} vs {bot_pick}. Вы выиграли {reward} Виртов."
            update_stats(user, 'rps', 'win')
        elif pick == bot_pick:
            if bet:
                add_balance(user, bet)
                update_stats(user, 'rps', 'draw')
            msg = f"🤝 Ничья: {pick} vs {bot_pick}"
        elif win_map.get(pick) == bot_pick:
            reward = int(bet * 2 * multiplier)
            if reward:
                add_balance(user, reward)
            msg = f"🏆 Победа: {pick} beats {bot_pick}. Вы выиграли {reward} Виртов."
            update_stats(user, 'rps', 'win')
        else:
            msg = f"😞 Поражение: {pick} vs {bot_pick}. {'Вы проиграли ставку.' if bet else ''}"
            update_stats(user, 'rps', 'lose')
        if luck and not msg.startswith("🍀"): msg += " 🍀"
        if boost: msg += " ⚡"
        msg += f"\n💰 Баланс: {get_balance(user)} Виртов"
        bot.send_message(message.chat.id, msg)

def update_stats(user_id, game, result):
    data = load_json(STATS_FILE)
    uid = str(user_id)
    data.setdefault(uid, {'coin': {'win':0,'lose':0}, 'slots': {'win':0,'lose':0}, 'rps': {'win':0,'lose':0,'draw':0}})
    data[uid][game][result] += 1
    save_json(STATS_FILE, data)
# ...existing code...
def update_stats(user_id, game, result):
    data = load_json(STATS_FILE)
    uid = str(user_id)

    DEFAULT_GAMES = {
        'coin':  {'win': 0, 'lose': 0},
        'slots': {'win': 0, 'lose': 0},
        'rps':   {'win': 0, 'lose': 0, 'draw': 0}
    }

    # пользователь
    if uid not in data:
        data[uid] = {}

    # игра
    if game not in data[uid]:
        data[uid][game] = DEFAULT_GAMES[game].copy()

    # результат
    if result not in data[uid][game]:
        data[uid][game][result] = 0

    data[uid][game][result] += 1
    save_json(STATS_FILE, data)
# ...existing code...