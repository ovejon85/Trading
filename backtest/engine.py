import backtrader as bt
import pandas as pd
import matplotlib.pyplot as plt

class BacktestEngine:
    def __init__(self, data: pd.DataFrame, strategy: bt.Strategy, initial_cash: float = 10000.0):
        self.cerebro = bt.Cerebro()
        self.cerebro.addstrategy(strategy)
        
        # Load data into Backtrader
        bt_data = bt.feeds.PandasData(dataname=data)
        self.cerebro.adddata(bt_data)
        
        self.cerebro.broker.setcash(initial_cash)
        # Add commission - 0.1% ... divide by 100 to remove %
        self.cerebro.broker.setcommission(commission=0.001)

    def run(self):
        print(f"Starting Portfolio Value: {self.cerebro.broker.getvalue():.2f}")
        results = self.cerebro.run()
        print(f"Final Portfolio Value: {self.cerebro.broker.getvalue():.2f}")
        return results

    def plot(self):
        # Note: Backtrader's default plot can be tricky in some environments
        # We might want to use plotly in the Streamlit app instead
        self.cerebro.plot(style='candlestick')
