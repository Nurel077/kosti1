import random
import time
import threading
import logging
from helpers import get_display_name
from data_base import add_balance
from confiq import DICE_PHRASES
from admin import is_chat_disabled

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

active_chests = {}  # {chat_id: {'amount': int, 'timestamp': float, 'winner': Optional[int]}}
active_chests_lock = threading.Lock()

CHAT_IDS = [-5097423575,-1003173623720]  # Список ID чатов для событий

# Включите тестовый режим для быстрого тестирования (интервалы 5-10 сек)
TEST_MODE = True  # Поставь True для тестирования

def _wait_range(min_s, max_s):
    if TEST_MODE:
        return 1800, 3600  # 5-10 секунд для теста
    return min_s, max_s

def register(bot):
    @bot.message_handler(func=lambda message: message.text and 'забрать' in message.text.lower())
    def grab_chest(message):
        try:
            if is_chat_disabled(message.chat.id):
                return

            chat_id = message.chat.id
            user_id = message.from_user.id
            
            with active_chests_lock:
                chest = active_chests.get(chat_id)
                
                if not chest:
                    bot.reply_to(message, "❌ Нет активного сундука!")
                    return
                    
                # Проверяем таймер (5 минут)
                if time.time() - chest['timestamp'] > 300:
                    bot.reply_to(message, "⏰ Время на захват сундука истекло!")
                    del active_chests[chat_id]
                    return
                
                # Проверяем, не забран ли уже
                if chest.get('winner'):
                    winner_name = chest.get('winner_name', 'кто-то')
                    bot.reply_to(message, f"🎯 Сундук уже забран {winner_name}!")
                    return
                
                amount = chest['amount']
                add_balance(user_id, amount)
                
                # Сохраняем победителя
                chest['winner'] = user_id
                chest['winner_name'] = get_display_name(message.from_user)
                
                bot.send_message(
                    chat_id,
                    f"🎉 {chest['winner_name']} забрал сундук и получил {amount} Виртов!"
                )
                
                # Удалим через 30 секунд
                def cleanup():
                    time.sleep(30)
                    with active_chests_lock:
                        if chat_id in active_chests:
                            del active_chests[chat_id]
                
                threading.Thread(target=cleanup, daemon=True).start()
                
        except Exception:
            logging.exception("Ошибка в grab_chest")

    def chest_event():
        min_w, max_w = _wait_range(1200, 3600)  # 20-60 минут (или 5-10 сек в тесте)
        while True:
            try:
                for chat_id in CHAT_IDS:
                    if is_chat_disabled(chat_id):
                        continue
                    wait_time = random.randint(min_w, max_w)
                    logging.info(f"chest_event: жду {wait_time}s для чата {chat_id}")
                    time.sleep(wait_time)

                    amount = random.randint(100, 300)
                    with active_chests_lock:
                        if active_chests.get(chat_id):
                            logging.info(f"chest_event: сундук уже активен в {chat_id}, пропускаю")
                            continue
                        active_chests[chat_id] = {
                            'amount': amount, 
                            'timestamp': time.time(),
                            'winner': None,
                            'winner_name': None
                        }

                    try:
                        logging.info(f"chest_event: отправляю сундук в {chat_id} ({amount})")
                        bot.send_message(
                            chat_id,
                            f"🎁 Найден сундук! Напиши 'забрать' первым, чтобы получить {amount} Виртов! (таймер 5 мин)"
                        )
                    except Exception as e:
                        logging.error(f"Ошибка отправки сундука в {chat_id}: {e}")
            except Exception:
                logging.exception("Ошибка в chest_event, перезапуск через 5s")
                time.sleep(5)

    def philosophy_event():
        min_w, max_w = _wait_range(1600, 3600)  # 13-30 минут (или 5-10 сек в тесте)
        while True:
            try:
                for chat_id in CHAT_IDS:
                    if is_chat_disabled(chat_id):
                        continue
                    wait_time = random.randint(min_w, max_w)
                    logging.info(f"philosophy_event: жду {wait_time}s для {chat_id}")
                    time.sleep(wait_time)
                    phrase = random.choice(DICE_PHRASES)
                    try:
                        bot.send_message(chat_id, f"📜 Философия дня: {phrase}")
                    except Exception as e:
                        logging.error(f"Ошибка отправки философии в {chat_id}: {e}")
            except Exception:
                logging.exception("Ошибка в philosophy_event, перезапуск через 5s")
                time.sleep(5)

    # Запускаем потоки
    threading.Thread(target=chest_event, daemon=True).start()
    threading.Thread(target=philosophy_event, daemon=True).start()
    logging.info("Модуль событий запущен!")