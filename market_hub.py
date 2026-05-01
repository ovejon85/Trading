import pandas as pd
import numpy as np
import os

class MarketHub:
    def __init__(self):
        pass

    def load_market_data(self, filepath="market_data_gold.parquet"):
        """
        Loads the 'market_data_gold.parquet' file as requested.
        If the file is not found locally, falls back to generating
        sample data to allow the backtest to run.
        """
        if os.path.exists(filepath):
            print(f"Loading data from {filepath}...")
            df = pd.read_parquet(filepath)

            # Ensure index is datetime if it's not already
            if not isinstance(df.index, pd.DatetimeIndex):
                if 'datetime' in df.columns:
                    df.set_index('datetime', inplace=True)
                elif 'date' in df.columns:
                    df.set_index('date', inplace=True)

            return df
        else:
            print(f"Warning: {filepath} not found. Using fallback mock data for backtest.")

            # Generate some sample data for backtesting
            dates = pd.date_range("2023-01-01", "2023-12-31", freq="B")
            num_days = len(dates)

            np.random.seed(42)
            close = 100 + np.cumsum(np.random.randn(num_days))
            high = close + np.random.rand(num_days) * 2
            low = close - np.random.rand(num_days) * 2
            open_price = low + np.random.rand(num_days) * (high - low)
            volume = np.random.randint(1000, 100000, size=num_days)

            df = pd.DataFrame({
                "datetime": dates,
                "open": open_price,
                "high": high,
                "low": low,
                "close": close,
                "volume": volume
            })

            df.set_index("datetime", inplace=True)
            return df
