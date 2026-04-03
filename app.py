import streamlit as st
import pandas as pd
import plotly.express as px
import os
import uuid
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

# --- UI Components (Dialogs) ---
@st.dialog("LOG NEW TRADE", width="small")
def show_trade_dialog(account_name):
    with st.form("trade_form", clear_on_submit=True):
        pair = st.text_input("Pair (e.g. EUR/USD)", value="EUR/USD")
        trade_type = st.selectbox("Action", ["Buy", "Sell"])
        c1, c2 = st.columns(2)
        entry_price = c1.number_input("Entry", format="%.5f", step=0.0001)
        exit_price = c2.number_input("Exit", format="%.5f", step=0.0001)
        lot_size = st.number_input("Lot Size", min_value=0.01, value=1.0, step=0.1)
        notes = st.text_area("Notes")
        uploaded_file = st.file_uploader("Attach Screenshot", type=['png', 'jpg', 'jpeg'])
        
        if st.form_submit_button("COMMIT TRADE", use_container_width=True):
            img_path = None
            if uploaded_file is not None:
                # Create screenshots dir if missing
                os.makedirs("screenshots", exist_ok=True)
                # Generate unique filename
                file_ext = uploaded_file.name.split('.')[-1]
                file_name = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}.{file_ext}"
                img_path = os.path.join("screenshots", file_name)
                # Save file locally
                with open(img_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())
            
            pips = calculate_pips(pair, entry_price, exit_price, trade_type)
            profit = calculate_profit(pips, lot_size)
            add_trade(account_name, pair, trade_type, entry_price, exit_price, lot_size, pips, profit, notes, image_path=img_path)
            st.success("TRADE RECORDED")
            st.rerun()

# --- Data Initialization ---
if "accounts" not in st.session_state:
    st.session_state.accounts = list_accounts()

if "active_account" not in st.session_state:
    st.session_state.active_account = st.session_state.accounts[0]

if "starting_balance" not in st.session_state:
    st.session_state.starting_balance = get_starting_balance(st.session_state.active_account)

# --- Sidebar Data Fetch ---
df = load_trades(st.session_state.active_account)

# --- App Header (Ozymandias Style) ---
h_col1, h_col2 = st.columns([2, 1])
with h_col1:
    st.markdown(f"""
        <div style="display: flex; align-items: center; gap: 20px;">
            <h1 style="margin: 0; padding: 0;">Ozymandias Journal</h1>
            <div class="status-badge">
                <div class="status-dot"></div>
                OZY TERMINAL
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

# Quick Actions (Sidebar Management Only)
# LOG NEW TRADE REMOVED FROM SIDEBAR PER REQUEST

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
            e_img = st.file_uploader("Update/Add Screenshot", type=['png', 'jpg', 'jpeg'], key=f"edit_img_{edit_idx}")
            
            if st.form_submit_button("UPDATE"):
                new_pips = calculate_pips(e_pair, e_entry, e_exit, e_action)
                new_profit = calculate_profit(new_pips, e_lot)
                update_fields = {
                    "Pair": e_pair.upper(), 
                    "Type": e_action.capitalize(), 
                    "Entry": e_entry, 
                    "Exit": e_exit, 
                    "Lot Size": e_lot, 
                    "Pips": new_pips, 
                    "Profit": new_profit
                }
                
                if e_img:
                    # Save the new screenshot
                    os.makedirs("screenshots", exist_ok=True)
                    file_ext = e_img.name.split('.')[-1]
                    file_name = f"update_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:4]}.{file_ext}"
                    img_path = os.path.join("screenshots", file_name)
                    with open(img_path, "wb") as f:
                        f.write(e_img.getbuffer())
                    update_fields["Image"] = img_path
                
                update_trade(st.session_state.active_account, edit_idx, update_fields)
                st.success("UPDATED")
                st.rerun()
        
        if st.checkbox("Check to Enable Delete"):
            if st.button("DELETE PERMANENTLY", type="primary"):
                delete_trade(st.session_state.active_account, edit_idx)
                st.rerun()

st.sidebar.markdown("---")
st.sidebar.markdown("---")
with st.sidebar.expander("💰 BALANCE SETTINGS"):
    current_sb = get_starting_balance(st.session_state.active_account)
    sb_input = st.number_input(
        "Starting Capital ($)", 
        value=float(current_sb), 
        step=100.0,
        key=f"sb_input_{st.session_state.active_account}"
    )
    if st.button("SAVE INITIAL BALANCE"):
        set_starting_balance(st.session_state.active_account, sb_input)
        st.session_state.starting_balance = sb_input
        st.success("BALANCE UPDATED")
        st.rerun()

with st.sidebar.expander("🏢 CREATE ACCOUNT"):
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
            st.warning("ENTER A NAME")

with st.sidebar.expander("🗑️ DELETE ACCOUNT"):
    delete_options = [acc for acc in st.session_state.accounts if acc != "Sheet1"]
    if delete_options:
        to_delete = st.selectbox("SELECT ACCOUNT TO REMOVE", delete_options)
        if st.button("🗑️ DELETE PERMANENTLY", type="primary", use_container_width=True):
            delete_account(to_delete)
            st.session_state.accounts = list_accounts()
            if st.session_state.active_account == to_delete:
                st.session_state.active_account = st.session_state.accounts[0]
            st.success(f"ACCOUNT '{to_delete}' DELETED")
            st.rerun()
    else:
        st.info("NO ADDITIONAL ACCOUNTS")

if st.sidebar.button("🔄 REFRESH DATABASE", use_container_width=True):
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

# 📈 Performance Analytics (Institutional Trading Growth)
st.markdown("### Trading Growth Curve")
if not df.empty:
    df_curve = df.copy()
    df_curve['Timestamp'] = pd.to_datetime(df_curve['Timestamp'])
    df_curve = df_curve.sort_values('Timestamp')
    
    # Calculate Cumulative Balance
    df_curve['Cumulative Profit'] = df_curve['Profit'].cumsum()
    df_curve['Balance'] = start_bal + df_curve['Cumulative Profit']
    
    # Add a starting point row at the exact starting capital
    first_row = pd.DataFrame([{
        'Timestamp': df_curve['Timestamp'].min() - pd.Timedelta(minutes=5),
        'Balance': start_bal,
        'Profit': 0
    }])
    df_curve = pd.concat([first_row, df_curve], ignore_index=True)
    
    # Formatting X-axis for that "Jan 31" look
    df_curve['DateStr'] = df_curve['Timestamp'].dt.strftime('%b %d')
    
    line_color = "#10b981" if current_bal >= start_bal else "#ef4444"
    fill_color = "rgba(16, 185, 129, 0.05)" if current_bal >= start_bal else "rgba(239, 68, 68, 0.05)"
    
    with st.container():
        st.markdown('<div class="lumina-card">', unsafe_allow_html=True)
        import plotly.graph_objects as go
        
        fig_growth = go.Figure()
        
        # Add the professional Spline Curve
        fig_growth.add_trace(go.Scatter(
            x=df_curve['Timestamp'],
            y=df_curve['Balance'],
            mode='lines+markers',
            name='Account Balance',
            line=dict(color=line_color, width=3, shape='spline', smoothing=1.3, dash='dash'),
            marker=dict(size=8, color=line_color, symbol='circle', line=dict(color="white", width=1)),
            fill='tozeroy', 
            fillcolor=fill_color,
            hovertemplate="<b>Date:</b> %{x}<br><b>Balance:</b> $%{y:,.2f}<extra></extra>"
        ))
        
        # Add the institutional Baseline
        fig_growth.add_hline(
            y=start_bal, 
            line_dash="dot", 
            line_color="rgba(255,255,255,0.15)",
            annotation_text="STARTING POINT", 
            annotation_position="bottom right"
        )
        
        fig_growth.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=60, r=20, t=20, b=30), # Increased margins for labels
            xaxis=dict(
                showgrid=True, 
                gridcolor="rgba(255,255,255,0.05)", 
                title=None, 
                color="#cbd5e1", # Brighter slate
                tickfont=dict(size=10),
                tickformat="%b %d"
            ),
            yaxis=dict(
                showgrid=True, 
                gridcolor="rgba(255,255,255,0.05)", 
                title=None, 
                color="#cbd5e1", # Brighter slate
                tickfont=dict(size=10),
                tickprefix="$",
                tickformat=",."
            ),
            showlegend=False,
            height=380
        )
        
        st.plotly_chart(fig_growth, use_container_width=True, theme=None)
        st.markdown('</div>', unsafe_allow_html=True)
else:
    st.info("Log your first trade to see the Growth Curve.")

# 📊 Recent Trade Log
st.markdown("### Recent Trade Log")
st.markdown('<div class="lumina-card">', unsafe_allow_html=True)
search_col1, search_col2 = st.columns([3, 1])
# Using label_visibility="collapsed" ensures perfect vertical alignment with the button
search_term = search_col1.text_input("Search", "", placeholder="FILTER TRADES...", label_visibility="collapsed").upper()
if search_col2.button("➕ NEW TRADE", use_container_width=True):
    show_trade_dialog(st.session_state.active_account)

if not df.empty:
    filtered_df = df[df["Pair"].str.contains(search_term) | df["Type"].str.contains(search_term)] if search_term else df
    display_df = filtered_df.sort_values(by="Timestamp", ascending=False).head(10)
    
    # Render table (excluding the raw Image path for clean look)
    st.dataframe(
        display_df[["Timestamp", "Pair", "Type", "Entry", "Exit", "Profit"]], 
        use_container_width=True,
        hide_index=True
    )
    
    # 🖼️ Screenshot Viewer Section
    st.markdown("---")
    with st.expander("🖼️ VIEW SCREENSHOTS"):
        # Filter only trades that have an image
        trades_with_img = display_df[display_df["Image"].notna()]
        if not trades_with_img.empty:
            img_options = [f"{row['Timestamp']} - {row['Pair']}" for _, row in trades_with_img.iterrows()]
            selected_img = st.selectbox("Select Trade to View Screenshot", img_options)
            
            # Find the path for the selected trade
            selected_timestamp = selected_img.split(" - ")[0]
            img_path = trades_with_img[trades_with_img["Timestamp"] == selected_timestamp]["Image"].values[0]
            
            if os.path.exists(img_path):
                st.image(img_path, use_container_width=True, caption=f"Analysis for {selected_img}")
            else:
                st.error("Screenshot file not found locally.")
        else:
            st.info("No screenshots available for recent trades.")
else:
    st.write("No trades found.")
st.markdown('</div>', unsafe_allow_html=True)
