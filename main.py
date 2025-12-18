# Импорты библиотек
from telebot import TeleBot
from confiq import TOKEN
from server import keep_alive

# Импорты модулей бота
import commands, transfer, admin
from chest_event import register as register_chest
from xp_status import register as register_xp_stats
from wheel import register as register_wheel
from shop import register as shop_reg
from duel_2x2 import register as duel_2x2_
from duel import register as duel
from roulette import register as roulet
import jobs

# Инициализация бота
bot = TeleBot(TOKEN)

# Регистрация обработчиков команд и событий
jobs.register(bot)
register_wheel(bot)          # Мини-игры (монета, слоты, камень-ножницы-бумага)
register_xp_stats(bot)       # Статус XP
shop_reg(bot)                # Магазин
duel_2x2_(bot)               # Дуэли 2x2
register_chest(bot)          # События сундуков и философии
commands.register(bot)       # Основные команды
duel(bot)                    # Обычные дуэли
transfer.register(bot)       # Переводы Виртов
admin.register(bot)          # Админ-функции
roulet(bot)                  # Рулетка

def print_banner():
    """Печатает баннер запуска бота."""
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
    print("🤖 Бот запущен!")
    keep_alive()  # Запуск сервера (если нужно)
    bot.infinity_polling()  # Запуск бота в бесконечном цикле