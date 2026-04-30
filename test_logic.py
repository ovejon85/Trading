import pandas as pd
import numpy as np
from backtest.engine import BacktestEngine
from strategies.sample_strategy import MACD_RSI_Strategy

def test_backtest():
    # Create mock data
    dates = pd.date_range(start="2023-01-01", periods=100, freq='D')
    data = pd.DataFrame({
        "Open": np.linspace(100, 110, 100) + np.random.randn(100),
        "High": np.linspace(101, 111, 100) + np.random.randn(100),
        "Low": np.linspace(99, 109, 100) + np.random.randn(100),
        "Close": np.linspace(100, 110, 100) + np.random.randn(100),
        "Volume": np.random.randint(1000, 5000, 100)
    }, index=dates)

    print("Running Mock Backtest...")
    engine = BacktestEngine(data, MACD_RSI_Strategy)
    engine.run()
    print("Test Successful!")

if __name__ == "__main__":
    test_backtest()
