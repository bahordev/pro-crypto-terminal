import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas_ta as ta # Texnik tahlil uchun
from datetime import datetime
import time

# --- SAHIFA KONFIGURATSIYASI ---
st.set_page_config(page_title="BahorDev Pro Terminal", page_icon="📈", layout="wide")

# --- STYLE (Professional Dark Theme) ---
st.markdown("""
    <style>
    .main { background-color: #0b0e11; }
    .stMetric { background-color: #1e2329; border-radius: 10px; padding: 15px; border: 1px solid #363a45; }
    </style>
""", unsafe_allow_html=True)

# --- FUNKSIYALAR ---
@st.cache_data(ttl=5)
def fetch_data(symbol, interval, limit=150):
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit={limit}"
    data = requests.get(url).json()
    df = pd.DataFrame(data, columns=['time', 'open', 'high', 'low', 'close', 'vol', 'close_t', 'q_vol', 'trades', 't_base', 't_quote', 'ignore'])
    df['time'] = pd.to_datetime(df['time'], unit='ms')
    for col in ['open', 'high', 'low', 'close', 'vol']:
        df[col] = df[col].astype(float)
    return df

def get_order_book(symbol):
    url = f"https://api.binance.com/api/v3/depth?symbol={symbol}&limit=10"
    data = requests.get(url).json()
    bids = pd.DataFrame(data['bids'], columns=['Price', 'Quantity']).astype(float)
    asks = pd.DataFrame(data['asks'], columns=['Price', 'Quantity']).astype(float)
    return bids, asks

# --- SIDEBAR ---
st.sidebar.title("💎 PRO TERMINAL")
symbol = st.sidebar.selectbox("Valyuta Juftligi:", ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "ARBUSDT"], index=0)
timeframe = st.sidebar.selectbox("Taymfreym:", ["1m", "5m", "15m", "1h", "4h", "1d"], index=2)
indicator = st.sidebar.multiselect("Indikatorlar:", ["RSI", "EMA 20", "EMA 50", "Bollinger Bands"], default=["RSI", "EMA 20"])

# --- ASOSIY QISM ---
df = fetch_data(symbol, timeframe)
bids, asks = get_order_book(symbol)

# Metrikalar
last_price = df['close'].iloc[-1]
change = ((df['close'].iloc[-1] - df['close'].iloc[0]) / df['close'].iloc[0]) * 100

c1, c2, c3, c4 = st.columns(4)
c1.metric(f"{symbol} Narxi", f"${last_price:,}", f"{change:.2f}%")
c2.metric("24s Hajm", f"{df['vol'].sum():,.0f}")
c3.metric("Eng Yuqori", f"${df['high'].max():,}")
c4.metric("Eng Past", f"${df['low'].min():,}")

# --- GRAFIK QURISH ---
fig = make_subplots(rows=2, cols=1, shared_xaxes=True, vertical_spacing=0.05, row_heights=[0.7, 0.3])

# Shamlar grafigi
fig.add_trace(go.Candlestick(x=df['time'], open=df['open'], high=df['high'], low=df['low'], close=df['close'], name="Narx"), row=1, col=1)

# Indikatorlar qo'shish
if "EMA 20" in indicator:
    df['EMA20'] = ta.ema(df['close'], length=20)
    fig.add_trace(go.Scatter(x=df['time'], y=df['EMA20'], line=dict(color='yellow', width=1), name="EMA 20"), row=1, col=1)

if "RSI" in indicator:
    df['RSI'] = ta.rsi(df['close'], length=14)
    fig.add_trace(go.Scatter(x=df['time'], y=df['RSI'], line=dict(color='magenta', width=1.5), name="RSI"), row=2, col=1)
    fig.add_hline(y=70, line_dash="dot", row=2, col=1, line_color="red")
    fig.add_hline(y=30, line_dash="dot", row=2, col=1, line_color="green")

fig.update_layout(template="plotly_dark", height=700, xaxis_rangeslider_visible=False, margin=dict(l=10, r=10, t=10, b=10))
st.plotly_chart(fig, use_container_width=True)

# --- ORDER BOOK VA TAHLIL ---
col_left, col_right = st.columns(2)

with col_left:
    st.subheader("📊 Canli Order Book (Bozor Chuqurligi)")
    o_col1, o_col2 = st.columns(2)
    o_col1.write("🟢 Bids (Sotib olish)")
    o_col1.dataframe(bids, use_container_width=True)
    o_col2.write("🔴 Asks (Sotish)")
    o_col2.dataframe(asks, use_container_width=True)

with col_right:
    st.subheader("💡 AI Signal & Tahlil")
    rsi_val = ta.rsi(df['close'], length=14).iloc[-1]
    if rsi_val < 30:
        st.success(f"STRONG BUY: RSI ({rsi_val:.2f}) haddan tashqari sotilgan hududda.")
    elif rsi_val > 70:
        st.error(f"STRONG SELL: RSI ({rsi_val:.2f}) haddan tashqari sotib olingan hududda.")
    else:
        st.warning(f"NEUTRAL: Bozor hozircha yo'nalish tanlamadi. RSI: {rsi_val:.2f}")
    
    st.info("Eslatma: Ushbu tahlil avtomatik algoritmlar tomonidan generatsiya qilingan.")

# --- AVTOMATIK YANGILANISH ---
time.sleep(2)
st.rerun()