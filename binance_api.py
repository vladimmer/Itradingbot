# binance_api.py
import requests
import time
from config import BINANCE_REST

KLINES_ENDPOINT = BINANCE_REST + "/fapi/v1/klines"
TICKER_24H_ENDPOINT = BINANCE_REST + "/fapi/v1/ticker/24hr"

def get_klines(symbol: str, interval: str = "5m", limit: int = 1, end_time: int = None):
    """Получает свечи с Binance"""
    params = {"symbol": symbol.upper(), "interval": interval, "limit": limit}
    if end_time:
        params["endTime"] = end_time
    try:
        response = requests.get(KLINES_ENDPOINT, params=params, timeout=10)
        response.raise_for_status()
        return response.json()
    except Exception as e:
        print(f"Ошибка при получении klines для {symbol}: {e}")
        return []

def get_recent_klines(symbol: str, interval: str = "5m", count: int = 4032):
    """Получает последние N свечей (для истории или порогов)"""
    klines = []
    end_time = None
    remaining = count
    while remaining > 0:
        batch_limit = min(1000, remaining)
        batch = get_klines(symbol, interval, batch_limit, end_time)
        if not batch:
            break
        klines = batch + klines  # Добавляем в конец (API даёт старые сначала)
        if batch:
            earliest_time = int(batch[0][0])
            end_time = earliest_time - 1
        remaining -= len(batch)
        time.sleep(0.2)  # Задержка, чтобы не превысить лимиты API
    return klines[-count:] if len(klines) > count else klines

def get_top_symbols(count: int = 100):
    """Получает топ-N символов по 24h quoteVolume (только USDT-фьючерсы)"""
    try:
        response = requests.get(TICKER_24H_ENDPOINT, timeout=10)
        response.raise_for_status()
        data = response.json()
        usdt_futures = [item for item in data if item["symbol"].endswith("USDT")]
        sorted_symbols = sorted(usdt_futures, key=lambda x: float(x["quoteVolume"]), reverse=True)
        return [item["symbol"] for item in sorted_symbols[:count]]
    except Exception as e:
        print(f"Ошибка при получении топ-символов: {e}")
        return []
