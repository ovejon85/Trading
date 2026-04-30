import os
import pandas as pd
import concurrent.futures
from datetime import datetime, timedelta
from dotenv import load_dotenv
from data_providers.massive_s3_provider import MassiveS3Provider

# Load environment variables
load_dotenv()

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
    except Exception as e:
        # Commonly fails on non-trading days where S3 files do not exist
        return date_str, False

def main():
    # Number of years to look back
    YEARS_BACK = 5

    # Calculate start and end dates
    end_date = datetime.now()
    start_date = end_date - timedelta(days=365 * YEARS_BACK)

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
    # Use ThreadPoolExecutor to download files in parallel
    # We use a moderate number of workers to speed up downloads without overwhelming the network/CPU
    MAX_WORKERS = 10

    successful_downloads = 0
    failed_downloads = 0

    print(f"Downloading files using {MAX_WORKERS} concurrent workers...")

    with concurrent.futures.ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
        # Map the download_day function over all dates
        # Submit all tasks
        futures = {executor.submit(download_day, provider, date_str): date_str for date_str in date_strings}

        # Process results as they complete
        for i, future in enumerate(concurrent.futures.as_completed(futures), 1):
            date_str, success = future.result()
            if success:
                successful_downloads += 1
                # Print progress occasionally
                if successful_downloads % 50 == 0:
                    print(f"Progress: Successfully downloaded/verified {successful_downloads} days...")
            else:
                failed_downloads += 1

    print("\nDownload process completed!")
    print(f"Successfully downloaded or verified: {successful_downloads} files.")
    print(f"Skipped (likely weekends/holidays): {failed_downloads} files.")
    print(f"Data is stored in the '{provider.cache_dir}' directory.")

if __name__ == "__main__":
    main()
