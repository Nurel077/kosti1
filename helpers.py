from datetime import datetime
from confiq import DUEL_HISTORY_FILE
from data_base import load_json, save_json

# Кэш для имён пользователей (чтобы не терять в дуэлях)
user_name_cache = {}

def can_duel(user_id):
    """Проверяет, может ли пользователь участвовать в дуэли (макс 10 в час)."""
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
    """Получить отображаемое имя пользователя."""
    # Сначала проверяем username (предпочтительнее)
    if hasattr(user, 'username') and user.username:
        return f"@{user.username}"
    
    # Потом имя и фамилию
    if hasattr(user, 'first_name') and user.first_name:
        full_name = user.first_name
        if hasattr(user, 'last_name') and user.last_name:
            full_name += f" {user.last_name}"
        return full_name
    
    return f"User {user.id}"