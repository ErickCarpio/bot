# backtesting.py
import pandas as pd
import logging
from utils import error_handler

@error_handler
def evaluate_strategy(strategy_func, df_main, df_context, df_5m=None, symbol=""):
    """
    Ejecuta backtesting para una estrategia en un DataFrame.
    Retorna una lista de operaciones y métricas.
    Registra la estrategia que generó la señal (si se especifica) y guarda los resultados en un CSV.
    """
    operations = []
    equity = [10000]  # Capital inicial
    position = None
    entry_price = 0
    entry_time = None
    strategy_name = None
    total_cost = 0.0018  # Comisión aproximada
    
    for i in range(50, len(df_main)):
        df_main_subset = df_main.iloc[:i+1].copy()
        df_context_subset = df_context.iloc[:i+1].copy() if len(df_context) > i else df_context.copy()
        df_5m_subset = df_5m.iloc[:i+1].copy() if df_5m is not None and len(df_5m) > i else None
        
        current_price = df_main_subset['close'].iloc[-1]
        signal = strategy_func(df_main_subset, df_context_subset, df_5m=df_5m_subset)
        
        if signal:
            if not position:
                position = signal.get('action')
                entry_price = signal.get('entry')
                entry_time = df_main_subset.index[-1]
                strategy_name = signal.get('strategy', 'Desconocida')
            # Para operaciones de compra
            if position == 'buy' and current_price >= signal.get('tp'):
                profit = (current_price - entry_price) / entry_price - total_cost
                operations.append({
                    'symbol': symbol,
                    'entry_time': entry_time,
                    'exit_time': df_main_subset.index[-1],
                    'entry_price': entry_price,
                    'exit_price': current_price,
                    'profit': profit,
                    'strategy': strategy_name,
                    'action': 'buy'
                })
                equity.append(equity[-1]*(1+profit))
                position = None
            # Para operaciones de venta
            elif position == 'sell' and current_price <= signal.get('tp'):
                profit = (entry_price - current_price) / entry_price - total_cost
                operations.append({
                    'symbol': symbol,
                    'entry_time': entry_time,
                    'exit_time': df_main_subset.index[-1],
                    'entry_price': entry_price,
                    'exit_price': current_price,
                    'profit': profit,
                    'strategy': strategy_name,
                    'action': 'sell'
                })
                equity.append(equity[-1]*(1+profit))
                position = None

    win_rate = sum(1 for op in operations if op['profit'] > 0) / len(operations) if operations else 0
    metrics = {
        'total_operations': len(operations),
        'win_rate': win_rate,
        'final_equity': equity[-1]
    }
    
    # Guardar operaciones en CSV para análisis posterior
    if operations:
        df_ops = pd.DataFrame(operations)
        try:
            # Si ya existe el archivo, se agregan las nuevas operaciones
            existing_df = pd.read_csv("backtesting_results.csv")
            df_ops = pd.concat([existing_df, df_ops], ignore_index=True)
        except Exception:
            # Si no existe, se crea desde cero
            pass
        df_ops.to_csv("backtesting_results.csv", index=False)
        logging.info("Resultados de backtesting guardados en 'backtesting_results.csv'")
    
    return operations, metrics
