"""
tests/test_storage.py
-----------------------
Tests for storage.py. Each test points storage.DB_PATH at a temporary
file (via the db_path fixture below) so these tests never touch your
real data/crypto_pulse.db.
"""

import pytest

import storage


@pytest.fixture
def db_path(tmp_path, monkeypatch):
    """Redirect storage.DB_PATH to a throwaway file for this test only."""
    test_db = tmp_path / "test_crypto_pulse.db"
    monkeypatch.setattr(storage, "DB_PATH", test_db)
    storage.init_db()
    return test_db


def test_init_db_creates_file(db_path):
    assert db_path.exists()


def test_insert_and_fetch_price_rows(db_path):
    rows = [
        {
            "coin_id": "bitcoin",
            "price_usd": 77000.5,
            "market_cap_usd": 1.5e12,
            "volume_24h_usd": 3e10,
            "pct_change_24h": 2.1,
        }
    ]
    storage.insert_price_rows(rows)

    history = storage.fetch_history("bitcoin", limit_hours=24)
    assert len(history) == 1
    assert history[0][0] == "bitcoin"
    assert history[0][1] == 77000.5


def test_insert_empty_rows_does_nothing(db_path):
    storage.insert_price_rows([])
    history = storage.fetch_history("bitcoin", limit_hours=24)
    assert history == []


def test_list_tracked_coins_returns_distinct_ids(db_path):
    storage.insert_price_rows(
        [
            {"coin_id": "bitcoin", "price_usd": 1, "market_cap_usd": None, "volume_24h_usd": None, "pct_change_24h": None},
            {"coin_id": "bitcoin", "price_usd": 2, "market_cap_usd": None, "volume_24h_usd": None, "pct_change_24h": None},
            {"coin_id": "ethereum", "price_usd": 3, "market_cap_usd": None, "volume_24h_usd": None, "pct_change_24h": None},
        ]
    )
    coins = storage.list_tracked_coins()
    assert sorted(coins) == ["bitcoin", "ethereum"]


def test_fetch_history_excludes_other_coins(db_path):
    storage.insert_price_rows(
        [
            {"coin_id": "bitcoin", "price_usd": 100, "market_cap_usd": None, "volume_24h_usd": None, "pct_change_24h": None},
            {"coin_id": "dogecoin", "price_usd": 0.1, "market_cap_usd": None, "volume_24h_usd": None, "pct_change_24h": None},
        ]
    )
    btc_history = storage.fetch_history("bitcoin", limit_hours=24)
    assert len(btc_history) == 1
    assert btc_history[0][0] == "bitcoin"


def test_log_run_records_status(db_path):
    storage.log_run("success", detail="inserted 5 rows")
    storage.log_run("failure", detail="timeout")
    with storage.get_connection() as conn:
        rows = conn.execute("SELECT status FROM ingestion_log ORDER BY id").fetchall()
    assert [r[0] for r in rows] == ["success", "failure"]