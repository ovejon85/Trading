import streamlit as st
import pandas as pd
import plotly.graph_objects as go
from data_providers.alpaca_provider import AlpacaProvider
from data_providers.massive_provider import MassiveProvider
from data_providers.massive_s3_provider import MassiveS3Provider
from engine.screener import Screener
from engine.pattern_detector import PatternDetector
from backtest.engine import BacktestEngine
from strategies.sample_strategy import MACD_RSI_Strategy
import pandas_ta as ta

st.set_page_config(page_title="Financial Dashboard", layout="wide")

st.title("📈 Financial Dashboard & Backtesting")

# Sidebar - Configuration
st.sidebar.header("Settings")
provider_name = st.sidebar.selectbox("Data Provider", ["Alpaca", "Massive REST", "Massive S3"])
symbol = st.sidebar.text_input("Symbol", "AAPL")
timeframe = st.sidebar.selectbox("Timeframe", ["1Day", "1Hour", "1Min"])
start_date = st.sidebar.date_input("Start Date", pd.to_datetime("2023-01-01"))
end_date = st.sidebar.date_input("End Date", pd.to_datetime("today"))

# Initialize Provider
if provider_name == "Alpaca":
    provider = AlpacaProvider()
elif provider_name == "Massive REST":
    provider = MassiveProvider()
else:
    provider = MassiveS3Provider()

# Main Tabs
tab1, tab2, tab3 = st.tabs(["Analysis", "Screener", "Backtest"])

with tab1:
    st.header(f"Analysis: {symbol}")
    if st.button("Fetch & Analyze"):
        df = provider.fetch_data(symbol, timeframe, str(start_date), str(end_date))
        if not df.empty:
            # Indicators
            df.ta.macd(append=True)
            df.ta.rsi(append=True)
            df.ta.atr(append=True)
            
            # Chart
            fig = go.Figure(data=[go.Candlestick(x=df.index,
                            open=df['Open'], high=df['High'],
                            low=df['Low'], close=df['Close'], name="Price")])
            
            # Pattern Detection
            hammers = PatternDetector.is_hammer(df)
            if hammers.any():
                hammer_dates = df.index[hammers]
                fig.add_trace(go.Scatter(x=hammer_dates, y=df.loc[hammer_dates, 'Low'] * 0.98,
                                         mode="markers", marker=dict(symbol="triangle-up", size=10, color="green"),
                                         name="Hammer Pattern"))

            st.plotly_chart(fig, use_container_width=True)
            st.dataframe(df.tail())
        else:
            st.error("No data found for this symbol/range.")

with tab2:
    st.header("Stock Screener (Daily Data)")
    symbols_list = st.text_area("Symbols (comma separated)", "AAPL, MSFT, TSLA, GOOGL, AMD, NVDA, META, AMZN, NFLX")
    col1, col2 = st.columns(2)
    with col1:
        min_cap = st.number_input("Min Market Cap ($)", value=0)
        min_change = st.number_input("Min Price Change (%)", value=1.0)
    with col2:
        min_vol = st.number_input("Min Volume Spike (x Avg)", value=1.2)
        lookback = st.slider("Lookback Days", 1, 30, 7)
    
    if st.button("Run Optimized Screener"):
        screener = Screener(provider)
        list_of_symbols = [s.strip() for s in symbols_list.split(",")]
        results = screener.screen(list_of_symbols, min_market_cap=min_cap, min_price_change=min_change, min_vol_spike=min_vol, days=lookback)
        
        if results:
            st.success(f"Found {len(results)} matches!")
            st.table(results)
            st.session_state['screened_results'] = results
        else:
            st.info("No stocks matched your criteria.")

with tab3:
    st.header("Paper Trading Simulation (2-Min Data)")
    sim_symbol = st.selectbox("Select Screened Symbol", 
                             [r['symbol'] for r in st.session_state.get('screened_results', [])] if 'screened_results' in st.session_state else [symbol])
    
    if st.button("Run 2-Min Simulation"):
        # Use last 3 market days for high-res simulation
        sim_start = (pd.Timestamp.now() - pd.Timedelta(days=3)).strftime('%Y-%m-%d')
        sim_end = pd.Timestamp.now().strftime('%Y-%m-%d')
        
        st.write(f"Fetching 2-minute data for {sim_symbol} from {sim_start} to {sim_end}...")
        df_2m = provider.fetch_data(sim_symbol, "2Min", sim_start, sim_end)
        
        if not df_2m.empty:
            st.write(f"Loaded {len(df_2m)} bars. Running backtest...")
            engine = BacktestEngine(df_2m, MACD_RSI_Strategy)
            engine.run()
            
            final_val = engine.cerebro.broker.getvalue()
            st.metric(f"Simulation Result ({sim_symbol})", f"${final_val:.2f}", delta=f"{final_val - 10000.0:.2f}")
            
            # Plotly Chart for 2Min data
            fig_sim = go.Figure(data=[go.Candlestick(x=df_2m.index,
                                open=df_2m['Open'], high=df_2m['High'],
                                low=df_2m['Low'], close=df_2m['Close'], name="2Min Price")])
            st.plotly_chart(fig_sim, use_container_width=True)
        else:
            st.error("Could not fetch 2-minute data. Check your API limits or symbol availability.")
