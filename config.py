import os
from dotenv import load_dotenv

# Загружаем .env из корня проекта
load_dotenv()

# Токен телеграм-бота
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
if not TELEGRAM_TOKEN:
    raise ValueError("Не найден TELEGRAM_TOKEN в .env")

# Binance API
BINANCE_REST = os.getenv("BINANCE_REST", "https://fapi.binance.com")

# Папки
DATA_DIR = os.getenv("DATA_DIR", "data")
LOG_DIR = os.getenv("LOG_DIR", "logs")
ADMIN_ID = int(os.getenv("ADMIN_ID", "0"))  # потом заменишь на свой настоящий ID

# Создаём папки, если их нет
os.makedirs(DATA_DIR, exist_ok=True)
os.makedirs(LOG_DIR, exist_ok=True)

# Пути к файлам с данными
USERS_FILE = os.path.join(DATA_DIR, "users.json")
THRESHOLDS_FILE = os.path.join(DATA_DIR, "thresholds.json")
SYMBOL_CACHE_FILE = os.path.join(DATA_DIR, "symbol_cache.json")