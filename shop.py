import time
import threading
from data_base import load_json, save_json, get_balance, reduce_balance, add_balance
from xp_status import get_display_name, add_xp
from confiq import SHOP_FILE, BOOST_FILE
from telebot import types

# --- Предметы магазина ---
ITEMS = {
    "xp100": {"name": "🎓 +100 XP", "price": 5000, "effect": "add_xp"},
    "xp500": {"name": "🎓 +500 XP", "price": 20000, "effect": "add_xp500"},
    "vip": {"name": "👑 VIP статус (навсегда)", "price": 100000, "effect": "vip_status"},
    "luck": {"name": "🍀 Удача (повышает шанс в колесе на 1 час)", "price": 5000, "effect": "luck"},
    "boost": {"name": "⚡ Буст баланса (+10% к выигрышам на 1 час)", "price": 15000, "effect": "boost"},
}

# --- Работа с инвентарём ---
def get_inventory(user_id):
    data = load_json(SHOP_FILE)
    return data.get(str(user_id), [])

def add_to_inventory(user_id, item_code):
    data = load_json(SHOP_FILE)
    uid = str(user_id)
    data.setdefault(uid, [])
    data[uid].append(item_code)
    save_json(SHOP_FILE, data)

def remove_from_inventory(user_id, item_code):
    data = load_json(SHOP_FILE)
    uid = str(user_id)
    if uid in data and item_code in data[uid]:
        data[uid].remove(item_code)
        save_json(SHOP_FILE, data)

# --- VIP функции ---
def add_vip(user_id):
    data = load_json(BOOST_FILE)
    data.setdefault("vip", [])
    if str(user_id) not in data["vip"]:
        data["vip"].append(str(user_id))
    save_json(BOOST_FILE, data)

def remove_vip(user_id):
    data = load_json(BOOST_FILE)
    uid = str(user_id)
    if "vip" in data and uid in data["vip"]:
        data["vip"].remove(uid)
    save_json(BOOST_FILE, data)

def is_vip(user_id):
    data = load_json(BOOST_FILE)
    return "vip" in data and str(user_id) in data["vip"]

# --- Luck функции ---
def add_luck(user_id):
    data = load_json(BOOST_FILE)
    data.setdefault("luck", {})
    data["luck"][str(user_id)] = time.time() + 3600  # 1 час
    save_json(BOOST_FILE, data)
    # Автоматическое удаление через 1 час
    threading.Timer(3600, remove_luck, args=[user_id]).start()

def remove_luck(user_id):
    data = load_json(BOOST_FILE)
    uid = str(user_id)
    if "luck" in data and uid in data["luck"]:
        del data["luck"][uid]
        save_json(BOOST_FILE, data)

def is_luck_active(user_id):
    data = load_json(BOOST_FILE)
    uid = str(user_id)
    return "luck" in data and uid in data["luck"] and time.time() < data["luck"][uid]

# --- Boost функции ---
def add_boost(user_id):
    data = load_json(BOOST_FILE)
    data.setdefault("boost", {})
    data["boost"][str(user_id)] = time.time() + 3600  # 1 час
    save_json(BOOST_FILE, data)
    threading.Timer(3600, remove_boost, args=[user_id]).start()

def remove_boost(user_id):
    data = load_json(BOOST_FILE)
    uid = str(user_id)
    if "boost" in data and uid in data["boost"]:
        del data["boost"][uid]
        save_json(BOOST_FILE, data)

def is_boost_active(user_id):
    data = load_json(BOOST_FILE)
    uid = str(user_id)
    return "boost" in data and uid in data["boost"] and time.time() < data["boost"][uid]

# --- Применение эффекта предмета ---
def apply_effect(bot, user, code):
    if code == "xp100":
        add_xp(user.id, 100)
        return f"🎓 {get_display_name(user)} получил +100 XP!"
    elif code == "xp500":
        add_xp(user.id, 500)
        return f"🎓 {get_display_name(user)} получил +500 XP!"
    elif code == "vip":
        add_vip(user.id)
        return f"👑 {get_display_name(user)} теперь VIP навсегда!"
    elif code == "luck":
        add_luck(user.id)
        return f"🍀 Удача активирована на 1 час! Шанс в колесе выше."
    elif code == "boost":
        add_boost(user.id)
        return f"⚡ Буст активирован на 1 час! +10% к выигрышам."
    return "❌ Эффект не распознан."

# --- Регистрация команд бота ---
def register(bot):
    @bot.message_handler(commands=["shop"])
    def show_shop(message):
        text = "🛒 *Магазин предметов:*\n"
        for code, item in ITEMS.items():
            text += f"\n{item['name']} — `{item['price']} Виртов`\n➤ Купить: `/buy {code}`"
        bot.send_message(message.chat.id, text, parse_mode="Markdown")

    @bot.callback_query_handler(func=lambda call: call.data.startswith("confirm_buy:"))
    def confirm_buy(call):
        code = call.data.split(":")[1]
        user_id = call.from_user.id
        item = ITEMS.get(code)
        if not item or get_balance(user_id) < item["price"]:
            bot.answer_callback_query(call.id, "❌ Ошибка: недостаточно средств или предмета.")
            return
        reduce_balance(user_id, item["price"])
        add_to_inventory(user_id, code)
        bot.answer_callback_query(call.id, "✅ Куплено!")
        bot.edit_message_text(
            f"✅ Вы купили {item['name']}!\n➤ Используйте: `/use {code}`\n💰 Ваш баланс: {get_balance(user_id)} Виртов",
            call.message.chat.id, call.message.message_id, parse_mode="Markdown"
        )

    @bot.message_handler(commands=["buy"])
    def buy_item(message):
        args = message.text.split()
        if len(args) < 2:
            return bot.reply_to(message, "⚠️ Укажите код предмета: /buy xp100")
        code = args[1]
        if code not in ITEMS:
            return bot.reply_to(message, "❌ Нет такого предмета. Посмотрите /shop")
        item = ITEMS[code]
        if get_balance(message.from_user.id) < item["price"]:
            return bot.reply_to(message, "💸 Недостаточно Виртов.")
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("Подтвердить", callback_data=f"confirm_buy:{code}"))
        bot.send_message(
            message.chat.id,
            f"🛒 Подтвердите покупку {item['name']} за {item['price']} Виртов?",
            reply_markup=markup
        )

    @bot.message_handler(commands=["inventory"])
    def show_inventory(message):
        inv = get_inventory(message.from_user.id)
        if not inv:
            return bot.send_message(message.chat.id, "🎒 Инвентарь пуст.")
        text = "🎒 *Ваш инвентарь:*\n"
        for i, code in enumerate(inv, 1):
            name = ITEMS.get(code, {'name': code})['name']
            if code == "vip" and is_vip(message.from_user.id):
                name += " (Активирован навсегда)"
            elif code == "luck" and is_luck_active(message.from_user.id):
                name += " (Активна)"
            elif code == "boost" and is_boost_active(message.from_user.id):
                name += " (Активен)"
            text += f"{i}. {name} (`{code}`)\n"
        text += "\n➤ Использовать предмет: `/use <код>`"
        bot.send_message(message.chat.id, text, parse_mode="Markdown")

    @bot.callback_query_handler(func=lambda call: call.data.startswith("confirm_use:"))
    def confirm_use(call):
        code = call.data.split(":")[1]
        user_id = call.from_user.id
        inv = get_inventory(user_id)
        if code not in inv:
            bot.answer_callback_query(call.id, "❌ Предмета нет в инвентаре.")
            return
        msg = apply_effect(bot, call.from_user, code)
        remove_from_inventory(user_id, code)
        bot.answer_callback_query(call.id, "✅ Использовано!")
        bot.edit_message_text(msg, call.message.chat.id, call.message.message_id, parse_mode="Markdown")

    @bot.message_handler(commands=["use"])
    def use_item(message):
        args = message.text.split()
        if len(args) < 2:
            return bot.reply_to(message, "⚠️ Укажите код предмета: /use xp100")
        code = args[1]
        inv = get_inventory(message.from_user.id)
        if code not in inv:
            return bot.reply_to(message, "❌ У вас нет такого предмета.")
        markup = types.InlineKeyboardMarkup()
        markup.add(types.InlineKeyboardButton("Подтвердить", callback_data=f"confirm_use:{code}"))
        bot.send_message(
            message.chat.id,
            f"🎒 Подтвердите использование {ITEMS[code]['name']}?",
            reply_markup=markup
        )
# ...existing code...