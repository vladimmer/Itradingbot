# notifier.py
from telegram import Bot
from telegram.constants import ParseMode
from config import TELEGRAM_TOKEN
from analytics import get_level_emoji

bot = Bot(token=TELEGRAM_TOKEN)

async def send_message(chat_id: int, text: str, disable_notification=False):
    try:
        await bot.send_message(
            chat_id=chat_id,
            text=text,
            parse_mode=ParseMode.HTML,
            disable_notification=disable_notification
        )
    except Exception as e:
        print(f"Ошибка отправки сообщения {chat_id}: {e}")

def format_volume_info(volume_5m, taker_buy_volume, avg_volume):
    volume_str = f"{int(volume_5m):,}".replace(",", " ")
    color = "🟢" if taker_buy_volume > volume_5m / 2 else "🔴"
    food = "🍗" if volume_5m > avg_volume else "🦴"
    return f"Volume 5 min: {volume_str} {color}{food}"

def format_signal(symbol, vol_pct, level, volume_5m, taker_buy_volume, avg_volume, btc_vol_pct, btc_level):
    pair_emoji = get_level_emoji(level)
    btc_emoji = get_level_emoji(btc_level)

    text = f"<b>{symbol}</b>\n"
    text += f"{format_volume_info(volume_5m, taker_buy_volume, avg_volume)}\n"
    text += f"Volatility 5 min: {vol_pct:.2f}% {pair_emoji}\n"
    text += f"BTC volatility 5 min: {btc_vol_pct:.2f}% {btc_emoji}"

    return text

def format_top_3(top_vols):
    text = "<b>Топ-3 волатильных монет сейчас:</b>\n"
    for sym, vol in top_vols:
        text += f"• {sym}: {vol:.2f}%\n"
    return text