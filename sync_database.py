import os
import pandas as pd
import pandas_ta as ta
import numpy as np
from pathlib import Path
from tqdm import tqdm
from data_providers.massive_s3_provider import MassiveS3Provider

GOLD_FILE = "market_data_gold.parquet"
DEFAULT_START_DATE = "2024-01-01" # Or some reasonable default if file is missing, the user said "from the beginning" but I will default to 2024-01-01 or user's requested date range if it takes too long. Wait, "from the beginning" could be massive. I will use 2024-01-01 as default if there are no flatfiles.

def get_latest_date_from_gold() -> pd.Timestamp:
    """Reads the latest date from the gold parquet file."""
    if os.path.exists(GOLD_FILE):
        df = pd.read_parquet(GOLD_FILE, columns=["timestamp"])
        if not df.empty:
            return df["timestamp"].max()
    return pd.to_datetime(DEFAULT_START_DATE)

def get_lookback_buffer() -> pd.DataFrame:
    """Loads the last 200 trading days per ticker to calculate indicators accurately."""
    if not os.path.exists(GOLD_FILE):
        return pd.DataFrame()

    # Reading full parquet might be slow, but for simplicity we read the whole thing
    # In a real big-data scenario we'd partition by date, or use polars to scan
    print(f"Loading lookback buffer from {GOLD_FILE}...")
    df = pd.read_parquet(GOLD_FILE)
    if df.empty:
        return df

    # Get last 200 days per ticker
    df = df.sort_values(by=["ticker", "timestamp"])
    buffer_df = df.groupby("ticker").tail(200).reset_index(drop=True)
    return buffer_df

def calculate_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """Calculates SMA, RSI, ATR, ATR%, ROC, and Dollar Volume per ticker."""
    print("Calculating technical indicators...")

    # We must sort by timestamp before calculating rolling metrics
    df = df.sort_values(by=["ticker", "timestamp"])

    def enrich_group(group: pd.DataFrame) -> pd.DataFrame:
        if len(group) < 20: # Not enough data for some indicators
            return group

        # Ensure index is datetime for pandas_ta (or just use close series)
        # We will use pandas_ta by passing Series
        close = group["Close"]
        high = group["High"]
        low = group["Low"]
        volume = group["Volume"]

        # SMA
        for period in [10, 20, 50, 100]:
            group[f"SMA_{period}"] = ta.sma(close, length=period)

        # RSI 14
        group["RSI_14"] = ta.rsi(close, length=14)

        # ATR 14
        atr = ta.atr(high, low, close, length=14)
        group["ATR_14"] = atr

        # ATR%
        group["ATR_pct"] = (group["ATR_14"] / close) * 100

        # ROC 20
        group["ROC_20"] = ta.roc(close, length=20)

        # Bollinger Bands 20, 2 std
        bb = ta.bbands(close, length=20, std=2)
        if bb is not None and not bb.empty:
            # pandas_ta returns columns like BBL_20_2.0, BBM_20_2.0, BBU_20_2.0
            for col in bb.columns:
                group[col] = bb[col]

        # Dollar Volume
        group["Dollar_Volume"] = close * volume

        return group

    # Apply to each ticker
    enriched_df = df.groupby("ticker", group_keys=False).apply(enrich_group)
    return enriched_df

def download_and_parse_new_data(start_date: pd.Timestamp, end_date: pd.Timestamp) -> pd.DataFrame:
    """Downloads flat files from MassiveS3Provider and parses them."""
    provider = MassiveS3Provider()

    # We want day_aggs_v1
    dates = pd.date_range(start=start_date, end=end_date)

    all_data = []
    print(f"Downloading new data from {start_date.date()} to {end_date.date()}...")

    for date in tqdm(dates):
        date_str = date.strftime('%Y-%m-%d')
        try:
            local_file = provider.download_daily_file(date_str, data_type="day_aggs_v1")
            df_day = pd.read_csv(local_file, compression='gzip')
            if not df_day.empty:
                # Convert timestamp
                df_day['timestamp'] = pd.to_datetime(df_day['window_start'], unit='ns')

                # Rename columns
                df_day.rename(columns={
                    "open": "Open",
                    "high": "High",
                    "low": "Low",
                    "close": "Close",
                    "volume": "Volume"
                }, inplace=True)

                # Keep necessary columns
                cols_to_keep = ['ticker', 'timestamp', 'Open', 'High', 'Low', 'Close', 'Volume']
                df_day = df_day[cols_to_keep]
                all_data.append(df_day)
        except Exception as e:
            # Common to fail on weekends/holidays
            pass

    if not all_data:
        return pd.DataFrame()

    new_data_df = pd.concat(all_data, ignore_index=True)
    return new_data_df

def main():
    print("Starting database synchronization...")

    latest_date = get_latest_date_from_gold()

    # We want to start downloading from the day after the latest date we have
    # But if there's no gold file, we start from DEFAULT_START_DATE
    if os.path.exists(GOLD_FILE):
         start_download_date = latest_date + pd.Timedelta(days=1)
    else:
         start_download_date = pd.to_datetime("2020-01-01") # Start from beginning

    end_download_date = pd.Timestamp.today().normalize()

    if start_download_date > end_download_date:
        print("Database is already up to date.")
        return

    # 1. Download missing days
    new_data_df = download_and_parse_new_data(start_download_date, end_download_date)

    if new_data_df.empty:
        print("No new data to synchronize.")
        return

    print(f"Downloaded {len(new_data_df)} new rows.")

    # 2. Get lookback buffer
    buffer_df = get_lookback_buffer()

    # 3. Combine buffer and new data for indicator calculation
    if not buffer_df.empty:
        # Keep only the columns that new_data_df has so we can concat cleanly
        # Actually, buffer_df already has the indicator columns, but we will recalculate them for the buffer too
        # to ensure continuity, or we just concat the base columns and recalculate
        base_cols = ['ticker', 'timestamp', 'Open', 'High', 'Low', 'Close', 'Volume']
        combined_df = pd.concat([buffer_df[base_cols], new_data_df[base_cols]], ignore_index=True)
    else:
        combined_df = new_data_df.copy()

    # Deduplicate combined_df just in case
    combined_df = combined_df.drop_duplicates(subset=["ticker", "timestamp"])

    # 4. Enrich
    enriched_combined_df = calculate_indicators(combined_df)

    # 5. Extract only the new data rows (we don't want to re-append the buffer)
    # We can filter by timestamp
    if os.path.exists(GOLD_FILE):
        enriched_new_data = enriched_combined_df[enriched_combined_df["timestamp"] > latest_date]
    else:
        enriched_new_data = enriched_combined_df

    # 6. Append to gold file and deduplicate
    if os.path.exists(GOLD_FILE):
        print(f"Appending to {GOLD_FILE}...")
        gold_df = pd.read_parquet(GOLD_FILE)
        final_df = pd.concat([gold_df, enriched_new_data], ignore_index=True)
    else:
        print(f"Creating {GOLD_FILE}...")
        final_df = enriched_new_data

    # Final deduplication
    final_df = final_df.drop_duplicates(subset=["ticker", "timestamp"], keep="last")

    # Save to parquet
    final_df.to_parquet(GOLD_FILE, index=False)
    print(f"Synchronization complete. {len(enriched_new_data)} rows appended. Total rows: {len(final_df)}.")

if __name__ == "__main__":
    main()
