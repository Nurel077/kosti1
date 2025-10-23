from telebot.types import Message
from data_base import load_json, save_json  # или откуда ты подгружаешь JSON
from confiq import XP_FILE, STATS_FILE
from admin import is_chat_disabled  # <- импортируем функцию проверки чата

def add_xp(user_id, amount):
    xp_data = load_json(XP_FILE)
    uid = str(user_id)
    xp_data[uid] = xp_data.get(uid, 0) + amount
    save_json(XP_FILE, xp_data)

def get_xp(user_id):
    xp_data = load_json(XP_FILE)
    return xp_data.get(str(user_id), 0)

def get_display_name(user):
    return user.first_name or user.username or f"{user.id}"

def get_stats(user_id):
    stats = load_json(STATS_FILE)
    return stats.get(str(user_id), {"wins": 0, "losses": 0, "won": 0, "lost": 0})

def update_stats(user_id, won=0, lost=0, win=False, loss=False):
    stats = load_json(STATS_FILE)
    uid = str(user_id)
    if uid not in stats:
        stats[uid] = {"wins": 0, "losses": 0, "won": 0, "lost": 0}
    if win:
        stats[uid]["wins"] += 1
    if loss:
        stats[uid]["losses"] += 1
    stats[uid]["won"] += won
    stats[uid]["lost"] += lost
    save_json(STATS_FILE, stats)

# 👇 Эту функцию используем для определения ранга
def get_rank(xp):
    if xp < 100:
        return "Бомжара"
    elif xp < 300:
        return "Шарик"
    elif xp < 1000:
        return "Лудоман"
    else:
        return "Читер"

def register(bot):
    @bot.message_handler(commands=['xp'])
    def xp_command(message: Message):
        if is_chat_disabled(message.chat.id):  # <- проверка чата
            return  # чат выключен — не выполняем команду

        xp = get_xp(message.from_user.id)
        rank = get_rank(xp)
        bot.send_message(
            message.chat.id,
            f"📊 *Ваш XP:* {xp}\n🎖️ Ранг: {rank}",
            parse_mode="Markdown"
        )

    @bot.message_handler(commands=['stats'])
    def stats_command(message: Message):
        if is_chat_disabled(message.chat.id):  # <- проверка чата
            return  # чат выключен — не выполняем команду

        uid = message.from_user.id
        stats = get_stats(uid)
        total = stats["wins"] + stats["losses"]
        bot.send_message(
            message.chat.id,
            f"📈 *Ваша статистика:*\n🎮 Дуэлей сыграно: {total}"
            f"\n🏆 Побед: {stats['wins']}\n💀 Поражений: {stats['losses']}"
            f"\n💸 Выиграно Виртов: {stats['won']}\n📉 Потеряно Виртов: {stats['lost']}",
            parse_mode="Markdown"
        )
