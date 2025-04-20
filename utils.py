# utils.py
import os
import pandas as pd
from datetime import datetime, timedelta, timezone
import logging
import talib
from requests.exceptions import RequestException

DATA_FOLDER = 'data'
os.makedirs(DATA_FOLDER, exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.FileHandler("bot.log"), logging.StreamHandler()]
)

def error_handler(func):
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except Exception as e:
            logging.error(f"Error en {func.__name__}: {e}", exc_info=True)
            return None
    return wrapper

@error_handler
def get_high_volume_perpetual_pairs(client, top_n=200, min_volume=5000000):
    try:
        tickers = client.futures_ticker()
        exchange_info = client.futures_exchange_info()
    except Exception as e:
        logging.error("Error obteniendo datos de Binance")
        return []
    
    perpetuals = {
        s['symbol']: s['contractType']
        for s in exchange_info['symbols'] 
        if s.get('quoteAsset') == 'USDT' and s.get('contractType') == 'PERPETUAL'
    }
    
    filtered = []
    for t in tickers:
        symbol = t['symbol']
        if symbol.endswith('USDT') and perpetuals.get(symbol) == 'PERPETUAL':
            volume = float(t.get('quoteVolume', 0))
            if volume >= min_volume:
                filtered.append((symbol, volume))
    
    filtered.sort(key=lambda x: x[1], reverse=True)
    top_pairs = [symbol for symbol, vol in filtered[:top_n]]
    logging.info(f"Se seleccionaron {len(top_pairs)} pares de futuros con alto volumen")
    return top_pairs

@error_handler
def convert_symbol_to_ccxt(symbol):
    if not isinstance(symbol, str) or not symbol.endswith('USDT'):
        return None
    return f"{symbol.replace('USDT', '')}/USDT"

@error_handler
def get_or_update_data(client, symbol, timeframe='15m', days=30):
    filepath = os.path.join(DATA_FOLDER, f"{symbol}_{timeframe}.csv")
    now = datetime.now(timezone.utc)
    
    if timeframe == '1m':
        days = 1
    elif timeframe == '5m':
        days = 5
    elif timeframe == '15m':
        days = 30
    elif timeframe == '1h':
        days = 60
    
    since = now - timedelta(days=days)
    
    if os.path.exists(filepath):
        try:
            df = pd.read_csv(filepath)
            df['timestamp'] = pd.to_datetime(df['timestamp'], utc=True)
            df.set_index('timestamp', inplace=True)
            if len(df) < 50:
                logging.warning(f"Datos insuficientes para {symbol} en {timeframe}")
                return None
            last_timestamp = df.index.max()
            tf_minutes = int(timeframe[:-1]) * (60 if 'h' in timeframe else 1)
            if last_timestamp >= now - timedelta(minutes=tf_minutes*2):
                return df
            since = last_timestamp + timedelta(minutes=tf_minutes)
        except Exception as e:
            logging.warning(f"Error leyendo {filepath}: {e}. Regenerando archivo.")
            os.remove(filepath)
            df = pd.DataFrame()
    else:
        df = pd.DataFrame()
    
    try:
        new_klines = client.futures_klines(
            symbol=symbol,
            interval=timeframe,
            start_str=since.strftime('%Y-%m-%d %H:%M:%S')
        )
        if new_klines:
            new_data = []
            for k in new_klines:
                new_data.append({
                    'timestamp': pd.to_datetime(k[0], unit='ms', utc=True),
                    'open': float(k[1]),
                    'high': float(k[2]),
                    'low': float(k[3]),
                    'close': float(k[4]),
                    'volume': float(k[5])
                })
            new_df = pd.DataFrame(new_data)
            new_df.set_index('timestamp', inplace=True)
            df = pd.concat([df, new_df]).drop_duplicates().sort_index()
            df.to_csv(filepath)
            logging.info(f"Datos actualizados para {symbol} en {timeframe}")
        else:
            logging.warning(f"No se obtuvieron nuevos datos para {symbol} en {timeframe}")
    except Exception as e:
        logging.error(f"Error obteniendo datos para {symbol}: {e}")
    
    return df

# Funciones auxiliares para detectar fractales (útiles para EMA Fractal)
def is_fractal_low(df, idx):
    if idx < 2 or idx > len(df) - 3:
        return False
    return (df['low'].iloc[idx] < df['low'].iloc[idx-1] and 
            df['low'].iloc[idx] < df['low'].iloc[idx-2] and 
            df['low'].iloc[idx] < df['low'].iloc[idx+1] and 
            df['low'].iloc[idx] < df['low'].iloc[idx+2])

def is_fractal_high(df, idx):
    if idx < 2 or idx > len(df) - 3:
        return False
    return (df['high'].iloc[idx] > df['high'].iloc[idx-1] and 
            df['high'].iloc[idx] > df['high'].iloc[idx-2] and 
            df['high'].iloc[idx] > df['high'].iloc[idx+1] and 
            df['high'].iloc[idx] > df['high'].iloc[idx+2])

def determine_trend(df):
    """
    Determina la tendencia a partir de los últimos 10 valores de 'close'.
    Retorna 'alcista' si el último cierre es significativamente mayor que el promedio,
    'bajista' si es significativamente menor, o 'neutral' en caso contrario.
    """
    try:
        if df.empty:
            return 'neutral'
        recent = df['close'].tail(10)
        avg = recent.mean()
        last = recent.iloc[-1]
        if last > avg * 1.005:
            return 'alcista'
        elif last < avg * 0.995:
            return 'bajista'
        else:
            return 'neutral'
    except Exception as e:
        logging.error(f"Error en determine_trend: {e}")
        return 'neutral'

def determine_short_term_trend(df):
    """
    Determina la tendencia a corto plazo a partir de los últimos 5 valores de 'close'.
    Utiliza una heurística similar a determine_trend.
    """
    try:
        if df.empty:
            return 'neutral'
        recent = df['close'].tail(5)
        avg = recent.mean()
        last = recent.iloc[-1]
        if last > avg * 1.002:
            return 'alcista'
        elif last < avg * 0.998:
            return 'bajista'
        else:
            return 'neutral'
    except Exception as e:
        logging.error(f"Error en determine_short_term_trend: {e}")
        return 'neutral'

import numpy as np

def get_all_swings(df, window=5, threshold=0.005, limit_candles=None):
    """
    Detecta swing highs y swing lows en un DataFrame utilizando una ventana de 'window' velas.
    Si se proporciona 'limit_candles', se utilizan únicamente las últimas 'limit_candles' velas.
    'threshold' puede usarse para filtrar swings con cambios porcentuales mínimos (aquí no se aplica directamente).
    Retorna dos listas de tuplas: (timestamp, valor) para swing_highs y swing_lows.
    """
    if limit_candles is not None:
        df = df.tail(limit_candles)
    swing_highs = []
    swing_lows = []
    for i in range(window, len(df) - window):
        current_high = df['high'].iloc[i]
        if all(current_high > df['high'].iloc[i - window:i]) and all(current_high > df['high'].iloc[i + 1:i + window + 1]):
            swing_highs.append((df.index[i], current_high))
        current_low = df['low'].iloc[i]
        if all(current_low < df['low'].iloc[i - window:i]) and all(current_low < df['low'].iloc[i + 1:i + window + 1]):
            swing_lows.append((df.index[i], current_low))
    return swing_highs, swing_lows

def project_next_swing(swings, mode='low'):
    """
    Proyecta el próximo swing mediante regresión lineal simple sobre la lista de swings.
    'swings' es una lista de tuplas (timestamp, valor).
    Retorna el valor proyectado usando el índice de la lista como variable independiente.
    """
    if len(swings) < 2:
        return None
    values = [s[1] for s in swings]
    x = np.arange(len(values))
    m, b = np.polyfit(x, values, 1)
    projected = m * len(values) + b
    return projected
