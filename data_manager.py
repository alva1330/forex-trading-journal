import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# Initialize Google Sheets Connection
conn = st.connection("gsheets", type=GSheetsConnection)

COLUMNS = ["Timestamp", "Pair", "Type", "Entry", "Exit", "Lot Size", "Pips", "Profit", "Notes"]

@st.cache_data(ttl=5)
def list_accounts():
    """List all accounts (worksheets) in the Google Sheet."""
    # Access the underlying client to list all worksheets
    client = conn.client
    # Get the URL from secrets
    url = st.secrets["connections"]["gsheets"]["spreadsheet"]
    # Force a fresh open of the spreadsheet
    sh = client.open_by_url(url)
    # Get all worksheet names
    titles = [ws.title for ws in sh.worksheets()]
    return titles

def create_account(name):
    """Create a new account (worksheet) with headers."""
    try:
        df_headers = pd.DataFrame(columns=COLUMNS)
        # Create a new worksheet and initialize with headers
        conn.create(worksheet=name, data=df_headers)
        # Clear the cache
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"SYSTEM ERROR: {e}")
        return False

def load_trades(worksheet_name="Sheet1"):
    """Load trades from a specific Google Sheet tab."""
    try:
        # Set ttl to 0 to always get the freshest data from the cloud
        df = conn.read(worksheet=worksheet_name, ttl=0)
        if df is None or df.empty:
             return pd.DataFrame(columns=COLUMNS)
        return df
    except Exception as e:
        return pd.DataFrame(columns=COLUMNS)

def add_trade(worksheet_name, pair, trade_type, entry, exit, lot_size, pips, profit, notes):
    """Add a new trade to a specific Google Sheet tab."""
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
    
    # Load freshest history for the selected account
    df = load_trades(worksheet_name)
    
    # Ensure COLUMNS are present
    if df.empty:
        df = pd.DataFrame(columns=COLUMNS)

    # Append new trade to the list
    new_df = pd.concat([df, pd.DataFrame([new_trade])], ignore_index=True)
    
    # Push the full updated list back to the specific tab
    conn.update(worksheet=worksheet_name, data=new_df)
    return new_df
