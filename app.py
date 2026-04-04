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
def apply_theme():
    if "theme" not in st.session_state:
        st.session_state.theme = "Dark"
        
    theme_css = ""
    if st.session_state.theme == "Light":
        theme_css = """
        <style>
        :root {
            --bg-main: #f8fafc;
            --sidebar-bg: #f1f5f9;
            --card-bg: #ffffff;
            --card-border: rgba(0, 0, 0, 0.1);
            --text-dim: #64748b;
            --text-main: #0f172a;
            --hover-glow: rgba(16, 185, 129, 0.2);
        }
        [data-testid="stSidebar"] { border-right: 1px solid rgba(0,0,0,0.1) !important; }
        .stDataFrame { border: 1px solid rgba(0,0,0,0.1) !important; }
        </style>
        """
    
    with open("styles.css") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)
    if theme_css:
        st.markdown(theme_css, unsafe_allow_html=True)

apply_theme()

# --- UI Components (Dialogs) ---
@st.dialog("LOG NEW TRADE", width="small")
def show_trade_dialog(account_name):
    with st.form("trade_form", clear_on_submit=True):
        pair = st.text_input("Pair (e.g. EUR/USD)", value="EUR/USD")
        trade_type = st.selectbox("Action", ["Buy", "Sell"])
        
        c1, c2 = st.columns(2)
        entry_price = c1.number_input("Entry Price", format="%.5f", step=0.0001)
        exit_price = c2.number_input("Exit Price (Optional)", value=0.0, format="%.5f", step=0.0001, help="Leave at 0.0 if the trade is still OPEN.")
        
        d1, d2 = st.columns(2)
        entry_date = d1.date_input("Entry Date", datetime.now())
        entry_time = d1.time_input("Entry Time", datetime.now().time())
        
        exit_date = None
        is_open = exit_price == 0.0
        
        if not is_open:
            exit_date_val = d2.date_input("Exit Date", datetime.now())
            exit_time_val = d2.time_input("Exit Time", datetime.now().time())
            exit_date = datetime.combine(exit_date_val, exit_time_val).strftime("%Y-%m-%d %H:%M:%S")

        entry_dt = datetime.combine(entry_date, entry_time).strftime("%Y-%m-%d %H:%M:%S")
        
        lot_size = st.number_input("Lot Size", min_value=0.01, value=1.0, step=0.1)
        notes = st.text_area("Notes")
        uploaded_file = st.file_uploader("Attach Screenshot", type=['png', 'jpg', 'jpeg'])
        
        if st.form_submit_button("COMMIT TRADE", use_container_width=True):
            img_path = None
            if uploaded_file is not None:
                os.makedirs("screenshots", exist_ok=True)
                file_ext = uploaded_file.name.split('.')[-1]
                file_name = f"{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:6]}.{file_ext}"
                img_path = os.path.join("screenshots", file_name)
                with open(img_path, "wb") as f:
                    f.write(uploaded_file.getbuffer())
            
            pips = 0.0
            profit = 0.0
            if not is_open:
                pips = calculate_pips(pair, entry_price, exit_price, trade_type)
                profit = calculate_profit(pips, lot_size)
            
            # Save to DB
            add_trade(
                account_name, pair, trade_type, entry_price, 
                None if is_open else exit_price, 
                lot_size, pips, profit, notes, 
                image_path=img_path,
                entry_date=entry_dt,
                exit_date=exit_date
            )
            st.success("OPEN POSITION LOGGED" if is_open else "TRADE FINALIZED")
            st.rerun()

@st.dialog("EDIT TRADE", width="small")
def show_edit_dialog(t_data, edit_idx):
    with st.form(f"edit_form_dialog_{edit_idx}"):
        e_pair = st.text_input("Pair", value=t_data["Pair"])
        e_action = st.selectbox("Action", ["Buy", "Sell"], index=0 if t_data["Type"] == "Buy" else 1)
        
        c1, c2 = st.columns(2)
        e_entry = c1.number_input("Entry", value=float(t_data["Entry"]), format="%.5f")
        
        # Handle potentially empty exit price
        exit_val = float(t_data["Exit"]) if pd.notna(t_data["Exit"]) and t_data["Exit"] != 0 else 0.0
        e_exit = c2.number_input("Exit", value=exit_val, format="%.5f", help="Set to 0.0 to keep OPEN.")
        
        e_lot = st.number_input("Lots", value=float(t_data["Lot Size"]))
        
        e_entry_date = st.text_input("Entry Date", value=t_data["Entry Date"])
        e_exit_date = st.text_input("Exit Date", value=str(t_data["Exit Date"]) if pd.notna(t_data["Exit Date"]) else "")
        
        e_notes = st.text_area("Notes", value=t_data["Notes"] if pd.notna(t_data["Notes"]) else "")
        e_img = st.file_uploader("Update Screenshot", type=['png', 'jpg', 'jpeg'], key=f"edit_img_dialog_{edit_idx}")
        
        if st.form_submit_button("SAVE CHANGES", use_container_width=True):
            is_closing = e_exit != 0.0 and (pd.isna(t_data["Exit"]) or t_data["Exit"] == 0)
            
            new_pips = 0.0
            new_profit = 0.0
            if e_exit != 0.0:
                new_pips = calculate_pips(e_pair, e_entry, e_exit, e_action)
                new_profit = calculate_profit(new_pips, e_lot)
            
            update_fields = {
                "Pair": e_pair.upper(), 
                "Type": e_action.capitalize(), 
                "Entry": e_entry, 
                "Exit": None if e_exit == 0.0 else e_exit, 
                "Lot Size": e_lot, 
                "Pips": new_pips, 
                "Profit": new_profit,
                "Entry Date": e_entry_date,
                "Notes": e_notes
            }
            
            # If finalizing an open trade, set exit date to now unless manually edited
            if is_closing and not e_exit_date:
                update_fields["Exit Date"] = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            elif e_exit_date:
                update_fields["Exit Date"] = e_exit_date
            
            if e_img:
                os.makedirs("screenshots", exist_ok=True)
                file_ext = e_img.name.split('.')[-1]
                file_name = f"update_{datetime.now().strftime('%Y%m%d_%H%M%S')}_{uuid.uuid4().hex[:4]}.{file_ext}"
                img_path = os.path.join("screenshots", file_name)
                with open(img_path, "wb") as f:
                    f.write(e_img.getbuffer())
                update_fields["Image"] = img_path
            
            update_trade(st.session_state.active_account, edit_idx, update_fields)
            st.success("UPDATED" if not is_closing else "POSITION CLOSED")
            st.rerun()

@st.dialog("DELETE TRADE", width="small")
def show_delete_dialog(t_data, edit_idx):
    st.warning(f"Are you sure you want to delete this trade: **{t_data['Pair']}** on **{t_data['Entry Date']}**?")
    st.info("This action cannot be undone.")
    c1, c2 = st.columns(2)
    if c1.button("CANCEL", use_container_width=True):
        st.rerun()
    if c2.button("DELETE PERMANENTLY", type="primary", use_container_width=True):
        delete_trade(st.session_state.active_account, edit_idx)
        st.success("TRADE DELETED")
        st.rerun()

# --- Data Initialization ---
if "accounts" not in st.session_state:
    st.session_state.accounts = list_accounts()

if "active_account" not in st.session_state:
    st.session_state.active_account = st.session_state.accounts[0]

if "starting_balance" not in st.session_state:
    st.session_state.starting_balance = get_starting_balance(st.session_state.active_account)

if "log_page" not in st.session_state:
    st.session_state.log_page = 0

# --- Sidebar Data Fetch ---
df = load_trades(st.session_state.active_account)

# --- App Header (Ozymandias Style) ---
h_col1, h_col2 = st.columns([2, 1])
with h_col1:
    st.markdown(f"""
        <div style="display: flex; align-items: center; gap: 20px;">
            <h1 style="margin: 0; padding: 0;">Ozymandias Journal</h1>
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

# Theme Toggle
t1, t2 = st.sidebar.columns([3, 1])
t1.markdown(f"**MODE: {st.session_state.theme.upper()}**")
if t2.button("🌓", use_container_width=True):
    st.session_state.theme = "Light" if st.session_state.theme == "Dark" else "Dark"
    st.rerun()

st.sidebar.markdown("<br>", unsafe_allow_html=True)

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

# --- Main Analytics Dashboard (Closed Trades Only) ---
start_bal = float(st.session_state.starting_balance)

# Filter for metrics
closed_df = df[df["Exit"].notna() & (df["Exit"] != 0)]
open_df = df[df["Exit"].isna() | (df["Exit"] == 0)]

if not open_df.empty:
    st.markdown("### 🎯 ACTIVE SWINGS")
    for idx, row in open_df.iterrows():
        with st.container():
            st.markdown(f"""
                <div class="lumina-card" style="border-left: 4px solid var(--primary); margin-bottom: 10px; padding: 15px;">
                    <div style="display: flex; justify-content: space-between; align-items: center;">
                        <div>
                            <span style="color: var(--primary); font-weight: 700;">{row['Pair']}</span>
                            <span style="color: var(--text-dim); margin-left: 10px;">{row['Type']} @ {row['Entry']:.5f}</span>
                        </div>
                        <div style="text-align: right;">
                            <span style="color: var(--text-dim); font-size: 0.8rem;">ENTRY: {row['Entry Date']}</span>
                        </div>
                    </div>
                </div>
            """, unsafe_allow_html=True)
    st.markdown("<br>", unsafe_allow_html=True)

if not closed_df.empty:
    total_trades = len(closed_df)
    total_profit = closed_df["Profit"].sum()
    current_bal = start_bal + total_profit
    wins = len(closed_df[closed_df["Profit"] > 0])
    win_rate = (wins / total_trades) * 100 if total_trades > 0 else 0
else:
    total_trades, total_profit, current_bal, win_rate = 0, 0, start_bal, 0

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
if not closed_df.empty:
    df_curve = closed_df.copy()
    df_curve['Timestamp'] = pd.to_datetime(df_curve['Entry Date'])
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
    
    # Theme-Aware Chart Colors
    is_dark = st.session_state.theme == "Dark"
    chart_text = "#cbd5e1" if is_dark else "#475569"
    chart_grid = "rgba(255,255,255,0.05)" if is_dark else "rgba(0,0,0,0.05)"
    baseline_color = "rgba(255,255,255,0.15)" if is_dark else "rgba(0,0,0,0.2)"
    marker_border = "white" if is_dark else "#f8fafc"
    
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
            marker=dict(size=8, color=line_color, symbol='circle', line=dict(color=marker_border, width=1)),
            fill='tozeroy', 
            fillcolor=fill_color,
            hovertemplate="<b>Date:</b> %{x}<br><b>Balance:</b> $%{y:,.2f}<extra></extra>"
        ))
        
        # Add the institutional Baseline
        fig_growth.add_hline(
            y=start_bal, 
            line_dash="dot", 
            line_color=baseline_color,
            annotation_text="STARTING POINT", 
            annotation_position="bottom right"
        )
        
        fig_growth.update_layout(
            paper_bgcolor="rgba(0,0,0,0)",
            plot_bgcolor="rgba(0,0,0,0)",
            margin=dict(l=60, r=20, t=20, b=30), # Increased margins for labels
            xaxis=dict(
                showgrid=True, 
                gridcolor=chart_grid, 
                title=None, 
                color=chart_text, 
                tickfont=dict(size=10),
                tickformat="%b %d"
            ),
            yaxis=dict(
                showgrid=True, 
                gridcolor=chart_grid, 
                title=None, 
                color=chart_text, 
                tickfont=dict(size=10),
                tickprefix="$",
                tickformat=",."
            ),
            showlegend=False,
            height=380,
            dragmode='pan' # Default to panning mode (like MT5/TradingView)
        )
        
        # Enable Scroll Zoom and Hide the "Cluster" of buttons (Modebar)
        st.plotly_chart(
            fig_growth, 
            use_container_width=True, 
            theme=None, 
            config={'scrollZoom': True, 'displayModeBar': False}
        )
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
    
    # Pagination Setup
    PAGE_SIZE = 10
    total_trades = len(filtered_df)
    max_pages = max(1, (total_trades + PAGE_SIZE - 1) // PAGE_SIZE)
    
    if st.session_state.log_page >= max_pages:
        st.session_state.log_page = max_pages - 1
    
    start_idx = st.session_state.log_page * PAGE_SIZE
    end_idx = min(start_idx + PAGE_SIZE, total_trades)
    
    # Sort and slice for display
    display_df = filtered_df.sort_values(by="Entry Date", ascending=False)
    page_df = display_df.iloc[start_idx:end_idx].copy()
    
    # Custom Table Header
    h_col1, h_col2, h_col3, h_col4, h_col5, h_col6, h_col7 = st.columns([1.5, 1.5, 1, 1, 1, 1.2, 1.5])
    h_col1.markdown("**DATE / TIME**")
    h_col2.markdown("**PAIR**")
    h_col3.markdown("**TYPE**")
    h_col4.markdown("**ENTRY**")
    h_col5.markdown("**EXIT**")
    h_col6.markdown("**PROFIT**")
    h_col7.markdown("**ACTIONS**")
    st.markdown("<hr style='margin: 5px 0; opacity: 0.1;'>", unsafe_allow_html=True)
    
    # Render Rows
    for idx, row in page_df.iterrows():
        r_col1, r_col2, r_col3, r_col4, r_col5, r_col6, r_col7 = st.columns([1.5, 1.5, 1, 1, 1, 1.2, 1.5])
        
        # Format date for cleaner look
        dt_str = row["Entry Date"].split(" ")[0] if " " in str(row["Entry Date"]) else str(row["Entry Date"])
        r_col1.write(dt_str)
        
        r_col2.write(f"**{row['Pair']}**")
        
        # Type Badge
        type_color = "var(--primary)" if row["Type"] == "Buy" else "var(--secondary)"
        r_col3.markdown(f"<span style='color: {type_color}; font-weight: 700;'>{row['Type']}</span>", unsafe_allow_html=True)
        
        r_col4.write(f"{row['Entry']:.5f}")
        exit_val = f"{row['Exit']:.5f}" if pd.notna(row['Exit']) and row['Exit'] != 0 else "---"
        r_col5.write(exit_val)
        
        # Profit Status
        if pd.notna(row['Exit']) and row['Exit'] != 0:
            p_color = "metric-pos" if row['Profit'] >= 0 else "metric-neg"
            r_col6.markdown(f"<span class='{p_color}' style='font-weight: 600;'>${row['Profit']:,.2f}</span>", unsafe_allow_html=True)
        else:
            r_col6.markdown("<span style='color: #fbbf24; font-weight: 600;'>🟢 OPEN</span>", unsafe_allow_html=True)
            
        # Action Buttons
        btn_col1, btn_col2 = r_col7.columns(2)
        if btn_col1.button("📝", key=f"edit_btn_{idx}", help="Edit Trade", use_container_width=True):
            show_edit_dialog(row, idx)
        if btn_col2.button("🗑️", key=f"del_btn_{idx}", help="Delete Trade", use_container_width=True):
            show_delete_dialog(row, idx)
        
        st.markdown("<hr style='margin: 5px 0; opacity: 0.05;'>", unsafe_allow_html=True)

    # Pagination Controls
    st.markdown("<br>", unsafe_allow_html=True)
    p_col1, p_col2, p_col3 = st.columns([1, 2, 1])
    with p_col1:
        if st.button("PREVIOUS", disabled=st.session_state.log_page == 0, use_container_width=True):
            st.session_state.log_page -= 1
            st.rerun()
    with p_col2:
        st.markdown(f"<div style='text-align: center; color: var(--text-dim); padding-top: 5px;'>Page {st.session_state.log_page + 1} of {max_pages}</div>", unsafe_allow_html=True)
    with p_col3:
        if st.button("NEXT", disabled=st.session_state.log_page >= max_pages - 1, use_container_width=True):
            st.session_state.log_page += 1
            st.rerun()
    
    # 🖼️ Screenshot Viewer Section
    st.markdown("---")
    with st.expander("🖼️ VIEW SCREENSHOTS"):
        # Filter only trades that have an image
        trades_with_img = display_df[display_df["Image"].notna()]
        if not trades_with_img.empty:
            img_options = [f"{row['Entry Date']} - {row['Pair']}" for _, row in trades_with_img.iterrows()]
            selected_img = st.selectbox("Select Trade to View Screenshot", img_options)
            
            # Find the path for the selected trade
            selected_date = selected_img.split(" - ")[0]
            img_path = trades_with_img[trades_with_img["Entry Date"] == selected_date]["Image"].values[0]
            
            if os.path.exists(img_path):
                st.image(img_path, use_container_width=True, caption=f"Analysis for {selected_img}")
            else:
                st.error("Screenshot file not found locally.")
        else:
            st.info("No screenshots available for recent trades.")
else:
    st.write("No trades found.")
st.markdown('</div>', unsafe_allow_html=True)
