import MetaTrader5 as mt5
from datetime import datetime, timedelta
import pandas as pd

def connect_mt5():
    """Connect to the locally running MT5 terminal."""
    if not mt5.initialize():
        return False
    return True

def get_active_account_info():
    """Get the currently logged-in account number and balance."""
    if not connect_mt5():
        return None
    
    account_info = mt5.account_info()
    if account_info is None:
        return None
    
    return {
        "login": account_info.login,
        "balance": account_info.balance,
        "equity": account_info.equity,
        "server": account_info.server,
        "name": account_info.name
    }

def fetch_mt5_history(days=7):
    """Fetch closed trades (deals) from MT5 for the last X days."""
    if not connect_mt5():
        return []
    
    from_date = datetime.now() - timedelta(days=days)
    to_date = datetime.now()
    
    # Get all deals (including entries and exits)
    deals = mt5.history_deals_get(from_date, to_date)
    if deals is None or len(deals) == 0:
        return []
    
    processed_trades = []
    
    # We look for DEAL_ENTRY_OUT (the closing deal) to identify a full trade
    for deal in deals:
        # entry 1 = DEAL_ENTRY_OUT (closing)
        if deal.entry == 1: 
            # Find the opening deal for this position to get the entry price
            position_deals = mt5.history_deals_get(position=deal.position_id)
            entry_price = 0
            if position_deals:
                for p_deal in position_deals:
                    if p_deal.entry == 0: # DEAL_ENTRY_IN
                        entry_price = p_deal.price
                        break
            
            # Map type (deal.type is 0 for BUY, 1 for SELL)
            # For a closing deal (OUT), the original trade type is the opposite? 
            # No, deal.type for a BUY-OUT is SELL (the deal that closed it).
            # So if the closing deal is a SELL, the original trade was a BUY.
            trade_type = "Buy" if deal.type == 1 else "Sell"
            
            # Pip calculation (simplified for the sync)
            # We already have the logic in calculations.py, but we need to know the pair
            
            trade = {
                "ticket": deal.ticket,
                "pair": deal.symbol,
                "type": trade_type,
                "entry": entry_price,
                "exit": deal.price,
                "lot_size": deal.volume,
                "profit": deal.profit + deal.commission + deal.swap,
                "timestamp": datetime.fromtimestamp(deal.time).strftime("%Y-%m-%d %H:%M:%S"),
                "notes": f"Sync from MT5 Account {deal.external_id or ''}"
            }
            processed_trades.append(trade)
            
    return processed_trades

def shutdown_mt5():
    mt5.shutdown()
