import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import requests

st.set_page_config(page_title="Trade Signals", layout="centered")

st.markdown("""
    <style>
    .buy-signal {
        background-color: #0e3a24;
        border: 2px solid #00c853;
        border-radius: 12px;
        padding: 20px;
        text-align: center;
        margin-bottom: 15px;
        color: white;
    }
    .sell-signal {
        background-color: #3a1010;
        border: 2px solid #ff3d00;
        border-radius: 12px;
        padding: 20px;
        text-align: center;
        margin-bottom: 15px;
        color: white;
    }
    </style>
""", unsafe_allow_html=True)

st.title("🎯 Quick Trade Signal")

INSTRUMENTS = {
    "BITCOIN (Delta Exchange)": "DELTA_BTC",
    "NIFTY 50": "^NSEI",
    "BANK NIFTY": "^NSEBANK",
    "FINNIFTY": "NIFTY_FIN_SERVICE.NS",
    "SENSEX": "^BSESN",
    "RELIANCE": "RELIANCE.NS",
    "HDFC BANK": "HDFCBANK.NS"
}

selected_name = st.selectbox("Choose Instrument", list(INSTRUMENTS.keys()), index=0)
ticker_key = INSTRUMENTS[selected_name]

@st.cache_data(ttl=5)
def get_delta_btc():
    # Fetch live BTCUSD spot/mark price directly from Delta Exchange India
    urls = [
        "https://api.india.delta.exchange/v2/tickers/BTCUSD",
        "https://api.delta.exchange/v2/tickers/BTCUSD"
    ]
    for url in urls:
        try:
            res = requests.get(url, timeout=3).json()
            if res.get("success"):
                mark_price = float(res["result"]["mark_price"])
                spot_price = float(res["result"]["spot_price"])
                close_24h = float(res["result"]["close"])
                return mark_price, spot_price, close_24h
        except Exception:
            continue
    return None, None, None

@st.cache_data(ttl=60)
def get_market_data(symbol):
    df = yf.download(symbol, period="5d", interval="15m", progress=False)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df

@st.cache_data(ttl=300)
def get_usd_inr_rate():
    try:
        usd_inr = yf.download("USDINR=X", period="1d", interval="5m", progress=False)
        if not usd_inr.empty:
            if isinstance(usd_inr.columns, pd.MultiIndex):
                usd_inr.columns = usd_inr.columns.get_level_values(0)
            return float(usd_inr['Close'].iloc[-1])
    except Exception:
        pass
    return 84.0

if ticker_key == "DELTA_BTC":
    mark_price, spot_price, close_24h = get_delta_btc()
    
    if mark_price is None:
        st.error("Connecting to Delta Exchange feed... Please pull down to refresh.")
    else:
        usd_inr = get_usd_inr_rate()
        price_inr = mark_price * usd_inr
        change_24h = (mark_price - close_24h) * usd_inr
        
        # Trend evaluation based on 24h delta
        is_bullish = mark_price >= close_24h
        signal = "BUY / CALL (LONG)" if is_bullish else "SELL / PUT (SHORT)"
        css_class = "buy-signal" if is_bullish else "sell-signal"
        color = "#00c853" if is_bullish else "#ff3d00"
        
        # Target & SL calculation (1.5% intraday risk brackets)
        sl = round(price_inr * (0.985 if is_bullish else 1.015), 2)
        target = round(price_inr * (1.025 if is_bullish else 0.975), 2)

        st.markdown(f"""
        <div class="{css_class}">
            <h3 style="margin: 0; color: {color};">{signal}</h3>
            <h1 style="margin: 6px 0; font-size: 34px;">₹{price_inr:,.2f}</h1>
            <p style="margin: 0; opacity: 0.85; font-size: 15px;">Delta Mark: <b>${mark_price:,.2f}</b> | Spot: <b>${spot_price:,.2f}</b></p>
        </div>
        """, unsafe_allow_html=True)

        col1, col2 = st.columns(2)
        with col1:
            st.metric(label="🛑 Stop Loss", value=f"₹{sl:,.2f}")
        with col2:
            st.metric(label="🎯 Target", value=f"₹{target:,.2f}")

        st.caption("Live feed connected directly to Delta Exchange India.")

else:
    with st.spinner("Fetching signal..."):
        data = get_market_data(ticker_key)

    if data.empty or len(data) < 20:
        st.error("Market feed currently unavailable.")
    else:
        data['EMA20'] = data['Close'].ewm(span=20, adjust=False).mean()
        curr_price = float(data['Close'].iloc[-1])
        ema20 = float(data['EMA20'].iloc[-1])
        recent_low = float(data['Low'].tail(15).min())
        recent_high = float(data['High'].tail(15).max())

        is_bullish = curr_price > ema20
        signal = "BUY / CALL (LONG)" if is_bullish else "SELL / PUT (SHORT)"
        css_class = "buy-signal" if is_bullish else "sell-signal"
        color = "#00c853" if is_bullish else "#ff3d00"

        if is_bullish:
            sl = round(min(ema20, recent_low), 2)
            risk = max(curr_price - sl, 10)
            target = round(curr_price + (risk * 1.5), 2)
        else:
            sl = round(max(ema20, recent_high), 2)
            risk = max(sl - curr_price, 10)
            target = round(curr_price - (risk * 1.5), 2)

        st.markdown(f"""
        <div class="{css_class}">
            <h3 style="margin: 0; color: {color};">{signal}</h3>
            <h1 style="margin: 6px 0; font-size: 34px;">₹{curr_price:,.2f}</h1>
            <p style="margin: 0; opacity: 0.85;">Live Index Price</p>
        </div>
        """, unsafe_allow_html=True)

        col1, col2 = st.columns(2)
        with col1:
            st.metric(label="🛑 Stop Loss", value=f"₹{sl:,.2f}")
        with col2:
            st.metric(label="🎯 Target", value=f"₹{target:,.2f}")

        st.caption("Setup calculated on 15-minute trend structure.")

