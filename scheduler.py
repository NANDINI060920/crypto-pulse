"""
scheduler.py
------------
Runs ingest.py on a repeating interval while this process stays alive.
Useful for local development/demoing. For a "real" always-on pipeline
without keeping a machine running, see .github/workflows/ingest.yml
instead, which runs the same script on a GitHub Actions cron schedule.

Usage:
    python scheduler.py            # every 15 minutes (default)
    python scheduler.py --minutes 5
"""

import argparse

from apscheduler.schedulers.blocking import BlockingScheduler

from ingest import run


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--minutes", type=int, default=15, help="Interval between ingestion runs"
    )
    args = parser.parse_args()

    scheduler = BlockingScheduler()
    scheduler.add_job(run, "interval", minutes=args.minutes, next_run_time=None)

    print(f"Starting scheduler: ingesting every {args.minutes} minute(s). Ctrl+C to stop.")
    run()  # run once immediately so there's data right away
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        print("Scheduler stopped.")


if __name__ == "__main__":
    main()
