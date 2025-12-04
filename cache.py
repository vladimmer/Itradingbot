# cache.py
import time
from threading import Lock

class SimpleCache:
    def __init__(self):
        self._store = {}
        self._lock = Lock()

    def set(self, key, value, ttl=300):  # ttl в секундах, default 5 мин
        with self._lock:
            self._store[key] = {"value": value, "expiry": time.time() + ttl}

    def get(self, key):
        with self._lock:
            item = self._store.get(key)
            if not item:
                return None
            if item["expiry"] < time.time():
                del self._store[key]
                return None
            return item["value"]

    def clear(self):
        with self._lock:
            self._store.clear()

# Глобальный кеш
cache = SimpleCache()