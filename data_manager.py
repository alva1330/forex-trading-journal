import streamlit as st
from streamlit_gsheets import GSheetsConnection
import pandas as pd
from datetime import datetime

# Initialize Google Sheets Connection
conn = st.connection("gsheets", type=GSheetsConnection)

COLUMNS = ["Timestamp", "Pair", "Type", "Entry", "Exit", "Lot Size", "Pips", "Profit", "Notes"]

import gspread

@st.cache_data(ttl=120)
def list_accounts():
    """List all accounts (worksheets) in the Google Sheet using direct gspread access."""
    try:
        # Get credentials dictionary from Streamlit secrets
        creds_dict = dict(st.secrets["connections"]["gsheets"])
        
        # Remove the spreadsheet URL from the dict so gspread doesn't complain about extra keys
        url = creds_dict.pop("spreadsheet", None)
        
        # Authorize directly with gspread for the metadata list
        gc = gspread.service_account_from_dict(creds_dict)
        sh = gc.open_by_url(url)
        
        return [ws.title for ws in sh.worksheets()]
    except Exception as e:
        # Fallback to Sheet1 if listing fails to keep the app alive
        return ["Sheet1"]

def get_starting_balance(name):
    """Fetch the starting balance for an account from the _metadata worksheet."""
    try:
        # Get credentials dictionary from Streamlit secrets
        creds_dict = dict(st.secrets["connections"]["gsheets"])
        url = creds_dict.pop("spreadsheet", None)
        
        # Authorize directly with gspread
        gc = gspread.service_account_from_dict(creds_dict)
        sh = gc.open_by_url(url)
        
        # Open or create _metadata worksheet
        try:
            ws_meta = sh.worksheet("_metadata")
        except gspread.exceptions.WorksheetNotFound:
            ws_meta = sh.add_worksheet(title="_metadata", rows="100", cols="2")
            ws_meta.append_row(["AccountName", "StartingBalance"])
        
        # Find the account's balance
        records = ws_meta.get_all_records()
        for row in records:
            if row["AccountName"] == name:
                return float(row["StartingBalance"])
        return 0.0
    except Exception as e:
        return 0.0

def set_starting_balance(name, balance):
    """Set the starting balance for an account in the _metadata worksheet."""
    try:
        # Get credentials dictionary from Streamlit secrets
        creds_dict = dict(st.secrets["connections"]["gsheets"])
        url = creds_dict.pop("spreadsheet", None)
        
        # Authorize directly with gspread
        gc = gspread.service_account_from_dict(creds_dict)
        sh = gc.open_by_url(url)
        
        # Open or create _metadata worksheet
        try:
            ws_meta = sh.worksheet("_metadata")
        except gspread.exceptions.WorksheetNotFound:
            ws_meta = sh.add_worksheet(title="_metadata", rows="100", cols="2")
            ws_meta.append_row(["AccountName", "StartingBalance"])
        
        # Check if record exists
        cell = ws_meta.find(name)
        if cell:
            # Update existing balance
            ws_meta.update_cell(cell.row, 2, balance)
        else:
            # Add new record
            ws_meta.append_row([name, balance])
            
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"SYSTEM ERROR: {e}")
        return False

def delete_account(name):
    """Delete an account (worksheet) from the Google Sheet."""
    try:
        # Get credentials dictionary from Streamlit secrets
        creds_dict = dict(st.secrets["connections"]["gsheets"])
        url = creds_dict.pop("spreadsheet", None)
        
        # Authorize directly with gspread
        gc = gspread.service_account_from_dict(creds_dict)
        sh = gc.open_by_url(url)
        
        # Find and delete the worksheet
        worksheet = sh.worksheet(name)
        sh.del_worksheet(worksheet)
        
        # Clear all caches
        st.cache_data.clear()
        return True
    except Exception as e:
        st.error(f"SYSTEM ERROR: {e}")
        return False

def update_trade_record(account_name, timestamp, updated_data):
    """Update an existing trade row in Google Sheets identified by its timestamp."""
    try:
        # Get credentials dictionary from Streamlit secrets
        creds_dict = dict(st.secrets["connections"]["gsheets"])
        url = creds_dict.pop("spreadsheet", None)
        
        # Authorize directly with gspread
        gc = gspread.service_account_from_dict(creds_dict)
        sh = gc.open_by_url(url)
        ws = sh.worksheet(account_name)
        
        # Find the row with the unique timestamp
        cell = ws.find(str(timestamp), in_column=1)
        if cell:
            # Overwrite the row with updated data
            ws.update(range_name=f"A{cell.row}:I{cell.row}", values=[updated_data])
            return True
        return False
    except Exception as e:
        st.error(f"SYSTEM ERROR UPDATING TRADE: {e}")
        return False

def create_account(name):
    """Create a new account (worksheet) with headers."""
    try:
        df_headers = pd.DataFrame(columns=COLUMNS)
        # Create a new worksheet and initialize with headers
        conn.create(worksheet=name, data=df_headers)
        # Clear all caches
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
