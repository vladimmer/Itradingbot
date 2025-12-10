# scheduler.py
import asyncio
import time
from datetime import datetime
import pytz

from storage import load_users, save_symbol_cache, load_symbol_cache
from binance_api import get_klines, get_top_symbols
from analytics import (
    kline_to_volatility, quote_volume_from_kline,
    compute_avg_volume, determine_level, calculate_sma
)
from notifier import send_message, format_signal, format_top_3
from cache import cache

INTERVAL = 300  # 5 минут
MOSCOW_TZ = pytz.timezone('Europe/Moscow')

# Тренд BTC
async def get_trend_status():
    tfs = {"4h": ("4h", 200), "1h": ("1h", 200), "15m": ("15m", 200)}
    result = []
    for tf_name, (interval, period) in tfs.items():
        klines = get_klines("BTCUSDT", interval=interval, limit=period + 10)
        if klines and len(klines) >= period:
            sma = calculate_sma(klines, period)
            price = float(klines[-1][4])
            emoji = "🟢" if price > sma else "🔴"
        else:
            emoji = "⚪"
        result.append(f"{tf_name}{emoji}")
    return "".join(result)

# Обновление истории (только для нужных монет)
async def update_symbol_history(symbol: str):
    cache_data = load_symbol_cache()
    klines = get_klines(symbol, limit=73)
    if not klines:
        return
    new_kline = klines[-1]
    if symbol not in cache_data:
        cache_data[symbol] = []
    history = cache_data[symbol]
    if not history or new_kline[0] > history[-1][0]:
        history.append(new_kline)
        if len(history) > 72:
            history = history[-72:]
        cache_data[symbol] = history
        save_symbol_cache(cache_data)

async def main_cycle():
    print(f"[{datetime.now(MOSCOW_TZ).strftime('%H:%M:%S')}] Запуск цикла...")

    users = load_users()
    all_symbols = {"BTCUSDT"}
    top_users = []

    # Сбор символов и кто хочет топ-3
    for chat_id_str, data in users.items():
        chat_id = int(chat_id_str)
        all_symbols.update(data.get("symbols", []))

    top_volatile = data.get("top_volatile", False)
    if isinstance(top_volatile, str):
        top_volatile = top_volatile.lower() == "true"
    if top_volatile:
        top_users.append(chat_id)


    # Топ-30 (если хоть один хочет топ)
    top100 = get_top_symbols(30) if top_users else []
    all_symbols.update(top100)

    # Текущие свечи для всех
    current_data = {}
    for symbol in all_symbols:
        kline = get_klines(symbol, limit=1)
        if kline:
            current_data[symbol] = kline[-1]

    # История только для твоих монет + BTC (чтобы были сигналы!)
    need_history = {"BTCUSDT"}
    for data in users.values():
        need_history.update(data.get("symbols", []))
    for symbol in need_history:
        if symbol in current_data:  # уже есть свеча
            await update_symbol_history(symbol)

    # BTC
    btc_kline = current_data.get("BTCUSDT")
    btc_vol = kline_to_volatility(btc_kline) if btc_kline else 0
    btc_level = determine_level(btc_vol, "BTCUSDT")
    symbol_cache = load_symbol_cache()
    trend_text = await get_trend_status()

    # По каждому пользователю
    for chat_id_str, user_data in users.items():
        chat_id = int(chat_id_str)
        symbols = user_data.get("symbols", [])

        # Сигналы
        for symbol in symbols:
            kline = current_data.get(symbol)
            if not kline:
                continue
            vol_pct = kline_to_volatility(kline)
            volume_5m = quote_volume_from_kline(kline)
            taker_buy_volume = float(kline[9]) if len(kline) > 9 else volume_5m / 2
            history = symbol_cache.get(symbol, [])
            avg_volume = compute_avg_volume(history)
            level = determine_level(vol_pct, symbol)

            send = (btc_level >= 3) or (level >= 3)
            if send and volume_5m > avg_volume:
                text = format_signal(
                    symbol=symbol, vol_pct=vol_pct, level=level,
                    volume_5m=volume_5m, taker_buy_volume=taker_buy_volume,
                    avg_volume=avg_volume, btc_vol_pct=btc_vol, btc_level=btc_level
                )
                await send_message(chat_id, text)

        # Топ-3 + тренд
        if chat_id in top_users and top100:
            top_list = [(sym, kline_to_volatility(current_data[sym])) 
                       for sym in top100 if sym in current_data]
            top_list = sorted(top_list, key=lambda x: x[1], reverse=True)[:3]
            if top_list:
                text = f"<b>Тренд BTC:</b> {trend_text}\n\n"
                text += format_top_3(top_list)
                await send_message(chat_id, text)

async def run_scheduler():
    while True:
        start = time.time()
        await main_cycle()
        elapsed = time.time() - start
        print(f"Цикл завершён за {elapsed:.2f} сек")
        await asyncio.sleep(max(0, INTERVAL - elapsed))