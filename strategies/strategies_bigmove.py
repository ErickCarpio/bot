import talib
import pandas as pd
import logging
from config import ATR_MIN, DEFAULT_TRAILING_STOP_MULTIPLIER, BIGMOVE_THRESHOLD_PERCENT, BIGMOVE_STOCH_BUY, BIGMOVE_STOCH_SELL, SWING_WINDOW_MIN_1M
from utils import error_handler, get_all_swings, project_next_swing

THRESHOLD_PERCENT = 0.02  
FIB_RATIO = 0.5           

@error_handler
def big_move_stochrsi_strategy(df_15m, df_1h, df_1m=None):
    if len(df_15m) < 40 or len(df_1h) < 40:
        return None

    # Utilizar df_1m para swings si está disponible
    swing_source = df_1m if (df_1m is not None and not df_1m.empty) else df_15m
    current_price = swing_source['close'].iloc[-1]
    atr = talib.ATR(df_15m['high'], df_15m['low'], df_15m['close'], timeperiod=14).iloc[-1]
    if atr / current_price < BIGMOVE_THRESHOLD_PERCENT:
        return None

    stochrsi = talib.STOCHRSI(df_15m['close'], timeperiod=14)[0]
    if stochrsi.iloc[-1] < BIGMOVE_STOCH_BUY:
        action = 'buy'
    elif stochrsi.iloc[-1] > BIGMOVE_STOCH_SELL:
        action = 'sell'
    else:
        return None

    # Refinar la entrada utilizando swings calculados con datos limitados a SWING_WINDOW_MIN_1M velas de 1m
    swing_highs, swing_lows = get_all_swings(swing_source, window=5, threshold=0.005, limit_candles=SWING_WINDOW_MIN_1M)
    if action == 'buy':
        if swing_lows and len(swing_lows) >= 1:
            refined = project_next_swing(swing_lows, mode='low')
            diff = abs(refined - current_price) / current_price
            entry = current_price + (refined - current_price) * FIB_RATIO if diff > THRESHOLD_PERCENT else refined * 1.002
        else:
            entry = current_price
        tp = project_next_swing(swing_highs, mode='high') * 1.002 if swing_highs else entry + atr * 1.2
        sl = project_next_swing(swing_lows, mode='low') * 0.998 if swing_lows else entry - atr * 1.2
    else:
        if swing_highs and len(swing_highs) >= 1:
            refined = project_next_swing(swing_highs, mode='high')
            diff = abs(refined - current_price) / current_price
            entry = current_price + (refined - current_price) * FIB_RATIO if diff > THRESHOLD_PERCENT else refined * 0.998
        else:
            entry = current_price
        tp = project_next_swing(swing_lows, mode='low') * 0.998 if swing_lows else entry - atr * 1.2
        sl = project_next_swing(swing_highs, mode='high') * 1.002 if swing_highs else entry + atr * 1.2

    trailing_stop = atr * DEFAULT_TRAILING_STOP_MULTIPLIER

    return {
        'action': action,
        'entry': entry,
        'tp': tp,
        'sl': sl,
        'trailing_stop': trailing_stop,
        'strategy': 'BigMoveStochRSI'
    }
