import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import time
# --- SAHIFA SOZLAMALARI ---
st.set_page_config(page_title="BahorDev Elite Terminal", layout="wide", initial_sidebar_state="expanded")

# --- CSS: DIZAYNNI PROFESSIONAL QILISH ---
st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    div[data-testid="stMetricValue"] { font-size: 24px; color: #00ffc8; }
    .stAlert { border-radius: 10px; border: 1px solid #1f2937; }
    </style>
    """, unsafe_allow_html=True)

# --- TEXNIK INDIKATORLAR (BACKEND) ---
def add_indicators(df):
    # EMA (Exponential Moving Average)
    df['EMA9'] = df['close'].ewm(span=9, adjust=False).mean()
    df['EMA21'] = df['close'].ewm(span=21, adjust=False).mean()
    
    # RSI
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    df['RSI'] = 100 - (100 / (1 + (gain / loss)))
    
    # MACD
    exp1 = df['close'].ewm(span=12, adjust=False).mean()
    exp2 = df['close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = exp1 - exp2
    df['Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
    return df

# --- MA'LUMOTLARNI YUKLASH ---
@st.cache_data(ttl=2)
def get_crypto_data(symbol, interval):
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit=100"
    res = requests.get(url).json()
    df = pd.DataFrame(res, columns=['time','open','high','low','close','vol','c_time','q_vol','trades','tb_vol','tq_vol','ignore'])
    df['time'] = pd.to_datetime(df['time'], unit='ms')
    df[['open','high','low','close','vol']] = df[['open','high','low','close','vol']].apply(pd.to_numeric)
    return add_indicators(df)

@st.cache_data(ttl=1)
def get_order_book(symbol):
    url = f"https://api.binance.com/api/v3/depth?symbol={symbol}&limit=10"
    res = requests.get(url).json()
    bids = pd.DataFrame(res['bids'], columns=['Price', 'Qty']).astype(float)
    asks = pd.DataFrame(res['asks'], columns=['Price', 'Qty']).astype(float)
    return bids, asks

# --- SIDEBAR (BOSHQARUV) ---
st.sidebar.image("https://cdn-icons-png.flaticon.com/512/2091/2091665.png", width=100)
st.sidebar.title("ELITE ANALYTICS")
target_coin = st.sidebar.selectbox("Market:", ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "ARBUSDT"], index=0)
tf = st.sidebar.radio("Timeframe:", ["1m", "5m", "15m", "1h", "4h"], horizontal=True)

# --- ASOSIY PANEL ---
col1, col2 = st.columns([3, 1])

with col1:
    df = get_crypto_data(target_coin, tf)
    
    # Grafik yaratish
    fig = make_subplots(rows=3, cols=1, shared_xaxes=True, 
                        vertical_spacing=0.05, row_heights=[0.6, 0.2, 0.2])

    # Candlestick + EMA
    fig.add_trace(go.Candlestick(x=df['time'], open=df['open'], high=df['high'], low=df['low'], close=df['close'], name="Market"), row=1, col=1)
    fig.add_trace(go.Scatter(x=df['time'], y=df['EMA9'], name="EMA 9", line=dict(color='#00ffc8', width=1)), row=1, col=1)
    fig.add_trace(go.Scatter(x=df['time'], y=df['EMA21'], name="EMA 21", line=dict(color='#ff007a', width=1)), row=1, col=1)

    # RSI
    fig.add_trace(go.Scatter(x=df['time'], y=df['RSI'], name="RSI", line=dict(color='#ffd700')), row=2, col=1)
    fig.add_hline(y=70, line_dash="dash", line_color="red", row=2, col=1)
    fig.add_hline(y=30, line_dash="dash", line_color="green", row=2, col=1)

    # MACD
    fig.add_trace(go.Bar(x=df['time'], y=df['MACD']-df['Signal'], name="Histogram"), row=3, col=1)

    fig.update_layout(height=800, template="plotly_dark", showlegend=False, xaxis_rangeslider_visible=False)
    st.plotly_chart(fig, use_container_width=True)

with col2:
    # Narx Metrikasi
    curr_p = df['close'].iloc[-1]
    prev_p = df['close'].iloc[-2]
    diff = ((curr_p - prev_p) / prev_p) * 100
    st.metric("Live Price", f"${curr_p:,}", f"{diff:.2f}%")
    
    st.markdown("### 🏦 Order Book")
    bids, asks = get_order_book(target_coin)
    
    st.write("🔴 Asks (Sotish)")
    st.dataframe(asks.sort_values(by="Price", ascending=False), hide_index=True, use_container_width=True)
    
    st.write("🟢 Bids (Sotib olish)")
    st.dataframe(bids, hide_index=True, use_container_width=True)

# --- AVTOMAT YANGILANISH ---
st.toast(f"Market updated: {target_coin}")
st.empty()
import time
time.sleep(2)
st.rerun()