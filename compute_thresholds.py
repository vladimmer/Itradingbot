# compute_thresholds.py
import json
from config import THRESHOLDS_FILE
from binance_api import get_recent_klines
from analytics import compute_thresholds_from_klines

# Базовые символы для старта (можно расширить)
BASE_SYMBOLS = ["BTCUSDT", "ETHUSDT", "SOLUSDT", "TRXUSDT"]

def main():
    thresholds = {}
    for symbol in BASE_SYMBOLS:
        print(f"Загрузка 14-дневной истории для {symbol}...")
        klines = get_recent_klines(symbol, count=4032)  # 14 дней * 24 * 12 = 4032
        if klines:
            thresh = compute_thresholds_from_klines(klines)
            thresholds[symbol] = thresh
            print(f"Пороги для {symbol}: {thresh}")
        else:
            print(f"Не удалось загрузить данные для {symbol}")
    
    with open(THRESHOLDS_FILE, 'w', encoding='utf-8') as f:
        json.dump(thresholds, f, ensure_ascii=False, indent=4)
    print(f"Пороги сохранены в {THRESHOLDS_FILE}")

if __name__ == "__main__":
    main()