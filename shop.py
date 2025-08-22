from data_base import load_json, save_json, get_balance, reduce_balance, add_balance
from xp_status import get_display_name, add_xp
from confiq import SHOP_FILE, BOOST_FILE
from telebot.types import Message

# --- Предметы магазина ---
ITEMS = {
    "xp100": {"name": "🎓 +100 XP", "price": 5000, "effect": "add_xp"},
    "vip": {"name": "👑 VIP статус", "price": 100000, "effect": "vip_status"},
    "luck": {"name": "🍀 Удача (повышает шанс в колесе)", "price": 5000, "effect": "luck"},
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
    uid = str(user_id)
    data.setdefault("vip", [])
    if uid not in data["vip"]:
        data["vip"].append(uid)
    save_json(BOOST_FILE, data)

def remove_vip(user_id):
    data = load_json(BOOST_FILE)
    uid = str(user_id)
    if "vip" in data and uid in data["vip"]:
        data["vip"].remove(uid)
    save_json(BOOST_FILE, data)

def is_vip(user_id):
    data = load_json(BOOST_FILE)
    uid = str(user_id)
    return "vip" in data and uid in data["vip"]

# --- Другие эффекты ---
def add_luck(user_id):
    data = load_json(BOOST_FILE)
    uid = str(user_id)
    data.setdefault("luck", [])
    if uid not in data["luck"]:
        data["luck"].append(uid)
    save_json(BOOST_FILE, data)

# --- Применение эффекта предмета ---
def apply_effect(bot, user, code):
    if code == "xp100":
        add_xp(user.id, 100)
        return f"🎓 {get_display_name(user)} получил +100 XP!"
    elif code == "vip":
        add_vip(user.id)
        return f"👑 {get_display_name(user)} теперь VIP!"
    elif code == "luck":
        add_luck(user.id)
        return f"🍀 Удача активирована! Теперь шанс в колесе выше"
    return "❌ Эффект не распознан."

# --- Регистрация команд бота ---
def register(bot):
    @bot.message_handler(commands=["shop"])
    def show_shop(message: Message):
        text = "🛒 *Магазин предметов:*\n"
        for code, item in ITEMS.items():
            text += f"\n{item['name']} — `{item['price']} Виртов`\n➤ Купить: `/buy {code}`"
        bot.send_message(message.chat.id, text, parse_mode="Markdown")

    @bot.message_handler(commands=["buy"])
    def buy_item(message: Message):
        args = message.text.split()
        if len(args) < 2:
            return bot.reply_to(message, "⚠️ Укажите код предмета: /buy xp100")

        code = args[1]
        user = message.from_user

        if code not in ITEMS:
            return bot.reply_to(message, "❌ Нет такого предмета. Посмотрите /shop")

        item = ITEMS[code]
        if get_balance(user.id) < item["price"]:
            return bot.reply_to(message, "💸 Недостаточно Виртов.")

        reduce_balance(user.id, item["price"])
        add_to_inventory(user.id, code)

        bot.send_message(
            message.chat.id,
            f"✅ Вы купили {item['name']}!\n➤ Используйте: `/use {code}`",
            parse_mode="Markdown"
        )

    @bot.message_handler(commands=["inventory"])
    def show_inventory(message: Message):
        inv = get_inventory(message.from_user.id)
        if not inv:
            return bot.send_message(message.chat.id, "🎒 Инвентарь пуст.")
        text = "🎒 *Ваш инвентарь:*\n"
        for i, code in enumerate(inv, 1):
            name = ITEMS.get(code, {'name': code})['name']
            if code == "vip" and is_vip(message.from_user.id):
                name += " (Активирован)"
            elif code == "luck":
                from_boost = load_json(BOOST_FILE)
                if str(message.from_user.id) in from_boost.get("luck", []):
                    name += " (Активирована)"
            text += f"{i}. {name} (`{code}`)\n"
        text += "\n➤ Использовать предмет: `/use <код>`"
        bot.send_message(message.chat.id, text, parse_mode="Markdown")

    @bot.message_handler(commands=["use"])
    def use_item(message: Message):
        args = message.text.split()
        if len(args) < 2:
            return bot.reply_to(message, "⚠️ Укажите код предмета: /use xp100")

        code = args[1]
        inv = get_inventory(message.from_user.id)
        if code not in inv:
            return bot.reply_to(message, "❌ У вас нет такого предмета.")

        msg = apply_effect(bot, message.from_user, code)
        remove_from_inventory(message.from_user.id, code)
        bot.send_message(message.chat.id, msg, parse_mode="Markdown")
