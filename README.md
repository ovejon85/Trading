# Financial Dashboard & Backtesting System

This project is a flexible, extensible framework for financial data analysis, screening, and backtesting.

## Features
- **Multi-Source Data:** Support for Alpaca and Massive.com.
- **Web Dashboard:** Interactive UI built with Streamlit and Plotly.
- **Backtesting Engine:** Event-driven backtesting using Backtrader.
- **Stock Screener:** Filter stocks by market cap and price performance.
- **Pattern Detection:** Automated detection of candlestick patterns (e.g., Hammer).
- **Technical Analysis:** Integrated with `pandas-ta` for MACD, RSI, ATR, etc.
- **MCP Server:** Expose tools to AI agents via the Model Context Protocol.

## Project Structure
- `app.py`: The main Streamlit web application.
- `mcp_server.py`: MCP server to expose tools to AI assistants.
- `data_providers/`: Interfaces for fetching data from different APIs.
- `engine/`: Logic for screening and pattern detection.
- `backtest/`: The core backtesting execution engine.
- `strategies/`: Directory to define your trading strategies.

## Setup Instructions
1. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
2. **Configure API Keys:**
   - Copy `.env.example` to `.env`.
   - Add your Alpaca and Massive.com API keys.
3. **Run the Dashboard:**
   ```bash
   streamlit run app.py
   ```
4. **Run the MCP Server (Optional):**
   ```bash
   python mcp_server.py
   ```

## Defining New Strategies
To add a new strategy:
1. Create a new `.py` file in the `strategies/` directory.
2. Define a class that inherits from `bt.Strategy`.
3. Implement your logic in the `__init__` and `next` methods.
4. Import and select your strategy in `app.py`.
