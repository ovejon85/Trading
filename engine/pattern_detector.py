import pandas as pd
import numpy as np

class PatternDetector:
    @staticmethod
    def is_hammer(df: pd.DataFrame) -> pd.Series:
        """
        Detects Hammer candlestick pattern.
        """
        body = abs(df['Close'] - df['Open'])
        lower_shadow = df[['Open', 'Close']].min(axis=1) - df['Low']
        upper_shadow = df['High'] - df[['Open', 'Close']].max(axis=1)
        
        # Hammer criteria: lower shadow at least 2x body, very small upper shadow
        is_hammer = (lower_shadow >= 2 * body) & (upper_shadow <= 0.1 * body)
        return is_hammer

    @staticmethod
    def find_local_extrema(df: pd.DataFrame, window: int = 5):
        """
        Finds local peaks and troughs.
        """
        from scipy.signal import argrelextrema
        
        peaks = argrelextrema(df['Close'].values, np.greater_equal, order=window)[0]
        troughs = argrelextrema(df['Close'].values, np.less_equal, order=window)[0]
        
        return peaks, troughs
