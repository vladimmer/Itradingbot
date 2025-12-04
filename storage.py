# storage.py
import json
import os
from config import USERS_FILE, THRESHOLDS_FILE, SYMBOL_CACHE_FILE
from threading import Lock

# Защита от одновременной записи в JSON
_lock = Lock()

def _load_json(filepath, default):
    if not os.path.exists(filepath):
        return default
    try:
        with open(filepath, 'r', encoding='utf-8') as f:
            return json.load(f)
    except:
        return default

def _save_json(filepath, data):
    with _lock:
        with open(filepath, 'w', encoding='utf-8') as f:
            json.dump(data, f, ensure_ascii=False, indent=4)

# Пользователи
def load_users():
    return _load_json(USERS_FILE, {})

def save_users(users):
    _save_json(USERS_FILE, users)

# Пороги волатильности (Q25/Q50/Q75)
def load_thresholds():
    return _load_json(THRESHOLDS_FILE, {})

def save_thresholds(thresholds):
    _save_json(THRESHOLDS_FILE, thresholds)

# История свечей (72 последние 5-мин свечи на каждый символ)
def load_symbol_cache():
    return _load_json(SYMBOL_CACHE_FILE, {})

def save_symbol_cache(cache):
    _save_json(SYMBOL_CACHE_FILE, cache)

# Удобные функции для работы с пользователем
def get_user_data(chat_id):
    users = load_users()
    chat_id_str = str(chat_id)
    if chat_id_str not in users:
        users[chat_id_str] = {
            "mode": "modbag",
            "symbols": [],
            "top_volatile": False
        }
        save_users(users)
    return users[chat_id_str]

def update_user_data(chat_id, updates):
    users = load_users()
    chat_id_str = str(chat_id)
    if chat_id_str not in users:
        users[chat_id_str] = {"mode": "modbag", "symbols": [], "top_volatile": False}
    users[chat_id_str].update(updates)
    save_users(users)