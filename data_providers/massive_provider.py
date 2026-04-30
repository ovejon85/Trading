import os
import pandas as pd
from polygon import RESTClient
from polygon.websocket import WebSocketClient, Market
from .base import DataProvider
from dotenv import load_dotenv
import threading

load_dotenv()

class MassiveProvider(DataProvider):
    def __init__(self):
        self.api_key = os.getenv("MASSIVE_API_KEY")
        if not self.api_key:
            raise ValueError(
                "Massive API key missing. Please set MASSIVE_API_KEY "
                "in your environment variables or .env file."
            )
        # Massive.com is the successor to Polygon.io; the client handles the migration.
        self.client = RESTClient(self.api_key)
        self.ws_client = None

    def fetch_data(self, symbol: str, timeframe: str, start: str, end: str) -> pd.DataFrame:
        # Map timeframe to Massive/Polygon format
        # e.g., '1Day' -> multiplier=1, timespan='day'
        import re
        match = re.match(r"(\d+)?([a-zA-Z]+)", timeframe)
        multiplier = int(match.group(1)) if match.group(1) else 1
        unit = match.group(2).lower()
        
        if "min" in unit:
            timespan = "minute"
        elif "hour" in unit:
            timespan = "hour"
        elif "day" in unit:
            timespan = "day"
        else:
            timespan = "day"

        aggs = self.client.get_aggs(
            ticker=symbol,
            multiplier=multiplier,
            timespan=timespan,
            from_=start,
            to=end
        )
        
        df = pd.DataFrame(aggs)
        if df.empty:
            return df
            
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('timestamp', inplace=True)
        
        df.rename(columns={
            "open": "Open",
            "high": "High",
            "low": "Low",
            "close": "Close",
            "volume": "Volume"
        }, inplace=True)
        
        return df[['Open', 'High', 'Low', 'Close', 'Volume']]

    def get_market_cap(self, symbol: str) -> float:
        try:
            details = self.client.get_ticker_details(symbol)
            return getattr(details, "market_cap", 0.0)
        except Exception:
            return 0.0

    def start_streaming(self, symbol: str, callback):
        """
        Starts a WebSocket connection to stream real-time minute aggregates.
        :param symbol: Ticker symbol to subscribe to.
        :param callback: Function to handle incoming data.
        """
        def on_message(msgs):
            for m in msgs:
                # 'AM' is Minute Aggregates
                if hasattr(m, "event_type") and m.event_type == "AM":
                    # Convert to standard format
                    data = {
                        "timestamp": pd.to_datetime(m.end_timestamp, unit='ms'),
                        "Open": m.open,
                        "High": m.high,
                        "Low": m.low,
                        "Close": m.close,
                        "Volume": m.volume
                    }
                    callback(data)

        self.ws_client = WebSocketClient(
            api_key=self.api_key,
            market=Market.Stocks,
            on_message=on_message
        )
        
        # Subscribe to minute aggregates for the symbol
        self.ws_client.subscribe(f"AM.{symbol}")
        
        # Run in a separate thread so it doesn't block the main app
        self.ws_thread = threading.Thread(target=self.ws_client.run_forever)
        self.ws_thread.daemon = True
        self.ws_thread.start()

    def stop_streaming(self):
        if self.ws_client:
            self.ws_client.close()
