"""
APEX INDIA — Streamlit Live Dashboard
========================================
Real-time trading dashboard with live P&L, positions,
signals, risk exposure, and backtest analytics.

Launch:
    streamlit run apex_india/dashboard/app.py
"""

import sys
from pathlib import Path

PROJECT_ROOT = str(Path(__file__).resolve().parent.parent.parent)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)

from datetime import datetime, time as dtime
from typing import Any, Dict

import numpy as np
import pandas as pd
import pytz
import streamlit as st
import plotly.graph_objects as go
from plotly.subplots import make_subplots

from apex_india.utils.constants import MARKET_TIMEZONE
from apex_india.dashboard.charts import ChartBuilder

IST = pytz.timezone(MARKET_TIMEZONE)

# ═══════════════════════════════════════════════════════════════
#  PAGE CONFIG
# ═══════════════════════════════════════════════════════════════

st.set_page_config(
    page_title="APEX INDIA — Trading Dashboard",
    page_icon="📊",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ═══════════════════════════════════════════════════════════════
#  CUSTOM CSS
# ═══════════════════════════════════════════════════════════════

st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700;800&display=swap');
    @import url('https://fonts.googleapis.com/css2?family=JetBrains+Mono:wght@400;600&display=swap');

    :root {
        --bg-primary: #0A0E17;
        --bg-secondary: #111827;
        --bg-card: #1A2332;
        --bg-card-hover: #1F2937;
        --border: #2A3441;
        --text-primary: #F1F5F9;
        --text-secondary: #94A3B8;
        --accent-blue: #3B82F6;
        --accent-purple: #8B5CF6;
        --accent-green: #10B981;
        --accent-red: #EF4444;
        --accent-yellow: #F59E0B;
        --accent-cyan: #06B6D4;
        --gradient-1: linear-gradient(135deg, #3B82F6, #8B5CF6);
        --gradient-2: linear-gradient(135deg, #10B981, #06B6D4);
        --gradient-3: linear-gradient(135deg, #F59E0B, #EF4444);
    }

    .stApp {
        background: var(--bg-primary);
        font-family: 'Inter', -apple-system, sans-serif;
    }

    div[data-testid="stSidebar"] {
        background: linear-gradient(180deg, #0A0E17 0%, #111827 100%);
        border-right: 1px solid var(--border);
    }

    .main-header {
        background: linear-gradient(135deg, rgba(59,130,246,0.1), rgba(139,92,246,0.1));
        border: 1px solid rgba(59,130,246,0.2);
        border-radius: 16px;
        padding: 24px 32px;
        margin-bottom: 24px;
    }

    .main-title {
        background: var(--gradient-1);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 36px;
        font-weight: 800;
        letter-spacing: -0.5px;
        margin: 0;
    }

    .main-subtitle {
        color: var(--text-secondary);
        font-size: 14px;
        margin-top: 4px;
    }

    .metric-card {
        background: var(--bg-card);
        border: 1px solid var(--border);
        border-radius: 16px;
        padding: 20px 24px;
        transition: all 0.3s ease;
        position: relative;
        overflow: hidden;
    }
    .metric-card::before {
        content: '';
        position: absolute;
        top: 0; left: 0; right: 0;
        height: 3px;
        border-radius: 16px 16px 0 0;
    }
    .metric-card:hover {
        border-color: rgba(59,130,246,0.4);
        transform: translateY(-2px);
        box-shadow: 0 8px 25px rgba(0,0,0,0.3);
    }

    .metric-card.green::before { background: var(--gradient-2); }
    .metric-card.red::before { background: var(--gradient-3); }
    .metric-card.blue::before { background: var(--gradient-1); }
    .metric-card.purple::before { background: linear-gradient(135deg, #8B5CF6, #EC4899); }

    .metric-label {
        color: var(--text-secondary);
        font-size: 12px;
        font-weight: 600;
        text-transform: uppercase;
        letter-spacing: 1.5px;
        margin-bottom: 8px;
    }

    .metric-value {
        font-family: 'JetBrains Mono', monospace;
        font-size: 28px;
        font-weight: 700;
        line-height: 1.2;
    }

    .metric-delta {
        font-size: 13px;
        margin-top: 6px;
        font-weight: 500;
    }

    .positive { color: var(--accent-green); }
    .negative { color: var(--accent-red); }
    .neutral  { color: var(--accent-blue); }
    .warning  { color: var(--accent-yellow); }
    .purple   { color: var(--accent-purple); }

    .status-badge {
        display: inline-flex;
        align-items: center;
        gap: 6px;
        padding: 6px 14px;
        border-radius: 24px;
        font-size: 13px;
        font-weight: 600;
    }
    .badge-active {
        background: rgba(16,185,129,0.12);
        color: var(--accent-green);
        border: 1px solid rgba(16,185,129,0.3);
    }
    .badge-closed {
        background: rgba(239,68,68,0.12);
        color: var(--accent-red);
        border: 1px solid rgba(239,68,68,0.3);
    }
    .badge-paper {
        background: rgba(245,158,11,0.12);
        color: var(--accent-yellow);
        border: 1px solid rgba(245,158,11,0.3);
    }

    .section-title {
        color: var(--text-primary);
        font-size: 20px;
        font-weight: 700;
        margin: 16px 0 12px 0;
        display: flex;
        align-items: center;
        gap: 8px;
    }

    .trade-row {
        background: var(--bg-card);
        border: 1px solid var(--border);
        border-radius: 12px;
        padding: 16px 20px;
        margin-bottom: 8px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        transition: border-color 0.2s;
    }
    .trade-row:hover {
        border-color: var(--accent-blue);
    }

    .activity-item {
        padding: 10px 16px;
        border-left: 3px solid var(--border);
        margin-bottom: 8px;
        font-size: 14px;
        color: var(--text-secondary);
        transition: border-color 0.2s;
    }
    .activity-item:hover {
        border-left-color: var(--accent-blue);
        color: var(--text-primary);
    }

    .risk-bar {
        height: 8px;
        border-radius: 4px;
        background: var(--bg-secondary);
        overflow: hidden;
        margin-top: 6px;
    }
    .risk-bar-fill {
        height: 100%;
        border-radius: 4px;
        transition: width 0.5s ease;
    }

    /* Hide streamlit defaults */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}

    div[data-testid="stMetricValue"] {
        font-family: 'JetBrains Mono', monospace;
    }

    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
    }
    .stTabs [data-baseweb="tab"] {
        background: var(--bg-card);
        border-radius: 8px;
        border: 1px solid var(--border);
        color: var(--text-secondary);
        padding: 8px 20px;
    }
    .stTabs [aria-selected="true"] {
        background: rgba(59,130,246,0.15);
        border-color: var(--accent-blue);
        color: var(--accent-blue);
    }
</style>
""", unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════
#  SESSION STATE (simulated system state)
# ═══════════════════════════════════════════════════════════════

if "initialized" not in st.session_state:
    st.session_state.initialized = True
    st.session_state.capital = 1_000_000
    st.session_state.equity = 1_004_240
    st.session_state.day_pnl = 4_240
    st.session_state.positions = [
        {"symbol": "RELIANCE", "dir": "LONG", "qty": 50, "entry": 1500,
         "current": 1548, "pnl": 2400, "strategy": "Trend Rider"},
        {"symbol": "HDFCBANK", "dir": "LONG", "qty": 30, "entry": 1600,
         "current": 1625, "pnl": 750, "strategy": "ORB"},
        {"symbol": "INFY", "dir": "SHORT", "qty": 20, "entry": 1800,
         "current": 1775, "pnl": 500, "strategy": "VWAP MR"},
    ]
    st.session_state.trades_today = [
        {"time": "09:32", "action": "BUY", "symbol": "RELIANCE", "qty": 50,
         "price": 1500, "strategy": "Trend Rider"},
        {"time": "09:45", "action": "BUY", "symbol": "HDFCBANK", "qty": 30,
         "price": 1600, "strategy": "ORB"},
        {"time": "10:15", "action": "SELL", "symbol": "INFY", "qty": 20,
         "price": 1800, "strategy": "VWAP MR"},
        {"time": "11:30", "action": "EXIT", "symbol": "TCS", "qty": 15,
         "price": 3550, "strategy": "Trend Rider", "pnl": 1740},
    ]


# ═══════════════════════════════════════════════════════════════
#  HELPERS
# ═══════════════════════════════════════════════════════════════

def metric_card(label, value, delta="", card_class="blue", value_class="neutral"):
    st.markdown(f"""
    <div class="metric-card {card_class}">
        <div class="metric-label">{label}</div>
        <div class="metric-value {value_class}">{value}</div>
        {f'<div class="metric-delta {value_class}">{delta}</div>' if delta else ''}
    </div>
    """, unsafe_allow_html=True)


def risk_bar(label, current, limit, color="#3B82F6"):
    pct = min(current / limit * 100, 100)
    danger = pct > 80
    bar_color = "#EF4444" if danger else color
    st.markdown(f"""
    <div style="margin-bottom:12px;">
        <div style="display:flex;justify-content:space-between;margin-bottom:4px;">
            <span style="color:#94A3B8;font-size:13px;">{label}</span>
            <span style="color:{'#EF4444' if danger else '#F1F5F9'};font-size:13px;font-weight:600;font-family:'JetBrains Mono';">
                {current:.1f}% / {limit:.1f}%
            </span>
        </div>
        <div class="risk-bar">
            <div class="risk-bar-fill" style="width:{pct:.0f}%;background:{bar_color};"></div>
        </div>
    </div>
    """, unsafe_allow_html=True)


# ═══════════════════════════════════════════════════════════════
#  SIDEBAR
# ═══════════════════════════════════════════════════════════════

with st.sidebar:
    st.markdown('<p class="main-title" style="font-size:28px;">APEX INDIA</p>',
                unsafe_allow_html=True)
    st.markdown('<p class="main-subtitle">Autonomous Quantitative Trading</p>',
                unsafe_allow_html=True)

    st.markdown("---")

    now = datetime.now(IST)
    st.markdown(f"**🕐 {now.strftime('%H:%M:%S')} IST**")
    st.markdown(f"📅 {now.strftime('%d %b %Y, %A')}")

    market_open = now.weekday() < 5 and dtime(9, 15) <= now.time() <= dtime(15, 30)
    if market_open:
        st.markdown('<span class="status-badge badge-active">● MARKET OPEN</span>',
                     unsafe_allow_html=True)
    else:
        st.markdown('<span class="status-badge badge-closed">○ MARKET CLOSED</span>',
                     unsafe_allow_html=True)

    st.markdown("---")

    page = st.radio(
        "Navigation", 
        ["📈 Live Trading", "💼 Portfolio", "🎯 Signals", "📊 Backtesting", "🛡️ Risk Monitor"],
        label_visibility="collapsed",
    )

    st.markdown("---")

    st.markdown('<span class="status-badge badge-paper">◉ PAPER MODE</span>',
                 unsafe_allow_html=True)

    st.markdown("---")
    st.caption("APEX INDIA v3.0")
    st.caption("Built on discipline. Powered by intelligence.")


# ═══════════════════════════════════════════════════════════════
#  PAGE: LIVE TRADING
# ═══════════════════════════════════════════════════════════════

if "Live Trading" in page:
    st.markdown("""
    <div class="main-header">
        <p class="main-title">Live Trading Dashboard</p>
        <p class="main-subtitle">Real-time positions, P&L tracking, and trade activity</p>
    </div>
    """, unsafe_allow_html=True)

    # Top metrics
    c1, c2, c3, c4, c5 = st.columns(5)
    with c1:
        pnl_pct = st.session_state.day_pnl / st.session_state.capital * 100
        metric_card("Equity", f"₹{st.session_state.equity:,.0f}",
                    f"Initial: ₹{st.session_state.capital:,.0f}", "blue", "neutral")
    with c2:
        cls = "positive" if st.session_state.day_pnl >= 0 else "negative"
        metric_card("Today's P&L", f"₹{st.session_state.day_pnl:+,.0f}",
                    f"{pnl_pct:+.2f}%", "green" if cls == "positive" else "red", cls)
    with c3:
        metric_card("Open Positions", f"{len(st.session_state.positions)}",
                    "of 10 max", "purple", "purple")
    with c4:
        metric_card("Win Rate", "62.5%", "Last 20 trades", "green", "positive")
    with c5:
        total_deployed = sum(p["qty"] * p["entry"] for p in st.session_state.positions)
        dep_pct = total_deployed / st.session_state.capital * 100
        metric_card("Deployed", f"{dep_pct:.1f}%",
                    f"₹{total_deployed:,.0f}", "blue", "neutral")

    st.markdown("<br>", unsafe_allow_html=True)

    # Positions + Activity
    col1, col2 = st.columns([3, 2])

    with col1:
        st.markdown('<div class="section-title">📋 Open Positions</div>', unsafe_allow_html=True)

        for p in st.session_state.positions:
            emoji = "🟢" if p["dir"] == "LONG" else "🔴"
            pnl_color = "positive" if p["pnl"] >= 0 else "negative"
            pnl_pct = (p["current"] - p["entry"]) / p["entry"] * 100
            if p["dir"] == "SHORT":
                pnl_pct = -pnl_pct
            st.markdown(f"""
            <div class="trade-row">
                <div>
                    <div style="font-weight:700;color:#F1F5F9;font-size:16px;">{emoji} {p['symbol']}</div>
                    <div style="color:#94A3B8;font-size:12px;">{p['strategy']} · {p['dir']} x{p['qty']}</div>
                </div>
                <div style="text-align:center;">
                    <div style="color:#94A3B8;font-size:12px;">Entry → Current</div>
                    <div style="color:#F1F5F9;font-family:'JetBrains Mono';font-size:14px;">
                        ₹{p['entry']:,.0f} → ₹{p['current']:,.0f}
                    </div>
                </div>
                <div style="text-align:right;">
                    <div class="{pnl_color}" style="font-family:'JetBrains Mono';font-size:18px;font-weight:700;">
                        ₹{p['pnl']:+,.0f}
                    </div>
                    <div class="{pnl_color}" style="font-size:12px;">{pnl_pct:+.1f}%</div>
                </div>
            </div>
            """, unsafe_allow_html=True)

    with col2:
        st.markdown('<div class="section-title">⚡ Today\'s Activity</div>', unsafe_allow_html=True)

        for t in st.session_state.trades_today:
            if t["action"] == "BUY":
                icon, color = "🟢", "#10B981"
            elif t["action"] == "SELL":
                icon, color = "🔴", "#EF4444"
            else:
                icon, color = "✅", "#F59E0B"

            extra = f" · P&L: ₹{t['pnl']:+,.0f}" if "pnl" in t else ""
            st.markdown(f"""
            <div class="activity-item" style="border-left-color:{color};">
                <span style="color:{color};font-weight:600;">{t['time']}</span>
                &nbsp;{icon} {t['action']} <b>{t['symbol']}</b> x{t['qty']} @₹{t['price']:,.0f}
                <span style="color:#94A3B8;font-size:12px;">{extra}</span>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Equity curve
    st.markdown('<div class="section-title">📈 Equity Curve</div>', unsafe_allow_html=True)
    np.random.seed(42)
    equity_data = pd.Series(
        np.cumsum(np.random.normal(150, 800, 60)) + 1_000_000,
        index=pd.date_range(end=datetime.now(), periods=60, freq="D")
    )
    fig = ChartBuilder.equity_curve(equity_data, "60-Day Equity Curve")
    if fig:
        st.plotly_chart(fig, use_container_width=True)


# ═══════════════════════════════════════════════════════════════
#  PAGE: PORTFOLIO
# ═══════════════════════════════════════════════════════════════

elif "Portfolio" in page:
    st.markdown("""
    <div class="main-header">
        <p class="main-title">Portfolio Overview</p>
        <p class="main-subtitle">Sector exposure, risk metrics, and allocation analysis</p>
    </div>
    """, unsafe_allow_html=True)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        metric_card("Total Return", "+8.24%", "Since inception", "green", "positive")
    with c2:
        metric_card("Sharpe Ratio", "1.85", "Annualized", "blue", "neutral")
    with c3:
        metric_card("Max Drawdown", "-3.2%", "Peak to trough", "red", "negative")
    with c4:
        metric_card("Portfolio Beta", "0.96", "vs Nifty 50", "purple", "purple")

    st.markdown("<br>", unsafe_allow_html=True)

    col1, col2 = st.columns([1, 1])
    with col1:
        st.markdown('<div class="section-title">🥧 Sector Allocation</div>', unsafe_allow_html=True)
        fig = ChartBuilder.sector_exposure({
            "Energy": 75000, "Banking": 48000, "IT": 36000,
            "FMCG": 45000, "Cash": 796000,
        }, "Current Allocation")
        if fig:
            st.plotly_chart(fig, use_container_width=True)

    with col2:
        st.markdown('<div class="section-title">📊 Daily P&L</div>', unsafe_allow_html=True)
        np.random.seed(123)
        daily_pnl = {f"Day {i+1}": int(np.random.normal(500, 3000))
                     for i in range(15)}
        fig = ChartBuilder.pnl_waterfall(daily_pnl, "Last 15 Days")
        if fig:
            st.plotly_chart(fig, use_container_width=True)


# ═══════════════════════════════════════════════════════════════
#  PAGE: SIGNALS
# ═══════════════════════════════════════════════════════════════

elif "Signals" in page:
    st.markdown("""
    <div class="main-header">
        <p class="main-title">Signal Analytics</p>
        <p class="main-subtitle">Strategy performance, signal history, and model accuracy</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown('<div class="section-title">📊 Strategy Performance (30 Days)</div>',
                unsafe_allow_html=True)

    strategies = pd.DataFrame({
        "Strategy": ["Trend Momentum Rider", "Opening Range Breakout", "VWAP Mean Reversion",
                      "Volatility Breakout", "SMC Reversal", "Gap Trade"],
        "Trades": [12, 18, 15, 8, 6, 10],
        "Win Rate": ["58.3%", "55.6%", "66.7%", "50.0%", "66.7%", "60.0%"],
        "Avg P&L": ["+₹1,240", "+₹890", "+₹780", "+₹420", "+₹1,100", "+₹650"],
        "Sharpe": [1.42, 1.28, 1.65, 0.95, 1.52, 1.18],
        "Status": ["✅ Active", "✅ Active", "✅ Active", "⚠️ Review", "✅ Active", "✅ Active"],
    })
    st.dataframe(strategies, use_container_width=True, hide_index=True)

    st.markdown("<br>", unsafe_allow_html=True)
    st.markdown('<div class="section-title">🎯 Regime Detection</div>', unsafe_allow_html=True)

    r1, r2, r3 = st.columns(3)
    with r1:
        metric_card("Current Regime", "TRENDING BULL", "Detected 09:30 IST", "green", "positive")
    with r2:
        metric_card("Regime Confidence", "82%", "HMM + Rule-Based", "blue", "neutral")
    with r3:
        metric_card("Active Strategies", "5 / 10", "Matching current regime", "purple", "purple")


# ═══════════════════════════════════════════════════════════════
#  PAGE: BACKTESTING
# ═══════════════════════════════════════════════════════════════

elif "Backtesting" in page:
    st.markdown("""
    <div class="main-header">
        <p class="main-title">Backtest Results</p>
        <p class="main-subtitle">Walk-forward validation, Monte Carlo analysis, and performance benchmarks</p>
    </div>
    """, unsafe_allow_html=True)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        metric_card("Total Return", "+32.4%", "252 trading days", "green", "positive")
    with c2:
        metric_card("Profit Factor", "1.94", "Gross P / Gross L", "blue", "neutral")
    with c3:
        metric_card("Max Drawdown", "-8.7%", "Below 15% limit", "green", "positive")
    with c4:
        metric_card("Monte Carlo P5", "₹11.4L", "5th percentile", "purple", "purple")

    st.markdown("<br>", unsafe_allow_html=True)

    st.markdown('<div class="section-title">📐 Walk-Forward Validation</div>', unsafe_allow_html=True)
    wf = pd.DataFrame({
        "Window": ["W1 (Jan-Mar)", "W2 (Apr-Jun)", "W3 (Jul-Sep)", "W4 (Oct-Dec)"],
        "IS Sharpe": [1.82, 1.65, 1.91, 1.74],
        "OOS Sharpe": [1.45, 1.38, 1.52, 1.41],
        "Divergence": ["20.3%", "16.4%", "20.4%", "19.0%"],
        "Result": ["✅ PASS", "✅ PASS", "⚠️ MARGINAL", "✅ PASS"],
    })
    st.dataframe(wf, use_container_width=True, hide_index=True)

    st.markdown("<br>", unsafe_allow_html=True)

    # Monte Carlo chart
    st.markdown('<div class="section-title">🎲 Monte Carlo Distribution (5,000 sims)</div>',
                unsafe_allow_html=True)
    np.random.seed(99)
    mc_returns = np.random.normal(15, 12, 5000)
    fig = go.Figure(go.Histogram(
        x=mc_returns, nbinsx=80,
        marker_color="rgba(59,130,246,0.6)",
        marker_line=dict(color="rgba(59,130,246,0.9)", width=1),
    ))
    fig.add_vline(x=np.percentile(mc_returns, 5), line_dash="dash",
                  line_color="#EF4444", annotation_text="P5")
    fig.add_vline(x=np.percentile(mc_returns, 95), line_dash="dash",
                  line_color="#10B981", annotation_text="P95")
    fig.add_vline(x=np.median(mc_returns), line_dash="solid",
                  line_color="#F59E0B", annotation_text="Median")
    fig.update_layout(
        title="Return Distribution (%)", height=400,
        paper_bgcolor="#0A0E17", plot_bgcolor="#111827",
        font=dict(color="#F1F5F9", family="Inter"),
        xaxis=dict(title="Annual Return %", gridcolor="#2A3441"),
        yaxis=dict(title="Frequency", gridcolor="#2A3441"),
    )
    st.plotly_chart(fig, use_container_width=True)


# ═══════════════════════════════════════════════════════════════
#  PAGE: RISK MONITOR
# ═══════════════════════════════════════════════════════════════

elif "Risk" in page:
    st.markdown("""
    <div class="main-header">
        <p class="main-title">Risk Monitor</p>
        <p class="main-subtitle">Circuit breakers, position limits, and portfolio risk assessment</p>
    </div>
    """, unsafe_allow_html=True)

    c1, c2, c3, c4 = st.columns(4)
    with c1:
        metric_card("Circuit Breaker", "NORMAL", "All levels clear", "green", "positive")
    with c2:
        metric_card("Daily P&L", "-0.12%", "Limit: -2.5%", "green", "positive")
    with c3:
        metric_card("Drawdown", "-1.8%", "Max: -15%", "green", "positive")
    with c4:
        metric_card("India VIX", "14.2", "Normal range", "blue", "neutral")

    st.markdown("<br>", unsafe_allow_html=True)

    col1, col2 = st.columns([1, 1])

    with col1:
        st.markdown('<div class="section-title">⚡ Circuit Breaker Levels</div>',
                    unsafe_allow_html=True)
        risk_bar("L1: Daily Loss", 0.12, 2.5, "#10B981")
        risk_bar("L2: Weekly Loss", 0.8, 5.0, "#3B82F6")
        risk_bar("L3: Monthly Loss", 1.2, 8.0, "#8B5CF6")
        risk_bar("L4: Max Drawdown", 1.8, 15.0, "#F59E0B")
        risk_bar("VIX Level", 14.2, 35.0, "#06B6D4")

    with col2:
        st.markdown('<div class="section-title">📐 Position Limits</div>',
                    unsafe_allow_html=True)
        risk_bar("Single Stock Exposure", 7.5, 8.0, "#3B82F6")
        risk_bar("Sector Exposure", 12.0, 25.0, "#8B5CF6")
        risk_bar("Portfolio Deployment", 24.0, 85.0, "#10B981")
        risk_bar("Correlation Risk", 0.45, 0.70, "#F59E0B")

        st.markdown("<br>", unsafe_allow_html=True)
        st.markdown('<div class="section-title">💰 Capital Status</div>',
                    unsafe_allow_html=True)

        cash = st.session_state.capital * 0.76
        metric_card("Cash Reserve", f"₹{cash:,.0f}",
                    f"{76:.0f}% — well above 15% minimum", "green", "positive")
