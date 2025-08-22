import os
import json
from confiq import BALANCE_FILE



def load_json(filename):
    if not os.path.exists(filename):
        return {}
    with open(filename, "r", encoding="utf-8") as f:
        return json.load(f)

def save_json(filename, data):
    with open(filename, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def load_json(file):
    if not os.path.exists(file):
        return {}
    with open(file, 'r') as f:
        return json.load(f)

def save_json(file, data):
    with open(file, 'w') as f:
        json.dump(data, f)

def get_balance(user_id):
    balances = load_json(BALANCE_FILE)
    return balances.get(str(user_id), 1000)

def set_balance(user_id, amount):
    balances = load_json(BALANCE_FILE)
    balances[str(user_id)] = amount
    save_json(BALANCE_FILE, balances)

def add_balance(user_id, amount):
    set_balance(user_id, get_balance(user_id) + amount)

def reduce_balance(user_id, amount):
    set_balance(user_id, get_balance(user_id) - amount)
