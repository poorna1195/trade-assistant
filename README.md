import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np

st.set_page_config(page_title="Trade Signals", layout="centered")

# Minimal Custom Styling for Mobile
st.markdown("""
    <style>
    .metric-card {
        background-color: #1e222d;
        border-radius: 12px;
        padding: 16px;
        margin-bottom: 12px;
        text-align: center;
        color: white;
    }
    .buy-signal {
        background-color: #0e3a24;
        border: 2px solid #00c853;
        border-radius: 12px;
        padding: 20px;
        text-align: center;
        margin-bottom: 15px;
    }
    .sell-signal {
        background-color: #3a1010;
        border: 2px solid #ff3d00;
        border-radius: 12px;
        padding: 20px;
        text-align: center;
        margin-bottom: 15px;
    }
    </style>
""", unsafe_allow_html=True)

st.title("🎯 Quick Trade Signal")

INSTRUMENTS = {
    "NIFTY 50": "^NSEI",
    "BANK NIFTY": "^NSEBANK",
    "FINNIFTY": "NIFTY_FIN_SERVICE.NS",
    "SENSEX": "^BSESN",
    "BITCOIN": "BTC-INR",
    "RELIANCE": "RELIANCE.NS",
    "HDFC BANK": "HDFCBANK.NS"
}

# 1-Tap Dropdown at the top (no hidden sidebar menu)
selected_name = st.selectbox("Choose Instrument", list(INSTRUMENTS.keys()), index=0)
ticker = INSTRUMENTS[selected_name]

@st.cache_data(ttl=30)
def get_signal_data(symbol):
    df = yf.download(symbol, period="5d", interval="15m", progress=False)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df

with st.spinner("Fetching signal..."):
    data = get_signal_data(ticker)

if data.empty or len(data) < 20:
    st.error("Market feed currently unavailable.")
else:
    data['EMA20'] = data['Close'].ewm(span=20, adjust=False).mean()
    data['EMA50'] = data['Close'].ewm(span=50, adjust=False).mean()

    curr_price = float(data['Close'].iloc[-1])
    ema20 = float(data['EMA20'].iloc[-1])
    ema50 = float(data['EMA50'].iloc[-1])

    recent_low = float(data['Low'].tail(15).min())
    recent_high = float(data['High'].tail(15).max())

    is_bullish = curr_price > ema20

    if is_bullish:
        signal = "BUY / CALL (LONG)"
        css_class = "buy-signal"
        color = "#00c853"
        sl = round(min(ema20, recent_low), 2)
        risk = curr_price - sl if curr_price > sl else 10
        target = round(curr_price + (risk * 1.5), 2)
    else:
        signal = "SELL / PUT (SHORT)"
        css_class = "sell-signal"
        color = "#ff3d00"
        sl = round(max(ema20, recent_high), 2)
        risk = sl - curr_price if sl > curr_price else 10
        target = round(curr_price - (risk * 1.5), 2)

    # 1. High-level Signal Banner
    st.markdown(f"""
    <div class="{css_class}">
        <h3 style="margin: 0; color: {color};">{signal}</h3>
        <h1 style="margin: 5px 0; font-size: 38px;">₹{curr_price:,.2f}</h1>
        <p style="margin: 0; opacity: 0.8;">Live Price</p>
    </div>
    """, unsafe_allow_html=True)

    # 2. Key Numbers (SL & Target)
    col1, col2 = st.columns(2)
    with col1:
        st.metric(label="🛑 Stop Loss", value=f"₹{sl:,.2f}")
    with col2:
        st.metric(label="🎯 Target (1:1.5)", value=f"₹{target:,.2f}")

    st.markdown("---")
    st.caption("Pull down to refresh. Setup calculated on 15-minute trend structure.")

