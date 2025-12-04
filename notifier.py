# notifier.py
from telegram import Bot
from telegram.constants import ParseMode
from config import TELEGRAM_TOKEN
from analytics import get_level_emoji

bot = Bot(token=TELEGRAM_TOKEN)

async def send_message(chat_id: int, text: str):
    """Отправляет сообщение пользователю"""
    try:
        await bot.send_message(chat_id=chat_id, text=text, parse_mode=ParseMode.HTML)
    except Exception as e:
        print(f"Ошибка отправки сообщения {chat_id}: {e}")

def format_signal(symbol, vol_pct, level, volume, avg_volume, btc_vol_pct=None, btc_level=None):
    """Форматирует текст сигнала"""
    emoji = get_level_emoji(level)
    text = f"<b>{symbol}</b>: Волатильность {vol_pct:.2f}% {emoji}\n"
    text += f"Объём: {volume:.2f} USDT (средний за 6ч: {avg_volume:.2f} USDT)\n"
    if btc_vol_pct is not None and btc_level is not None:
        btc_emoji = get_level_emoji(btc_level)
        text += f"BTC: {btc_vol_pct:.2f}% {btc_emoji}"
    return text

def format_top_3(top_vols):
    """Форматирует топ-3"""
    text = "Топ-3 волатильных монет сейчас:\n"
    for sym, vol in top_vols:
        text += f"{sym}: {vol:.2f}%\n"
    return text