import sqlite3
import pandas as pd
import streamlit as st
from datetime import datetime
import os

DB_PATH = "trades.db"
COLUMNS = ["Entry Date", "Exit Date", "Pair", "Type", "Entry", "Exit", "Lot Size", "Pips", "Profit", "Notes", "Image"]

def init_db():
    """Initialize the SQLite database with required tables."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    
    # Create Accounts table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS accounts (
            name TEXT PRIMARY KEY,
            starting_balance REAL DEFAULT 0.0
        )
    ''')
    
    # Create Trades table
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS trades (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            account_name TEXT,
            entry_date TEXT,
            exit_date TEXT,
            pair TEXT,
            type TEXT,
            entry REAL,
            exit REAL,
            lot_size REAL,
            pips REAL,
            profit REAL,
            notes TEXT,
            image_path TEXT,
            FOREIGN KEY (account_name) REFERENCES accounts (name)
        )
    ''')
    
    # MIGRATION: Check if 'timestamp' exists and rename it to 'entry_date'
    cursor.execute("PRAGMA table_info(trades)")
    cols = [c[1] for c in cursor.fetchall()]
    if 'timestamp' in cols:
        cursor.execute("ALTER TABLE trades RENAME COLUMN timestamp TO entry_date")
    if 'exit_date' not in cols:
        cursor.execute("ALTER TABLE trades ADD COLUMN exit_date TEXT")
    
    # Ensure at least one default account exists
    cursor.execute("SELECT COUNT(*) FROM accounts")
    if cursor.fetchone()[0] == 0:
        cursor.execute("INSERT INTO accounts (name, starting_balance) VALUES (?, ?)", ("Sheet1", 0.0))
    
    conn.commit()
    conn.close()

# Initialize DB on import
init_db()

def list_accounts():
    """List all accounts from the database. No cache to ensure instant updates."""
    conn = sqlite3.connect(DB_PATH)
    df = pd.read_sql_query("SELECT name FROM accounts", conn)
    conn.close()
    return df['name'].tolist()

def get_starting_balance(name):
    """Fetch starting balance for an account."""
    conn = sqlite3.connect(DB_PATH)
    cursor = conn.cursor()
    cursor.execute("SELECT starting_balance FROM accounts WHERE name = ?", (name,))
    result = cursor.fetchone()
    conn.close()
    return result[0] if result else 0.0

def set_starting_balance(name, balance):
    """Update starting balance for an account."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("UPDATE accounts SET starting_balance = ? WHERE name = ?", (balance, name))
        conn.commit()
        conn.close()
        return True
    except Exception:
        return False

def create_account(name):
    """Create a new account."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("INSERT INTO accounts (name, starting_balance) VALUES (?, ?)", (name, 0.0))
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        return False

def delete_account(name):
    """Delete an account and its associated trades."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        cursor.execute("DELETE FROM trades WHERE account_name = ?", (name,))
        cursor.execute("DELETE FROM accounts WHERE name = ?", (name,))
        conn.commit()
        conn.close()
        return True
    except Exception:
        return False

def load_trades(account_name="Sheet1"):
    """Load trades for a specific account, formatted as a DataFrame."""
    conn = sqlite3.connect(DB_PATH)
    query = """
        SELECT 
            entry_date as 'Entry Date', 
            exit_date as 'Exit Date',
            pair as 'Pair', 
            type as 'Type', 
            entry as 'Entry', 
            exit as 'Exit', 
            lot_size as 'Lot Size', 
            pips as 'Pips', 
            profit as 'Profit', 
            notes as 'Notes',
            image_path as 'Image'
        FROM trades 
        WHERE account_name = ?
        ORDER BY id ASC
    """
    df = pd.read_sql_query(query, conn, params=(account_name,))
    conn.close()
    if df.empty:
        return pd.DataFrame(columns=COLUMNS)
    return df

def add_trade(account_name, pair, trade_type, entry, exit, lot_size, pips, profit, notes, image_path=None, entry_date=None, exit_date=None):
    """Log a new trade to the database with optional screenshot and dates."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Default to Now if dates are empty
        if entry_date is None:
            entry_date = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        
        cursor.execute('''
            INSERT INTO trades (account_name, entry_date, exit_date, pair, type, entry, exit, lot_size, pips, profit, notes, image_path)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (account_name, entry_date, exit_date, pair.upper(), trade_type.capitalize(), entry, exit, lot_size, pips, profit, notes, image_path))
        conn.commit()
        conn.close()
        return True
    except Exception:
        return False

def update_trade(account_name, index, updated_fields):
    """Update a specific trade. Since we use a list in the UI, we find the nth trade and update it."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Pull trade IDs for this account in original order
        cursor.execute("SELECT id FROM trades WHERE account_name = ? ORDER BY id ASC", (account_name,))
        ids = [row[0] for row in cursor.fetchall()]
        
        if index < len(ids):
            trade_id = ids[index]
            # Mapping from DF columns to DB columns
            db_map = {
                "Pair": "pair",
                "Type": "type",
                "Entry": "entry",
                "Exit": "exit",
                "Lot Size": "lot_size",
                "Pips": "pips",
                "Profit": "profit",
                "Notes": "notes",
                "Image": "image_path",
                "Entry Date": "entry_date",
                "Exit Date": "exit_date"
            }
            
            for key, val in updated_fields.items():
                db_col = db_map.get(key, key)
                cursor.execute(f"UPDATE trades SET {db_col} = ? WHERE id = ?", (val, trade_id))
            
            conn.commit()
        conn.close()
        return True
    except Exception:
        return False

def delete_trade(account_name, index):
    """Delete a specific trade for an account based on its display index."""
    try:
        conn = sqlite3.connect(DB_PATH)
        cursor = conn.cursor()
        
        # Pull trade IDs for this account in original order
        cursor.execute("SELECT id FROM trades WHERE account_name = ? ORDER BY id ASC", (account_name,))
        ids = [row[0] for row in cursor.fetchall()]
        
        if index < len(ids):
            trade_id = ids[index]
            cursor.execute("DELETE FROM trades WHERE id = ?", (trade_id,))
            conn.commit()
        
        conn.close()
        return True
    except Exception:
        return False
