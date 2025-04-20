# strategies_trend.py
import talib
import pandas as pd
import logging
from config import ATR_MIN, GOLDEN_CROSS_EMA_DIFF_THRESHOLD, DEFAULT_TRAILING_STOP_MULTIPLIER, BREAKOUT_PERCENTAGE, SWING_WINDOW_MIN_1M
from utils import error_handler, determine_trend, determine_short_term_trend, get_all_swings, project_next_swing

# Parámetros para ajuste Fibonacci
THRESHOLD_PERCENT = 0.02  # Si la diferencia es mayor al 2% del precio actual
FIB_RATIO = 0.5           # Usar el 50% de la diferencia como nivel intermedio

@error_handler
def breakout_strategy(df_15m, df_1h, df_1m=None, df_5m=None):
    if len(df_15m) < 40:
        return None

    trend_1h = determine_trend(df_1h)
    if trend_1h == 'neutral':
        return None

    # Utilizar df_1m para swings si está disponible, limitando a las últimas 120 velas
    swing_source = df_1m if (df_1m is not None and not df_1m.empty) else df_15m
    swing_highs, swing_lows = get_all_swings(swing_source, window=5, threshold=0.005, limit_candles=SWING_WINDOW_MIN_1M)
    current_price = swing_source['close'].iloc[-1]

    if swing_lows and len(swing_lows) >= 2:
        refined_low = project_next_swing(swing_lows, mode='low')
    else:
        refined_low = swing_source['low'].min()
    if swing_highs and len(swing_highs) >= 2:
        refined_high = project_next_swing(swing_highs, mode='high')
    else:
        refined_high = swing_source['high'].max()

    # Ajuste con Fibonacci para que los niveles no estén demasiado alejados:
    diff_low = abs(refined_low - current_price) / current_price
    support = current_price + (refined_low - current_price) * FIB_RATIO if diff_low > THRESHOLD_PERCENT else refined_low

    diff_high = abs(refined_high - current_price) / current_price
    resistance = current_price + (refined_high - current_price) * FIB_RATIO if diff_high > THRESHOLD_PERCENT else refined_high

    atr = talib.ATR(df_15m['high'], df_15m['low'], df_15m['close'], timeperiod=14).iloc[-1]
    if pd.isna(atr) or atr < ATR_MIN:
        return None

    df_15m['ADX'] = talib.ADX(df_15m['high'], df_15m['low'], df_15m['close'], timeperiod=14)
    adx = df_15m['ADX'].iloc[-1]
    if pd.isna(adx) or adx < 25:
        return None

    tp_multiplier = 0.8 * max(1.0 + adx / 50, 1.0)
    sl_multiplier = max(1.0 + adx / 75, 1.0)

    if df_5m is not None and not df_5m.empty:
        trend_5m = determine_short_term_trend(df_5m)
        if (trend_1h == 'alcista' and trend_5m == 'bajista') or (trend_1h == 'bajista' and trend_5m == 'alcista'):
            return None

    # Condición de ruptura y definición de niveles basados en swings
    if trend_1h == 'alcista' and current_price > resistance * (1 + BREAKOUT_PERCENTAGE):
        action = 'buy'
        tp = refined_high * 1.002 if refined_high > current_price else current_price + atr * tp_multiplier
        sl = refined_low * 0.998 if refined_low < current_price else current_price - atr * sl_multiplier
    elif trend_1h == 'bajista' and current_price < support * (1 - BREAKOUT_PERCENTAGE):
        action = 'sell'
        tp = refined_low * 0.998 if refined_low < current_price else current_price - atr * tp_multiplier
        sl = refined_high * 1.002 if refined_high > current_price else current_price + atr * sl_multiplier
    else:
        return None

    # Trailing stop dinámico basado en ATR (se puede ajustar según volatilidad o swings)
    trailing_stop = atr * DEFAULT_TRAILING_STOP_MULTIPLIER

    return {
        'action': action,
        'entry': current_price,
        'tp': tp,
        'sl': sl,
        'trailing_stop': trailing_stop,
        'strategy': 'Breakout'
    }

@error_handler
def golden_cross_strategy(df_15m, df_1h, df_1m=None):
    if len(df_15m) < 40:
        return None

    trend_1h = determine_trend(df_1h)
    if trend_1h != 'alcista':
        return None

    df_15m['EMA20'] = talib.EMA(df_15m['close'], timeperiod=20)
    df_15m['EMA50'] = talib.EMA(df_15m['close'], timeperiod=50)
    current_price = (df_1m['close'].iloc[-1] if (df_1m is not None and not df_1m.empty)
                     else df_15m['close'].iloc[-1])
    atr = talib.ATR(df_15m['high'], df_15m['low'], df_15m['close'], timeperiod=14).iloc[-1]
    if pd.isna(atr) or atr < ATR_MIN:
        return None

    if df_15m['EMA20'].iloc[-1] > df_15m['EMA50'].iloc[-1] + GOLDEN_CROSS_EMA_DIFF_THRESHOLD:
        swing_source = df_1m if (df_1m is not None and not df_1m.empty) else df_15m
        swing_highs, swing_lows = get_all_swings(swing_source, window=5, threshold=0.005, limit_candles=SWING_WINDOW_MIN_1M)
        if swing_lows and len(swing_lows) >= 1:
            refined = project_next_swing(swing_lows, mode='low')
            diff = abs(refined - current_price) / current_price
            entry = current_price + (refined - current_price) * FIB_RATIO if diff > THRESHOLD_PERCENT else refined * 1.002
        else:
            entry = current_price
        action = 'buy'
        tp = project_next_swing(swing_highs, mode='high') * 1.002 if swing_highs else entry + atr * 1.0
        sl = project_next_swing(swing_lows, mode='low') * 0.998 if swing_lows else entry - atr * 1.0
    else:
        return None

    trailing_stop = atr * DEFAULT_TRAILING_STOP_MULTIPLIER
    return {
        'action': action,
        'entry': entry,
        'tp': tp,
        'sl': sl,
        'trailing_stop': trailing_stop,
        'strategy': 'GoldenCross'
    }

@error_handler
def death_cross_strategy(df_15m, df_1h, df_1m=None):
    if len(df_15m) < 40:
        return None

    trend_1h = determine_trend(df_1h)
    if trend_1h != 'bajista':
        return None

    df_15m['EMA20'] = talib.EMA(df_15m['close'], timeperiod=20)
    df_15m['EMA50'] = talib.EMA(df_15m['close'], timeperiod=50)
    current_price = (df_1m['close'].iloc[-1] if (df_1m is not None and not df_1m.empty)
                     else df_15m['close'].iloc[-1])
    atr = talib.ATR(df_15m['high'], df_15m['low'], df_15m['close'], timeperiod=14).iloc[-1]
    if pd.isna(atr) or atr < ATR_MIN:
        return None

    if df_15m['EMA20'].iloc[-1] < df_15m['EMA50'].iloc[-1] - GOLDEN_CROSS_EMA_DIFF_THRESHOLD:
        swing_source = df_1m if (df_1m is not None and not df_1m.empty) else df_15m
        swing_highs, swing_lows = get_all_swings(swing_source, window=5, threshold=0.005, limit_candles=SWING_WINDOW_MIN_1M)
        if swing_highs and len(swing_highs) >= 1:
            refined = project_next_swing(swing_highs, mode='high')
            diff = abs(refined - current_price) / current_price
            entry = current_price + (refined - current_price) * FIB_RATIO if diff > THRESHOLD_PERCENT else refined * 0.998
        else:
            entry = current_price
        action = 'sell'
        sl = project_next_swing(swing_highs, mode='high') * 1.002 if swing_highs else entry + atr * 1.0
        tp = project_next_swing(swing_lows, mode='low') * 0.998 if swing_lows else entry - atr * 1.0
    else:
        return None

    trailing_stop = atr * DEFAULT_TRAILING_STOP_MULTIPLIER
    return {
        'action': action,
        'entry': entry,
        'tp': tp,
        'sl': sl,
        'trailing_stop': trailing_stop,
        'strategy': 'DeathCross'
    }
