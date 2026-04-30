import pandas as pd
import pandas_ta as ta

def enrich_data(input_file="market_data_5y.parquet", output_file="market_data_gold.parquet"):
    print(f"Loading {input_file}...")
    df = pd.read_parquet(input_file)

    # Ensure it's sorted by symbol and date
    df = df.sort_values(by=["symbol", "date"]).reset_index(drop=True)

    enriched_dfs = []

    print("Enriching data with indicators...")
    for symbol, group in df.groupby("symbol"):
        # Create a copy to avoid SettingWithCopyWarning
        group = group.copy()

        # We need a proper DatetimeIndex for some pandas-ta functions to work best,
        # though not strictly necessary if 'date' is present.

        # Technical Indicators using pandas-ta
        group.ta.rsi(length=14, append=True)
        group.ta.sma(length=20, append=True)
        group.ta.sma(length=50, append=True)
        group.ta.sma(length=200, append=True)

        # ATR requires high, low, close
        group.ta.atr(length=14, append=True)

        # ATR%
        if "ATRr_14" in group.columns:
            group["ATR_pct"] = (group["ATRr_14"] / group["close"]) * 100

        # ROC (Rate of Change)
        group.ta.roc(length=21, append=True)

        # Bollinger Bands
        group.ta.bbands(length=20, std=2, append=True)

        # Forward Returns (T+1, T+5, T+10)
        # Shift close price backwards by N periods, calculate percentage change from current
        group["Fwd_Ret_1d"] = group["close"].shift(-1) / group["close"] - 1.0
        group["Fwd_Ret_5d"] = group["close"].shift(-5) / group["close"] - 1.0
        group["Fwd_Ret_10d"] = group["close"].shift(-10) / group["close"] - 1.0

        enriched_dfs.append(group)

    final_df = pd.concat(enriched_dfs).reset_index(drop=True)

    print(f"Saving to {output_file}...")
    final_df.to_parquet(output_file)
    print("Done!")

if __name__ == "__main__":
    enrich_data()
