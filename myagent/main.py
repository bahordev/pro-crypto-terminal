import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import time

# --- 1. SAHIFA SOZLAMALARI ---
st.set_page_config(page_title="BahorDev Pro Terminal", layout="wide", initial_sidebar_state="expanded")

# Professional qora mavzu (CSS)
st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    div[data-testid="stMetricValue"] { font-size: 24px; color: #00ffc8; }
    .stAlert { border-radius: 10px; border: 1px solid #1f2937; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. TEXNIK ANALIZ MODULI (BACKEND) ---
def add_indicators(df):
    # EMA (Exponential Moving Average) - Trendni aniqlash
    df['EMA9'] = df['close'].ewm(span=9, adjust=False).mean()
    df['EMA21'] = df['close'].ewm(span=21, adjust=False).mean()
    
    # RSI (Relative Strength Index) - Kuchlanish indeksi
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    
    # MACD (Moving Average Convergence Divergence)
    exp1 = df['close'].ewm(span=12, adjust=False).mean()
    exp2 = df['close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = exp1 - exp2
    df['Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
    return df

# --- 3. BINANCE API BILAN ISHLASH ---
@st.cache_data(ttl=2)
def get_crypto_data(symbol, interval):
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit=150"
    try:
        res = requests.get(url).json()
        df = pd.DataFrame(res, columns=['time','open','high','low','close','vol','c_time','q_vol','trades','tb_vol','tq_vol','ignore'])
        df['time'] = pd.to_datetime(df['time'], unit='ms')
        df[['open','high','low','close','vol']] = df[['open','high','low','close','vol']].apply(pd.to_numeric)
        return add_indicators(df)
    except:
        return pd.DataFrame()

@st.cache_data(ttl=1)
def get_order_book(symbol):
    url = f"https://api.binance.com/api/v3/depth?symbol={symbol}&limit=10"
    try:
        res = requests.get(url).json()
        bids = pd.DataFrame(res['bids'], columns=['Price', 'Qty']).astype(float)
        asks = pd.DataFrame(res['asks'], columns=['Price', 'Qty']).astype(float)
        return bids, asks
    except:
        return pd.DataFrame(), pd.DataFrame()

# --- 4. SIDEBAR (BOSHQARUV PANELI) ---
st.sidebar.title("💎 ELITE ANALYTICS")
target_coin = st.sidebar.selectbox("Valyuta:", ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT"], index=0)
tf = st.sidebar.radio("Vaqt (Timeframe):", ["1m", "5m", "15m", "1h", "1d"], horizontal=True)

# --- 5. ASOSIY EKRAN ---
df = get_crypto_data(target_coin, tf)

if not df.empty:
    col1, col2 = st.columns([3, 1])

    with col1:
        # Grafik yaratish
        fig = make_subplots(rows=3, cols=1, shared_xaxes=True, 
                            vertical_spacing=0.05, row_heights=[0.6, 0.2, 0.2])

        # Candlestick + EMA
        fig.add_trace(go.Candlestick(x=df['time'], open=df['open'], high=df['high'], 
                                     low=df['low'], close=df['close'], name="Narx"), row=1, col=1)
        fig.add_trace(go.Scatter(x=df['time'], y=df['EMA9'], name="EMA 9", line=dict(color='#00ffc8', width=1.5)), row=1, col=1)
        fig.add_trace # EMA 21 qo'shish
        fig.add_trace(go.Scatter(x=df['time'], y=df['EMA21'], name="EMA 21", line=dict(color='#ff007a', width=1.5)), row=1, col=1)

        # RSI grafik
        fig.add_trace(go.Scatter(x=df['time'], y=df['RSI'], name="RSI", line=dict(color='#ffd700')), row=2, col=1)
        fig.add_hline(y=70, line_dash="dash", line_color="red", row=2, col=1)
        fig.add_hline(y=30, line_dash="dash", line_color="green", row=2, col=1)

        # MACD Histogram
        fig.add_trace(go.Bar(x=df['time'], y=df['MACD']-df['Signal'], name="MACD"), row=3, col=1)

        fig.update_layout(height=800, template="plotly_dark", showlegend=False, xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        # Metrikalar va Order Book
        curr_p = df['close'].iloc[-1]
        prev_p = df['close'].iloc[-2]
        change = ((curr_p - prev_p) / prev_p) * 100
        st.metric(f"Narx: {target_coin}", f"${curr_p:,.2f}", f"{change:.2f}%")
        
        st.markdown("### 🏦 Order Book")
        bids, asks = get_order_book(target_coin)
        
        if not asks.empty:
            st.write("🔴 Sotuvchilar (Asks)")
            st.dataframe(asks.sort_values(by="Price", ascending=False), hide_index=True, use_container_width=True)
            st.write("🟢 Xaridorlar (Bids)")
            st.dataframe(bids, hide_index=True, use_container_width=True)

    # Avtomat yangilash (Streamlit Cloud uchun optimallashgan)
    time.sleep(3)
    st.rerun()
else:
    st.error("Ma'lumot yuklashda xatolik. Binance API bilan aloqani tekshiring.")