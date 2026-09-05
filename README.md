import streamlit as st
import yfinance as yf
import pandas as pd
import requests

st.set_page_config(page_title="Trade Assistant", layout="centered", initial_sidebar_state="collapsed")

# Custom Dark Trading Card Styling
st.markdown("""
<style>
    #MainMenu, header, footer {visibility: hidden;}
    .block-container {padding-top: 1.5rem; padding-bottom: 2rem;}
    
    .trade-card {
        background: #161b22;
        border-radius: 16px;
        padding: 24px 20px;
        border: 1px solid #30363d;
        box-shadow: 0 4px 20px rgba(0,0,0,0.4);
        margin-top: 10px;
    }
    .badge-bull {
        display: inline-block;
        background: rgba(35, 134, 54, 0.2);
        color: #3fb950;
        border: 1px solid #238636;
        padding: 4px 12px;
        border-radius: 20px;
        font-weight: 700;
        font-size: 14px;
    }
    .badge-bear {
        display: inline-block;
        background: rgba(218, 54, 51, 0.2);
        color: #f85149;
        border: 1px solid #da3633;
        padding: 4px 12px;
        border-radius: 20px;
        font-weight: 700;
        font-size: 14px;
    }
    .price-text {
        font-size: 38px;
        font-weight: 800;
        letter-spacing: -1px;
        margin: 12px 0 4px 0;
        color: #f0f6fc;
    }
    .sub-rate {
        color: #8b949e;
        font-size: 13px;
        margin-bottom: 20px;
    }
    .data-grid {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 12px;
        border-top: 1px solid #21262d;
        padding-top: 16px;
    }
    .grid-box {
        background: #0d1117;
        padding: 12px;
        border-radius: 10px;
        text-align: center;
        border: 1px solid #21262d;
    }
    .grid-label {
        font-size: 11px;
        color: #8b949e;
        text-transform: uppercase;
        font-weight: 600;
    }
    .grid-value {
        font-size: 16px;
        font-weight: 700;
        color: #f0f6fc;
        margin-top: 2px;
    }
</style>
""", unsafe_allow_html=True)

INSTRUMENTS = {
    "⚡ Bitcoin (Delta India)": "DELTA_BTC",
    "📊 NIFTY 50": "^NSEI",
    "🏦 BANK NIFTY": "^NSEBANK",
    "📈 FINNIFTY": "NIFTY_FIN_SERVICE.NS",
    "🏢 SENSEX": "^BSESN",
    "🔹 Reliance": "RELIANCE.NS",
    "🔹 HDFC Bank": "HDFCBANK.NS"
}

selected_label = st.selectbox("Select Market", list(INSTRUMENTS.keys()), label_visibility="collapsed")
ticker = INSTRUMENTS[selected_label]

@st.cache_data(ttl=10)
def fetch_delta_btc():
    try:
        r = requests.get("https://api.india.delta.exchange/v2/tickers/BTCUSD", timeout=3).json()
        if r.get("success"):
            return float(r["result"]["mark_price"]), float(r["result"]["close"])
    except Exception:
        pass
    try:
        r = requests.get("https://api.coingecko.com/api/v3/simple/price?ids=bitcoin&vs_currencies=usd", timeout=3).json()
        val = float(r["bitcoin"]["usd"])
        return val, val
    except Exception:
        return None, None

@st.cache_data(ttl=300)
def fetch_usd_inr():
    try:
        data = yf.download("USDINR=X", period="1d", interval="5m", progress=False)
        if not data.empty:
            if isinstance(data.columns, pd.MultiIndex):
                data.columns = data.columns.get_level_values(0)
            return float(data['Close'].iloc[-1])
    except Exception:
        pass
    return 84.0

@st.cache_data(ttl=60)
def fetch_nse_data(symbol):
    df = yf.download(symbol, period="5d", interval="15m", progress=False)
    if isinstance(df.columns, pd.MultiIndex):
        df.columns = df.columns.get_level_values(0)
    return df

# Display Card Logic
if ticker == "DELTA_BTC":
    mark_price, close_24h = fetch_delta_btc()
    if mark_price is None:
        st.warning("Reconnecting to Delta feed...")
    else:
        usd_inr = fetch_usd_inr()
        price_inr = mark_price * usd_inr
        is_bullish = mark_price >= close_24h
        
        badge = '<span class="badge-bull">🟢 BUY / CALL</span>' if is_bullish else '<span class="badge-bear">🔴 SELL / PUT</span>'
        sl = price_inr * (0.985 if is_bullish else 1.015)
        target = price_inr * (1.025 if is_bullish else 0.975)
        
        st.markdown(f"""
        <div class="trade-card">
            {badge}
            <div class="price-text">₹{price_inr:,.2f}</div>
            <div class="sub-rate">Delta Mark: ${mark_price:,.2f} · USD/INR: ₹{usd_inr:.2f}</div>
            <div class="data-grid">
                <div class="grid-box">
                    <div class="grid-label">🛑 Stop Loss</div>
                    <div class="grid-value">₹{sl:,.2f}</div>
                </div>
                <div class="grid-box">
                    <div class="grid-label">🎯 Target</div>
                    <div class="grid-value">₹{target:,.2f}</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
else:
    df = fetch_nse_data(ticker)
    if df.empty or len(df) < 15:
        st.warning("Market feed currently offline.")
    else:
        df['EMA20'] = df['Close'].ewm(span=20, adjust=False).mean()
        curr_price = float(df['Close'].iloc[-1])
        ema20 = float(df['EMA20'].iloc[-1])
        recent_low = float(df['Low'].tail(15).min())
        recent_high = float(df['High'].tail(15).max())
        
        is_bullish = curr_price > ema20
        badge = '<span class="badge-bull">🟢 BUY / CALL</span>' if is_bullish else '<span class="badge-bear">🔴 SELL / PUT</span>'
        
        if is_bullish:
            sl = min(ema20, recent_low)
            risk = max(curr_price - sl, 10)
            target = curr_price + (risk * 1.5)
        else:
            sl = max(ema20, recent_high)
            risk = max(sl - curr_price, 10)
            target = curr_price - (risk * 1.5)

        st.markdown(f"""
        <div class="trade-card">
            {badge}
            <div class="price-text">₹{curr_price:,.2f}</div>
            <div class="sub-rate">{selected_label} · 15m Trend Structure</div>
            <div class="data-grid">
                <div class="grid-box">
                    <div class="grid-label">🛑 Stop Loss</div>
                    <div class="grid-value">₹{sl:,.2f}</div>
                </div>
                <div class="grid-box">
                    <div class="grid-label">🎯 Target</div>
                    <div class="grid-value">₹{target:,.2f}</div>
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)
