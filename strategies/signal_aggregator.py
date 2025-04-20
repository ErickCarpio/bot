import logging

def aggregate_signals(signal_list):
    """
    Recibe una lista de señales (diccionarios) de distintas estrategias para un mismo par,
    incluidas las que usan detección de swings y proyección lineal.
    
    Retorna una señal consolidada si al menos 2 estrategias coinciden en la dirección,
    e incluye la lista de nombres de estrategias que respaldan la señal.
    """
    if not signal_list:
        return None
    
    action_counts = {}
    strategies_used = {}
    for signal in signal_list:
        action = signal.get('action')
        strat_name = signal.get('strategy', 'Desconocida')
        if action:
            action_counts[action] = action_counts.get(action, 0) + 1
            strategies_used.setdefault(action, []).append(strat_name)
            
    if not action_counts:
        return None
    best_action = max(action_counts, key=action_counts.get)
    if action_counts[best_action] < 2:
        return None
    
    consolidated = {
        'action': best_action,
        'entry': sum(sig['entry'] for sig in signal_list if sig['action'] == best_action) / action_counts[best_action],
        'tp': sum(sig['tp'] for sig in signal_list if sig['action'] == best_action) / action_counts[best_action],
        'sl': sum(sig['sl'] for sig in signal_list if sig['action'] == best_action) / action_counts[best_action],
        'trailing_stop': sum(sig['trailing_stop'] for sig in signal_list if sig['action'] == best_action) / action_counts[best_action],
        'score': action_counts[best_action],
        'strategies': list(set(strategies_used.get(best_action, [])))
    }
    return consolidated
