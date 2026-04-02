import streamlit as st
import pandas as pd
import plotly.express as px
from calculations import calculate_pips, calculate_profit
from data_manager import load_trades, add_trade, list_accounts, create_account, delete_account, get_starting_balance, set_starting_balance

# Configuration
st.set_page_config(page_title="Forex Terminal Journal", page_icon="📈", layout="wide")

# Injection of custom CSS
def local_css(file_name):
    with open(file_name) as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)

local_css("styles.css")

# --- Data Initialization ---
if "accounts" not in st.session_state:
    st.session_state.accounts = list_accounts()

if "active_account" not in st.session_state:
    st.session_state.active_account = st.session_state.accounts[0]

if "starting_balance" not in st.session_state:
    st.session_state.starting_balance = get_starting_balance(st.session_state.active_account)

# --- App Header ---
st.title("📟 FOREX TERMINAL JOURNAL v1.0")
st.markdown(f'<div class="status-indicator">[ SESSION: {st.session_state.active_account} ]</div>', unsafe_allow_html=True)
st.markdown("---")

# --- Sidebar: Account Management ---
with st.sidebar.expander("🏢 ACCOUNT MANAGEMENT", expanded=False):
    # Action: Manual Sync
    if st.button("SYNC NOW (Refresh Tabs)"):
        st.cache_data.clear()
        st.session_state.accounts = list_accounts()
        st.rerun()

    accounts = st.session_state.accounts
    
    # Safer index lookup to prevent "ValueError: ... is not in list"
    try:
        current_index = accounts.index(st.session_state.active_account)
    except ValueError:
        current_index = 0
        st.session_state.active_account = accounts[0]
        
    active_acc = st.selectbox("SELECT ACTIVE ACCOUNT", accounts, index=current_index)
    
    # Switch logic: Update balance only when account actually changes
    if active_acc != st.session_state.active_account:
        st.session_state.active_account = active_acc
        st.session_state.starting_balance = get_starting_balance(active_acc)
        st.rerun()
    
    # Create New Account
    st.markdown("---")
    new_acc_name = st.text_input("New Account Name")
    if st.button("CREATE"):
        if new_acc_name and new_acc_name not in accounts:
            if create_account(new_acc_name):
                st.success(f"ACCOUNT '{new_acc_name}' CREATED!")
                st.session_state.accounts = list_accounts()
                st.session_state.active_account = new_acc_name
                st.rerun()
        else:
            st.error("INVALID NAME OR ALREADY EXISTS.")

    # Delete Account Section
    st.markdown("---")
    st.caption("🗑️ DELETE ACCOUNT")
    delete_options = [acc for acc in accounts if acc != st.session_state.active_account]
    
    if len(accounts) > 1:
        if delete_options:
            acc_to_delete = st.selectbox("SELECT ACCOUNT TO DELETE", delete_options)
            if st.button("DELETE PERMANENTLY", type="secondary"):
                if delete_account(acc_to_delete):
                    st.success(f"ACCOUNT '{acc_to_delete}' DELETED!")
                    st.session_state.accounts = list_accounts()
                    st.rerun()
        else:
            st.info("SWITCH ACCOUNTS TO DELETE OTHERS.")
    else:
        st.info("CANNOT DELETE THE LAST ACCOUNT.")
    
    # Starting Balance Section
    st.markdown("---")
    st.caption("💼 BALANCE SETTINGS")
    current_sb = get_starting_balance(st.session_state.active_account)
    sb_input = st.number_input("Starting Capital ($)", value=float(current_sb), step=100.0)
    if st.button("SAVE BALANCE"):
        if set_starting_balance(st.session_state.active_account, sb_input):
            st.session_state.starting_balance = sb_input
            st.success("BALANCE SAVED!")
            st.rerun()

# --- Sidebar: Add New Trade ---
with st.sidebar.expander("➕ LOG NEW TRADE", expanded=False):
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
    # Sort for chart
    df_chart = df.copy().sort_values("Timestamp")
    start_bal = float(st.session_state.starting_balance)
    df_chart["Cumulative"] = start_bal + df_chart["Profit"].cumsum()
    
    total_trades = len(df)
    total_profit = df["Profit"].sum()
    current_bal = start_bal + total_profit
    wins = len(df[df["Profit"] > 0])
    win_rate = (wins / total_trades) * 100 if total_trades > 0 else 0
    
    # Dashboard Metrics - Wrapped in Glass Card
    st.markdown('<div class="glass-card">', unsafe_allow_html=True)
    m1, m2, m3 = st.columns(3)
    m1.metric("TOTAL TRADES", total_trades)
    m2.metric("WIN RATE", f"{win_rate:.1f}%")
    # Color based on profit
    p_class = "profit-pos" if current_bal >= start_bal else "profit-neg"
    m3.markdown(f'<div style="text-align: center;"><label style="font-size: 0.8rem; color: #888; text-transform: uppercase; letter-spacing: 1.5px;">ACCOUNT BALANCE</label><br/><span class="{p_class}" style="font-family: Orbitron, sans-serif; font-size: 2rem;">${current_bal:,.2f}</span></div>', unsafe_allow_html=True)
    st.markdown('</div>', unsafe_allow_html=True)

    # --- Feature 1: Equity Curve ---
    st.markdown("### 📈 EQUITY GROWTH CURVE")
    with st.container():
        st.markdown('<div class="glass-card">', unsafe_allow_html=True)
        fig = px.line(
            df_chart, 
            x="Timestamp", 
            y="Cumulative", 
            template="plotly_dark",
            labels={"Cumulative": "Balance ($)", "Timestamp": "Time"}
        )
        # Style the line with Neon Green
        fig.update_traces(line_color="#00ffa3", line_width=3)
        fig.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=10, r=10, t=10, b=10),
            xaxis=dict(showgrid=False),
            yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.05)")
        )
        st.plotly_chart(fig, use_container_width=True, theme=None)
        st.markdown('</div>', unsafe_allow_html=True)
else:
    st.info("NO TRADE DATA DETECTED. INITIALIZE LOG IN SIDEBAR.")

st.markdown("### 📊 TRADE HISTORY DATA")

# Table Area - Wrapped in Glass Card
st.markdown('<div class="glass-card">', unsafe_allow_html=True)
search_term = st.text_input("FILTER BY PAIR/TYPE", "").upper()

if not df.empty:
    if search_term:
        filtered_df = df[df["Pair"].str.contains(search_term) | df["Type"].str.contains(search_term)]
    else:
        filtered_df = df

    if not filtered_df.empty:
        st.dataframe(filtered_df.sort_values(by="Timestamp", ascending=False), use_container_width=True)
    else:
        st.write("NO HISTORY MATCHES SEARCH CRITERIA.")
else:
    st.write("NO TRADES LOGGED YET.")
st.markdown('</div>', unsafe_allow_html=True)

# Terminal-style Footer
st.markdown("---")
st.caption("SYSTEM STATUS: ONLINE | DATABASE: GOOGLE SHEETS | ENCRYPTION: SSL")
