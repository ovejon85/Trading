# Tastation Ecosystem Technical Documentation

This document centralizes the technical specifications, scoring logic, and architectural details for the **Tastation (YoelPM)** financial research system, discovered via deep-dive analysis of the Render API and Cloudflare Worker.

## 1. System Architecture
The ecosystem operates across two primary cloud layers:
*   **Intelligence Layer (Render):** `https://tastation.onrender.com`
    *   Responsible for indicator calculation, signal detection (`reversal_v3`, `bullish_engulfing`), and pattern recognition.
*   **Execution & Simulation Layer (Worker):** `https://tastation-worker.yoelpm.workers.dev`
    *   Handles the paper-trading ledger, portfolio simulation, and persistence of the "V2" clustering logic.

---

## 2. Core Strategy: `reversal_v3`
A mean-reversion engine based on the Stochastic Oscillator and Average Directional Index.

### Indicator Thresholds
| Indicator | Parameter | Value/Trigger |
| :--- | :--- | :--- |
| **Stochastic** | Period | (14, 3, 3) |
| **Stoch Bullish** | Crossing | %K > %D while both < 20 |
| **Stoch Bearish** | Crossing | %K < %D while both > 80 |
| **ADX (14)** | Threshold | < 20 (Triggers `regime_ranging`) |
| **ATR (14)** | Stop Multiplier | 0.5x |

### Trade Management
*   **Stop Loss (Long):** `Low - 0.5 * ATR`
*   **Stop Loss (Short):** `High + 0.5 * ATR`
*   **Profit Target:** Calculated at a strict **1:2 Risk/Reward ratio** from the entry price.

---

## 3. Scoring Engine (`allocationScore`)
The system calculates a final confidence score (0.0 to 1.0) to determine position multipliers.

*   **Base Score:** `0.40`
*   **Regime Bonus:** `+0.03` (if ADX < 20)
*   **Confluence Bonus:** `+0.15` (if signal occurs within ±5 bars of a recognized chart pattern)
*   **Counter-Trend Penalty:** `-0.15` (if direction opposes long-term SMA trend)
*   **Advanced Factors:** `div_score` (MACD Divergence) and `struct_score` (Proximity to SR Levels).

---

## 4. Portfolio Simulation (V2 Logic)
The simulation enforces strict risk limits to prevent over-concentration.

### Global Risk Parameters
*   **Risk Per Trade:** 1% (`0.01`)
*   **Base Portfolio:** $100,000 USD
*   **Max Single Position:** 10% ($10,000)

### Position Multipliers (Score-Based)
| Score Range | Size Multiplier |
| :--- | :--- |
| `< 0.45` | 0.40x |
| `0.45 - 0.54` | 0.60x |
| `0.55 - 0.64` | 0.80x |
| `≥ 0.65` | 1.00x (Full Size) |

### Portfolio Cluster Caps (Exposure Limits)
| Cluster | Max Exposure | Tickers |
| :--- | :--- | :--- |
| **ARG_ADR** | 25% | GGAL, BMA, BBAR, SUPV, YPF, VIST, PAM, TGS, CEPU, EDN, LOMA, IRS |
| **MAG7** | 35% | AAPL, MSFT, NVDA, GOOGL, AMZN, META, TSLA |
| **ETF** | 50% | SPY, QQQ, IWM, DIA, SMH, SOXX, IGV, XOP, KRE, XHB, IYT, XME |
| **OTHER** | 30% | All other tickers |

---

## 5. API Endpoints Reference
### Intelligence (Render)
*   `GET /analyze/{ticker}?timeframe={tf}`: Core indicator data and active signals.
*   `GET /chart-patterns/{ticker}?timeframe={tf}&lookback={n}`: Detection of Double Tops/Bottoms, Wedges, and Triangles.
*   `GET /sr-levels/{ticker}`: Price levels with high "touches" representing support/resistance.
*   `GET /signals/recent?limit={n}`: Global stream of latest market signals.

### Execution (Worker)
*   `GET /paper-trades`: Full execution history and status (open/closed).
*   `POST /trades`: Entry point for registering new simulation trades.
*   `POST /trades/{id}/close`: Closing logic for active simulation positions.
