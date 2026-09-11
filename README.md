# CryptoPulse — Live Crypto Price Pipeline & Anomaly Dashboard

A small data engineering + ML project that ingests live cryptocurrency
prices on a schedule, stores them, automatically flags anomalous price
movements, and visualizes everything in an interactive dashboard.

![status](https://img.shields.io/badge/status-active-brightgreen)

## Why this project

Most "ML portfolio" projects stop at `model.fit()` on a static CSV.
This one instead covers the full loop a real data product needs:

**Ingestion → Storage → Detection → Visualization → Automation**

using a public API, a real (if simple) database, two different anomaly
detection strategies, and a scheduled job that keeps running without
anyone babysitting it.

## Architecture

```
CoinGecko API
     │  (every 30 min, via cron)
     ▼
ingest.py  ──►  SQLite (data/crypto_pulse.db)
                       │
                       ▼
              anomaly.py (z-score / IsolationForest)
                       │
                       ▼
              dashboard.py (Streamlit + Plotly)
```

Ingestion runs two ways:
- **Locally** via `scheduler.py` (APScheduler) for development
- **In the cloud, for free**, via a GitHub Actions cron workflow
  (`.github/workflows/ingest.yml`) that runs the ingestion script every
  30 minutes and commits the updated database back to the repo — no
  server required.

## What it catches

Two anomaly detection methods are implemented so you can compare them:

- **Rolling z-score** — flags a price change that deviates more than
  2.5 standard deviations from its recent rolling average. Fast,
  interpretable, and a good baseline.
- **Isolation Forest** (`scikit-learn`) — an unsupervised model that
  isolates outliers based on price and rate-of-change features.
  Catches patterns the simple statistical method can miss.

Both are unit-tested against a synthetic price series with a known
injected spike to confirm they actually detect it (see `anomaly.py`
docstrings for the approach).

## Getting started

```bash
git clone <your-repo-url>
cd crypto-pulse
pip install -r requirements.txt

# Pull data once
python ingest.py

# Or run continuously, ingesting every 15 minutes
python scheduler.py --minutes 15

# Launch the dashboard (in a separate terminal)
streamlit run dashboard.py
```

No API key is required — CoinGecko's `/simple/price` endpoint is
public.

## Project structure

```
crypto-pulse/
├── ingest.py         # Pulls prices from CoinGecko, writes to SQLite
├── storage.py         # SQLite schema + query helpers
├── anomaly.py          # Rolling z-score & Isolation Forest detection
├── dashboard.py         # Streamlit dashboard
├── scheduler.py           # Local recurring-job runner (APScheduler)
├── requirements.txt
└── .github/workflows/
    └── ingest.yml          # Scheduled cloud ingestion via GitHub Actions
```

## Design decisions worth knowing about

- **Batched API calls.** All tracked coins are fetched in a single
  request rather than one call per coin, to stay well within
  CoinGecko's free-tier rate limits.
- **Failures are expected, not exceptional.** `ingest.py` retries once
  on failure, then logs the failure to an `ingestion_log` table and
  exits cleanly rather than crashing — so a scheduler can safely retry
  on the next cycle without manual intervention.
- **SQLite over Postgres**, deliberately, to keep the project runnable
  by anyone with zero setup. Swapping storage backends only requires
  changes in `storage.py`.

## Possible extensions

- Swap SQLite for Postgres/TimescaleDB for higher-frequency ingestion
- Add Slack/email alerts when an anomaly is flagged
- Add more coins or a second data source (e.g. on-chain metrics)
- Backtest the anomaly detector against known historical crash/pump events

## License

MIT
**Live demo:**https://crypto-pulse-nandini.streamlit.app