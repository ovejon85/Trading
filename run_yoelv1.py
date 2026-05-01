import backtrader as bt
from market_hub import MarketHub
from strategies.yoelv1 import Yoelv1

def run_backtest():
    print("Initializing MarketHub...")
    hub = MarketHub()

    print("Loading data from MarketHub...")
    df = hub.load_market_data()

    print("Setting up Backtrader Cerebro...")
    cerebro = bt.Cerebro()

    # Create a Backtrader data feed from the pandas dataframe
    data = bt.feeds.PandasData(dataname=df)
    cerebro.adddata(data)

    # Add strategy
    cerebro.addstrategy(Yoelv1)

    # Set starting cash
    start_portfolio_value = 100000.0
    cerebro.broker.setcash(start_portfolio_value)

    # Set commission - 0.1% ... divide by 100 to remove the %
    cerebro.broker.setcommission(commission=0.001)

    print(f"Starting Portfolio Value: {start_portfolio_value:.2f}")

    # Run the backtest
    results = cerebro.run()

    # Print the final result
    end_portfolio_value = cerebro.broker.getvalue()
    print(f"Final Portfolio Value: {end_portfolio_value:.2f}")

    # Output summary report
    print("\n--- Backtest Summary Report ---")
    print(f"Strategy: Yoelv1 (reversal_v3)")
    print(f"Start Date: {df.index.min().date()}")
    print(f"End Date: {df.index.max().date()}")
    print(f"Total Return: {((end_portfolio_value / start_portfolio_value) - 1) * 100:.2f}%")
    print(f"Absolute Return: {end_portfolio_value - start_portfolio_value:.2f}")
    print("-------------------------------")

if __name__ == '__main__':
    run_backtest()
