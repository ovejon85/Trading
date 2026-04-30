import os
import pandas as pd
import pandas_ta as ta
from pathlib import Path
from data_providers.massive_s3_provider import MassiveS3Provider

class IntradayLoader:
    def __init__(self, cache_dir: str = "intraday_cache"):
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)
        self.provider = MassiveS3Provider()

    def get_intraday_data(self, symbol: str, start: str, end: str) -> pd.DataFrame:
        """
        Fetches 2m or 1m intraday data and resamples it to 2m if needed,
        or just fetches the 1m and resamples to 2m, caching it as Parquet.
        """
        cache_file = self.cache_dir / f"{symbol}_{start}_{end}_2m.parquet"

        if cache_file.exists():
            return pd.read_parquet(cache_file)

        df = self.provider.fetch_data(symbol, "1Min", start, end)

        if df.empty:
            return df

        # Resample to 2m
        df_2m = self.resample_data(df, "2min")

        # Calculate indicators
        df_2m = self.add_indicators(df_2m)

        # Save to cache
        df_2m.to_parquet(cache_file)

        return df_2m

    def resample_data(self, df: pd.DataFrame, timeframe: str) -> pd.DataFrame:
        """
        Resamples a DataFrame to a given timeframe (e.g., '2min', '5min', '15min').
        """
        if df.empty:
            return df

        resampled = df.resample(timeframe).agg({
            'Open': 'first',
            'High': 'max',
            'Low': 'min',
            'Close': 'last',
            'Volume': 'sum'
        }).dropna()

        return resampled

    def add_indicators(self, df: pd.DataFrame) -> pd.DataFrame:
        """
        Adds Bollinger Bands, Daily VWAP, and 2-Day VWAP.
        """
        if df.empty or len(df) < 20:
            return df

        # Calculate Bollinger Bands
        bb = ta.bbands(df['Close'], length=20, std=2)
        if bb is not None:
            df = pd.concat([df, bb], axis=1)

        # Calculate Daily VWAP
        df['VWAP_D'] = ta.vwap(high=df['High'], low=df['Low'], close=df['Close'], volume=df['Volume'], anchor='D')

        # Calculate 2-Day VWAP
        # Use rolling 2-day VWAP or manually compute cumulative values.
        # Assuming 2 trading days means around 390 * 2 minutes if the market is 6.5 hours long.
        tp = (df['High'] + df['Low'] + df['Close']) / 3
        tp_v = tp * df['Volume']

        df['VWAP_2D'] = tp_v.rolling(window=390*2).sum() / df['Volume'].rolling(window=390*2).sum()

        return df

    def fetch_for_markethub(self, symbol: str, date: str) -> dict:
        """
        Method to simulate integration with MarketHub (which is a framework architecture component mentioned in memory).
        Given a daily signal candidate, fetch intraday data and return 5m/15m data ready for use.
        """
        dt = pd.to_datetime(date)
        start_dt = dt - pd.Timedelta(days=2) # 2 days before for 2-day VWAP
        start = start_dt.strftime('%Y-%m-%d')
        end = dt.strftime('%Y-%m-%d')

        df = self.get_intraday_data(symbol, start, end)

        if df.empty:
            return {"5m": df, "15m": df}

        df_5m = self.resample_data(df, "5min")
        df_15m = self.resample_data(df, "15min")

        return {"5m": df_5m, "15m": df_15m}
