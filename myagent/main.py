import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime
import time

# --- SAHIFA KONFIGURATSIYASI ---
st.set_page_config(page_title="BahorDev Pro Terminal", page_icon="📈", layout="wide")

# --- RSI HISOB-KITOBI ---
def calculate_rsi(series, period=14):
    delta = series.diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=period).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=period).mean()
    rs = gain / loss
    return 100 - (100 / (1 + rs))

# --- BINANCE'DAN MA'LUMOT OLISH ---
@st.cache_data(ttl=5)
def fetch_data(symbol, interval, limit=150):
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
    try:
        data = requests.get(url).json()
        df = pd.DataFrame(data, columns=['time', 'open', 'high', 'low', 'close', 'vol', 'close_t', 'q_vol', 'trades', 't_base', 't_quote', 'ignore'])
        df['time'] = pd.to_datetime(df['time'], unit='ms')
        for col in ['open', 'high', 'low', 'close', 'vol']:
            df[col] = df[col].astype(float)
        return df
    except:
        return pd.DataFrame()

# --- SIDEBAR ---
st.sidebar.title("💎 PRO TERMINAL")
symbol = st.sidebar.selectbox("Valyuta Juftligi:", ["BTCUSDT", "ETHUSDT", "SOLUSDT"], index=0)
timeframe = st.sidebar.selectbox("Taymfreym:", ["1m", "5m", "15m", "1h", "4h", "1d"], index=2)

# --- ASOSIY QISM ---
df = fetch_data(symbol, timeframe)

if not df.empty:
    # Metrikalar
    last_price = df['close'].iloc[-1]
    st.metric(f"{symbol} Narxi", f"${last_price:,}")

    # Grafik
    fig = make_subplots(rows=2, cols=1, shared_xaxes=True, row_heights=[0.7, 0.3])
    fig.add_trace(go.Candlestick(x=df['time'], open=df['open'], high=df['high'], low=df['low'], close=df['close'], name="Narx"), row=1, col=1)
    
    # RSI
    df['RSI'] = calculate_rsi(df['close'])
    fig.add_trace(go.Scatter(x=df['time'], y=df['RSI'], name="RSI", line=dict(color='magenta')), row=2, col=1)
    
    fig.update_layout(template="plotly_dark", height=600, xaxis_rangeslider_visible=False)
    st.plotly_chart(fig, use_container_width=True)

    st.success("Terminal muvaffaqiyatli ishlamoqda!")
    time.sleep(5)
    st.rerun()