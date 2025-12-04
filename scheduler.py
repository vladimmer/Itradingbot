# scheduler.py
import asyncio
import time
from datetime import datetime
import pytz

from storage import load_users, save_symbol_cache, load_symbol_cache
from binance_api import get_klines, get_top_symbols
from analytics import (
    kline_to_volatility, quote_volume_from_kline,
    compute_avg_volume, determine_level
)
from notifier import send_message, format_signal, format_top_3
from cache import cache

INTERVAL = 300  # 5 минут
MOSCOW_TZ = pytz.timezone('Europe/Moscow')

async def update_symbol_history(symbol: str):
    """Обновляет историю свечей (последние 72) в symbol_cache.json"""
    cache_data = load_symbol_cache()
    klines = get_klines(symbol, limit=73)  # 73 чтобы точно была новая
    if not klines:
        return
    new_kline = klines[-1]
    if symbol not in cache_data:
        cache_data[symbol] = []
    history = cache_data[symbol]
    # Добавляем новую свечу, если она новее последней
    if not history or new_kline[0] > history[-1][0]:
        history.append(new_kline)
        # Оставляем только последние 72
        if len(history) > 72:
            history = history[-72:]
        cache_data[symbol] = history
        save_symbol_cache(cache_data)

async def main_cycle():
    """Основной цикл — выполняется каждые 5 минут"""
    print(f"[{datetime.now(MOSCOW_TZ).strftime('%H:%M:%S')}] Запуск цикла проверки...")
    
    users = load_users()
    all_symbols = {"BTCUSDT"}  # всегда мониторим BTC
    top_users = []

    # Собираем все нужные символы
    for chat_id, data in users.items():
        all_symbols.update(data.get("symbols", []))
        if data.get("top_volatile", False):
            top_users.append(int(chat_id))

    # Топ-100 только в 15:00–21:00 МСК
    now_moscow = datetime.now(MOSCOW_TZ)
    is_top_time = 15 <= now_moscow.hour < 21
    top100 = get_top_symbols(100) if (is_top_time and top_users) else []
    all_symbols.update(top100)

    # Получаем текущие данные для всех символов
    current_data = {}
    for symbol in all_symbols:
        await update_symbol_history(symbol)
        kline = get_klines(symbol, limit=1)
        if kline:
            cache.set(symbol, kline[-1])  # кешируем на 5 мин
            current_data[symbol] = kline[-1]

    # Отправляем сигналы
    btc_kline = current_data.get("BTCUSDT")
    btc_vol = kline_to_volatility(btc_kline) if btc_kline else 0
    btc_level = determine_level(btc_vol, "BTCUSDT")

    symbol_cache = load_symbol_cache()

    for chat_id_str, user_data in users.items():
        chat_id = int(chat_id_str)
        mode = user_data.get("mode", "modbag")
        symbols = user_data.get("symbols", [])

        for symbol in symbols:
            kline = current_data.get(symbol)
            if not kline:
                continue

            vol_pct = kline_to_volatility(kline)
            volume = quote_volume_from_kline(kline)
            history = symbol_cache.get(symbol, [])
            avg_volume = compute_avg_volume(history)

            if volume <= avg_volume:
                continue  # объём не выше среднего — пропускаем

            level = determine_level(vol_pct, symbol)

            send = False
            if mode == "modmarket" and btc_level >= 3:
                send = True
            elif mode == "modbag" and level >= 3:
                send = True

            if send:
                text = format_signal(
                    symbol=symbol,
                    vol_pct=vol_pct,
                    level=level,
                    volume=volume,
                    avg_volume=avg_volume,
                    btc_vol_pct=btc_vol if mode == "modmarket" else None,
                    btc_level=btc_level if mode == "modmarket" else None
                )
                await send_message(chat_id, text)

        # Топ-3
        if chat_id in top_users and is_top_time and top100:
            top_list = []
            for sym in top100:
                k = current_data.get(sym)
                if k:
                    top_list.append((sym, kline_to_volatility(k)))
            top_list = sorted(top_list, key=lambda x: x[1], reverse=True)[:3]
            if top_list:
                text = format_top_3(top_list)
                await send_message(chat_id, text)

async def run_scheduler():
    """Запускает бесконечный цикл каждые 5 минут"""
    while True:
        start_time = time.time()
        await main_cycle()
        elapsed = time.time() - start_time
        sleep_time = max(0, INTERVAL - elapsed)
        await asyncio.sleep(sleep_time)
