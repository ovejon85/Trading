import pandas as pd
import numpy as np
import backtrader as bt
from strategies.parabolic_short import ParabolicShortStrategy

def create_synthetic_data():
    dates = pd.date_range(start="2023-01-01", periods=100, freq='D')
    closes = np.linspace(10, 15, 100)
    opens = closes - 0.1
    highs = closes + 0.2
    lows = closes - 0.2
    volumes = np.full(100, 1_000_000)

    closes[29] = 5.0
    closes[50] = 11.0
    opens[50] = 8.0
    highs[50] = 11.5
    lows[50] = 7.5

    for i in range(30, 50):
        opens[i] = closes[i] - 0.05

    volumes[50] = 5_000_000

    closes[51] = 9.0
    closes[52] = 8.0
    closes[53] = 7.0
    closes[54] = 6.0
    closes[55] = 5.0

    for i in range(51, 56):
        opens[i] = closes[i-1]
        highs[i] = opens[i] + 0.1
        lows[i] = closes[i] - 0.1

    for i in range(56, 60):
        closes[i] = 4.0
        opens[i] = 4.0
        highs[i] = 4.1
        lows[i] = 3.9

    # We remove the end values that cause another signal
    for i in range(60, 100):
        closes[i] = 4.0
        opens[i] = 4.0
        highs[i] = 4.0
        lows[i] = 4.0

    data = pd.DataFrame({
        "Open": opens,
        "High": highs,
        "Low": lows,
        "Close": closes,
        "Volume": volumes
    }, index=dates)
    return data

class LoggingStrategy(ParabolicShortStrategy):
    def next(self):
        super().next()
        if self.position:
            print(f"[{self.data.datetime.date(0)}] SHORT POSITION HELD. Bars: {self.bars_held}. Close: {self.data.close[0]:.2f}")

    def notify_order(self, order):
        super().notify_order(order)
        if order.status in [order.Completed]:
            if order.isbuy():
                print(f"[{self.data.datetime.date(0)}] BUY EXECUTED @ {order.executed.price:.2f}")
            else:
                print(f"[{self.data.datetime.date(0)}] SELL EXECUTED @ {order.executed.price:.2f}")

if __name__ == "__main__":
    data = create_synthetic_data()

    print("--- Testing T+1 Holding Period (Entry on Open) ---")
    cerebro1 = bt.Cerebro()
    cerebro1.adddata(bt.feeds.PandasData(dataname=data))
    cerebro1.broker.setcash(100000.0)
    cerebro1.broker.setcommission(commission=0.001)
    cerebro1.addsizer(bt.sizers.PercentSizer, percents=95)
    cerebro1.addstrategy(LoggingStrategy, hold_days=1, entry_on_close=False)
    cerebro1.run()
    print(f"Final Value: ${cerebro1.broker.getvalue():.2f}\n")

    print("--- Testing T+1 Holding Period (Entry on Close) ---")
    cerebro2 = bt.Cerebro(cheat_on_open=False)
    cerebro2.adddata(bt.feeds.PandasData(dataname=data))
    cerebro2.broker.setcash(100000.0)
    cerebro2.broker.setcommission(commission=0.001)
    cerebro2.addsizer(bt.sizers.PercentSizer, percents=95)
    cerebro2.addstrategy(LoggingStrategy, hold_days=1, entry_on_close=True)
    cerebro2.run()
    print(f"Final Value: ${cerebro2.broker.getvalue():.2f}\n")

    print("--- Testing Stop Loss Trigger ---")
    data_stop = create_synthetic_data()
    data_stop.loc[data_stop.index[52], 'High'] = 12.0

    cerebro3 = bt.Cerebro()
    cerebro3.adddata(bt.feeds.PandasData(dataname=data_stop))
    cerebro3.broker.setcash(100000.0)
    cerebro3.broker.setcommission(commission=0.001)
    cerebro3.addsizer(bt.sizers.PercentSizer, percents=95)
    cerebro3.addstrategy(LoggingStrategy, hold_days=5, entry_on_close=False)
    cerebro3.run()
    print(f"Final Value: ${cerebro3.broker.getvalue():.2f}\n")
