"""
APScheduler background scheduler for STEWARD.

Starts alongside Flask in the same process.
Jobs registered here run without blocking the web server.

Current jobs:
  email_poll — checks configured inbox for new document attachments (every N minutes)

Usage:
    from src.scheduler import start_scheduler, stop_scheduler
    start_scheduler()   # call once at app boot
    stop_scheduler()    # call at shutdown (optional — daemon threads die with the process)
"""

from __future__ import annotations

import logging
from typing import Optional

logger = logging.getLogger(__name__)

_scheduler = None   # BackgroundScheduler instance, set by start_scheduler()


def get_scheduler():
    return _scheduler


def is_running() -> bool:
    return _scheduler is not None and _scheduler.running


def start_scheduler() -> None:
    """
    Initialise and start the background scheduler.
    Safe to call multiple times — subsequent calls are no-ops if already running.
    """
    global _scheduler

    if is_running():
        return

    try:
        from apscheduler.schedulers.background import BackgroundScheduler
    except ImportError:
        logger.warning("apscheduler not installed — background jobs disabled. Run: pip install apscheduler")
        return

    from src.config import settings

    _scheduler = BackgroundScheduler(timezone="UTC", job_defaults={"misfire_grace_time": 60})

    # ── Email polling job ────────────────────────────────────────────────────
    if settings.steward_email and settings.steward_email_password:
        from src.email_ingest import poll_inbox
        _scheduler.add_job(
            poll_inbox,
            trigger="interval",
            minutes=settings.email_poll_minutes,
            id="email_poll",
            replace_existing=True,
            next_run_time=None,   # don't fire immediately on startup; wait one full interval
        )
        logger.info(
            "Email polling scheduled: %s every %d minute(s)",
            settings.steward_email,
            settings.email_poll_minutes,
        )
    else:
        logger.info("Email polling disabled (STEWARD_EMAIL not set in .env)")

    _scheduler.start()
    logger.info("Background scheduler started")


def stop_scheduler() -> None:
    """Gracefully stop the scheduler. Called at Flask shutdown."""
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("Background scheduler stopped")


def trigger_email_poll_now() -> bool:
    """
    Manually fire the email poll job immediately.
    Returns True if the job was found and triggered, False otherwise.
    """
    if not is_running():
        return False
    job = _scheduler.get_job("email_poll")
    if not job:
        return False
    job.modify(next_run_time=__import__("datetime").datetime.now(__import__("datetime").timezone.utc))
    return True
