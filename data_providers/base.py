from abc import ABC, abstractmethod
import pandas as pd

class DataProvider(ABC):
    @abstractmethod
    def fetch_data(self, symbol: str, timeframe: str, start: str, end: str) -> pd.DataFrame:
        """
        Fetch historical data for a given symbol.
        Returns a Pandas DataFrame with columns: [Open, High, Low, Close, Volume] and a DatetimeIndex.
        """
        pass

    @abstractmethod
    def get_market_cap(self, symbol: str) -> float:
        """
        Fetch market capitalization for a given symbol.
        """
        pass
