import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
from calculations import calculate_pips, calculate_profit
from data_manager import load_trades, add_trade, update_trade, delete_trade, list_accounts, create_account, delete_account, get_starting_balance, set_starting_balance

# Configuration
st.set_page_config(
    page_title="Lumina Journal | Professional Trading Terminal", 
    page_icon="💹", 
    layout="wide",
    initial_sidebar_state="expanded"  # Forces the sidebar to stay open!
)

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

# --- Sidebar Data Fetch ---
df = load_trades(st.session_state.active_account)

# --- App Header (Lumina Style) ---
h_col1, h_col2 = st.columns([2, 1])
with h_col1:
    st.markdown(f"""
        <div style="display: flex; align-items: center; gap: 20px;">
            <h1 style="margin: 0; padding: 0;">Lumina Journal</h1>
            <div class="status-badge">
                <div class="status-dot"></div>
                PRO TERMINAL
            </div>
        </div>
    """, unsafe_allow_html=True)
with h_col2:
    st.markdown(f"""
        <div style="text-align: right; padding-top: 10px;">
            <span style="color: #94a3b8; font-size: 0.8rem;">SESSION ACTIVE:</span>
            <span style="color: #10b981; font-weight: 600; font-family: 'Outfit';"> {st.session_state.active_account}</span>
        </div>
    """, unsafe_allow_html=True)

st.markdown("<br>", unsafe_allow_html=True)

# --- Sidebar Navigation ---
st.sidebar.markdown("### 🧭 NAVIGATION")

# Account Selection
accounts = st.session_state.accounts
try:
    current_index = accounts.index(st.session_state.active_account)
except ValueError:
    current_index = 0
    st.session_state.active_account = accounts[0]
active_acc = st.sidebar.selectbox("ACTIVE ACCOUNT", accounts, index=current_index)

if active_acc != st.session_state.active_account:
    st.session_state.active_account = active_acc
    st.session_state.starting_balance = get_starting_balance(active_acc)
    st.rerun()

st.sidebar.markdown("---")

# Quick Actions
with st.sidebar.expander("➕ LOG NEW TRADE"):
    with st.form("trade_form", clear_on_submit=True):
        pair = st.text_input("Pair (e.g. EUR/USD)", value="EUR/USD")
        trade_type = st.selectbox("Action", ["Buy", "Sell"])
        c1, c2 = st.columns(2)
        entry_price = c1.number_input("Entry", format="%.5f", step=0.0001)
        exit_price = c2.number_input("Exit", format="%.5f", step=0.0001)
        lot_size = st.number_input("Lot Size", min_value=0.01, value=1.0, step=0.1)
        notes = st.text_area("Notes")
        if st.form_submit_button("COMMIT TRADE"):
            pips = calculate_pips(pair, entry_price, exit_price, trade_type)
            profit = calculate_profit(pips, lot_size)
            add_trade(st.session_state.active_account, pair, trade_type, entry_price, exit_price, lot_size, pips, profit, notes)
            st.success("TRADE RECORDED")
            st.rerun()

with st.sidebar.expander("📝 EDIT / DELETE"):
    if not df.empty:
        trade_options = [f"{i}: {row['Pair']} ({row['Timestamp']})" for i, row in df.iterrows()]
        trade_options.reverse()
        selected_option = st.selectbox("SELECT TRADE", trade_options)
        edit_idx = int(selected_option.split(":")[0])
        t_data = df.iloc[edit_idx]
        
        with st.form(f"edit_form_{edit_idx}"):
            e_pair = st.text_input("Pair", value=t_data["Pair"])
            e_action = st.selectbox("Action", ["Buy", "Sell"], index=0 if t_data["Type"] == "Buy" else 1)
            e_entry = st.number_input("Entry", value=float(t_data["Entry"]), format="%.5f")
            e_exit = st.number_input("Exit", value=float(t_data["Exit"]), format="%.5f")
            e_lot = st.number_input("Lots", value=float(t_data["Lot Size"]))
            if st.form_submit_button("UPDATE"):
                new_pips = calculate_pips(e_pair, e_entry, e_exit, e_action)
                new_profit = calculate_profit(new_pips, e_lot)
                update_trade(st.session_state.active_account, edit_idx, {"Pair": e_pair.upper(), "Type": e_action.capitalize(), "Entry": e_entry, "Exit": e_exit, "Lot Size": e_lot, "Pips": new_pips, "Profit": new_profit})
                st.success("UPDATED")
                st.rerun()
        
        if st.checkbox("Check to Enable Delete"):
            if st.button("DELETE PERMANENTLY", type="primary"):
                delete_trade(st.session_state.active_account, edit_idx)
                st.rerun()

st.sidebar.markdown("---")
with st.sidebar.expander("⚙️ SETTINGS"):
    st.markdown("### ACCOUNT SETTINGS")
    current_sb = get_starting_balance(st.session_state.active_account)
    sb_input = st.number_input("Starting Capital ($)", value=float(current_sb), step=100.0)
    if st.button("SAVE INITIAL BALANCE"):
        set_starting_balance(st.session_state.active_account, sb_input)
        st.session_state.starting_balance = sb_input  # FORCE REFRESH APP MEMORY
        st.success("BALANCE UPDATED")
        st.rerun()
    
    st.markdown("---")
    st.markdown("### 🏢 ACCOUNT MANAGEMENT")
    
    # Create Account
    new_acc_name = st.text_input("New Account Name", placeholder="e.g. Funding Challenge")
    if st.button("➕ CREATE ACCOUNT"):
        if new_acc_name:
            if create_account(new_acc_name):
                st.session_state.accounts = list_accounts()
                st.session_state.active_account = new_acc_name
                st.success(f"ACCOUNT '{new_acc_name}' CREATED")
                st.rerun()
            else:
                st.error("ACCOUNT ALREADY EXISTS")
        else:
            st.warning("ENTER A NAME First")
            
    # Delete Account
    st.markdown("<br>", unsafe_allow_html=True)
    if st.session_state.active_account != "Sheet1": # Don't delete the default
        if st.checkbox("Confirm Delete Active Account"):
            if st.button("🗑️ DELETE THIS ACCOUNT", type="primary"):
                delete_account(st.session_state.active_account)
                st.session_state.accounts = list_accounts()
                st.session_state.active_account = st.session_state.accounts[0]
                st.rerun()
    
    st.markdown("---")
    if st.button("🔄 REFRESH DATABASE"):
        st.cache_data.clear()
        st.session_state.accounts = list_accounts()
        st.rerun()

# --- Main Analytics Dashboard ---
start_bal = float(st.session_state.starting_balance)

if not df.empty:
    total_trades = len(df)
    total_profit = df["Profit"].sum()
    current_bal = start_bal + total_profit
    wins = len(df[df["Profit"] > 0])
    win_rate = (wins / total_trades) * 100 if total_trades > 0 else 0
    profit_factor = abs(df[df["Profit"] > 0]["Profit"].sum() / df[df["Profit"] < 0]["Profit"].sum()) if not df[df["Profit"] < 0].empty else 1.0
else:
    total_trades, total_profit, current_bal, win_rate, profit_factor = 0, 0, start_bal, 0, 0

# 💎 Top Metric Cards
m_col1, m_col2, m_col3 = st.columns(3)

with m_col1:
    st.markdown(f"""
        <div class="lumina-card">
            <div class="metric-container">
                <span class="metric-label">TOTAL PROFIT/LOSS</span>
                <span class="metric-value {'metric-pos' if total_profit >= 0 else 'metric-neg'}">
                    {'+$' if total_profit >= 0 else '-$'}{abs(total_profit):,.2f}
                </span>
            </div>
        </div>
    """, unsafe_allow_html=True)

with m_col2:
    st.markdown(f"""
        <div class="lumina-card">
            <div class="metric-container">
                <span class="metric-label">WIN RATE</span>
                <span class="metric-value">{win_rate:.1f}%</span>
            </div>
        </div>
    """, unsafe_allow_html=True)

with m_col3:
    st.markdown(f"""
        <div class="lumina-card">
            <div class="metric-container">
                <span class="metric-label">ACCOUNT BALANCE</span>
                <span class="metric-value">${current_bal:,.2f}</span>
            </div>
        </div>
    """, unsafe_allow_html=True)

# 📈 Performance Analytics (Bar Chart Monthly)
st.markdown("### Equity Curve Performance")
if not df.empty:
    df_chart = df.copy()
    df_chart['Timestamp'] = pd.to_datetime(df_chart['Timestamp'])
    df_chart['Month'] = df_chart['Timestamp'].dt.strftime('%b %Y')
    
    # Group by month and calculate profit
    df_monthly = df_chart.groupby('Month')['Profit'].sum().reset_index()
    # Ensure correct month ordering by converting back to dt for sorting
    df_monthly['sort_dt'] = pd.to_datetime(df_monthly['Month'])
    df_monthly = df_monthly.sort_values('sort_dt')
    
    with st.container():
        st.markdown('<div class="lumina-card">', unsafe_allow_html=True)
        fig_monthly = px.bar(
            df_monthly,
            x='Month',
            y='Profit',
            template="plotly_dark",
            color='Profit',
            color_continuous_scale=[[0, '#ef4444'], [0.5, '#ef4444'], [0.5, '#10b981'], [1, '#10b981']],
            labels={'Profit': 'Monthly P/L ($)'}
        )
        fig_monthly.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=10, r=10, t=20, b=10),
            coloraxis_showscale=False,
            xaxis=dict(showgrid=False, title=None),
            yaxis=dict(showgrid=True, gridcolor="rgba(255,255,255,0.05)", title=None)
        )
        st.plotly_chart(fig_monthly, use_container_width=True, theme=None)
        st.markdown('</div>', unsafe_allow_html=True)
else:
    st.info("Log your first trade to see performance data.")

# 📊 Recent Trade Log
st.markdown("### Recent Trade Log")
st.markdown('<div class="lumina-card">', unsafe_allow_html=True)
search_col1, search_col2 = st.columns([3, 1])
search_term = search_col1.text_input("Search pairs or type...", "", placeholder="FILTER TRADES...").upper()
if search_col2.button("➕ NEW TRADE", use_container_width=True):
    st.sidebar.markdown('<p style="color: #10b981; font-weight: bold;">USE THE "LOG NEW TRADE" SECTION IN SIDEBAR</p>', unsafe_allow_html=True)

if not df.empty:
    filtered_df = df[df["Pair"].str.contains(search_term) | df["Type"].str.contains(search_term)] if search_term else df
    display_df = filtered_df.sort_values(by="Timestamp", ascending=False).head(10)
    
    # Render a cleaner dataframe
    st.dataframe(
        display_df[["Timestamp", "Pair", "Type", "Entry", "Exit", "Profit"]], 
        use_container_width=True,
        hide_index=True
    )
else:
    st.write("No trades found.")
st.markdown('</div>', unsafe_allow_html=True)
