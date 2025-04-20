# swing_estimator.py
import pandas as pd
import numpy as np
import logging
from config import SWING_WINDOW_MIN_1M

def get_swing_levels(df, window=SWING_WINDOW_MIN_1M):
    """
    Calcula el swing high y swing low en un DataFrame de precios usando una ventana determinada.
    Se utiliza únicamente la data de los últimos 'window' registros.
    Devuelve un diccionario con 'swing_high' y 'swing_low'.
    """
    try:
        if len(df) < window:
            logging.warning("No hay suficientes datos para calcular swings")
            return None
        # Se toman las últimas 'window' velas
        recent = df['close'].tail(window)
        swing_high = recent.max()
        swing_low = recent.min()
        return {'swing_high': swing_high, 'swing_low': swing_low}
    except Exception as e:
        logging.error(f"Error en get_swing_levels: {e}")
        return None
