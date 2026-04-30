import backtrader as bt
import numpy as np

class ParabolicShortStrategy(bt.Strategy):
    params = (
        ('hold_days', 1),  # Days to hold the short position (1 for T+1, 5 for T+5)
        ('period_roc', 21), # 21-day rolling price increase
        ('roc_threshold', 1.0), # 100% increase
        ('body_period', 20), # 20 periods for average body size
        ('vol_period', 4), # 4 days for relative volume
        ('min_dollar_vol', 10_000_000), # Dollar volume >= $10m
        ('entry_on_close', False), # True to enter on signal day close, False to enter on next day open
    )

    def __init__(self):
        # 1. 21-day rolling price increase
        self.roc = (self.data.close - self.data.close(-self.p.period_roc)) / self.data.close(-self.p.period_roc)

        # 2. Big Green Candle or Gap Up
        self.body = self.data.close - self.data.open
        self.abs_body = abs(self.body)

        self.avg_body = bt.indicators.SMA(self.abs_body, period=self.p.body_period)
        self.std_body = bt.indicators.StdDev(self.abs_body, period=self.p.body_period)

        self.gap_up = self.data.open > self.data.high(-1)

        # Volume
        self.avg_vol = bt.indicators.SMA(self.data.volume, period=self.p.vol_period)

        # Track entry day and stop loss
        self.bars_held = 0
        self.stop_price = None
        self.stop_order = None
        self.exit_order = None

    def notify_order(self, order):
        if order.status in [order.Completed]:
            # If our stop order or time-based exit order is completed, we reset
            if order == self.stop_order or order == self.exit_order:
                self.stop_order = None
                self.exit_order = None
                self.stop_price = None
                self.bars_held = 0

        elif order.status in [order.Canceled, order.Margin, order.Rejected]:
            if order == self.stop_order:
                self.stop_order = None
            if order == self.exit_order:
                self.exit_order = None

    def next(self):
        # We need to compute dollar vol here manually since Backtrader doesn't easily let us look ahead for cheat-on-close
        dollar_vol = self.data.close[0] * self.data.volume[0]

        if not self.position:
            # Condition 1: 21-day price increase >= 100%
            cond1 = self.roc[0] >= self.p.roc_threshold

            # Condition 2: Big Green Candle OR Gap Up
            is_green = self.body[0] > 0
            is_big = self.body[0] >= (self.avg_body[-1] + 2 * self.std_body[-1])
            big_green_candle = is_green and is_big

            cond2 = big_green_candle or self.gap_up[0]

            # Condition 3: Relative volume > average of previous 4 days
            cond3 = self.data.volume[0] > self.avg_vol[-1]

            # Condition 4: Dollar volume >= 10 million
            cond4 = dollar_vol >= self.p.min_dollar_vol

            if cond1 and cond2 and cond3 and cond4:
                # Enter short position
                # Stop loss at the high of the signal day
                self.stop_price = self.data.high[0]

                # Backtrader defaults to Market orders executing on the next bar's Open.
                # To execute on today's close, Cerebro must be initialized with cheat_on_open=True or similar,
                # but we will simply use bt.Order.Close to execute at the session close.
                if self.p.entry_on_close:
                    self.sell(exectype=bt.Order.Close)
                else:
                    self.sell(exectype=bt.Order.Market) # Without cheat on close, this is tomorrow's open

                self.bars_held = 0

        else:
            # Re-issue the stop order if we haven't already (or update it if needed)
            if self.stop_order is None and self.stop_price is not None:
                self.stop_order = self.buy(exectype=bt.Order.Stop, price=self.stop_price)

            self.bars_held += 1

            # Time-based exit
            if self.bars_held >= self.p.hold_days:
                # Cancel the stop order if we are exiting based on time
                if self.stop_order:
                    self.cancel(self.stop_order)
                    self.stop_order = None

                # Make sure we don't spam multiple exit orders if we're already trying to exit
                if self.exit_order is None:
                    if self.p.entry_on_close:
                        self.exit_order = self.buy(exectype=bt.Order.Close)
                    else:
                        self.exit_order = self.buy(exectype=bt.Order.Market)

    def stop(self):
        self.final_value = self.broker.getvalue()
