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
        # Set ttl to 0 to always get the freshest data from the cloud
        df = conn.read(ttl=0)
        if df is None or df.empty:
             return pd.DataFrame(columns=COLUMNS)
        return df
    except Exception as e:
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
    
    # Load freshest history
    df = load_trades()
    
    # Ensure COLUMNS are present
    if df.empty:
        df = pd.DataFrame(columns=COLUMNS)

    # Append new trade to the list
    new_df = pd.concat([df, pd.DataFrame([new_trade])], ignore_index=True)
    
    # Push the full updated list back to Google Sheets
    conn.update(data=new_df)
    return new_df
