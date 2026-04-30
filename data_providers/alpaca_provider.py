import os
import pandas as pd
from alpaca.data.historical import StockHistoricalDataClient
from alpaca.data.requests import StockBarsRequest
from alpaca.data.timeframe import TimeFrame
from .base import DataProvider
from dotenv import load_dotenv

load_dotenv()

class AlpacaProvider(DataProvider):
    def __init__(self):
        api_key = os.getenv("ALPACA_API_KEY")
        secret_key = os.getenv("ALPACA_SECRET_KEY")
        if not api_key or not secret_key:
            raise ValueError(
                "Alpaca API credentials missing. Please set ALPACA_API_KEY and ALPACA_SECRET_KEY "
                "in your environment variables or .env file."
            )
        self.client = StockHistoricalDataClient(api_key, secret_key)

    def fetch_data(self, symbol: str, timeframe: str, start: str, end: str) -> pd.DataFrame:
        # Parse timeframe: e.g., '2Min', '1Day', '1Hour'
        import re
        match = re.match(r"(\d+)?([a-zA-Z]+)", timeframe)
        multiplier = int(match.group(1)) if match.group(1) else 1
        unit_str = match.group(2).lower()

        if "min" in unit_str:
            tf = TimeFrame.Minute
        elif "hour" in unit_str:
            tf = TimeFrame.Hour
        elif "day" in unit_str:
            tf = TimeFrame.Day
        else:
            tf = TimeFrame.Day
        
        # Alpaca TimeFrame can take a multiplier in newer SDKs, 
        # but for simplicity we'll handle standard ones or use custom if supported.
        # Actually, TimeFrame.Minute with multiplier is: TimeFrame(multiplier, TimeFrameUnit.Minute)
        from alpaca.data.timeframe import TimeFrameUnit
        if "min" in unit_str:
            tf = TimeFrame(multiplier, TimeFrameUnit.Minute)
        elif "hour" in unit_str:
            tf = TimeFrame(multiplier, TimeFrameUnit.Hour)
        elif "day" in unit_str:
            tf = TimeFrame(multiplier, TimeFrameUnit.Day)

        request_params = StockBarsRequest(
            symbol_or_symbols=symbol,
            timeframe=tf,
            start=start,
            end=end
        )
        
        bars = self.client.get_stock_bars(request_params)
        df = bars.df
        
        # Reset index and set timestamp as index if multi-index
        if isinstance(df.index, pd.MultiIndex):
            df = df.xs(symbol, level=0)
            
        # Ensure column names match Backtrader requirements
        df.rename(columns={
            "open": "Open",
            "high": "High",
            "low": "Low",
            "close": "Close",
            "volume": "Volume"
        }, inplace=True)
        
        return df

    def get_market_cap(self, symbol: str) -> float:
        # Alpaca doesn't directly provide market cap in the data client easily
        # Usually needs the TradingClient or another source.
        # For now, returning 0 or a mock value, or we can use another API.
        return 0.0
