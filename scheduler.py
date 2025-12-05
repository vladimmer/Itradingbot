# scheduler.py
import asyncio
import time
from datetime import datetime
import pytz

from storage import load_users, save_symbol_cache, load_symbol_cache, _load_json, _save_json
from binance_api import get_klines, get_top_symbols
from analytics import (
    kline_to_volatility, quote_volume_from_kline,
    compute_avg_volume, determine_level, calculate_sma
)
from notifier import send_message, format_signal, format_top_3
from cache import cache

INTERVAL = 300  # 5 минут
MOSCOW_TZ = pytz.timezone('Europe/Moscow')
PINNED_FILE = "data/pinned_messages.json"  # храним ID закреплённых сообщений

def load_pinned():
    return _load_json(PINNED_FILE, {})

def save_pinned(data):
    _save_json(PINNED_FILE, data)

async def get_trend_status():
    """Возвращает строку вроде '4h🔴1h🟢15m🔴' для BTCUSDT"""
    tfs = {
        "4h": ("4h", 200),
        "1h": ("1h", 200),
        "15m": ("15m", 200)
    }
    result = []
    for tf_name, (interval, period) in tfs.items():
        klines = get_klines("BTCUSDT", interval=interval, limit=period + 10)
        if klines and len(klines) >= period:
            sma = calculate_sma(klines, period)
            current_price = float(klines[-1][4])
            emoji = "🟢" if current_price > sma else "🔴"
        else:
            emoji = "⚪"
        result.append(f"{tf_name}{emoji}")
    return "".join(result)

async def update_pinned_trend(chat_id):
    """Создаёт или обновляет закреплённое сообщение с трендом"""
    pinned_data = load_pinned()
    current_text = await get_trend_status()
    message_id = pinned_data.get(str(chat_id))

    msg = await send_message(chat_id, current_text + "\n\n<i>Тренд BTC по 200 SMA (обновляется каждые 5 мин)</i>", disable_notification=True)
    
    if message_id:
        # редактируем старое
        try:
            await msg.edit_text(current_text + "\n\n<i>Тренд BTC по 200 SMA (обновляется каждые 5 мин)</i>", parse_mode="HTML")
            await msg.pin(disable_notification=True)
            return
        except:
            pass  # если не удалось — создаём новое ниже
    
    # создаём новое и закрепляем
    await msg.pin(disable_notification=True)
    pinned_data[str(chat_id)] = msg.message_id
    save_pinned(pinned_data)

async def unpin_old_message(chat_id):
    """Открепляет старое сообщение при выходе из времени 15-21"""
    pinned_data = load_pinned()
    message_id = pinned_data.get(str(chat_id))
    if message_id:
        try:
            # тут просто удалим запись — бот не может сам открепить чужое сообщение, но мы перестанем его трогать
            del pinned_data[str(chat_id)]
            save_pinned(pinned_data)
        except:
            pass

async def main_cycle():
    print(f"[{datetime.now(MOSCOW_TZ).strftime('%H:%M:%S')}] Запуск цикла проверки...")
    
    users = load_users()
    all_symbols = {"BTCUSDT"}
    top_users = []
    market_mode_users = []  # пользователи в modmarket

    for chat_id, data in users.items():
        all_symbols.update(data.get("symbols", []))
        if data.get("top_volatile", False):
            top_users.append(int(chat_id))
        if data.get("mode") == "modmarket":
            market_mode_users.append(int(chat_id))

    now_moscow = datetime.now(MOSCOW_TZ)
    is_trend_time = 15 <= now_moscow.hour < 21

    # === ТРЕНД (закреплённое сообщение) ===
    if is_trend_time and market_mode_users:
        for chat_id in market_mode_users:
            await update_pinned_trend(chat_id)
    else:
        # если время вышло — убираем закреплённые сообщения у всех
        for chat_id in market_mode_users:
            await unpin_old_message(chat_id)

    # === Остальная логика (сигналы + топ-3) без изменений ===
    top100 = get_top_symbols(100) if (is_trend_time and top_users) else []
    all_symbols.update(top100)

    current_data = {}
    for symbol in all_symbols:
        await update_symbol_history(symbol)
        kline = get_klines(symbol, limit=1)
        if kline:
            cache.set(symbol, kline[-1])
            current_data[symbol] = kline[-1]

    btc_kline = current_data.get("BTCUSDT")
    btc_vol = kline_to_volatility(btc_kline) if btc_kline else 0
    btc_level = determine_level(btc_vol, "BTCUSDT")
    symbol_cache = load_symbol_cache()

    for chat_id_str, user_data in users.items():
        chat_id = int(chat_id_str)
        mode = user_data.get("mode", "modbag")
        symbols = user_data.get("symbols", [])

        # обычные сигналы
        for symbol in symbols:
            kline = current_data.get(symbol)
            if not kline:
                continue

            vol_pct = kline_to_volatility(kline)
            volume_5m = quote_volume_from_kline(kline)
            taker_buy_volume = float(kline[9]) if len(kline) > 9 else volume_5m / 2
            history = symbol_cache.get(symbol, [])
            avg_volume = compute_avg_volume(history)

            # Уровни
            level = determine_level(vol_pct, symbol)

            # Условие отправки: BTC >=3 ИЛИ монета >=3 — вне зависимости от режима!
            send = (btc_level >= 3) or (level >= 3)

            if send and volume_5m > avg_volume:  # + объём выше среднего
                text = format_signal(
                    symbol=symbol,
                    vol_pct=vol_pct,
                    level=level,
                    volume_5m=volume_5m,
                    taker_buy_volume=taker_buy_volume,
                    avg_volume=avg_volume,
                    btc_vol_pct=btc_vol,
                    btc_level=btc_level
                )
                await send_message(chat_id, text)
        # топ-3
        if chat_id in top_users and is_trend_time and top100:
            top_list = []
            for sym in top100:
                k = current_data.get(sym)
                if k:
                    top_list.append((sym, kline_to_volatility(k)))
            top_list = sorted(top_list, key=lambda x: x[1], reverse=True)[:3]
            if top_list:
                await send_message(chat_id, format_top_3(top_list))

# оставляем функцию без изменений
async def update_symbol_history(symbol: str):
    cache_data = load_symbol_cache()
    klines = get_klines(symbol, limit=73)
    if not klines: return
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

async def run_scheduler():
    while True:
        start_time = time.time()
        await main_cycle()
        elapsed = time.time() - start_time
        await asyncio.sleep(max(0, INTERVAL - elapsed))