import os
import pandas as pd
import concurrent.futures
import argparse
from datetime import datetime, timedelta
from dotenv import load_dotenv
from tqdm import tqdm
from data_providers.massive_s3_provider import MassiveS3Provider

# Load environment variables
load_dotenv()

from botocore.exceptions import ClientError

def download_day(provider, date_str):
    """
    Attempts to download a single day's flat file.
    Returns the date_str and a boolean indicating success.
    """
    try:
        # download_daily_file will skip downloading if the file already exists locally.
        # It throws an exception if the file doesn't exist on S3 (e.g., weekends, holidays).
        path = provider.download_daily_file(date_str, data_type="day_aggs_v1")
        if path.exists():
            return date_str, True
        return date_str, False
    except ClientError as e:
        error_code = e.response.get('Error', {}).get('Code', 'Unknown')
        if error_code in ['404', 'NoSuchKey']:
            # Normal for weekends/holidays
            pass
        else:
            # We don't want to swallow auth or network errors
            tqdm.write(f"S3 Error downloading {date_str}: {e}")
        return date_str, False
    except Exception as e:
        tqdm.write(f"Unexpected error downloading {date_str}: {e}")
        return date_str, False

def main():
    parser = argparse.ArgumentParser(description="Download historical flat files from MassiveS3Provider.")
    parser.add_argument("--years", type=int, default=5, help="Number of years to look back (default: 5)")
    parser.add_argument("--workers", type=int, default=10, help="Number of concurrent workers (default: 10)")
    args = parser.parse_args()

    # Calculate start and end dates
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365 * args.years)

    try:
        provider = MassiveS3Provider()
    except ValueError as e:
        print(f"Error initializing MassiveS3Provider: {e}")
        print("Please ensure MASSIVE_S3_ACCESS_KEY and MASSIVE_S3_SECRET_KEY are set in your environment.")
        return

    # Check which files have already been downloaded to enable resume
    # The files are named like 'day_aggs_v1_YYYY-MM-DD.csv.gz'
    existing_files = list(provider.cache_dir.glob("day_aggs_v1_*.csv.gz"))
    existing_dates = set()
    for f in existing_files:
        try:
            # Extract the date part from the filename
            date_part = f.name.replace("day_aggs_v1_", "").replace(".csv.gz", "")
            existing_dates.add(date_part)
        except Exception:
            pass

    # Generate a list of dates (business days only to minimize unnecessary S3 calls)
    dates = pd.bdate_range(start=start_date, end=end_date)
    all_date_strings = [d.strftime('%Y-%m-%d') for d in dates]

    # Filter out dates that have already been downloaded
    date_strings = [d for d in all_date_strings if d not in existing_dates]

    if not date_strings:
        print("All files in the specified range have already been downloaded.")
        return

    print(f"Found {len(existing_dates)} existing files in cache.")
    print(f"Starting download process for {len(date_strings)} remaining potential trading days...")
    print(f"Remaining date range: {date_strings[0]} to {date_strings[-1]}")

    successful_downloads = 0
    failed_downloads = 0

    print(f"Downloading files using {args.workers} concurrent workers...")

    executor = concurrent.futures.ThreadPoolExecutor(max_workers=args.workers)
    # Submit all tasks
    futures = {executor.submit(download_day, provider, date_str): date_str for date_str in date_strings}

    try:
        # Process results as they complete with a progress bar
        with tqdm(total=len(futures), desc="Downloading data") as pbar:
            for future in concurrent.futures.as_completed(futures):
                date_str, success = future.result()
                if success:
                    successful_downloads += 1
                else:
                    failed_downloads += 1
                pbar.update(1)
    except KeyboardInterrupt:
        print("\nDownload interrupted by user. Shutting down workers...")
        executor.shutdown(wait=False, cancel_futures=True)
        print("Shutdown complete.")
        return
    finally:
        executor.shutdown(wait=True)

    print("\nDownload process completed!")
    print(f"Successfully downloaded or verified: {successful_downloads} files.")
    print(f"Skipped (likely weekends/holidays): {failed_downloads} files.")
    print(f"Data is stored in the '{provider.cache_dir}' directory.")

if __name__ == "__main__":
    main()
