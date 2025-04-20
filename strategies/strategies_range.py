import talib
import pandas as pd
import logging
from config import ATR_MIN, DEFAULT_TRAILING_STOP_MULTIPLIER, RANGE_ADX_THRESHOLD, RANGE_VOLUME_MULTIPLIER, SWING_WINDOW_MIN_1M
from utils import error_handler, determine_trend, get_all_swings, project_next_swing

THRESHOLD_PERCENT = 0.02  
FIB_RATIO = 0.5           

@error_handler
def range_trading_strategy(df_15m, df_1h, df_1m=None):
    if len(df_15m) < 40 or len(df_1h) < 40:
        return None

    adx = talib.ADX(df_15m['high'], df_15m['low'], df_15m['close'], timeperiod=14).iloc[-1]
    if pd.isna(adx) or adx > RANGE_ADX_THRESHOLD:
        return None

    rsi = talib.RSI(df_15m['close'], timeperiod=14).iloc[-1]
    if rsi < 40 or rsi > 60:
        return None

    vol = df_15m['volume'].iloc[-1]
    vol_avg = df_15m['volume'].rolling(10).mean().iloc[-1]
    if pd.isna(vol_avg) or vol < vol_avg * RANGE_VOLUME_MULTIPLIER or vol > vol_avg * (1 / RANGE_VOLUME_MULTIPLIER):
        return None

    # Utilizar datos de 1m (limitados a SWING_WINDOW_MIN_1M velas) para calcular swings
    swing_source = df_1m if (df_1m is not None and not df_1m.empty) else df_15m
    swing_highs, swing_lows = get_all_swings(swing_source, window=5, threshold=0.005, limit_candles=SWING_WINDOW_MIN_1M)
    if swing_lows and len(swing_lows) >= 1:
        refined_support = project_next_swing(swing_lows, mode='low')
        diff = abs(refined_support - swing_source['close'].iloc[-1]) / swing_source['close'].iloc[-1]
        support = swing_source['close'].iloc[-1] + (refined_support - swing_source['close'].iloc[-1]) * FIB_RATIO if diff > THRESHOLD_PERCENT else refined_support
    else:
        support = swing_source['low'].min()

    if swing_highs and len(swing_highs) >= 1:
        refined_resistance = project_next_swing(swing_highs, mode='high')
        diff = abs(refined_resistance - swing_source['close'].iloc[-1]) / swing_source['close'].iloc[-1]
        resistance = swing_source['close'].iloc[-1] + (refined_resistance - swing_source['close'].iloc[-1]) * FIB_RATIO if diff > THRESHOLD_PERCENT else refined_resistance
    else:
        resistance = swing_source['high'].max()

    current_price = swing_source['close'].iloc[-1]
    atr = talib.ATR(df_15m['high'], df_15m['low'], df_15m['close'], timeperiod=14).iloc[-1]
    if pd.isna(atr) or atr < ATR_MIN:
        return None

    if current_price <= support * 1.001:
        action = 'buy'
    elif current_price >= resistance * 0.999:
        action = 'sell'
    else:
        return None

    if action == 'buy':
        tp = refined_resistance * 1.002 if swing_highs else current_price + atr
        sl = refined_support * 0.998 if swing_lows else current_price - atr
    else:
        tp = refined_support * 0.998 if swing_lows else current_price - atr
        sl = refined_resistance * 1.002 if swing_highs else current_price + atr

    trailing_stop = atr * DEFAULT_TRAILING_STOP_MULTIPLIER

    return {
        'action': action,
        'entry': current_price,
        'tp': tp,
        'sl': sl,
        'trailing_stop': trailing_stop,
        'strategy': 'RangeTrading'
    }
