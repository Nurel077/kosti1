import os
import json
from confiq import BALANCE_FILE

def load_json(filename):
    """Загружает JSON из файла, возвращает {} если файла нет или ошибка."""
    try:
        if not os.path.exists(filename):
            return {}
        with open(filename, "r", encoding="utf-8") as f:
            return json.load(f)
    except (json.JSONDecodeError, IOError) as e:
        print(f"Ошибка загрузки {filename}: {e}")
        return {}

def save_json(filename, data):
    """Сохраняет данные в JSON файл."""
    try:
        with open(filename, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except IOError as e:
        print(f"Ошибка сохранения {filename}: {e}")

def get_balance(user_id):
    balances = load_json(BALANCE_FILE)
    return balances.get(str(user_id), 1000)

def set_balance(user_id, amount):
    balances = load_json(BALANCE_FILE)
    balances[str(user_id)] = amount  # Оставляю без max(0), баланс может быть отрицательным
    save_json(BALANCE_FILE, balances)

def add_balance(user_id, amount):
    set_balance(user_id, get_balance(user_id) + amount)

def reduce_balance(user_id, amount):
    set_balance(user_id, get_balance(user_id) - amount)

def transfer_balance(from_user_id, to_user_id, amount):
    """Перевести средства от одного пользователя к другому."""
    reduce_balance(from_user_id, amount)
    add_balance(to_user_id, amount)

def get_top_balances(limit=10):
    """Получить топ пользователей по балансу (список [(user_id, balance), ...])."""
    balances = load_json(BALANCE_FILE)
    return sorted(balances.items(), key=lambda x: x[1], reverse=True)[:limit]

def reset_all_balances():
    """Обнуляет баланс всех пользователей"""
    balances = load_json(BALANCE_FILE)

    if not balances:
        return False  # если база пустая

    for user_id in balances.keys():
        balances[user_id] = 0

    save_json(BALANCE_FILE, balances)
    return True
# ...existing code...