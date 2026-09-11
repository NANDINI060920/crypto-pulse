"""
tests/test_anomaly.py
----------------------
Tests for the two anomaly detection strategies in anomaly.py.

The core question these tests answer: does the detector actually
catch an anomaly, and does it stay quiet on normal data? A model
that never fires, or fires constantly, is useless -- these tests
catch both failure modes.
"""

import numpy as np
import pandas as pd
import pytest

from anomaly import isolation_forest_flags, rolling_zscore


def make_price_series(n=50, spike_index=None, spike_size=5000, seed=0):
    """Build a synthetic, mostly-smooth price series with an optional
    injected spike, for deterministic testing."""
    rng = np.random.default_rng(seed)
    prices = 60000 + np.cumsum(rng.normal(0, 50, n))
    if spike_index is not None:
        prices[spike_index] += spike_size
    dates = pd.date_range("2026-01-01", periods=n, freq="15min")
    return pd.DataFrame({"fetched_at": dates, "price_usd": prices})


def test_rolling_zscore_flags_injected_spike():
    df = make_price_series(n=50, spike_index=30, spike_size=5000)
    result = rolling_zscore(df)
    assert result.loc[30, "is_anomaly"], "Expected the injected spike to be flagged"


def test_rolling_zscore_quiet_on_smooth_data():
    df = make_price_series(n=50, spike_index=None)
    result = rolling_zscore(df)
    flagged_fraction = result["is_anomaly"].mean()
    assert flagged_fraction < 0.15, "Too many false positives on smooth data"


def test_rolling_zscore_handles_short_series():
    df = make_price_series(n=4)
    result = rolling_zscore(df, window=10)
    assert not result["is_anomaly"].any()


def test_isolation_forest_flags_injected_spike():
    df = make_price_series(n=60, spike_index=35, spike_size=6000)
    result = isolation_forest_flags(df)
    assert result.loc[35, "is_anomaly"], "Expected the injected spike to be flagged"


def test_isolation_forest_handles_tiny_dataset():
    df = make_price_series(n=5)
    result = isolation_forest_flags(df)
    assert not result["is_anomaly"].any()
    assert len(result) == 5


def test_both_methods_return_same_row_count():
    df = make_price_series(n=40, spike_index=20)
    z_result = rolling_zscore(df)
    iso_result = isolation_forest_flags(df)
    assert len(z_result) == len(df)
    assert len(iso_result) == len(df)