# analytics.py
import numpy as np
from storage import load_thresholds

def kline_to_volatility(kline):
    """Рассчитывает волатильность свечи: (high - low) / open * 100"""
    try:
        open_p = float(kline[1])
        high = float(kline[2])
        low = float(kline[3])
        if open_p == 0:
            return 0.0
        return (high - low) / open_p * 100.0
    except (IndexError, ValueError):
        return 0.0

def quote_volume_from_kline(kline):
    """Берёт quoteVolume (index 7) или fallback volume * close"""
    try:
        return float(kline[7])
    except (IndexError, ValueError):
        try:
            volume = float(kline[5])
            close = float(kline[4])
            return volume * close
        except:
            return 0.0

def compute_avg_volume(history_klines):
    """Средний quoteVolume за последние 72 свечи (или меньше, если нет)"""
    if not history_klines:
        return 0.0
    volumes = [quote_volume_from_kline(k) for k in history_klines]
    return sum(volumes) / len(volumes) if volumes else 0.0

def compute_thresholds_from_klines(klines):
    """Вычисляет Q25, Q50, Q75 волатильности за 14 дней (4032 свечи)"""
    vols = [kline_to_volatility(k) for k in klines if kline_to_volatility(k) > 0]
    if not vols:
        return {"q25": 0.0, "q50": 0.0, "q75": 0.0}
    q25 = float(np.percentile(vols, 25))
    q50 = float(np.percentile(vols, 50))
    q75 = float(np.percentile(vols, 75))
    return {"q25": q25, "q50": q50, "q75": q75}

def determine_level(vol_pct, symbol):
    """Определяет уровень 1-4 на основе порогов для символа"""
    thresholds = load_thresholds().get(symbol, {"q25": 0, "q50": 0, "q75": 0})
    q25, q50, q75 = thresholds["q25"], thresholds["q50"], thresholds["q75"]
    if vol_pct <= q25:
        return 1
    elif vol_pct <= q50:
        return 2
    elif vol_pct <= q75:
        return 3
    else:
        return 4

def get_level_emoji(level):
    """Emoji для уровня"""
    if level == 1:
        return "😶"
    elif level == 2:
        return "🙂"
    elif level == 3:
        return "🤪"
    elif level == 4:
        return "😱"
    return ""
