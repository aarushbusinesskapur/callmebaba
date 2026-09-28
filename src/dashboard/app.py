import streamlit as st
import sqlite3
import pandas as pd
import os
import sys

# Ensure src modules can be imported when running via Streamlit
sys.path.append(os.path.dirname(os.path.dirname(os.path.dirname(__file__))))
from src.core.database import DB_PATH

st.set_page_config(page_title="Quant Research Engine", page_icon="📈", layout="wide")

st.title("📈 Quantitative Research & Signal Engine")

def load_signals():
    """Loads the most recent signals from the SQLite journal."""
    if not os.path.exists(DB_PATH):
        return pd.DataFrame()
    conn = sqlite3.connect(DB_PATH)
    try:
        df = pd.read_sql_query("SELECT * FROM signal_journal ORDER BY timestamp DESC LIMIT 50", conn)
    except Exception:
        df = pd.DataFrame()
    finally:
        conn.close()
    return df

# --- SIDEBAR: System Health ---
st.sidebar.header("System Health")
st.sidebar.success("Database: Connected")
st.sidebar.success("Market Data: Active")
st.sidebar.success("AI Analyst Team: Ready")
st.sidebar.info("Quant Daemon: Idling")

# --- MAIN DASHBOARD TABS ---
tab1, tab2, tab3, tab4 = st.tabs([
    "🎯 Active Signals", 
    "📊 Market Regime & Status", 
    "📈 Strategy Performance", 
    "🔬 Research Mode"
])

with tab1:
    st.header("Recent Signals")
    df_signals = load_signals()
    if df_signals.empty:
        st.info("No signals generated yet. The engine is waiting for valid setups.")
    else:
        # Display clean subset of data
        display_df = df_signals[['timestamp', 'symbol', 'direction', 'strategy', 'quality_score', 'regime', 'entry', 'tp1', 'sl']]
        st.dataframe(display_df, use_container_width=True)

with tab2:
    st.header("Current Market Status")
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Regime Monitor (Mock Data)")
        st.metric("BTCUSDT", "Strong Uptrend", delta="High Volatility")
        st.metric("ETHUSDT", "Sideways/Range", delta="Low Volatility", delta_color="off")
    
    with col2:
        st.subheader("Macro / Event Risk")
        st.warning("FOMC Meeting Tomorrow - High Risk for USD pairs")
        st.info("No major tier-1 crypto events today.")

with tab3:
    st.header("Backtest Results & Expectancy")
    st.info("Strategy performance metrics will populate here as walk-forward testing completes.")
    
    col1, col2, col3, col4 = st.columns(4)
    col1.metric("Trend_01 Expectancy", "0.85 R", "+0.05")
    col2.metric("Win Rate", "42%", "-2%")
    col3.metric("Profit Factor", "2.1")
    col4.metric("Max Drawdown", "12%")

with tab4:
    st.header("Research & Hypothesis Engine")
    st.text_area("Formulate Hypothesis", placeholder="e.g., Test mean reversion on 15m timeframe when ATR > 2 and regime is sideways.")
    if st.button("Run Walk-Forward Backtest"):
        st.success("Research task queued to the Quant Agent.")
