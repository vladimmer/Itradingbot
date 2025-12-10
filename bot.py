# bot.py
import asyncio
import logging
import os
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters

from config import TELEGRAM_TOKEN, ADMIN_ID, LOG_DIR
from storage import get_user_data, update_user_data
from scheduler import run_scheduler

# Настройка логирования
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO,
    handlers=[logging.FileHandler(os.path.join(LOG_DIR, 'bot.log'))]
)
logger = logging.getLogger(__name__)

async def start(update, context):
    chat_id = update.effective_chat.id
    keyboard = [
        [InlineKeyboardButton("Нагибаю рынок (modmarket)", callback_data='mode_modmarket')],
        [InlineKeyboardButton("Нагибаю портфель (modbag)", callback_data='mode_modbag')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Привет! Выбери режим:", reply_markup=reply_markup)

async def mode_callback(update, context):
    query = update.callback_query
    chat_id = query.message.chat_id
    mode = query.data.split('_')[1]
    update_user_data(chat_id, {"mode": mode})
    await query.answer(f"Режим установлен: {mode}")
    keyboard = [
        [InlineKeyboardButton("BTC", callback_data='add_btc')],
        [InlineKeyboardButton("SOL", callback_data='add_sol')],
        [InlineKeyboardButton("ETH", callback_data='add_eth')],
        [InlineKeyboardButton("TRX", callback_data='add_trx')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.message.reply_text("Какой токен начнём отслеживать? (Нажми кнопку или используй /add<symbol>)", reply_markup=reply_markup)

async def add_symbol_callback(update, context):
    query = update.callback_query
    chat_id = query.message.chat_id
    symbol_lower = query.data.split('_')[1]
    symbol = f"{symbol_lower.upper()}USDT"
    user_data = get_user_data(chat_id)
    symbols = user_data["symbols"]
    if symbol not in symbols:
        symbols.append(symbol)
        if len(symbols) > 5:
            removed = symbols.pop(0)
            await query.answer(f"Добавлен {symbol}, удалён старый {removed} (лимит 5)")
        else:
            await query.answer(f"Добавлен {symbol}")
        update_user_data(chat_id, {"symbols": symbols})
    else:
        await query.answer(f"{symbol} уже добавлен")
    keyboard = [
        [InlineKeyboardButton("Да", callback_data='top_on')],
        [InlineKeyboardButton("Нет", callback_data='top_off')]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.message.reply_text("Хотите получать топ-3 волатильных монет (15:00-21:00 МСК)?", reply_markup=reply_markup)

async def top_toggle(update, context):
    chat_id = update.effective_chat.id
    try:
        arg = context.args[0].lower()
    except IndexError:
        await update.message.reply_text("Укажи: /top on или /top off")
        return

    if arg not in ["on", "off"]:
        await update.message.reply_text("Используй: /top on или /top off")
        return

    value = arg == "on"
    update_user_data(chat_id, {"top_volatile": value})  # сохраняем булево
    await update.message.reply_text(f"Топ-3 {'включён' if value else 'выключен'}")

async def add_symbol(update, context):
    chat_id = update.effective_chat.id
    symbol_lower = update.message.text.split('/add')[1].lower()
    symbol = f"{symbol_lower.upper()}USDT"
    user_data = get_user_data(chat_id)
    symbols = user_data["symbols"]
    if symbol not in symbols:
        symbols.append(symbol)
        if len(symbols) > 5:
            removed = symbols.pop(0)
            await update.message.reply_text(f"Добавлен {symbol}, удалён {removed} (FIFO)")
        else:
            await update.message.reply_text(f"Добавлен {symbol}")
        update_user_data(chat_id, {"symbols": symbols})
    else:
        await update.message.reply_text(f"{symbol} уже в списке")

async def remove_symbol(update, context):
    chat_id = update.effective_chat.id
    try:
        symbol = context.args[0].upper() + "USDT"
    except IndexError:
        await update.message.reply_text("Укажи символ: /remove SOL")
        return
    user_data = get_user_data(chat_id)
    symbols = user_data["symbols"]
    if symbol in symbols:
        symbols.remove(symbol)
        update_user_data(chat_id, {"symbols": symbols})
        await update.message.reply_text(f"Удалён {symbol}")
    else:
        await update.message.reply_text(f"{symbol} не найден")

async def list_symbols(update, context):
    chat_id = update.effective_chat.id
    user_data = get_user_data(chat_id)
    symbols = user_data["symbols"]
    mode = user_data["mode"]
    top = "включён" if user_data["top_volatile"] else "выключен"
    text = f"Режим: {mode}\nТоп-3: {top}\nПодписки: {', '.join(symbols) if symbols else 'Нет'}"
    await update.message.reply_text(text)

async def set_mode(update, context):
    chat_id = update.effective_chat.id
    mode = update.message.text[1:]  # /modmarket → modmarket
    if mode not in ["modmarket", "modbag"]:
        await update.message.reply_text("Неверный режим. Используй /modmarket или /modbag")
        return
    update_user_data(chat_id, {"mode": mode})
    await update.message.reply_text(f"Режим установлен: {mode}")

async def top_toggle(update, context):
    chat_id = update.effective_chat.id
    try:
        arg = context.args[0].lower()
    except IndexError:
        await update.message.reply_text("Укажи: /top on или /top off")
        return
    value = arg == "on"
    update_user_data(chat_id, {"top_volatile": value})
    await update.message.reply_text(f"Топ-3 {'включён' if value else 'выключен'}")

async def help_cmd(update, context):
    text = """
Команды:
/start - Начать настройку
/add<symbol> - Добавить монету (пример: /addsol)
/remove <SYMBOL> - Удалить (пример: /remove SOL)
/list - Показать настройки
/modmarket - Режим 'Нагибаю рынок'
/modbag - Режим 'Нагибаю портфель'
/top on/off - Вкл/выкл топ-3
/help - Это сообщение
/recalc - Пересчитать пороги (только админ)
"""
    await update.message.reply_text(text)

async def recalc(update, context):
    chat_id = update.effective_chat.id
    if chat_id != ADMIN_ID:
        await update.message.reply_text("Доступно только админу")
        return
    # Здесь вызовем логику пересчёта (пока заглушка, добавим позже)
    await update.message.reply_text("Пороги пересчитаны (заглушка)")

def main():
    application = Application.builder().token(TELEGRAM_TOKEN) \
        .concurrent_updates(True) \
        .connection_pool_size(100) \
        .pool_timeout(90.0) \
        .build()

    # Хендлеры команд
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("list", list_symbols))
    application.add_handler(CommandHandler("modmarket", set_mode))
    application.add_handler(CommandHandler("modbag", set_mode))
    application.add_handler(CommandHandler("top", top_toggle))
    application.add_handler(CommandHandler("remove", remove_symbol))
    application.add_handler(CommandHandler("help", help_cmd))
    application.add_handler(CommandHandler("recalc", recalc))

    # Кнопки
    application.add_handler(CallbackQueryHandler(mode_callback, pattern='^mode_'))
    application.add_handler(CallbackQueryHandler(add_symbol_callback, pattern='^add_'))

    # Кастом /add<symbol>
    application.add_handler(MessageHandler(filters.Regex(r'^/add\w+$'), add_symbol))

    # Запуск scheduler в фоне
    asyncio.get_event_loop().create_task(run_scheduler())

    application.run_polling()

if __name__ == "__main__":
    main()
