# trade_manager.py
import logging
import requests
from config import INITIAL_CAPITAL, RISK_PER_TRADE, LEVERAGE

def calculate_position_size(entry_price, stop_loss, capital=None):
    """
    Calcula el tamaño de la posición basado en el riesgo permitido.
    Se espera que 'stop_loss' se defina a partir de niveles técnicos (swings/resistencias)
    que combinen la información de los swings y la volatilidad.
    
    Fórmula: (capital * RISK_PER_TRADE) / (distancia entre entry y stop_loss)
    Se ajusta con apalancamiento.
    Si se especifica 'capital', se utiliza; de lo contrario se usa INITIAL_CAPITAL.
    """
    effective_capital = capital if capital is not None else INITIAL_CAPITAL
    risk_amount = effective_capital * RISK_PER_TRADE
    risk_per_unit = abs(entry_price - stop_loss)
    if risk_per_unit == 0:
        logging.error("Riesgo por unidad es 0, no se puede calcular tamaño de posición")
        return 0
    position_size = (risk_amount / risk_per_unit) * LEVERAGE
    return position_size

def calculate_percentage_risk(entry_price, stop_loss):
    """
    Calcula el porcentaje del capital que representa el riesgo de la operación.
    """
    risk_per_unit = abs(entry_price - stop_loss)
    if entry_price == 0:
        return 0
    percentage_risk = (risk_per_unit / entry_price) * 100
    return percentage_risk

import requests
import logging
from config import DISCORD_WEBHOOK_URL, DISCORD_TIMEOUT

def send_discord_message(message):
    """
    Envía el mensaje a Discord.
    """
    try:
        data = {"content": message}
        response = requests.post(DISCORD_WEBHOOK_URL, json=data, timeout=DISCORD_TIMEOUT)
        response.raise_for_status()
        logging.info("Mensaje enviado a Discord")
    except Exception as e:
        logging.error(f"Error enviando mensaje a Discord: {e}")



