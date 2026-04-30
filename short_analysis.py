import polars as pl
import os
import glob
from sklearn.ensemble import RandomForestClassifier
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report
import numpy as np

def load_data(cache_dir="data_cache"):
    # 1. Efficiently load all files in 'data_cache/' using Polars lazy execution
    file_pattern = os.path.join(cache_dir, "*.csv.gz")
    if not glob.glob(file_pattern):
        print(f"No files found matching {file_pattern}")
        return pl.DataFrame()

    df = pl.scan_csv(file_pattern).collect()

    # Preprocess: convert window_start (nanoseconds) to date, sort by ticker and date
    df = df.with_columns(
        pl.from_epoch("window_start", time_unit="ns").dt.date().alias("date")
    ).sort(["ticker", "date"])

    return df

def analyze_shorts(df):
    if df.is_empty():
        return

    # 2. Implement a rolling 21-day window to find stocks with 100%+ price increase
    # Also calculate 21-day average volume for feature extraction
    df = df.with_columns([
        pl.col("close").shift(21).over("ticker").alias("close_21d_ago"),
        pl.col("volume").rolling_mean(window_size=21).over("ticker").alias("avg_vol_21d")
    ])

    df = df.with_columns(
        ((pl.col("close") - pl.col("close_21d_ago")) / pl.col("close_21d_ago")).alias("price_increase_21d")
    )

    # 3. Analyze post-spike performance (e.g., return after 1, 5, 10 days)
    df = df.with_columns([
        ((pl.col("close").shift(-1).over("ticker") - pl.col("close")) / pl.col("close")).alias("return_1d_forward"),
        ((pl.col("close").shift(-5).over("ticker") - pl.col("close")) / pl.col("close")).alias("return_5d_forward"),
        ((pl.col("close").shift(-10).over("ticker") - pl.col("close")) / pl.col("close")).alias("return_10d_forward")
    ])

    # Filter for spike events: 100%+ increase
    spikes = df.filter(pl.col("price_increase_21d") >= 1.0)

    print(f"Found {len(spikes)} spike events (>=100% in 21 days).")

    if len(spikes) == 0:
        print("Not enough data or no spikes found to analyze conditions.")
        return

    # 4. Identify conditions for successful shorts

    # Feature extraction
    spikes = spikes.with_columns([
        (pl.col("volume") / pl.col("avg_vol_21d")).alias("vol_spike_ratio"),
        ((pl.col("high") - pl.col("low")) / pl.col("close")).alias("intraday_volatility")
    ])

    # Drop rows with nulls in features or forward returns to ensure clean analysis
    analysis_df = spikes.drop_nulls(subset=["vol_spike_ratio", "intraday_volatility", "return_10d_forward"]).to_pandas()

    if len(analysis_df) < 5:
        print("Not enough valid spike events with forward returns to run models.")
        return

    print("\n--- Simple Model: Correlation Analysis ---")
    features = ["price_increase_21d", "vol_spike_ratio", "intraday_volatility"]
    targets = ["return_1d_forward", "return_5d_forward", "return_10d_forward"]

    corr_matrix = analysis_df[features + targets].corr()
    print("Correlation with future returns (Negative correlation means the feature helps predict a price drop):")
    print(corr_matrix.loc[features, targets])

    print("\n--- Complex Model: Random Forest Feature Importance ---")
    # Define a successful short as the price dropping (negative return) after 10 days
    analysis_df["successful_short"] = (analysis_df["return_10d_forward"] < 0).astype(int)

    X = analysis_df[features]
    y = analysis_df["successful_short"]

    # Use Random Forest to see which features are most predictive of a successful short
    # Note: For very small datasets, train_test_split might result in empty classes, so we wrap it
    try:
        X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42)
        rf = RandomForestClassifier(n_estimators=100, random_state=42)
        rf.fit(X_train, y_train)

        print("\nFeature Importances for Predicting Successful Shorts:")
        for feature, importance in zip(features, rf.feature_importances_):
            print(f"  - {feature}: {importance:.4f}")

        # Basic evaluation
        print("\nModel Evaluation on Test Set:")
        y_pred = rf.predict(X_test)
        print(classification_report(y_test, y_pred, zero_division=0))
    except Exception as e:
         print(f"Could not train Random Forest due to insufficient data variance/size: {e}")

if __name__ == "__main__":
    df = load_data()
    print(f"Total rows loaded: {len(df)}")
    analyze_shorts(df)
