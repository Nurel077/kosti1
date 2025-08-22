from telebot import TeleBot
from confiq import TOKEN
from server import keep_alive
import commands,  transfer, admin
from chest_event import register as register_chest
from xp_status import register as register_xp_stats
from wheel import register as register_wheel
from shop import register as shop_reg
from duel_2x2 import register as duel_2x2_
from duel import register as duel
from roulette import  register as roulet
bot = TeleBot(TOKEN)
# Регистрация обработчиков
register_wheel(bot)
register_xp_stats(bot)
shop_reg(bot)
duel_2x2_(bot)
register_chest(bot)
commands.register(bot)
duel(bot)
transfer.register(bot)
admin.register(bot)
roulet(bot)

def print_banner():
    banner = r"""
╔════════════════════════════════════════════════════════╗
║  🚀 БОТ ЗАПУЩЕН — KOSTI      BOT                       ║
║  🕒 Время запуска malabaevv__                          ║
║  🎲 Игра в кости активна. Ожидаем команду «кости»…     ║
║  💬 Ответьте на сообщение с:  кости <ставка>           ║
╚════════════════════════════════════════════════════════╝
""".format(__import__("datetime").datetime.now().strftime("%Y-%m-%d %H:%M:%S"))

    print(banner)

if __name__ == "__main__":
    print_banner()
    bot.infinity_polling()

print("🤖 Бот запущен!")
keep_alive()
bot.infinity_polling()
