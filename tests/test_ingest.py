"""
tests/test_ingest.py
----------------------
Tests for the pure transformation logic in ingest.py (to_rows).
Network calls (fetch_prices) are intentionally NOT tested here --
hitting a real external API in a test suite makes tests slow and
flaky. Instead we test what we control: correctly shaping whatever
the API gives us, including when it gives us something incomplete.
"""

from ingest import TRACKED_COINS, to_rows


def test_to_rows_converts_valid_payload():
    payload = {
        "bitcoin": {"usd": 77000, "usd_market_cap": 1.5e12, "usd_24h_vol": 3e10, "usd_24h_change": 2.1},
        "ethereum": {"usd": 3400, "usd_market_cap": 4e11, "usd_24h_vol": 1e10, "usd_24h_change": -1.3},
        "solana": {"usd": 180, "usd_market_cap": 8e10, "usd_24h_vol": 2e9, "usd_24h_change": 0.5},
        "dogecoin": {"usd": 0.15, "usd_market_cap": 2e10, "usd_24h_vol": 5e8, "usd_24h_change": 3.0},
        "cardano": {"usd": 0.9, "usd_market_cap": 3e10, "usd_24h_vol": 6e8, "usd_24h_change": -0.2},
    }
    rows = to_rows(payload)
    assert len(rows) == len(TRACKED_COINS)
    btc_row = next(r for r in rows if r["coin_id"] == "bitcoin")
    assert btc_row["price_usd"] == 77000
    assert btc_row["pct_change_24h"] == 2.1


def test_to_rows_skips_missing_coin_instead_of_crashing():
    payload = {
        "bitcoin": {"usd": 77000, "usd_market_cap": 1.5e12, "usd_24h_vol": 3e10, "usd_24h_change": 2.1},
    }
    rows = to_rows(payload)
    assert len(rows) == 1
    assert rows[0]["coin_id"] == "bitcoin"


def test_to_rows_handles_completely_empty_payload():
    rows = to_rows({})
    assert rows == []