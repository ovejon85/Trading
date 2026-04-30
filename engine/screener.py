import pandas as pd
from typing import List, Dict
from data_providers.base import DataProvider

class Screener:
    def __init__(self, provider: DataProvider):
        self.provider = provider

    def screen(self, symbols: List[str], min_market_cap: float = 0, min_price_change: float = -100, min_vol_spike: float = 1.0, days: int = 7) -> List[Dict]:
        results = []
        start_date = (pd.Timestamp.now() - pd.Timedelta(days=days+20)).strftime('%Y-%m-%d')
        end_date = pd.Timestamp.now().strftime('%Y-%m-%d')
        
        for symbol in symbols:
            try:
                # 1. Filter by Market Cap
                mkt_cap = self.provider.get_market_cap(symbol)
                if mkt_cap < min_market_cap:
                    continue
                
                # 2. Fetch Data
                df = self.provider.fetch_data(symbol, "1Day", start_date, end_date)
                if df.empty or len(df) < 10:
                    continue
                
                # 3. Price Change
                start_price = df.iloc[-days]['Close'] if len(df) >= days else df.iloc[0]['Close']
                end_price = df.iloc[-1]['Close']
                price_change = ((end_price - start_price) / start_price) * 100
                
                # 4. Volume Spike (Current Vol / Avg Vol of last 10 days)
                avg_vol = df['Volume'].iloc[-11:-1].mean()
                current_vol = df['Volume'].iloc[-1]
                vol_spike = current_vol / avg_vol if avg_vol > 0 else 1.0
                
                if price_change >= min_price_change and vol_spike >= min_vol_spike:
                    results.append({
                        "symbol": symbol,
                        "market_cap": mkt_cap,
                        "price_change": round(price_change, 2),
                        "vol_spike": round(vol_spike, 2),
                        "current_price": round(end_price, 2)
                    })
            except Exception as e:
                print(f"Error screening {symbol}: {e}")
                
        # Optimization: Sort results by a custom score (e.g., Price Change * Volume Spike)
        results.sort(key=lambda x: x['price_change'] * x['vol_spike'], reverse=True)
        return results
