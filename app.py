import streamlit as st
import pandas as pd
from calculations import calculate_pips, calculate_profit
from data_manager import load_trades, add_trade, list_accounts, create_account

# Configuration
st.set_page_config(page_title="Forex Terminal Journal", page_icon="📈", layout="wide")

# Injection of custom CSS
def local_css(file_name):
    with open(file_name) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

local_css("styles.css")

# --- App Header ---
st.title("📟 FOREX TERMINAL JOURNAL v1.0")
st.markdown("---")

# --- Sidebar: Account Management ---
with st.sidebar:
    st.header("🏢 ACCOUNT MANAGEMENT")
    
    # List existing accounts
    accounts = list_accounts()
    
    # Active Account Selection
    if "active_account" not in st.session_state:
        st.session_state.active_account = accounts[0]
        
    active_acc = st.selectbox("SELECT ACTIVE ACCOUNT", accounts, index=accounts.index(st.session_state.active_account))
    st.session_state.active_account = active_acc
    
    # Create New Account
    with st.expander("➕ CREATE NEW ACCOUNT"):
        new_acc_name = st.text_input("New Account Name")
        if st.button("CREATE"):
            if new_acc_name and new_acc_name not in accounts:
                if create_account(new_acc_name):
                    st.success(f"ACCOUNT '{new_acc_name}' CREATED!")
                    st.session_state.active_account = new_acc_name
                    st.rerun()
            else:
                st.error("INVALID NAME OR ALREADY EXISTS.")

    st.markdown("---")

# --- Sidebar: Add New Trade ---
with st.sidebar:
    st.header("➕ LOG NEW TRADE")
    st.caption(f"LOGGING TO: {st.session_state.active_account}")
    with st.form("trade_form", clear_on_submit=True):
        pair = st.text_input("Pair (e.g. GBP/USD)", value="EUR/USD")
        trade_type = st.selectbox("Action", ["Buy", "Sell"])
        
        col1, col2 = st.columns(2)
        with col1:
            entry_price = st.number_input("Entry Price", format="%.5f", step=0.0001)
            lot_size = st.number_input("Lot Size", min_value=0.01, value=1.0, step=0.1)
        with col2:
            exit_price = st.number_input("Exit Price", format="%.5f", step=0.0001)
        
        notes = st.text_area("Notes")
        submit = st.form_submit_button("SYSTEM: COMMIT TRADE")

        if submit:
            pips = calculate_pips(pair, entry_price, exit_price, trade_type)
            profit = calculate_profit(pips, lot_size)
            add_trade(st.session_state.active_account, pair, trade_type, entry_price, exit_price, lot_size, pips, profit, notes)
            st.success(f"TRADE RECORDED: {pips} PIPS / ${profit} USD")
            st.rerun()

# --- Main Dashboard ---
df = load_trades(st.session_state.active_account)

# Stats calculation
if not df.empty:
    total_trades = len(df)
    total_profit = df["Profit"].sum()
    wins = len(df[df["Profit"] > 0])
    win_rate = (wins / total_trades) * 100 if total_trades > 0 else 0
    
    # Dashboard Metrics
    m1, m2, m3 = st.columns(3)
    m1.metric("TOTAL TRADES", total_trades)
    m2.metric("WIN RATE", f"{win_rate:.1f}%")
    m3.metric("NET P/L (USD)", f"${total_profit:,.2f}")
else:
    st.info("NO TRADE DATA DETECTED. INITIALIZE LOG IN SIDEBAR.")

st.markdown("### 📊 TRADE HISTORY DATA")

# Search/Filter
search_term = st.text_input("FILTER BY PAIR/TYPE", "").upper()
if search_term:
    filtered_df = df[df["Pair"].str.contains(search_term) | df["Type"].str.contains(search_term)]
else:
    filtered_df = df

if not filtered_df.empty:
    # Stylized Trade Table
    st.dataframe(filtered_df.sort_values(by="Timestamp", ascending=False), use_container_width=True)
else:
    st.write("NO HISTORY MATCHES SEARCH CRITERIA.")

# Terminal-style Footer
st.markdown("---")
st.caption("SYSTEM STATUS: ONLINE | DATABASE: TRADES.CSV | ENCRYPTION: NONE")
