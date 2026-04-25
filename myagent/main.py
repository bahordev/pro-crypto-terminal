import streamlit as st
import pandas as pd
import numpy as np
import requests
import plotly.graph_objects as go
from plotly.subplots import make_subplots
from datetime import datetime
import logging
import time

# --- 1. LOGGING & CONFIGURATION ---
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

class CryptoTerminal:
    def __init__(self):
        self.base_url = "https://api.binance.com/api/v3"
        self.setup_ui()

    def setup_ui(self):
        st.set_page_config(page_title="BahorDev Elite Terminal v2.5", layout="wide", initial_sidebar_state="expanded")
        st.markdown("""
            <style>
            .stApp { background-color: #0b0e11; color: white; }
            .price-card { border: 1px solid #2b2f36; padding: 20px; border-radius: 10px; background: #1e2329; }
            .signal-buy { color: #00ffc8; font-weight: bold; border: 1px solid #00ffc8; padding: 5px; border-radius: 5px; }
            .signal-sell { color: #ff3b69; font-weight: bold; border: 1px solid #ff3b69; padding: 5px; border-radius: 5px; }
            </style>
        """, unsafe_allow_html=True)

    # --- 2. DATA ENGINE ---
    @st.cache_data(ttl=2)
    def fetch_market_data(_self, symbol: str, interval: str, limit: int = 200):
        try:
            endpoint = f"{_self.base_url}/klines"
            params = {"symbol": symbol, "interval": interval, "limit": limit}
            response = requests.get(endpoint, params=params, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            df = pd.DataFrame(data, columns=[
                'OpenTime', 'Open', 'High', 'Low', 'Close', 'Volume',
                'CloseTime', 'QuoteAssetVolume', 'NumberOfTrades',
                'TakerBuyBaseAssetVolume', 'TakerBuyQuoteAssetVolume', 'Ignore'
            ])
            
            # Data Cleaning
            df['time'] = pd.to_datetime(df['OpenTime'], unit='ms')
            numeric_cols = ['Open', 'High', 'Low', 'Close', 'Volume']
            df[numeric_cols] = df[numeric_cols].apply(pd.to_numeric)
            return df
        except Exception as e:
            logger.error(f"Data Fetch Error: {e}")
            return pd.DataFrame()

    @st.cache_data(ttl=1)
    def fetch_order_book(_self, symbol: str):
        try:
            endpoint = f"{_self.base_url}/depth"
            params = {"symbol": symbol, "limit": 15}
            res = requests.get(endpoint, params=params).json()
            bids = pd.DataFrame(res['bids'], columns=['Price', 'Qty']).astype(float)
            asks = pd.DataFrame(res['asks'], columns=['Price', 'Qty']).astype(float)
            return bids, asks
        except:
            return pd.DataFrame(), pd.DataFrame()

    # --- 3. ANALYTICS ENGINE (QUANT LOGIC) ---
    def apply_technical_analysis(self, df):
        # EMA Strategy
        df['EMA9'] = df['Close'].ewm(span=9, adjust=False).mean()
        df['EMA21'] = df['Close'].ewm(span=21, adjust=False).mean()
        df['EMA50'] = df['Close'].ewm(span=50, adjust=False).mean()

        # Bollinger Bands
        df['SMA20'] = df['Close'].rolling(window=20).mean()
        df['STD20'] = df['Close'].rolling(window=20).std()
        df['Upper_BB'] = df['SMA20'] + (df['STD20'] * 2)
        df['Lower_BB'] = df['SMA20'] - (df['STD20'] * 2)

        # RSI
        delta = df['Close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(window=14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(window=14).mean()
        df['RSI'] = 100 - (100 / (1 + (gain / loss)))

        # MACD
        exp1 = df['Close'].ewm(span=12, adjust=False).mean()
        exp2 = df['Close'].ewm(span=26, adjust=False).mean()
        df['MACD'] = exp1 - exp2
        df['Signal_Line'] = df['MACD'].ewm(span=9, adjust=False).mean()
        
        return df

    def generate_trading_signals(self, df):
        last_row = df.iloc[-1]
        prev_row = df.iloc[-2]
        
        signal = "NEUTRAL"
        # Golden Cross / RSI Strategy
        if last_row['EMA9'] > last_row['EMA21'] and last_row['RSI'] < 70:
            signal = "STRONG BUY"
        elif last_row['EMA9'] < last_row['EMA21'] and last_row['RSI'] > 30:
            signal = "STRONG SELL"
            
        return signal, last_row['Close']

    # --- 4. VISUALIZATION ENGINE ---
    def plot_dashboard(self, df, symbol):
        fig = make_subplots(
            rows=3, cols=1, 
            shared_xaxes=True, 
            vertical_spacing=0.03, 
            row_heights=[0.5, 0.2, 0.2],
            subplot_titles=(f'{symbol} Price Action', 'Relative Strength Index (RSI)', 'MACD Momentum')
        )

        # Candlestick
        fig.add_trace(go.Candlestick(
            x=df['time'], open=df['Open'], high=df['High'], low=df['Low'], close=df['Close'],
            name="Candlesticks"
        ), row=1, col=1)

        # Indicators on Main Chart
        fig.add_trace(go.Scatter(x=df['time'], y=df['EMA9'], name="EMA 9", line=dict(color='#00ffc8', width=1)), row=1, col=1)
        fig.add_trace(go.Scatter(x=df['time'], y=df['EMA50'], name="EMA 50", line=dict(color='#ff3b69', width=1)), row=1, col=1)
        fig.add_trace(go.Scatter(x=df['time'], y=df['Upper_BB'], name="BB Upper", line=dict(dash='dash', color='rgba(173, 204, 255, 0.3)')), row=1, col=1)
        fig.add_trace(go.Scatter(x=df['time'], y=df['Lower_BB'], name="BB Lower", line=dict(dash='dash', color='rgba(173, 204, 255, 0.3)')), row=1, col=1)

        # RSI
        fig.add_trace(go.Scatter(x=df['time'], y=df['RSI'], name="RSI", line=dict(color='#f3ba2f')), row=2, col=1)
        fig.add_hline(y=70, line_dash="dot", line_color="#ff3b69", row=2, col=1)
        fig.add_hline(y=30, line_dash="dot", line_color="#00ffc8", row=2, col=1)

        # MACD
        fig.add_trace(go.Bar(x=df['time'], y=df['MACD'] - df['Signal_Line'], name="MACD Histogram"), row=3, col=1)

        fig.update_layout(height=900, template="plotly_dark", showlegend=False, xaxis_rangeslider_visible=False)
        return fig

    # --- 5. EXECUTION ---
    def run(self):
        st.sidebar.title("💠 BAHORDEV PRO")
        symbol = st.sidebar.selectbox("Market Asset", ["BTCUSDT", "ETHUSDT", "SOLUSDT", "BNBUSDT", "ADAUSDT"], index=0)
        timeframe = st.sidebar.radio("Analysis Window", ["1m", "5m", "15m", "1h", "4h", "1d"], index=2, horizontal=True)

        df = self.fetch_market_data(symbol, timeframe)
        
        if not df.empty:
            df = self.apply_technical_analysis(df)
            signal, price = self.generate_trading_signals(df)
            
            # Header Metrics
            m1, m2, m3 = st.columns(3)
            with m1:
                st.metric("Live Price", f"${price:,.2f}")
            with m2:
                sig_class = "signal-buy" if "BUY" in signal else "signal-sell" if "SELL" in signal else ""
                st.markdown(f"AI Strategy: <span class='{sig_class}'>{signal}</span>", unsafe_allow_html=True)
            with m3:
                st.metric("RSI (14)", f"{df['RSI'].iloc[-1]:.2f}")

            # Main Layout
            c1, c2 = st.columns([3, 1])
            with c1:
                fig = self.plot_dashboard(df, symbol)
                st.plotly_chart(fig, use_container_width=True)
            
            with c2:
                st.markdown("### 📊 Order Book")
                bids, asks = self.fetch_order_book(symbol)
                st.write("Asks (Sellers)")
                st.dataframe(asks.sort_values(by='Price', ascending=False), hide_index=True)
                st.write("Bids (Buyers)")
                st.dataframe(bids, hide_index=True)

            time.sleep(5)
            st.rerun()

if __name__ == "__main__":
    terminal = CryptoTerminal()
    terminal.run()