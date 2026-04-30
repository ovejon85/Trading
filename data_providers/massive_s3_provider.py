import os
import boto3
import pandas as pd
from botocore.client import Config
from .base import DataProvider
from dotenv import load_dotenv
from pathlib import Path

load_dotenv()

class MassiveS3Provider(DataProvider):
    def __init__(self, cache_dir: str = "data_cache"):
        self.access_key = os.getenv("MASSIVE_S3_ACCESS_KEY")
        self.secret_key = os.getenv("MASSIVE_S3_SECRET_KEY")

        if not self.access_key or not self.secret_key:
            raise ValueError("MASSIVE_S3_ACCESS_KEY and MASSIVE_S3_SECRET_KEY must be set in the environment.")

        self.endpoint_url = "https://files.massive.com"
        self.bucket_name = "flatfiles"
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(exist_ok=True)

        self.s3 = boto3.client(
            's3',
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
            endpoint_url=self.endpoint_url,
            config=Config(signature_version='s3v4')
        )

    def _get_s3_path(self, date: str, data_type: str = "day_aggs_v1") -> str:
        # Expected date format: YYYY-MM-DD
        dt = pd.to_datetime(date)
        year = dt.strftime('%Y')
        month = dt.strftime('%m')
        day = dt.strftime('%Y-%m-%d')
        return f"us_stocks_sip/{data_type}/{year}/{month}/{day}.csv.gz"

    def download_daily_file(self, date: str, data_type: str = "day_aggs_v1") -> Path:
        """Downloads a market-wide file for a specific day and returns the local path."""
        s3_key = self._get_s3_path(date, data_type)
        local_path = self.cache_dir / f"{data_type}_{date}.csv.gz"

        if not local_path.exists():
            print(f"Downloading {s3_key} to {local_path}...")
            self.s3.download_file(self.bucket_name, s3_key, str(local_path))
        
        return local_path

    def fetch_data(self, symbol: str, timeframe: str, start: str, end: str) -> pd.DataFrame:
        """
        Fetches data for a specific symbol by reading local flat files.
        Note: This is efficient if you have already downloaded the range.
        """
        dates = pd.date_range(start=start, end=end)
        all_data = []
        
        # Decide data type based on timeframe
        data_type = "minute_aggs_v1" if "Min" in timeframe else "day_aggs_v1"

        for date in dates:
            date_str = date.strftime('%Y-%m-%d')
            try:
                local_file = self.download_daily_file(date_str, data_type)
                df_day = pd.read_csv(local_file, compression='gzip')
                
                # Filter for the symbol
                df_symbol = df_day[df_day['ticker'] == symbol].copy()
                if not df_symbol.empty:
                    all_data.append(df_symbol)
            except Exception as e:
                # Common to fail on weekends/holidays if we don't handle them
                pass

        if not all_data:
            return pd.DataFrame()

        df = pd.concat(all_data)
        
        # Standardize columns to Backtrader format
        # Massive flat files use: ticker, open, high, low, close, volume, window_start, etc.
        df['timestamp'] = pd.to_datetime(df['window_start'], unit='ns') # Usually nanoseconds in v1
        df.set_index('timestamp', inplace=True)
        
        df.rename(columns={
            "open": "Open",
            "high": "High",
            "low": "Low",
            "close": "Close",
            "volume": "Volume"
        }, inplace=True)
        
        return df[['Open', 'High', 'Low', 'Close', 'Volume']].sort_index()

    def get_market_cap(self, symbol: str) -> float:
        # Flat files don't typically include market cap in the OHLCV files.
        # You would still use the REST API (MassiveProvider) for this.
        return 0.0

    def get_market_wide_day(self, date: str) -> pd.DataFrame:
        """Helper for the Screener to get everything at once."""
        local_file = self.download_daily_file(date)
        return pd.read_csv(local_file, compression='gzip')
