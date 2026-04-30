import polars as pl

class MarketHub:
    """
    Universal Research Infrastructure Framework: MarketHub
    A high-speed, Polars-based vectorized backtesting and reporting engine.
    """

    def __init__(self, data_path: str = "market_data_gold.parquet"):
        """
        Initializes the MarketHub with the enriched market data.

        Args:
            data_path (str): The path to the enriched parquet file.
        """
        self.data_path = data_path
        self.df = pl.read_parquet(data_path)

    def get_data(self) -> pl.DataFrame:
        """Returns the loaded polars DataFrame."""
        return self.df

    def filter_by_symbol(self, symbol: str) -> pl.DataFrame:
        """Filters the dataset by symbol."""
        return self.df.filter(pl.col("symbol") == symbol)

    def run_vectorized_backtest(self, signal_col: str, forward_return_col: str = "Fwd_Ret_1d") -> pl.DataFrame:
        """
        Runs a simple vectorized backtest.
        Given a boolean signal column, computes the mean forward return when the signal is True.

        Args:
            signal_col (str): The name of the boolean column representing the trading signal.
            forward_return_col (str): The name of the forward return column to evaluate against.

        Returns:
            pl.DataFrame: A summary DataFrame with mean returns per symbol.
        """
        # Ensure signal column exists and is boolean
        if signal_col not in self.df.columns:
            raise ValueError(f"Signal column '{signal_col}' not found in data.")

        return (
            self.df
            .filter(pl.col(signal_col) == True)
            .group_by("symbol")
            .agg([
                pl.col(forward_return_col).mean().alias("mean_return"),
                pl.count(forward_return_col).alias("trade_count")
            ])
        )

if __name__ == "__main__":
    hub = MarketHub()
    df = hub.get_data()
    print(f"Loaded MarketHub with {len(df)} rows.")

    # Example: Create a dummy signal (RSI < 30) and run a quick backtest
    if "RSI_14" in df.columns:
        hub.df = hub.df.with_columns((pl.col("RSI_14") < 30).alias("buy_signal"))
        results = hub.run_vectorized_backtest("buy_signal", "Fwd_Ret_5d")
        print("Vectorized Backtest Results (RSI < 30 -> 5-day forward return):")
        print(results)
