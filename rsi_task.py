import os
import time
import asyncio
import aiohttp
import pandas as pd
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()
API_KEY = os.getenv("MASSIVE_API_KEY", os.getenv("POLYGON_API_KEY", ""))

if not API_KEY:
    print("Error: MASSIVE_API_KEY environment variable is not set.")
    exit(1)

BASE_URL = "https://api.polygon.io"
RATE_LIMIT = 90  # Target under 100 req/sec

async def fetch_json(session, url, params=None, retries=3):
    if params is None:
        params = {}
    params['apiKey'] = API_KEY
    for attempt in range(retries):
        try:
            async with session.get(url, params=params) as response:
                if response.status == 429:
                    await asyncio.sleep(1)
                    continue
                response.raise_for_status()
                return await response.json()
        except Exception as e:
            if attempt == retries - 1:
                print(f"Error fetching {url}: {e}")
                return None
            await asyncio.sleep(1)
    return None

async def get_active_tickers(session):
    print("Fetching active tickers...")
    url = f"{BASE_URL}/v3/reference/tickers"
    params = {"market": "stocks", "active": "true", "limit": 1000}
    tickers = []

    while url:
        data = await fetch_json(session, url, params)
        if not data:
            break

        for item in data.get('results', []):
            tickers.append(item['ticker'])

        url = data.get('next_url')
        params = {} # next_url already has the query params except maybe apikey which fetch_json adds

    print(f"Found {len(tickers)} active tickers.")
    return tickers

async def check_market_cap_and_rsi(session, ticker, semaphore, start_date, end_date):
    async with semaphore:
        # First, check market cap
        details_url = f"{BASE_URL}/v3/reference/tickers/{ticker}"
        details_data = await fetch_json(session, details_url)
        if not details_data or 'results' not in details_data:
            return None

        mcap = details_data['results'].get('market_cap', 0)
        if mcap < 100_000_000:
            return None

        # If market cap is good, fetch 5-year RSI
        rsi_url = f"{BASE_URL}/v1/indicators/rsi/{ticker}"
        rsi_params = {
            "timespan": "day",
            "adjusted": "true",
            "window": 14,
            "series_type": "close",
            "order": "asc",
            "timestamp.gte": start_date,
            "timestamp.lte": end_date,
            "limit": 5000
        }

        rsi_data = await fetch_json(session, rsi_url, rsi_params)
        if not rsi_data or 'results' not in rsi_data or not rsi_data['results'].get('values'):
            return None

        high_rsi_events = []
        values = rsi_data['results']['values']
        for val in values:
            if val['value'] > 90:
                # Polygon returns timestamp in milliseconds
                dt = pd.to_datetime(val['timestamp'], unit='ms')
                high_rsi_events.append({
                    "ticker": ticker,
                    "date": dt.strftime('%Y-%m-%d'),
                    "rsi": val['value']
                })

        return high_rsi_events

async def get_price_and_forward(session, event, semaphore):
    async with semaphore:
        ticker = event['ticker']
        date_str = event['date']

        # Get price on the event date
        aggs_url = f"{BASE_URL}/v2/aggs/ticker/{ticker}/range/1/day/{date_str}/{date_str}"
        aggs_data = await fetch_json(session, aggs_url)

        price = None
        if aggs_data and 'results' in aggs_data and len(aggs_data['results']) > 0:
            price = aggs_data['results'][0]['c']

        event['price'] = price

        # Calculate 5 business days forward
        date_obj = pd.to_datetime(date_str)
        # Add 5 business days
        forward_date = date_obj + pd.offsets.BDay(5)

        # If the forward date is in the future, skip fetching forward data
        if forward_date > pd.Timestamp.now():
            event['price_5d_forward'] = None
            event['rsi_5d_forward'] = None
            return event

        forward_date_str = forward_date.strftime('%Y-%m-%d')

        # We need a small range just in case the target forward day was a holiday
        forward_end = (forward_date + pd.offsets.BDay(2)).strftime('%Y-%m-%d')
        fwd_aggs_url = f"{BASE_URL}/v2/aggs/ticker/{ticker}/range/1/day/{forward_date_str}/{forward_end}"
        fwd_aggs_data = await fetch_json(session, fwd_aggs_url)

        fwd_price = None
        if fwd_aggs_data and 'results' in fwd_aggs_data and len(fwd_aggs_data['results']) > 0:
            fwd_price = fwd_aggs_data['results'][0]['c']
            actual_fwd_date = pd.to_datetime(fwd_aggs_data['results'][0]['t'], unit='ms').strftime('%Y-%m-%d')
        else:
            actual_fwd_date = forward_date_str

        event['price_5d_forward'] = fwd_price

        # Get RSI on forward date
        rsi_url = f"{BASE_URL}/v1/indicators/rsi/{ticker}"
        rsi_params = {
            "timespan": "day",
            "adjusted": "true",
            "window": 14,
            "series_type": "close",
            "timestamp": actual_fwd_date
        }

        rsi_data = await fetch_json(session, rsi_url, rsi_params)
        fwd_rsi = None
        if rsi_data and 'results' in rsi_data and rsi_data['results'].get('values'):
            fwd_rsi = rsi_data['results']['values'][0]['value']

        event['rsi_5d_forward'] = fwd_rsi

        return event

async def main():
    end_date = datetime.now().strftime('%Y-%m-%d')
    start_date = (datetime.now() - timedelta(days=5*365)).strftime('%Y-%m-%d')

    # We use a semaphore to limit concurrent requests
    # 100/sec limit across multiple endpoints.
    # A conservative concurrency limit is 20-30, combined with small sleeps if needed.
    semaphore = asyncio.Semaphore(25)

    # Limit connections to avoid local socket exhaustion
    connector = aiohttp.TCPConnector(limit=50)
    async with aiohttp.ClientSession(connector=connector) as session:
        # For testing/demo purposes, we can limit the tickers. But the request is "every stock".
        # We'll fetch all but might want to process in chunks to be safe.
        tickers = await get_active_tickers(session)

        print(f"Scanning {len(tickers)} tickers for RSI > 90 over the last 5 years...")

        # Create tasks for all tickers
        tasks = [check_market_cap_and_rsi(session, t, semaphore, start_date, end_date) for t in tickers]

        # Use asyncio.as_completed to process as they finish, with a progress indicator
        all_events = []
        completed = 0
        total = len(tasks)

        # Batching tasks to better manage memory and rate limits
        batch_size = 500
        for i in range(0, total, batch_size):
            batch_tasks = tasks[i:i+batch_size]
            results = await asyncio.gather(*batch_tasks)

            for res in results:
                if res:
                    all_events.extend(res)

            completed += len(batch_tasks)
            print(f"Processed {completed}/{total} tickers. Found {len(all_events)} events so far.")

            # Small pause between batches
            await asyncio.sleep(2)

        print(f"\nPhase 1 Complete. Found {len(all_events)} high RSI events across all valid tickers.")

        if not all_events:
            print("No events found.")
            return

        print("\nPhase 2: Fetching prices and 5-day forward data...")
        # Now fetch exact prices and forward data for the events
        event_tasks = [get_price_and_forward(session, ev, semaphore) for ev in all_events]

        final_results = []
        completed_events = 0
        total_events = len(event_tasks)

        for i in range(0, total_events, batch_size):
            batch_tasks = event_tasks[i:i+batch_size]
            results = await asyncio.gather(*batch_tasks)

            for res in results:
                if res:
                    final_results.append(res)

            completed_events += len(batch_tasks)
            print(f"Processed {completed_events}/{total_events} events.")
            await asyncio.sleep(1)

        # Clean up and save
        df = pd.DataFrame(final_results)

        # Format columns as requested: date, TICKER, PRice, RSI, price 5 days forward, RSI 5 days forwards
        df = df.rename(columns={
            "date": "Date",
            "ticker": "TICKER",
            "price": "Price",
            "rsi": "RSI",
            "price_5d_forward": "Price_5d_Forward",
            "rsi_5d_forward": "RSI_5d_Forward"
        })

        df = df[["Date", "TICKER", "Price", "RSI", "Price_5d_Forward", "RSI_5d_Forward"]]

        output_file = "rsi_results.csv"
        df.to_csv(output_file, index=False)
        print(f"\nDone! Processed {len(df)} results and saved to {output_file}.")
        if len(df) < 100:
            print(df)

if __name__ == "__main__":
    asyncio.run(main())
