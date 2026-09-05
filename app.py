import streamlit as st
import yfinance as yf
import pandas as pd
import numpy as np
import plotly.graph_objects as go

st.set_page_config(page_title="Markets Quantitative Assistant", layout="wide")
st.title("📈 Quantitative Trading Assistant (INR ₹)")

INSTRUMENTS = {
    "Crypto": {
        "BITCOIN": "BTC-INR",
        "ETHEREUM": "ETH-INR",
        "SOLANA": "SOL-INR"
    },
    "Indices": {
        "NIFTY 50": "^NSEI",
        "BANK NIFTY": "^NSEBANK",
        "FINNIFTY": "NIFTY_FIN_SERVICE.NS",
        "MIDCAP NIFTY": "NIFTY_MIDCAP_100.NS",
        "SENSEX": "^BSESN"
    },
    "Top Equities / F&O": {
        "RELIANCE": "RELIANCE.NS",
        "HDFC BANK": "HDFCBANK.NS",
        "ICICI BANK": "ICICIBANK.NS",
        "INFOSYS": "INFY.NS",
        "TCS": "TCS.NS",
        "STATE BANK OF INDIA": "SBIN.NS",
        "TATA MOTORS": "TATAMOTORS.NS",
        "ITC": "ITC.NS",
        "BHARTI AIRTEL": "BHARTIARTL.NS",
        "L&T": "LT.NS"
    },
    "Commodities (MCX/INR equivalent)": {
        "GOLD (Continuous / converted to ₹)": "GC=F",
        "SILVER (Continuous / converted to ₹)": "SI=F",
        "CRUDE OIL (Continuous / converted to ₹)": "CL=F"
    }
}

st.sidebar.header("Market Selection")
category = st.sidebar.selectbox("Category", list(INSTRUMENTS.keys()))
selected_name = st.sidebar.selectbox("Instrument", list(INSTRUMENTS[category].keys()))
custom_ticker = st.sidebar.text_input("Or Custom Symbol (e.g. BTC-INR, TATASTEEL.NS)", "")

ticker = custom_ticker.strip().upper() if custom_ticker.strip() else INSTRUMENTS[category][selected_name]

timeframe = st.sidebar.selectbox("Timeframe", ["5m", "15m", "1h", "1d"], index=1)
period = "5d" if timeframe in ["5m", "15m"] else "1mo"

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

@st.cache_data(ttl=60)
def load_market_data(symbol, tf, prd):
    df = yf.download(symbol, period=prd, interval=tf, progress=False)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df

with st.spinner(f"Fetching live data for {ticker}..."):
    data = load_market_data(ticker, timeframe, period)

if data.empty or len(data) < 15:
    st.error(f"Unable to fetch data for {ticker}. Please check the symbol format.")
else:
    is_usd = ticker.endswith("=F") or ticker.endswith("-USD")
    rate = get_usd_inr_rate() if is_usd else 1.0

    ohlc_cols = ['Open', 'High', 'Low', 'Close']
    for col in ohlc_cols:
        data[col] = data[col] * rate

    data['EMA20'] = data['Close'].ewm(span=20, adjust=False).mean()
    data['EMA50'] = data['Close'].ewm(span=50, adjust=False).mean()

    delta = data['Close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / (loss.replace(0, np.nan))
    data['RSI'] = 100 - (100 / (1 + rs))

    latest = data.iloc[-1]
    prev = data.iloc[-2]
    curr_price = float(latest['Close'])
    prev_price = float(prev['Close'])
    curr_rsi = float(latest['RSI'])
    ema20 = float(latest['EMA20'])
    ema50 = float(latest['EMA50'])

    c1, c2, c3, c4 = st.columns(4)
    c1.metric("LTP", f"₹{curr_price:,.2f}", f"₹{curr_price - prev_price:,.2f}")
    c2.metric("RSI (14)", f"{curr_rsi:.2f}")
    c3.metric("EMA 20", f"₹{ema20:,.2f}")
    c4.metric("EMA 50", f"₹{ema50:,.2f}")

    fig = go.Figure()
    fig.add_trace(go.Candlestick(
        x=data.index,
        open=data['Open'], high=data['High'],
        low=data['Low'], close=data['Close'],
        name="OHLC (₹)"
    ))
    fig.add_trace(go.Scatter(x=data.index, y=data['EMA20'], line=dict(color='#ff9900', width=1.5), name="EMA 20"))
    fig.add_trace(go.Scatter(x=data.index, y=data['EMA50'], line=dict(color='#0066ff', width=1.5), name="EMA 50"))
    fig.update_layout(xaxis_rangeslider_visible=False, height=450, margin=dict(l=10, r=10, t=25, b=10))
    st.plotly_chart(fig, width='stretch')

    st.subheader("⚡ Automated Quantitative Breakdown (All figures in ₹)")

    if curr_price > ema20 > ema50:
        trend = "Strong Bullish"
        trend_color = "green"
    elif curr_price < ema20 < ema50:
        trend = "Strong Bearish"
        trend_color = "red"
    elif curr_price > ema20:
        trend = "Mild Bullish / Pullback"
        trend_color = "blue"
    else:
        trend = "Mild Bearish / Consolidating"
        trend_color = "orange"

    if curr_rsi > 70:
        momentum = "Overbought zone (Risk of exhaustion/pullback)"
    elif curr_rsi < 30:
        momentum = "Oversold zone (Potential bounce territory)"
    elif curr_rsi >= 50:
        momentum = "Bullish momentum (> 50)"
    else:
        momentum = "Bearish momentum (< 50)"

    recent_low = float(data['Low'].tail(20).min())
    recent_high = float(data['High'].tail(20).max())

    st.markdown(f"**Market Bias:** :{trend_color}[**{trend}**]")
    st.markdown(f"**Momentum:** {momentum}")
    st.markdown(f"**Immediate Support (S1):** `₹{recent_low:,.2f}` | **Immediate Resistance (R1):** `₹{recent_high:,.2f}`")

    if "Bullish" in trend:
        entry = curr_price
        sl = round(min(ema20, recent_low), 2)
        risk = entry - sl
        target = round(entry + (risk * 1.8), 2)
        setup_type = "LONG Setup"
    else:
        entry = curr_price
        sl = round(max(ema20, recent_high), 2)
        risk = sl - entry
        target = round(entry - (risk * 1.8), 2)
        setup_type = "SHORT Setup"

    st.info(f"""
    **{setup_type}:**
    * **Suggested Entry Zone:** around `₹{entry:,.2f}`
    * **Calculated Invalidation (Stop Loss):** `₹{sl:,.2f}`
    * **1:1.8 Target:** `₹{target:,.2f}`
    """)
  
