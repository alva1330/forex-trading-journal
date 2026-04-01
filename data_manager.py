import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# Initialize Google Sheets Connection
conn = st.connection("gsheets", type=GSheetsConnection)

COLUMNS = ["Timestamp", "Pair", "Type", "Entry", "Exit", "Lot Size", "Pips", "Profit", "Notes"]

def load_trades():
    """Load trades from Google Sheet."""
    try:
        # Read the entire sheet. Assuming the sheet has a name (URL provided in secrets)
        return conn.read(ttl="10m") # Cache for 10 minutes
    except Exception as e:
        # Return empty DataFrame with columns if sheet is empty or error
        return pd.DataFrame(columns=COLUMNS)

def add_trade(pair, trade_type, entry, exit, lot_size, pips, profit, notes):
    """Add a new trade to the Google Sheet."""
    new_trade = {
        "Timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "Pair": pair.upper(),
        "Type": trade_type.capitalize(),
        "Entry": entry,
        "Exit": exit,
        "Lot Size": lot_size,
        "Pips": pips,
        "Profit": profit,
        "Notes": notes
    }
    
    # Load current history
    df = load_trades()
    
    # Check if df is empty (no headers)
    if df.empty:
        df = pd.DataFrame(columns=COLUMNS)

    # Append new trade
    new_df = pd.concat([df, pd.DataFrame([new_trade])], ignore_index=True)
    
    # Update Google Sheet
    conn.update(data=new_df)
    return new_df
