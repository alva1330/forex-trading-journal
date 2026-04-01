def calculate_pips(pair: str, entry: float, exit: float, trade_type: str) -> float:
    """
    Calculate pips based on the currency pair.
    JPY pairs: 0.01 is 1 pip.
    Others: 0.0001 is 1 pip.
    """
    is_jpy = "JPY" in pair.upper()
    multiplier = 100 if is_jpy else 10000
    
    if trade_type.lower() == "buy":
        pips = (exit - entry) * multiplier
    else:
        pips = (entry - exit) * multiplier
        
    return round(pips, 1)

def calculate_profit(pips: float, lot_size: float) -> float:
    """
    Calculate profit in USD.
    Standard Lot (1.0) = $10 per pip.
    """
    profit = pips * lot_size * 10
    return round(profit, 2)
