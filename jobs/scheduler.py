"""
scheduler.py — APScheduler configured to run run_fetch() every 8 hours.
Started from JobsConfig.ready() so it lives in the same process as Django.
"""
import logging

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.interval import IntervalTrigger

logger = logging.getLogger(__name__)

scheduler = BackgroundScheduler(timezone="UTC")


def start(interval_seconds: int = 28800) -> None:
    """Start the background scheduler (call once per process)."""
    from .tasks import run_fetch

    scheduler.add_job(
        run_fetch,
        trigger=IntervalTrigger(seconds=interval_seconds),
        id="fetch_jobs",
        name="Fetch jobs every 8 hours",
        replace_existing=True,
        misfire_grace_time=300,  # Allow 5-minute grace if job fires late
    )
    scheduler.start()
    logger.info(
        "Scheduler started — fetch_jobs runs every %d seconds (%d hours)",
        interval_seconds,
        interval_seconds // 3600,
    )
