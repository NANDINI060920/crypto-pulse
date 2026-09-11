"""
ingest.py
---------
Pulls current price/market data for a set of coins from the CoinGecko
public API and stores each snapshot in SQLite.

Design notes (worth mentioning in interviews):
- CoinGecko's free tier needs no API key, but IS rate-limited, so we
  use a single batched request (all coins in one call) rather than
  one request per coin.
- Network calls fail. This script treats that as an expected case,
  not an exception to crash on: it retries once, then logs the
  failure and exits cleanly so a scheduler can try again next cycle.
- Every run (success or failure) is written to ingestion_log so you
  can audit uptime later -- a real pipeline needs observability,
  not just happy-path code.
"""

import sys
import time
from datetime import datetime, timezone

import requests

from storage import init_db, insert_price_rows, log_run

COINGECKO_URL = "https://api.coingecko.com/api/v3/simple/price"

# Add/remove coin ids here. CoinGecko ids != ticker symbols
# (e.g. Bitcoin's id is "bitcoin", not "btc").
TRACKED_COINS = [
    "bitcoin",
    "ethereum",
    "solana",
    "dogecoin",
    "cardano",
]

REQUEST_TIMEOUT_SECONDS = 10
MAX_RETRIES = 2
RETRY_BACKOFF_SECONDS = 3


def fetch_prices() -> dict:
    """Fetch current price data for all tracked coins in one API call."""
    params = {
        "ids": ",".join(TRACKED_COINS),
        "vs_currencies": "usd",
        "include_market_cap": "true",
        "include_24hr_vol": "true",
        "include_24hr_change": "true",
    }

    last_error = None
    for attempt in range(1, MAX_RETRIES + 1):
        try:
            response = requests.get(
                COINGECKO_URL, params=params, timeout=REQUEST_TIMEOUT_SECONDS
            )
            response.raise_for_status()
            return response.json()
        except requests.RequestException as exc:
            last_error = exc
            print(f"[attempt {attempt}] fetch failed: {exc}", file=sys.stderr)
            if attempt < MAX_RETRIES:
                time.sleep(RETRY_BACKOFF_SECONDS)

    raise RuntimeError(f"All fetch attempts failed: {last_error}")


def to_rows(payload: dict) -> list[dict]:
    """Convert CoinGecko's JSON shape into flat rows for storage."""
    rows = []
    for coin_id in TRACKED_COINS:
        data = payload.get(coin_id)
        if data is None:
            # Coin missing from response (bad id, or CoinGecko hiccup).
            # Skip it rather than inserting garbage/nulls that would
            # silently corrupt downstream anomaly detection.
            print(f"warning: no data returned for '{coin_id}', skipping", file=sys.stderr)
            continue
        rows.append(
            {
                "coin_id": coin_id,
                "price_usd": data.get("usd"),
                "market_cap_usd": data.get("usd_market_cap"),
                "volume_24h_usd": data.get("usd_24h_vol"),
                "pct_change_24h": data.get("usd_24h_change"),
            }
        )
    return rows


def run() -> None:
    init_db()
    started_at = datetime.now(timezone.utc).isoformat()
    try:
        payload = fetch_prices()
        rows = to_rows(payload)
        insert_price_rows(rows)
        log_run("success", detail=f"inserted {len(rows)} rows")
        print(f"[{started_at}] OK: inserted {len(rows)} rows")
    except Exception as exc:
        log_run("failure", detail=str(exc))
        print(f"[{started_at}] FAILED: {exc}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    run()
