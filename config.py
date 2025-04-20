# config.py
# Archivo de configuración global para parámetros de indicadores, gestión de riesgo y ajustes operativos

# Parámetros de indicadores para marcos de 15 minutos
RSI_PERIOD_15m = 21
RSI_BUY_THRESHOLD = 25   # Para compras, RSI < 30
RSI_SELL_THRESHOLD = 75  # Para ventas, RSI > 70

# Parámetros para StochRSI
STOCHRSI_FASTK_PERIOD = 5
STOCHRSI_FASTD_PERIOD = 3
STOCHRSI_BUY_THRESHOLD = 25  
STOCHRSI_SELL_THRESHOLD = 75  

# Parámetros para ADX
ADX_MIN_TREND = 20   # Mínimo ADX para considerar una tendencia fuerte
ADX_MAX_RANGE = 20   # Para operar en mercados laterales

# Parámetros para volumen y volatilidad
VOLUME_FACTOR = 1.0  # El volumen actual debe ser al menos igual al promedio
VOLUME_MULTIPLIER = 0.5  # Mínimo volumen requerido en relación al promedio

# Parámetros para enfriamiento (cooldown)
COOLDOWN_PERIOD = 5  # Número de velas de cooldown

# Parámetros para TP/SL dinámicos
ATR_MIN = 5e-8  # Valor mínimo de ATR para considerar la operación
MIN_TP_MULTIPLIER = 1.2      
MIN_SL_MULTIPLIER = 1.0      
TP_DYNAMIC_OFFSET = 0.5      
SL_DYNAMIC_OFFSET = 0.5      
DEFAULT_TRAILING_STOP_MULTIPLIER = 2.0  
MAX_LOSS_PER_TRADE = 0.01  # Pérdida máxima permitida por trade (1%)

# Parámetros para estrategias
BREAKOUT_PERCENTAGE = 0.015  
GOLDEN_CROSS_EMA_DIFF_THRESHOLD = 0.007
MIN_ADX_GOLDEN = 20  
FIB_DISTANCE_THRESHOLD = 0.015  
MIN_ADX_HEIKIN = 20
BOLLINGER_LOWER_MULTIPLIER = 0.998  
BOLLINGER_UPPER_MULTIPLIER = 1.002  
BOLLINGER_TP_SL_OFFSET = 1.5

# Parámetros para estrategias adicionales

# Range Trading: operar en mercados laterales
RANGE_ADX_THRESHOLD = 20      # ADX bajo para rango
RANGE_OSC_THRESHOLD = 40      # Oscilador (RSI u otro) en zona neutral
RANGE_VOLUME_MULTIPLIER = 1.2  # Volumen debe ser moderado

# EMA Fractal: entradas basadas en fractales
EMA_FRACTAL_MIN_GAP = 0.01    # Diferencia mínima entre EMAs para confirmar tendencia

# BigMoveStochRSI: detectar movimientos bruscos
BIGMOVE_THRESHOLD_PERCENT = 0.04  # Movimiento mínimo del 4% (o basado en ATR)
BIGMOVE_STOCH_BUY = 0.05         # Umbral extremo para compra (<5%)
BIGMOVE_STOCH_SELL = 0.95        # Umbral extremo para venta (>95%)

# Parámetros para backtesting
BACKTEST_WAIT_CANDLES = 100

# Parámetros de gestión de riesgo
RISK_PER_TRADE = 0.02  # Porcentaje del capital a arriesgar por trade

# Parámetros de ciclo
SLEEP_INTERVAL = 1800  # 1800 segundos = 30 minutos

# Parámetros de operación en futuros
INITIAL_CAPITAL = 27.0
LEVERAGE = 10  # Apalancamiento

# Configuración del webhook de Discord
DISCORD_WEBHOOK_URL = "https://discord.com/api/webhooks/1355669830832750622/4QiMN1vEimE6LVKq60ice9XEWjdvrQpnLh532suluuJuWmnoUvpquRX6Cl7mSKl0nzkk"
DISCORD_TIMEOUT = 5

# Parámetros para cálculo de swings en datos de 1 minuto
SWING_WINDOW_MIN_1M = 120
