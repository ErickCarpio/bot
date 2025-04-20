import time
import logging
import random
import ccxt
from binance.client import Client
from config import INITIAL_CAPITAL, LEVERAGE, SLEEP_INTERVAL
from utils import get_high_volume_perpetual_pairs, get_or_update_data, convert_symbol_to_ccxt
from strategies import strategies_trend, strategies_momentum, strategies_range, strategies_fractal, strategies_bigmove, strategies_additional
from strategies.signal_aggregator import aggregate_signals
from trade_manager import calculate_position_size, calculate_percentage_risk
from discord_notifier import send_discord_message
import pandas as pd
import os

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(message)s",
    handlers=[logging.FileHandler("bot_main.log"), logging.StreamHandler()]
)

API_KEY = 'icXUeq9TIpBbxPpsSLGGCKb5nR1ZPHMbXGx6cMsjtFynlY56u248mZgo7f8PYBfb'
API_SECRET = '6zQwjggzfF18oxIoxG2cvHVT08wHcCH97TdaSbPKguFzpbX6jIgmNf20N6y23xh'
binance_client = Client(API_KEY, API_SECRET)
exchange = ccxt.binance({'apiKey': API_KEY, 'secret': API_SECRET, 'enableRateLimit': True})

def solicitar_capital():
    try:
        capital_str = input("Ingrese el capital disponible (en USD): ")
        capital = float(capital_str)
        return capital
    except Exception as e:
        logging.error(f"Error al leer el capital: {e}")
        return INITIAL_CAPITAL


def evaluate_pair(symbol, capital):
    df_15m = get_or_update_data(binance_client, symbol, timeframe='15m')
    df_1h  = get_or_update_data(binance_client, symbol, timeframe='1h')
    df_1m  = get_or_update_data(binance_client, symbol, timeframe='1m')
    df_5m  = get_or_update_data(binance_client, symbol, timeframe='5m')
    if df_15m is None or df_1h is None:
        logging.warning(f"Datos insuficientes para {symbol}")
        return None
    signals = []

    sig = strategies_trend.breakout_strategy(df_15m, df_1h, df_1m, df_5m)
    if sig: signals.append(sig)

    sig = strategies_trend.golden_cross_strategy(df_15m, df_1h, df_1m)
    if sig: signals.append(sig)

    sig = strategies_additional.fib_macd_strategy(df_15m, df_1h, df_1m)
    if sig: signals.append(sig)

    sig = strategies_additional.heikin_ashi_ema_strategy(df_15m, df_1h, df_1m)
    if sig: signals.append(sig)

    sig = strategies_additional.bollinger_reversion_strategy(df_15m, df_1h, df_1m)
    if sig: signals.append(sig)

    sig = strategies_momentum.momo_strategy(df_15m, df_1h, df_1m, df_5m)
    if sig: signals.append(sig)

    sig = strategies_momentum.stoch_rsi_macd_strategy(df_15m, df_1h, df_1m)
    if sig: signals.append(sig)

    sig = strategies_momentum.triple_ema_stochrsi_atr_strategy(df_15m, df_1h, df_1m)
    if sig: signals.append(sig)

    sig = strategies_range.range_trading_strategy(df_15m, df_1h, df_1m)
    if sig: signals.append(sig)

    sig = strategies_fractal.ema_fractal_strategy(df_15m, df_1h, df_1m)
    if sig: signals.append(sig)

    sig = strategies_bigmove.big_move_stochrsi_strategy(df_15m, df_1h, df_1m)
    if sig: signals.append(sig)

    sig = strategies_trend.death_cross_strategy(df_15m, df_1h, df_1m)
    if sig: signals.append(sig)
    
    final_signal = aggregate_signals(signals)
    if final_signal:
        entry = final_signal['entry']
        sl    = final_signal['sl']
        final_signal['position_size'] = calculate_position_size(entry, sl, capital)
        final_signal['percentage_risk'] = calculate_percentage_risk(entry, sl)
    return final_signal


def build_message(symbol, signal):
    message  = f"💥 Señal para {symbol}\n"
    message += f"📊 Estrategia consolidada (score: {signal.get('score')})\n"
    message += f"🔔 Acción: {signal.get('action')}\n"
    message += f"📌 Entrada: {signal.get('entry'):.5f}\n"
    message += f"🎯 TP: {signal.get('tp'):.5f}\n"
    message += f"🛑 SL: {signal.get('sl'):.5f}\n"
    message += f"🔄 Trailing Stop: {signal.get('trailing_stop'):.5f}\n"
    message += f"💰 Posición: {signal.get('position_size'):.5f} (Riesgo: {signal.get('percentage_risk'):.2f}% del capital)\n"
    strategies = signal.get('strategies', [])
    if strategies:
        message += f"🔍 Estrategias: {', '.join(strategies)}\n"
    return message


def log_signal(symbol, signal):
    log_entry = {
        'symbol': symbol,
        'action': signal.get('action'),
        'entry': signal.get('entry'),
        'tp': signal.get('tp'),
        'sl': signal.get('sl'),
        'trailing_stop': signal.get('trailing_stop'),
        'position_size': signal.get('position_size'),
        'percentage_risk': signal.get('percentage_risk'),
        'strategies': ','.join(signal.get('strategies', []))
    }
    df_log = pd.DataFrame([log_entry])
    if os.path.exists("signals_log.csv"):
        existing_df = pd.read_csv("signals_log.csv")
        df_log = pd.concat([existing_df, df_log], ignore_index=True)
    df_log.to_csv("signals_log.csv", index=False)


def main_loop():
    capital = solicitar_capital()
    logging.info(f"Capital para operar: {capital} USD")

    # Obtener y mezclar la lista inicial de pares
    pairs = get_high_volume_perpetual_pairs(binance_client, top_n=200)
    random.shuffle(pairs)
    idx = 0

    while True:
        # Al recorrer toda la lista, refrescar y reordenar
        if idx >= len(pairs):
            logging.info("Se completó el ciclo de evaluación de pares, obteniendo lista nueva")
            pairs = get_high_volume_perpetual_pairs(binance_client, top_n=200)
            random.shuffle(pairs)
            idx = 0

        symbol = pairs[idx]
        logging.info(f"Evaluando {symbol}")
        signal = evaluate_pair(symbol, capital)

        if signal:
            msg = build_message(symbol, signal)
            send_discord_message(msg)
            log_signal(symbol, signal)
            logging.info(f"Señal enviada para {symbol} - Estrategias: {signal.get('strategies', [])}")

            # Pausa para ejecución manual
            logging.info("Esperando 3 minutos para ejecución manual...")
            time.sleep(180)

        # Avanzar al siguiente par, continúe donde quedó
        idx += 1

if __name__ == "__main__":
    main_loop()
