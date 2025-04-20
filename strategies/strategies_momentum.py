# strategies_momentum.py
import talib
import pandas as pd
import logging
from config import ATR_MIN, DEFAULT_TRAILING_STOP_MULTIPLIER, SWING_WINDOW_MIN_1M
from utils import error_handler, determine_trend, get_all_swings, project_next_swing

# Parámetros para momentum
STOCHRSI_BUY_THRESHOLD = 0.05  
STOCHRSI_SELL_THRESHOLD = 0.95  
MAX_ADX_FOR_REVERSAL = 25       
VOLUME_MULTIPLIER_FILTER = 1.5  
THRESHOLD_PERCENT = 0.02  
FIB_RATIO = 0.5           

@error_handler
def momo_strategy(df_15m, df_1h, df_1m=None, df_5m=None):
    if len(df_15m) < 40:
        return None
    rsi = talib.RSI(df_15m['close'], timeperiod=14).iloc[-1]
    macd, signal, hist = talib.MACD(df_15m['close'], fastperiod=12, slowperiod=26, signalperiod=9)
    current_price = (df_1m['close'].iloc[-1] if (df_1m is not None and not df_1m.empty)
                     else df_15m['close'].iloc[-1])
    atr = talib.ATR(df_15m['high'], df_15m['low'], df_15m['close'], timeperiod=14).iloc[-1]
    if pd.isna(atr) or atr < ATR_MIN:
        return None
    stochrsi = talib.STOCHRSI(df_15m['close'], timeperiod=14)[0]
    if stochrsi.iloc[-1] < STOCHRSI_BUY_THRESHOLD and hist.iloc[-1] > 0:
        action = 'buy'
    elif stochrsi.iloc[-1] > STOCHRSI_SELL_THRESHOLD and hist.iloc[-1] < 0:
        action = 'sell'
    else:
        return None
    adx = talib.ADX(df_15m['high'], df_15m['low'], df_15m['close'], timeperiod=14).iloc[-1]
    if adx >= MAX_ADX_FOR_REVERSAL:
        return None
    vol_avg = df_15m['volume'].rolling(20).mean().iloc[-1]
    vol_actual = df_15m['volume'].iloc[-1]
    if vol_actual < VOLUME_MULTIPLIER_FILTER * vol_avg:
        return None

    # Usar swings calculados a partir de datos de 1m si están disponibles, limitando a SWING_WINDOW_MIN_1M
    swing_source = df_1m if (df_1m is not None and not df_1m.empty) else df_15m
    swing_highs, swing_lows = get_all_swings(swing_source, window=5, threshold=0.005, limit_candles=SWING_WINDOW_MIN_1M)
    if action == 'buy':
        if swing_lows and len(swing_lows) >= 1:
            refined = project_next_swing(swing_lows, mode='low')
            diff = abs(refined - current_price) / current_price
            entry = current_price + (refined - current_price) * FIB_RATIO if diff > THRESHOLD_PERCENT else refined * 1.002
        else:
            entry = current_price
        tp = project_next_swing(swing_highs, mode='high') * 1.002 if swing_highs else entry + atr * 0.8
        sl = project_next_swing(swing_lows, mode='low') * 0.998 if swing_lows else entry - atr * 0.8
    else:
        if swing_highs and len(swing_highs) >= 1:
            refined = project_next_swing(swing_highs, mode='high')
            diff = abs(refined - current_price) / current_price
            entry = current_price + (refined - current_price) * FIB_RATIO if diff > THRESHOLD_PERCENT else refined * 0.998
        else:
            entry = current_price
        tp = project_next_swing(swing_lows, mode='low') * 0.998 if swing_lows else entry - atr * 0.8
        sl = project_next_swing(swing_highs, mode='high') * 1.002 if swing_highs else entry + atr * 0.8

    trailing_stop = atr * DEFAULT_TRAILING_STOP_MULTIPLIER
    return {
        'action': action,
        'entry': entry,
        'tp': tp,
        'sl': sl,
        'trailing_stop': trailing_stop,
        'strategy': 'Momo'
    }

@error_handler
def stoch_rsi_macd_strategy(df_15m, df_1h, df_1m=None):
    if len(df_15m) < 40:
        return None
    stochrsi = talib.STOCHRSI(df_15m['close'], timeperiod=14)[0]
    macd, macdsignal, hist = talib.MACD(df_15m['close'], fastperiod=12, slowperiod=26, signalperiod=9)
    current_price = (df_1m['close'].iloc[-1] if (df_1m is not None and not df_1m.empty)
                     else df_15m['close'].iloc[-1])
    atr = talib.ATR(df_15m['high'], df_15m['low'], df_15m['close'], timeperiod=14).iloc[-1]
    if pd.isna(atr):
        return None
    if stochrsi.iloc[-1] < STOCHRSI_BUY_THRESHOLD and hist.iloc[-1] > 0:
        action = 'buy'
    elif stochrsi.iloc[-1] > STOCHRSI_SELL_THRESHOLD and hist.iloc[-1] < 0:
        action = 'sell'
    else:
        return None
    adx = talib.ADX(df_15m['high'], df_15m['low'], df_15m['close'], timeperiod=14).iloc[-1]
    if adx >= MAX_ADX_FOR_REVERSAL:
        return None

    swing_source = df_1m if (df_1m is not None and not df_1m.empty) else df_15m
    swing_highs, swing_lows = get_all_swings(swing_source, window=5, threshold=0.005, limit_candles=SWING_WINDOW_MIN_1M)
    if action == 'buy':
        if swing_lows and len(swing_lows) >= 1:
            refined = project_next_swing(swing_lows, mode='low')
            diff = abs(refined - current_price) / current_price
            entry = current_price + (refined - current_price) * FIB_RATIO if diff > THRESHOLD_PERCENT else refined * 1.002
        else:
            entry = current_price
        tp = project_next_swing(swing_highs, mode='high') * 1.002 if swing_highs else entry + atr * 0.7
        sl = project_next_swing(swing_lows, mode='low') * 0.998 if swing_lows else entry - atr * 0.7
    else:
        if swing_highs and len(swing_highs) >= 1:
            refined = project_next_swing(swing_highs, mode='high')
            diff = abs(refined - current_price) / current_price
            entry = current_price + (refined - current_price) * FIB_RATIO if diff > THRESHOLD_PERCENT else refined * 0.998
        else:
            entry = current_price
        tp = project_next_swing(swing_lows, mode='low') * 0.998 if swing_lows else entry - atr * 0.7
        sl = project_next_swing(swing_highs, mode='high') * 1.002 if swing_highs else entry + atr * 0.7

    trailing_stop = atr * DEFAULT_TRAILING_STOP_MULTIPLIER
    return {
        'action': action,
        'entry': entry,
        'tp': tp,
        'sl': sl,
        'trailing_stop': trailing_stop,
        'strategy': 'StochRSI_MACD'
    }

@error_handler
def triple_ema_stochrsi_atr_strategy(df_15m, df_1h, df_1m=None):
    if len(df_15m) < 40:
        return None
    ema_short = talib.EMA(df_15m['close'], timeperiod=10)
    ema_mid = talib.EMA(df_15m['close'], timeperiod=20)
    ema_long = talib.EMA(df_15m['close'], timeperiod=50)
    if not (ema_short.iloc[-1] > ema_mid.iloc[-1] * 1.01 and ema_mid.iloc[-1] > ema_long.iloc[-1] * 1.01):
        return None
    stochrsi = talib.STOCHRSI(df_15m['close'], timeperiod=14)[0]
    current_price = (df_1m['close'].iloc[-1] if (df_1m is not None and not df_1m.empty)
                     else df_15m['close'].iloc[-1])
    atr = talib.ATR(df_15m['high'], df_15m['low'], df_15m['close'], timeperiod=14).iloc[-1]
    if pd.isna(atr):
        return None
    if ema_short.iloc[-1] > ema_mid.iloc[-1] > ema_long.iloc[-1] and stochrsi.iloc[-1] < 0.10:
        action = 'buy'
    elif ema_short.iloc[-1] < ema_mid.iloc[-1] < ema_long.iloc[-1] and stochrsi.iloc[-1] > 0.90:
        action = 'sell'
    else:
        return None

    swing_source = df_1m if (df_1m is not None and not df_1m.empty) else df_15m
    swing_highs, swing_lows = get_all_swings(swing_source, window=5, threshold=0.005, limit_candles=SWING_WINDOW_MIN_1M)
    if action == 'buy':
        if swing_lows and len(swing_lows) >= 1:
            refined = project_next_swing(swing_lows, mode='low')
            diff = abs(refined - current_price) / current_price
            entry = current_price + (refined - current_price) * FIB_RATIO if diff > THRESHOLD_PERCENT else refined * 1.002
        else:
            entry = current_price
    else:
        if swing_highs and len(swing_highs) >= 1:
            refined = project_next_swing(swing_highs, mode='high')
            diff = abs(refined - current_price) / current_price
            entry = current_price + (refined - current_price) * FIB_RATIO if diff > THRESHOLD_PERCENT else refined * 0.998
        else:
            entry = current_price

    recent_high = df_15m['high'].tail(40).max()
    recent_low = df_15m['low'].tail(40).min()
    if action == 'buy' and entry > recent_low * 1.005:
        return None
    if action == 'sell' and entry < recent_high * 0.995:
        return None

    tp = entry + atr * 0.75 if action == 'buy' else entry - atr * 0.75
    sl = entry - atr * 0.75 if action == 'buy' else entry + atr * 0.75
    trailing_stop = atr * DEFAULT_TRAILING_STOP_MULTIPLIER
    return {
        'action': action,
        'entry': entry,
        'tp': tp,
        'sl': sl,
        'trailing_stop': trailing_stop,
        'strategy': 'TripleEMA_StochRSI_ATR'
    }
