# Project Memory: Financial Dashboard & Backtesting System

## Architecture Overview
This system is built as a modular financial analysis tool with three main layers:
1.  **Data Ingestion:** A multi-provider system (`data_providers/`) supporting Alpaca, Massive.com (REST & WebSockets), and Massive.com S3 Flat Files for bulk data.
2.  **Analysis Engine:** Includes a `Screener` for market-wide filtering (using daily data) and a `PatternDetector` for technical analysis.
3.  **Execution Engine:** A Backtrader-based `BacktestEngine` that can run simulations on historical data (specifically optimized for 2-minute "paper trading" simulations).

## Current Status (April 2026)
- **Massive.com Integration:** Fully implemented with REST (for fundamentals), WebSockets (for real-time minute aggregates), and S3 (for bulk year-long research).
- **Web Dashboard:** Streamlit app (`app.py`) is functional with tabs for Analysis, Screening, and Backtesting.
- **Screener:** Optimized to rank stocks by momentum and volume spikes.
- **Data Caching:** MassiveS3Provider handles local caching in `data_cache/` to avoid redundant downloads.

## Operational Workflows
- **For Screening:** Use `MassiveS3Provider` with daily flat files to scan the whole market.
- **For Simulation:** Use 2-minute intervals fetched via `MassiveS3Provider` (cached) or `MassiveProvider` (REST/WS).
- **Environment:** All code is strictly sandboxed in `C:\Users\Dario\Documents\GEmini CLI`.

## Technical Notes
- **Dependencies:** `polygon-api-client`, `boto3`, `backtrader`, `streamlit`, `pandas-ta`.
- **API Keys:** Managed via `.env` file (see `.env.example`).
