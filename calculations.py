def calculate_pips(pair: str, entry: float, exit: float, trade_type: str) -> float:
    """
    Calculate pips based on the currency pair.
    JPY pairs: 0.01 is 1 pip.
    Others: 0.0001 is 1 pip.
    """
    is_jpy = "JPY" in pair.upper()
    is_gold = "XAU" in pair.upper() or "GOLD" in pair.upper()
    
    # Institutional Multipliers:
    # JPY: 0.01 = 1 pip (*100)
    # Gold: 0.10 = 1 pip (*10)
    # Others: 0.0001 = 1 pip (*10000)
    if is_jpy:
        multiplier = 100
    elif is_gold:
        multiplier = 10
    else:
        multiplier = 10000
    
    if not exit or exit == 0:
        return 0.0
        
    if trade_type.lower() == "buy":
        pips = (exit - entry) * multiplier
    else:
        pips = (entry - exit) * multiplier
        
    return round(pips, 1)

def calculate_profit(pips: float, lot_size: float) -> float:
    """
    Calculate profit in USD.
    Standard Lot (1.0) = $10 per pip.
    Returns 0.0 if pips are 0 (open position).
    """
    if not pips:
        return 0.0
    profit = pips * lot_size * 10
    return round(profit, 2)
