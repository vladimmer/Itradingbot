# Traderbot — Binance Futures Volatility Bot

Telegram-бот, который ловит мощные движения на фьючерсах Binance и присылает сигналы в момент взрыва волатильности.

### Что умеет
- Два режима работы:  
  • **Нагибаю рынок** — сигналы только когда BTC тоже сильно двигается  
  • **Нагибаю портфель** — сигналы по каждой монете независимо  
- Уровни волатильности 1–4 (на основе квартилей за последние 14 дней)  
- Топ-3 самых жирных монет каждый день с 15:00 до 21:00 МСК  
- До 5 монет на пользователя (старые автоматически удаляются)  
- Автообновление порогов каждую неделю

### Как запустить локально

```bash
git clone https://github.com/ТВОЙ_НИК/Traderbot.git
cd Traderbot
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt

copy .env.example .env
# → открой .env и вставь свой настоящий TELEGRAM_TOKEN

mkdir data logs

python compute_thresholds.py   # первый раз — посчитать пороги
python bot.py                  # запуск бота