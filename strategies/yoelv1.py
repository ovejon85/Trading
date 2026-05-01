import backtrader as bt

class ScoringEngine:
    """
    Simulated implementation of the Scoring Engine as documented in TASTATION_LOGIC.md.
    Scores trading opportunities based on simple technical metrics.
    """
    def __init__(self):
        pass

    def score(self, current_close, prev_close, volume):
        """
        Calculate a basic score based on momentum and volume.
        """
        momentum = (current_close - prev_close) / prev_close if prev_close > 0 else 0
        volume_factor = min(volume / 50000, 2.0) # Cap volume multiplier

        # Base score is 1.0, adjusted by momentum direction and volume
        score = 1.0 + (momentum * volume_factor * 10)
        return max(0.0, min(score, 10.0)) # Clamp score between 0 and 10

class PortfolioClustering:
    """
    Simulated implementation of the Portfolio Clustering engine from TASTATION_LOGIC.md.
    Manages risk by grouping assets and limiting exposure.
    """
    def __init__(self):
        self.max_exposure_per_cluster = 0.25 # 25% max per group

    def check_allocation_allowed(self, cluster_id, current_exposure):
        """
        Returns True if the cluster has room for more allocation.
        """
        return current_exposure < self.max_exposure_per_cluster

class Yoelv1(bt.Strategy):
    """
    Yoelv1 strategy implementing the 'reversal_v3' logic:
    - Stochastic 14, 3, 3 crossovers in extreme zones
    - ADX < 20 filter
    - Integration with ScoringEngine and PortfolioClustering
    """
    params = (
        ('stoch_period', 14),
        ('stoch_smooth1', 3),
        ('stoch_smooth2', 3),
        ('stoch_overbought', 80),
        ('stoch_oversold', 20),
        ('adx_period', 14),
        ('adx_threshold', 20),
        ('min_score_threshold', 1.2), # Require a positive score to trade
    )

    def __init__(self):
        # Indicators
        self.stoch = bt.indicators.Stochastic(
            self.data,
            period=self.p.stoch_period,
            period_dfast=self.p.stoch_smooth1,
            period_dslow=self.p.stoch_smooth2
        )

        self.adx = bt.indicators.AverageDirectionalMovementIndex(
            self.data,
            period=self.p.adx_period
        )

        # Crossover indicator for Stochastic (K crossing D)
        self.stoch_cross = bt.indicators.CrossOver(self.stoch.percK, self.stoch.percD)

        # Integration engines
        self.scoring_engine = ScoringEngine()
        self.portfolio_clustering = PortfolioClustering()
        self.order = None

    def next(self):
        # Check if there is a pending order
        if self.order:
            return

        # Calculate dynamic score using the ScoringEngine
        prev_close = self.data.close[-1] if len(self.data) > 1 else self.data.close[0]
        current_score = self.scoring_engine.score(self.data.close[0], prev_close, self.data.volume[0])

        # Simulate checking portfolio constraints
        # Assume our test asset is in "Cluster A", and we currently have 0% exposure
        allowed_to_trade = self.portfolio_clustering.check_allocation_allowed("Cluster A", 0.0)

        # Reversal v3 logic
        # Buy condition: Stoch K crosses above D in oversold region AND ADX < 20 AND score is sufficient AND portfolio allows it
        buy_condition = (
            self.stoch_cross > 0 and
            self.stoch.percK[0] < self.p.stoch_oversold and
            self.adx[0] < self.p.adx_threshold and
            current_score >= self.p.min_score_threshold and
            allowed_to_trade
        )

        # Sell condition: Stoch K crosses below D in overbought region AND ADX < 20
        sell_condition = (
            self.stoch_cross < 0 and
            self.stoch.percK[0] > self.p.stoch_overbought and
            self.adx[0] < self.p.adx_threshold
        )

        if not self.position:
            if buy_condition:
                self.order = self.buy()
        else:
            if sell_condition:
                self.order = self.close()

    def notify_order(self, order):
        if order.status in [order.Submitted, order.Accepted]:
            return

        self.order = None
