"""
anomaly.py
----------
Two anomaly-detection strategies over price history, kept simple
enough to explain in an interview but real enough to be meaningful:

1. rolling_zscore   - flags points that deviate sharply from a
                       rolling mean/std of recent price changes.
                       Fast, interpretable, good default.
2. isolation_forest - a real (if lightweight) ML model from
                       scikit-learn, useful to show you understand
                       model-based detection, not just statistics.

Both take a pandas DataFrame with columns: fetched_at, price_usd
and return the same DataFrame with an added boolean `is_anomaly` column.
"""

import numpy as np
import pandas as pd
from sklearn.ensemble import IsolationForest


def rolling_zscore(df: pd.DataFrame, window: int = 10, threshold: float = 2.5) -> pd.DataFrame:
    """
    Flag points whose pct-change from the previous reading is more
    than `threshold` standard deviations from the rolling mean.
    """
    df = df.copy().sort_values("fetched_at").reset_index(drop=True)
    df["pct_change"] = df["price_usd"].pct_change()

    rolling_mean = df["pct_change"].rolling(window, min_periods=3).mean()
    rolling_std = df["pct_change"].rolling(window, min_periods=3).std()

    df["z_score"] = (df["pct_change"] - rolling_mean) / rolling_std.replace(0, np.nan)
    df["is_anomaly"] = df["z_score"].abs() > threshold
    df["is_anomaly"] = df["is_anomaly"].fillna(False)

    return df


def isolation_forest_flags(df: pd.DataFrame, contamination: float = 0.05) -> pd.DataFrame:
    """
    Fit an IsolationForest on price + pct_change features. Contamination
    is the expected fraction of anomalies -- 0.05 is a reasonable
    starting default for noisy market data.
    """
    df = df.copy().sort_values("fetched_at").reset_index(drop=True)
    df["pct_change"] = df["price_usd"].pct_change().fillna(0)

    if len(df) < 10:
        # Not enough data for a meaningful fit yet.
        df["is_anomaly"] = False
        return df

    features = df[["price_usd", "pct_change"]].values
    model = IsolationForest(contamination=contamination, random_state=42)
    predictions = model.fit_predict(features)  # -1 = anomaly, 1 = normal

    df["is_anomaly"] = predictions == -1
    return df
