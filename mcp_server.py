import os
import pandas as pd
from typing import List
from mcp.server.fastmcp import FastMCP
from data_providers.alpaca_provider import AlpacaProvider
from engine.screener import Screener

# Initialize FastMCP server
mcp = FastMCP("FinancialData")

@mcp.tool()
def screen_stocks(symbols: str, min_market_cap: float = 0, min_price_change: float = 2.0) -> str:
    """
    Screens a list of stocks based on market cap and price change.
    :param symbols: Comma-separated list of ticker symbols.
    :param min_market_cap: Minimum market capitalization.
    :param min_price_change: Minimum percentage price change.
    """
    provider = AlpacaProvider() # Default to Alpaca for MCP
    screener = Screener(provider)
    symbol_list = [s.strip() for s in symbols.split(",")]
    results = screener.screen(symbol_list, min_market_cap=min_market_cap, min_price_change=min_price_change)
    
    if not results:
        return "No stocks matched the criteria."
    
    return str(results)

@mcp.tool()
def get_historical_data(symbol: str, timeframe: str = "1Day", days: int = 30) -> str:
    """
    Fetches historical data for a symbol.
    """
    provider = AlpacaProvider()
    end_date = pd.Timestamp.now().strftime('%Y-%m-%d')
    start_date = (pd.Timestamp.now() - pd.Timedelta(days=days)).strftime('%Y-%m-%d')
    df = provider.fetch_data(symbol, timeframe, start_date, end_date)
    return df.tail().to_string()

if __name__ == "__main__":
    mcp.run()
