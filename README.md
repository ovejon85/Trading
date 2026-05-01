# Financial Dashboard & Backtesting System

This project is a high-performance framework for financial data analysis, screening, and vectorized backtesting, optimized for 5-year daily market sweeps.

## Core Features
- **Universal Research Infrastructure (Gold DB):** A 1.47GB local Parquet database (`market_data_gold.parquet`) containing 5 years of daily data (13.7M+ rows) with pre-calculated indicators (RSI, SMA, ATR) and forward returns.
- **Analysis Hub:** Polars-powered `MarketHub` for sub-second vectorized strategy evaluation across the entire market.
- **Multi-Source Data:** Support for Massive.com (S3 Flat Files, REST) and Alpaca APIs.
- **Yoelv1 Strategy Integration:** Native support for the `reversal_v3` mean-reversion model, including complex scoring, confluence detection, and sector-based portfolio clustering.
- **Interactive Dashboard:** Streamlit UI for visual research and trade logging.
- **AI-Agent Ready:** Integrated MCP server to expose research tools to AI assistants.

## Project Structure
- `market_hub.py`: The high-performance interface for Gold DB research.
- `sync_database.py`: Incremental update engine to keep Gold DB current from S3 sources.
- `TASTATION_LOGIC.md`: Comprehensive technical specifications for the Tastation ecosystem.
- `app.py`: The main Streamlit visualization application.
- `data_providers/`: Interfaces for Massive.com and Alpaca.
- `strategies/`: Core strategy definitions (e.g., `reversal_v3`, `bullish_engulfing`).

## Setup Instructions
1. **Install Dependencies:**
   ```bash
   pip install -r requirements.txt
   ```
2. **Configure API Keys:**
   - Create a `.env` file from `.env.example`.
   - Add your `MASSIVE_API_KEY` and broker credentials.
3. **Initialize Database:**
   - Run `python sync_database.py` to build/update your local Gold DB.
4. **Run Research Tools:**
   - Visual: `streamlit run app.py`
   - Command Line: Use `MarketHub` in your scripts for ultra-fast sweeps.

## Ongoing Work
- **Jules Implementation:** Automated backtest implementation of the Yoelv1 strategy is currently in progress (Session `17071597020818277567`).
- **Intraday Zoom:** Development of a JIT caching system for 2m/5m resolution analysis.
