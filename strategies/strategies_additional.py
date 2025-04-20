import talib
import pandas as pd
import numpy as np
import logging
try:
    from config import MACD_DIFF_THRESHOLD
except ImportError:
    MACD_DIFF_THRESHOLD = 0.01
from config import ATR_MIN, MIN_TP_MULTIPLIER, MIN_SL_MULTIPLIER, TP_DYNAMIC_OFFSET, SL_DYNAMIC_OFFSET, DEFAULT_TRAILING_STOP_MULTIPLIER, MAX_LOSS_PER_TRADE, FIB_DISTANCE_THRESHOLD, BOLLINGER_LOWER_MULTIPLIER, BOLLINGER_UPPER_MULTIPLIER, BOLLINGER_TP_SL_OFFSET, SWING_WINDOW_MIN_1M
from utils import error_handler, determine_trend, get_all_swings, project_next_swing

@error_handler
def fib_macd_strategy(df_15m, df_1h, df_1m=None):
    if len(df_15m) < 40:
        return None
    trend_1h = determine_trend(df_1h)
    if trend_1h == 'neutral':
        return None
    recent = df_15m.iloc[-40:].copy()
    current_price = df_1m['close'].iloc[-1] if (df_1m is not None and not df_1m.empty) else recent['close'].iloc[-1]
    
    fib_low = recent['low'].min()
    fib_high = recent['high'].max()
    fib_level = fib_high - 0.618 * (fib_high - fib_low)
    if abs(current_price - fib_level) / current_price < FIB_DISTANCE_THRESHOLD:
        return None
    macd, macdsignal, _ = talib.MACD(df_15m['close'])
    macd_last = macd.iloc[-1] if not pd.isna(macd.iloc[-1]) else 0
    macdsignal_last = macdsignal.iloc[-1] if not pd.isna(macdsignal.iloc[-1]) else 0
    if abs(macd_last - macdsignal_last) < MACD_DIFF_THRESHOLD:
        return None
    atr = talib.ATR(df_15m['high'], df_15m['low'], df_15m['close'], timeperiod=14).iloc[-1]
    if pd.isna(atr) or atr < ATR_MIN:
        return None

    # Usar datos de 1m si están disponibles, limitando a SWING_WINDOW_MIN_1M velas
    swing_source = df_1m if (df_1m is not None and not df_1m.empty) else df_15m
    swing_highs, swing_lows = get_all_swings(swing_source, window=5, threshold=0.005, limit_candles=SWING_WINDOW_MIN_1M)
    projected_low = project_next_swing(swing_lows, mode='low')
    projected_high = project_next_swing(swing_highs, mode='high') if swing_highs else None

    if projected_low is None:
        return None
    # Validar que el precio actual esté cerca (menos del 1% de diferencia) del swing low proyectado
    if abs(current_price - projected_low) / projected_low > 0.01:
        return None

    if trend_1h == 'alcista' and current_price < fib_level:
        action = 'buy'
        entry = projected_low * 1.002  # Máximo 0.2% por encima
        tp = projected_high if projected_high is not None else current_price + atr * TP_DYNAMIC_OFFSET
        sl = projected_low * 0.998      # Justo debajo del swing low proyectado
    elif trend_1h == 'bajista' and current_price > fib_level:
        action = 'sell'
        if projected_high is None:
            return None
        entry = projected_high * 0.998  # Máximo 0.2% por debajo
        tp = projected_high * 0.997
        sl = projected_high * 1.002
    else:
        return None

    trailing_stop = atr * DEFAULT_TRAILING_STOP_MULTIPLIER
    return {
        'action': action,
        'entry': entry,
        'tp': tp,
        'sl': sl,
        'trailing_stop': trailing_stop,
        'strategy': 'Fib_MACD'
    }

@error_handler
def heikin_ashi_ema_strategy(df_15m, df_1h, df_1m=None):
    if len(df_15m) < 40 or len(df_1h) < 40:
        return None
    trend_1h = determine_trend(df_1h)
    if trend_1h == 'neutral':
        return None

    ha_df = df_15m.copy()
    ha_df['ha_close'] = (ha_df['open'] + ha_df['high'] + ha_df['low'] + ha_df['close']) / 4
    ha_df['ha_open'] = ha_df['open'].shift(1).fillna(ha_df['open'])
    ha_df['ha_high'] = ha_df[['high', 'ha_open', 'ha_close']].max(axis=1)
    ha_df['ha_low'] = ha_df[['low', 'ha_open', 'ha_close']].min(axis=1)
    ha_df['ha_color'] = ha_df.apply(lambda row: 'green' if row['ha_close'] >= row['ha_open'] else 'red', axis=1)
    current_price = df_1m['close'].iloc[-1] if (df_1m is not None and not df_1m.empty) else ha_df['ha_close'].iloc[-1]
    
    swing_source = df_1m if (df_1m is not None and not df_1m.empty) else ha_df
    swing_highs, swing_lows = get_all_swings(swing_source, window=5, threshold=0.005, limit_candles=SWING_WINDOW_MIN_1M)
    projected_low = project_next_swing(swing_lows, mode='low')
    projected_high = project_next_swing(swing_highs, mode='high') if swing_highs else None
    if projected_low is None:
        return None
    if abs(current_price - projected_low) / projected_low > 0.01:
        return None

    ema20 = talib.EMA(ha_df['ha_close'], timeperiod=20).iloc[-1]
    atr = talib.ATR(ha_df['ha_high'], ha_df['ha_low'], ha_df['ha_close'], timeperiod=14).iloc[-1]
    if pd.isna(atr) or atr < ATR_MIN:
        return None
    ha_df['ADX'] = talib.ADX(ha_df['ha_high'], ha_df['ha_low'], ha_df['ha_close'], timeperiod=14)
    adx = ha_df['ADX'].iloc[-1]
    if pd.isna(adx) or adx < 25:
        return None

    if trend_1h == 'alcista' and ha_df['ha_color'].iloc[-1] == 'green' and current_price > ema20 * 1.02:
        action = 'buy'
        entry = projected_low * 1.002
        tp = projected_high if projected_high is not None else current_price + atr * TP_DYNAMIC_OFFSET
        sl = projected_low * 0.998
    elif trend_1h == 'bajista' and ha_df['ha_color'].iloc[-1] == 'red' and current_price < ema20 * 0.98:
        action = 'sell'
        if projected_high is None:
            return None
        entry = projected_high * 0.998
        tp = projected_high * 0.997
        sl = projected_high * 1.002
    else:
        return None

    trailing_stop = atr * DEFAULT_TRAILING_STOP_MULTIPLIER
    return {
        'action': action,
        'entry': entry,
        'tp': tp,
        'sl': sl,
        'trailing_stop': trailing_stop,
        'strategy': 'HeikinAshi_EMA'
    }

@error_handler
def bollinger_reversion_strategy(df_15m, df_1h, df_1m=None):
    if len(df_15m) < 40 or len(df_1h) < 40:
        return None
    trend_1h = determine_trend(df_1h)
    if trend_1h != 'neutral':
        return None
    df_15m['MA20'] = talib.SMA(df_15m['close'], timeperiod=20)
    df_15m['STD20'] = df_15m['close'].rolling(20).std()
    current_price = df_1m['close'].iloc[-1] if (df_1m is not None and not df_1m.empty) else df_15m['close'].iloc[-1]
    ma20 = df_15m['MA20'].iloc[-1]
    std20 = df_15m['STD20'].iloc[-1]
    if pd.isna(ma20) or pd.isna(std20):
        return None
    upper_band = ma20 + 2 * std20
    lower_band = ma20 - 2 * std20
    atr = talib.ATR(df_15m['high'], df_15m['low'], df_15m['close'], timeperiod=14).iloc[-1]

    swing_source = df_1m if (df_1m is not None and not df_1m.empty) else df_15m
    swing_highs, swing_lows = get_all_swings(swing_source, window=5, threshold=0.005, limit_candles=SWING_WINDOW_MIN_1M)
    projected_low = project_next_swing(swing_lows, mode='low')
    projected_high = project_next_swing(swing_highs, mode='high') if swing_highs else None
    if projected_low is None:
        return None
    if current_price <= lower_band * BOLLINGER_LOWER_MULTIPLIER:
        action = 'buy'
        entry = projected_low * 1.002
        tp = projected_high if projected_high is not None else current_price + atr * (TP_DYNAMIC_OFFSET + BOLLINGER_TP_SL_OFFSET)
        sl = projected_low * 0.998
    elif current_price >= upper_band * BOLLINGER_UPPER_MULTIPLIER:
        action = 'sell'
        if projected_high is None:
            return None
        entry = projected_high * 0.998
        tp = projected_high * 0.997
        sl = projected_high * 1.002
    else:
        return None

    trailing_stop = atr * DEFAULT_TRAILING_STOP_MULTIPLIER
    return {
        'action': action,
        'entry': entry,
        'tp': tp,
        'sl': sl,
        'trailing_stop': trailing_stop,
        'strategy': 'BollingerReversion'
    }
