import streamlit as st
import pandas as pd
import requests
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import time

# --- 1. SAHIFA KONFIGURATSIYASI ---
st.set_page_config(page_title="BahorDev Pro Terminal", layout="wide", initial_sidebar_state="expanded")

# Professional Dark UI
st.markdown("""
    <style>
    .main { background-color: #0e1117; }
    div[data-testid="stMetricValue"] { font-size: 24px; color: #00ffc8; }
    .stAlert { border-radius: 10px; }
    </style>
    """, unsafe_allow_html=True)

# --- 2. TEXNIK ANALIZ FUNKSIYALARI ---
def add_indicators(df):
    # EMA (Exponential Moving Average)
    df['EMA9'] = df['close'].ewm(span=9, adjust=False).mean()
    df['EMA21'] = df['close'].ewm(span=21, adjust=False).mean()
    
    # RSI (Relative Strength Index)
    delta = df['close'].diff()
    gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
    loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
    rs = gain / loss
    df['RSI'] = 100 - (100 / (1 + rs))
    
    # MACD
    exp1 = df['close'].ewm(span=12, adjust=False).mean()
    exp2 = df['close'].ewm(span=26, adjust=False).mean()
    df['MACD'] = exp1 - exp2
    df['Signal'] = df['MACD'].ewm(span=9, adjust=False).mean()
    return df

# --- 3. BINANCE MA'LUMOTLARINI OLISH ---
@st.cache_data(ttl=2)
def fetch_data(symbol, interval):
    url = f"https://api.binance.com/api/v3/klines?symbol={symbol}&interval={interval}&limit=150"
    try:
        response = requests.get(url)
        data = response.json()
        if isinstance(data, list):
            df = pd.DataFrame(data, columns=['time','open','high','low','close','vol','c_t','q_v','trd','tb_v','tq_v','ign'])
            df['time'] = pd.to_datetime(df['time'], unit='ms')
            for col in ['open', 'high', 'low', 'close', 'vol']:
                df[col] = df[col].astype(float)
            return add_indicators(df)
        return pd.DataFrame()
    except:
        return pd.DataFrame()

@st.cache_data(ttl=1)
def get_order_book(symbol):
    url = f"https://api.binance.com/api/v3/depth?symbol={symbol}&limit=10"
    try:
        response = requests.get(url)
        data = response.json()
        # 'bids' va 'asks' mavjudligini tekshirish (Xatolikni oldini olish)
        if 'bids' in data and 'asks' in data:
            bids = pd.DataFrame(data['bids'], columns=['Price', 'Quantity']).astype(float)
            asks = pd.DataFrame(data['asks'], columns=['Price', 'Quantity']).astype(float)
            return bids, asks
        return pd.DataFrame(), pd.DataFrame()
    except:
        return pd.DataFrame(), pd.DataFrame()

# --- 4. SIDEBAR ---
st.sidebar.title("💎 ELITE ANALYTICS")
symbol = st.sidebar.selectbox("Valyuta:", ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT"], index=0)
timeframe = st.sidebar.radio("Timeframe:", ["1m", "5m", "15m", "1h", "1d"], horizontal=True)

# --- 5. ASOSIY PANEL ---
df = fetch_data(symbol, timeframe)
bids, asks = get_order_book(symbol)

if not df.empty:
    col1, col2 = st.columns([3, 1])

    with col1:
        # Grafik yaratish
        fig = make_subplots(rows=3, cols=1, shared_xaxes=True, 
                            vertical_spacing=0.05, row_heights=[0.6, 0.2, 0.2])

        # Candlestick + EMA
        fig.add_trace(go.Candlestick(x=df['time'], open=df['open'], high=df['high'], 
                                     low=df['low'], close=df['close'], name="Market"), row=1, col=1)
        fig.add_trace(go.Scatter(x=df['time'], y=df['EMA9'], name="EMA 9", line=dict(color='#00ffc8')), row=1, col=1)
        fig.add_trace(go.Scatter(x=df['time'], y=df['EMA21'], name="EMA 21", line=dict(color='#ff007a')), row=1, col=1)

        # RSI
        fig.add_trace(go.Scatter(x=df['time'], y=df['RSI'], name="RSI", line=dict(color='#ffd700')), row=2, col=1)
        fig.add_hline(y=70, line_dash="dash", line_color="red", row=2, col=1)
        fig.add_hline(y=30, line_dash="dash", line_color="green", row=2, col=1)

        # MACD
        fig.add_trace(go.Bar(x=df['time'], y=df['MACD']-df['Signal'], name="MACD"), row=3, col=1)

        fig.update_layout(height=800, template="plotly_dark", showlegend=False, xaxis_rangeslider_visible=False)
        st.plotly_chart(fig, use_container_width=True)

    with col2:
        # Narx metrikasi
        curr_p = df['close'].iloc[-1]
        prev_p = df['close'].iloc[-2]
        change = ((curr_p - prev_p) / prev_p) * 100
        st.metric(f"{symbol}", f"${curr_p:,.2f}", f"{change:.2f}%")
        
        st.markdown("### 🏦 Order Book")
        if not asks.empty:
            st.write("🔴 Asks (Sotuv)")
            st.dataframe(asks.sort_values(by="Price", ascending=False), hide_index=True, use_container_width=True)
            st.write("🟢 Bids (Sotib olish)")
            st.dataframe(bids, hide_index=True, use_container_width=True)
        else:
            st.warning("Order book yuklanmadi (API Limit).")

    # Avtomat yangilash (Binance block qilmasligi uchun 5 soniya)
    time.sleep(5)