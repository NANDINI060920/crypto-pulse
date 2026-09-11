"""
storage.py
----------
Thin SQLite storage layer for CryptoPulse.

Keeping this in its own module (instead of inline in the ingestion
script) means the dashboard and any future analysis scripts can reuse
the exact same schema/queries without duplicating SQL.
"""

import sqlite3
from contextlib import contextmanager
from pathlib import Path

DB_PATH = Path(__file__).parent / "data" / "crypto_pulse.db"


def init_db() -> None:
    """Create the database file and table if they don't exist yet."""
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    with get_connection() as conn:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS price_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                coin_id TEXT NOT NULL,
                price_usd REAL NOT NULL,
                market_cap_usd REAL,
                volume_24h_usd REAL,
                pct_change_24h REAL,
                fetched_at TEXT NOT NULL DEFAULT (datetime('now'))
            )
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS idx_coin_time
            ON price_history (coin_id, fetched_at)
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS ingestion_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                run_at TEXT NOT NULL DEFAULT (datetime('now')),
                status TEXT NOT NULL,
                detail TEXT
            )
            """
        )


@contextmanager
def get_connection():
    """Context manager so callers never forget to close a connection."""
    conn = sqlite3.connect(DB_PATH)
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def insert_price_rows(rows: list[dict]) -> None:
    """
    Bulk-insert a list of price snapshot dicts.

    Each dict is expected to have: coin_id, price_usd, market_cap_usd,
    volume_24h_usd, pct_change_24h
    """
    if not rows:
        return
    with get_connection() as conn:
        conn.executemany(
            """
            INSERT INTO price_history
                (coin_id, price_usd, market_cap_usd, volume_24h_usd, pct_change_24h)
            VALUES (:coin_id, :price_usd, :market_cap_usd, :volume_24h_usd, :pct_change_24h)
            """,
            rows,
        )


def log_run(status: str, detail: str = "") -> None:
    """Record every ingestion attempt (success or failure) for auditability."""
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO ingestion_log (status, detail) VALUES (?, ?)",
            (status, detail),
        )


def fetch_history(coin_id: str, limit_hours: int = 24 * 7):
    """Return recent price history for a coin as a list of rows."""
    with get_connection() as conn:
        cursor = conn.execute(
            """
            SELECT coin_id, price_usd, market_cap_usd, volume_24h_usd,
                   pct_change_24h, fetched_at
            FROM price_history
            WHERE coin_id = ?
              AND fetched_at >= datetime('now', ?)
            ORDER BY fetched_at ASC
            """,
            (coin_id, f"-{limit_hours} hours"),
        )
        return cursor.fetchall()


def list_tracked_coins():
    """Distinct coin ids currently in the database."""
    with get_connection() as conn:
        cursor = conn.execute("SELECT DISTINCT coin_id FROM price_history")
        return [row[0] for row in cursor.fetchall()]
