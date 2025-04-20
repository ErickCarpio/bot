# strategies_fractal.py

import talib
import pandas as pd
import logging
from config import ATR_MIN, DEFAULT_TRAILING_STOP_MULTIPLIER, EMA_FRACTAL_MIN_GAP, SWING_WINDOW_MIN_1M
from utils import error_handler, determine_trend, get_all_swings, project_next_swing

THRESHOLD_PERCENT = 0.02  
FIB_RATIO = 0.5           

@error_handler
def ema_fractal_strategy(df_15m, df_1h, df_1m=None):
    if len(df_15m) < 40 or len(df_1h) < 40:
        return None

    trend = determine_trend(df_1h)
    if trend not in ['alcista', 'bajista']:
        return None

    # Usar datos de 1m si están disponibles, limitados a SWING_WINDOW_MIN_1M velas, para el cálculo de swings
    swing_source = df_1m if (df_1m is not None and not df_1m.empty) else df_15m
    swing_highs, swing_lows = get_all_swings(swing_source, window=5, threshold=0.005, limit_candles=SWING_WINDOW_MIN_1M)
    current_close = swing_source['close'].iloc[-1]
    
    if trend == 'alcista':
        # Proyección sólo si hay al menos 2 swings
        refined = project_next_swing(swing_lows, mode='low') if len(swing_lows) >= 2 else None
        if refined is not None:
            diff = abs(refined - current_close) / current_close
            entry = (current_close + (refined - current_close) * FIB_RATIO) if diff > THRESHOLD_PERCENT else refined * 1.002
        else:
            entry = current_close
        action = 'buy'
        tp = entry + talib.ATR(df_15m['high'], df_15m['low'], df_15m['close'], timeperiod=14).iloc[-1] * 0.8
        sl = entry - talib.ATR(df_15m['high'], df_15m['low'], df_15m['close'], timeperiod=14).iloc[-1] * 0.8
    else:
        # Análogo para swing highs en tendencia bajista
        refined = project_next_swing(swing_highs, mode='high') if len(swing_highs) >= 2 else None
        if refined is not None:
            diff = abs(refined - current_close) / current_close
            entry = (current_close + (refined - current_close) * FIB_RATIO) if diff > THRESHOLD_PERCENT else refined * 0.998
        else:
            entry = current_close
        action = 'sell'
        tp = entry - talib.ATR(df_15m['high'], df_15m['low'], df_15m['close'], timeperiod=14).iloc[-1] * 0.8
        sl = entry + talib.ATR(df_15m['high'], df_15m['low'], df_15m['close'], timeperiod=14).iloc[-1] * 0.8

    atr = talib.ATR(df_15m['high'], df_15m['low'], df_15m['close'], timeperiod=14).iloc[-1]
    if pd.isna(atr) or atr < ATR_MIN:
        return None

    trailing_stop = atr * DEFAULT_TRAILING_STOP_MULTIPLIER
    return {
        'action': action,
        'entry': entry,
        'tp': tp,
        'sl': sl,
        'trailing_stop': trailing_stop,
        'strategy': 'EMAFractal'
    }
