import backtrader as bt

class MACD_RSI_Strategy(bt.Strategy):
    params = (
        ('macd1', 12),
        ('macd2', 26),
        ('macdsig', 9),
        ('rsi_period', 14),
        ('rsi_low', 30),
        ('rsi_high', 70),
    )

    def __init__(self):
        self.macd = bt.indicators.MACD(
            self.data.close,
            period_me1=self.p.macd1,
            period_me2=self.p.macd2,
            period_signal=self.p.macdsig
        )
        self.rsi = bt.indicators.RSI(self.data.close, period=self.p.rsi_period)

    def next(self):
        if not self.position:
            # Buy if MACD is above signal and RSI is low (oversold)
            if self.macd.macd[0] > self.macd.signal[0] and self.rsi[0] < self.p.rsi_low:
                self.buy()
        else:
            # Sell if MACD is below signal or RSI is high (overbought)
            if self.macd.macd[0] < self.macd.signal[0] or self.rsi[0] > self.p.rsi_high:
                self.sell()
                
    def stop(self):
        # Callback when strategy finished
        self.final_value = self.broker.getvalue()
