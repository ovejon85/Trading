import polars as pl
import argparse
from pathlib import Path
import time

def process_files(cache_dir: str, num_workers: int = None):
    start_time = time.time()
    path = Path(cache_dir)

    # We use scan_csv to lazily load all csv.gz files in the directory.
    # Polars automatically parallelizes and optimizes this operation.
    print(f"Scanning for files in {path}...")

    # Check if there are actually files to read
    files = list(path.glob('*.csv.gz'))
    if not files:
        print("No .csv.gz files found in the data_cache directory.")
        return None

    print(f"Found {len(files)} files. Setting up lazy scan...")

    # Polars lazy frame for the glob pattern
    # It handles gzip automatically
    lazy_df = pl.scan_csv(f"{path}/*.csv.gz")

    # We can perform aggregations/filtering lazily here.
    # For now, we will just count the rows and symbols as a proof of concept.
    print("Collecting data (this might take a moment depending on the size)...")

    # If the files are massive, we shouldn't just `.collect()` everything into memory without filtering.
    # Let's run a basic aggregation to prove it works
    agg_df = lazy_df.group_by("ticker").agg(
        [
            pl.len().alias("count"),
            pl.col("close").mean().alias("avg_close"),
            pl.col("volume").sum().alias("total_volume")
        ]
    ).collect()

    end_time = time.time()

    print(f"\nProcessing complete in {end_time - start_time:.2f} seconds.")
    print(f"Processed data for {len(agg_df)} unique tickers.")

    # Show the top 5 by volume
    print("\nTop 5 symbols by volume:")
    print(agg_df.sort("total_volume", descending=True).head(5))

    return agg_df

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Efficiently load and process cached CSV data.")
    parser.add_argument("--cache-dir", type=str, default="data_cache", help="Directory containing gzipped CSV files")
    parser.add_argument("--workers", type=int, default=None, help="Number of workers (unused for Polars as it auto-scales)")

    args = parser.parse_args()
    process_files(args.cache_dir, args.workers)
