# Project Memory: Financial Dashboard & Backtesting System

## Architecture Overview
This system is built as a modular financial analysis tool with three main layers:
1.  **Data Ingestion & Sync:** A multi-provider system (`data_providers/`) supporting Alpaca, Massive.com (REST, WebSockets, and S3). The **Sync Engine** (`sync_database.py`) incrementally updates the master database from S3.
2.  **Universal Research Infrastructure (Gold DB):** A high-performance **Gold Parquet Database** (`market_data_gold.parquet`) containing 5 years of daily data (13.7M+ rows) enriched with technical indicators and forward analysis returns.
3.  **Analysis Hub:** The `MarketHub` class (`market_hub.py`) provides a Polars-powered interface for sub-second strategy evaluation.
4.  **Tastation Integration:** Connection to the `https://tastation.onrender.com` intelligence layer for external signal and pattern validation.

## Current Status (April 2026)
- **Infrastructure Upgrade:** Research speed increased by 100x+ via Polars and enriched Gold Parquet format.
- **Strategy Documentation:** Full reverse-engineering of the Tastation logic completed and documented in `TASTATION_LOGIC.md`.
- **Active Implementation:** A Jules task (Session `17071597020818277567`) is currently implementing the `reversal_v3` backtest engine.
- **Security:** Strict .env protocol enforced for all API keys.

## Strategic Direction
- **Backtest Validation:** Verify the Yoelv1 strategy performance against the Gold DB once the Jules implementation is complete.
- **Short Strategy Optimization:** Refine conditions for "Red Day Reversals" on liquid stocks (>$100M Vol) using vectorized filtering.
- **Intraday Zoom:** Finalize the `IntradayLoader` for high-resolution analysis of spike candidates.

## Operational Workflows
- **To Research:** Use `MarketHub` in `market_hub.py` for sub-second vectorized filtering.
- **To Sync:** Run `python sync_database.py` to fetch and enrich the latest market days.
- **To Implement:** Reference `TASTATION_LOGIC.md` for any new strategy components related to the Yoel ecosystem.

## Strategy Deep Dive: Yoelv1 (reversal_v3)
*   **Core Model:** Mean-reversion triggered by Stochastic (14,3,3) crossovers in extreme zones (<20 / >80).
*   **Market Regime:** Filtered by ADX < 20 (`regime_ranging`).
*   **Stop/Target:** Strictly 1:2 Risk/Reward based on `0.5 * ATR` stop distance.
*   **Scoring Engine:**
    *   Base: `0.40`
    *   Regime Bonus: `+0.03`
    *   Confluence Bonus: `+0.15` (Signal ±5 bars from Double Top/Bottom, Wedges, etc.)
    *   Counter-Trend Penalty: `-0.15` (Opposing long-term SMA trend)
*   **Portfolio Caps (V2 Simulation):**
    *   ARG_ADR: 25% | MAG7: 35% | ETF: 50% | OTHER: 30%
