import time
import random
import datetime
from telebot import types

from data_base import load_json, save_json, add_balance
from admin import is_chat_disabled

JOBS_FILE = "jobs.json"
MAX_WORKS_PER_DAY = 1  # 1 раз в день

# Обновленные профессии с реальными зарплатами
JOBS = {
    "schoolboy": {
        "name": "🎒 Школьник",
        "salary": (500, 500),  # Карманные 500₽ в день
        "cooldown": 86400,  # 24 часа в секундах
        "xp": 5,
        "type": "passive",
        "description": "Учёба в школе + карманные деньги"
    },
    "miner": {
        "name": "⛏ Шахтёр",
        "salary": (1800, 3000),  # от 1 800 до 3 000 ₽ в день
        "cooldown": 86400,  # 24 часа в секундах (1 раз в день)
        "xp": 10,
        "type": "passive",
        "description": "Работа в шахте, добыча полезных ископаемых"
    },
    "courier": {
        "name": "📦 Курьер",
        "salary": (1500, 5167),  # от 1 500 до 5 167 ₽ в день
        "cooldown": 86400,  # 24 часа в секундах
        "xp": 8,
        "type": "passive",
        "description": "Доставка товаров и документов"
    },
    "programmer": {
        "name": "💻 Программист (junior)",
        "salary": (2333, 5000),  # от 2 333 до 5 000 ₽ в день
        "cooldown": 86400,  # 24 часа в секундах
        "xp": 12,
        "type": "active",
        "description": "Разработка программного обеспечения"
    },
    "mathematician": {
        "name": "🧠 Математик",
        "salary": (3000, 5000),  # от 3 000 до 5 000 ₽ в день
        "cooldown": 86400,  # 24 часа в секундах
        "xp": 15,
        "type": "active",
        "description": "Решение математических задач и анализ данных"
    }
}


def get_level_xp(level):
    return level * 50  # Увеличил XP для уровня, так как работаем раз в день


def register(bot):

    # ===== /job =====
    @bot.message_handler(commands=['job'])
    def job_menu(message):
        if is_chat_disabled(message.chat.id):
            return

        uid = str(message.from_user.id)
        data = load_json(JOBS_FILE)

        if uid in data:
            job = JOBS[data[uid]['job']]['name']
            return bot.send_message(
                message.chat.id,
                f"❌ Ты уже работаешь: {job}\n"
                "Используй /work или /quitjob"
            )

        markup = types.InlineKeyboardMarkup(row_width=1)
        for jid, job in JOBS.items():
            salary_min, salary_max = job['salary']
            markup.add(
                types.InlineKeyboardButton(
                    f"{job['name']} - {salary_min:,}–{salary_max:,}₽/день",
                    callback_data=f"job_{jid}"
                )
            )

        bot.send_message(
            message.chat.id,
            "💼 *Выбери работу (можно работать 1 раз в день):*\n\n"
            "• 🎒 Школьник: 500₽/день (карманные)\n"
            "• ⛏ Шахтёр: 1,800–3,000₽/день\n"
            "• 📦 Курьер: 1,500–5,167₽/день\n"
            "• 💻 Программист: 2,333–5,000₽/день\n"
            "• 🧠 Математик: 3,000–5,000₽/день",
            reply_markup=markup,
            parse_mode='Markdown'
        )


    # ===== выбор работы =====
    @bot.callback_query_handler(func=lambda c: c.data.startswith("job_"))
    def set_job(call):
        uid = str(call.from_user.id)
        job_id = call.data.split("_")[1]

        data = load_json(JOBS_FILE)
        job = JOBS[job_id]
        salary_min, salary_max = job['salary']
        
        data[uid] = {
            "job": job_id,
            "level": 1,
            "xp": 0,
            "last_work": 0,
            "works_today": 0,
            "last_day": str(datetime.date.today())
        }
        save_json(JOBS_FILE, data)

        bot.answer_callback_query(call.id)
        bot.send_message(
            call.message.chat.id,
            f"✅ *Ты устроился на работу: {job['name']}*\n"
            f"💼 *Описание:* {job['description']}\n"
            f"💰 *Зарплата:* {salary_min:,}–{salary_max:,}₽ в день\n"
            f"⏰ *Работать можно:* 1 раз в 24 часа\n\n"
            f"Используй /work чтобы начать работу",
            parse_mode='Markdown'
        )


    # ===== /work =====
    @bot.message_handler(commands=['work'])
    def work(message):
        if is_chat_disabled(message.chat.id):
            return

        uid = str(message.from_user.id)
        data = load_json(JOBS_FILE)

        if uid not in data:
            return bot.send_message(message.chat.id, "❌ Ты нигде не работаешь. Используй /job")

        user = data[uid]
        job = JOBS[user['job']]
        now = time.time()

        # новый день
        today = str(datetime.date.today())
        if user['last_day'] != today:
            user['last_day'] = today
            user['works_today'] = 0

        # Проверка лимита (1 раз в день)
        if user['works_today'] >= MAX_WORKS_PER_DAY:
            # Проверяем, сколько времени прошло с последней работы
            time_since_last_work = now - user['last_work']
            
            if time_since_last_work < 86400:  # 24 часа в секундах
                remaining_time = 86400 - time_since_last_work
                hours = int(remaining_time // 3600)
                minutes = int((remaining_time % 3600) // 60)
                
                return bot.send_message(
                    message.chat.id,
                    f"🚫 *Лимит работ на сегодня исчерпан!*\n\n"
                    f"Ты уже работал сегодня.\n"
                    f"Следующая работа возможна через:\n"
                    f"⏰ *{hours} часов {minutes} минут*",
                    parse_mode='Markdown'
                )
            else:
                # Если прошло больше 24 часов, сбрасываем счетчик
                user['works_today'] = 0

        # кулдаун (24 часа с последней работы)
        if now - user['last_work'] < job['cooldown']:
            wait = job['cooldown'] - (now - user['last_work'])
            hours = int(wait // 3600)
            minutes = int((wait % 3600) // 60)
            
            return bot.send_message(
                message.chat.id,
                f"⏳ *Подожди {hours} часов {minutes} минут* до следующей работы.\n"
                f"Работать можно только 1 раз в 24 часа.",
                parse_mode='Markdown'
            )

        # активная работа
        if job['type'] == "active":
            if job['name'].startswith("💻"):
                code = random.choice(["World", "Python", "User"])
                
                # Отправляем сообщение и сохраняем его ID для replay
                sent_msg = bot.send_message(
                    message.chat.id,
                    '💻 *Задание программиста:*\n'
                    'Допиши код:\n`print("Hello ___")`\n\n'
                    'Ответь на это сообщение правильным словом:',
                    parse_mode='Markdown'
                )
                
                # Ждем ответа на это конкретное сообщение
                bot.register_for_reply(
                    sent_msg, 
                    lambda reply: handle_active_reply(reply, code, job, uid, sent_msg.message_id)
                )
                return

            if job['name'].startswith("🧠"):
                a, b = random.randint(10, 50), random.randint(10, 50)
                operation = random.choice(["+", "-", "*"])
                if operation == "+":
                    answer = a + b
                elif operation == "-":
                    answer = a - b
                else:
                    answer = a * b
                
                # Отправляем сообщение и сохраняем его ID для replay
                sent_msg = bot.send_message(
                    message.chat.id,
                    f'🧠 *Задание математика:*\n'
                    f'Реши пример: `{a} {operation} {b} = ?`\n\n'
                    f'Ответь на это сообщение правильным ответом:',
                    parse_mode='Markdown'
                )
                
                # Ждем ответа на это конкретное сообщение
                bot.register_for_reply(
                    sent_msg,
                    lambda reply: handle_math_reply(reply, answer, job, uid, sent_msg.message_id)
                )
                return

        # пассивная работа или школьник - сразу завершаем
        finish_work(message, job, uid)


    def handle_active_reply(reply, correct, job, expected_uid, original_msg_id):
        """Обработка ответа на активную работу (программист)"""
        # Проверяем, что ответил тот же пользователь
        uid = str(reply.from_user.id)
        
        if uid != expected_uid:
            bot.send_message(reply.chat.id, "❌ Это не твоя работа! Используй /work для своей работы.")
            return
            
        # Проверяем, что это ответ на правильное сообщение
        if not reply.reply_to_message or reply.reply_to_message.message_id != original_msg_id:
            bot.send_message(reply.chat.id, "❌ Пожалуйста, ответь на сообщение с заданием!")
            return
            
        data = load_json(JOBS_FILE)
        
        if uid not in data:
            bot.send_message(reply.chat.id, "❌ Ты больше не работаешь. Используй /job чтобы устроиться на работу.")
            return
            
        if reply.text != correct:
            bot.send_message(reply.chat.id, "❌ Неверно! Зарплата не начислена.")
            return
            
        finish_work(reply, job, uid)


    def handle_math_reply(reply, answer, job, expected_uid, original_msg_id):
        """Обработка ответа на математическую работу"""
        # Проверяем, что ответил тот же пользователь
        uid = str(reply.from_user.id)
        
        if uid != expected_uid:
            bot.send_message(reply.chat.id, "❌ Это не твоя работа! Используй /work для своей работы.")
            return
            
        # Проверяем, что это ответ на правильное сообщение
        if not reply.reply_to_message or reply.reply_to_message.message_id != original_msg_id:
            bot.send_message(reply.chat.id, "❌ Пожалуйста, ответь на сообщение с заданием!")
            return
            
        data = load_json(JOBS_FILE)
        
        if uid not in data:
            bot.send_message(reply.chat.id, "❌ Ты больше не работаешь. Используй /job чтобы устроиться на работу.")
            return
            
        if not reply.text.isdigit() or int(reply.text) != answer:
            bot.send_message(reply.chat.id, "❌ Неверно! Зарплата не начислена.")
            return
            
        finish_work(reply, job, uid)


    def finish_work(message, job, uid):
        data = load_json(JOBS_FILE)
        
        if uid not in data:
            bot.send_message(message.chat.id, "❌ Ты больше не работаешь. Используй /job чтобы устроиться на работу.")
            return
            
        user = data[uid]

        # Генерация зарплаты
        salary_min, salary_max = job['salary']
        salary = random.randint(salary_min, salary_max)
        
        # Бонус за уровень
        level_bonus = 1.0 + (user['level'] - 1) * 0.1  # +10% за каждый уровень
        salary = int(salary * level_bonus)
        
        xp = job['xp']

        add_balance(uid, salary)
        user['xp'] += xp
        user['last_work'] = time.time()
        user['works_today'] += 1
        user['last_day'] = str(datetime.date.today())

        # уровень
        level_up = False
        if user['xp'] >= get_level_xp(user['level']):
            user['xp'] = 0
            user['level'] += 1
            level_up = True

        save_json(JOBS_FILE, data)

        # Форматирование числа с разделителями тысяч
        salary_formatted = f"{salary:,}".replace(",", " ")
        
        # Специальное сообщение для школьника
        if job['name'].startswith("🎒"):
            text = (
                f"✅ *Башына хаям жакшы оку!*\n\n"
                f"🎒 *Профессия:* {job['name']}\n"
                f"💰 *Карманные:* {salary_formatted}₽\n"
                f"📚 *Опыт:* +{xp} XP\n"
                f"📊 *Уровень:* {user['level']} ({user['xp']}/{get_level_xp(user['level'])} XP)"
            )
        else:
            text = (
                f"✅ *Работа выполнена!*\n\n"
                f"💼 *Профессия:* {job['name']}\n"
                f"💰 *Зарплата:* {salary_formatted}₽\n"
                f"⭐ *Опыт:* +{xp} XP\n"
                f"📊 *Уровень:* {user['level']} ({user['xp']}/{get_level_xp(user['level'])} XP)"
            )

        if level_up:
            text += f"\n\n🎉 *ПОВЫШЕНИЕ УРОВНЯ!* Теперь ты {user['level']} уровня!"
            
        # Добавляем информацию о следующей работе
        next_work_time = user['last_work'] + 86400
        next_work_datetime = datetime.datetime.fromtimestamp(next_work_time)
        next_work_str = next_work_datetime.strftime("%d.%m.%Y в %H:%M")
        
        text += f"\n\n⏰ *Следующая работа доступна:*\n{next_work_str}"

        bot.send_message(message.chat.id, text, parse_mode='Markdown')


    # ===== /jobinfo =====
    @bot.message_handler(commands=['jobinfo'])
    def jobinfo(message):
        uid = str(message.from_user.id)
        data = load_json(JOBS_FILE)

        if uid not in data:
            bot.send_message(message.chat.id, "❌ Ты не работаешь.")
            return

        u = data[uid]
        job = JOBS[u['job']]
        salary_min, salary_max = job['salary']
        
        # Рассчитываем время до следующей работы
        now = time.time()
        time_since_last_work = now - u['last_work']
        
        if time_since_last_work >= 86400:
            next_work = "Сейчас"
        else:
            remaining = 86400 - time_since_last_work
            hours = int(remaining // 3600)
            minutes = int((remaining % 3600) // 60)
            next_work = f"через {hours}ч {minutes}м"
        
        # Форматируем зарплату
        salary_min_fmt = f"{salary_min:,}".replace(",", " ")
        salary_max_fmt = f"{salary_max:,}".replace(",", " ")
        
        bot.send_message(
            message.chat.id,
            f"📊 *Информация о работе*\n\n"
            f"💼 *Профессия:* {job['name']}\n"
            f"📝 *Описание:* {job['description']}\n"
            f"💰 *Зарплата:* {salary_min_fmt}–{salary_max_fmt}₽/день\n"
            f"🔹 *Уровень:* {u['level']}\n"
            f"⭐ *XP:* {u['xp']}/{get_level_xp(u['level'])}\n"
            f"⏰ *Следующая работа:* {next_work}\n"
            f"📅 *Работ сегодня:* {u['works_today']}/{MAX_WORKS_PER_DAY}",
            parse_mode='Markdown'
        )


    @bot.message_handler(commands=['quitjob'])
    def quitjob(message):
        uid = str(message.from_user.id)
        data = load_json(JOBS_FILE)

        if uid not in data:
            bot.send_message(message.chat.id, "❌ Ты не работаешь.")
            return

        name = JOBS[data[uid]['job']]['name']
        level = data[uid]['level']
        del data[uid]
        save_json(JOBS_FILE, data)

        bot.send_message(
            message.chat.id,
            f"🚪 *Ты уволился с работы*\n\n"
            f"💼 *Профессия:* {name}\n"
            f"🔹 *Достигнутый уровень:* {level}\n\n"
            f"Используй /job чтобы найти новую работу",
            parse_mode='Markdown'
        )