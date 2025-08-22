from datetime import datetime
from confiq import DUEL_HISTORY_FILE
from data_base import load_json, save_json

def can_duel(user_id):
    history = load_json(DUEL_HISTORY_FILE)
    now = datetime.now().timestamp()
    one_hour_ago = now - 3600
    user_id = str(user_id)
    history.setdefault(user_id, [])
    recent = [t for t in history[user_id] if t > one_hour_ago]
    if len(recent) >= 10:
        return False
    recent.append(now)
    history[user_id] = recent
    save_json(DUEL_HISTORY_FILE, history)
    return True

def get_display_name(user):
    return user.first_name or user.username or f"{user.id}"
from datetime import datetime
from confiq import DUEL_HISTORY_FILE
from data_base import load_json, save_json



def can_duel(user_id):
    history = load_json(DUEL_HISTORY_FILE)
    now = datetime.now().timestamp()
    one_hour_ago = now - 3600
    user_id = str(user_id)
    history.setdefault(user_id, [])
    recent = [t for t in history[user_id] if t > one_hour_ago]
    if len(recent) >= 10:
        return False
    recent.append(now)
    history[user_id] = recent
    save_json(DUEL_HISTORY_FILE, history)
    return True

def get_display_name(user):
    return user.first_name or user.username or f"{user.id}"
