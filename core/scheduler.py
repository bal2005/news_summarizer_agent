import logging
from typing import Callable
from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

logger = logging.getLogger(__name__)

_scheduler = BackgroundScheduler()

def schedule_job(
    job_func: Callable,
    cron: str,
    job_id: str
) -> None:
    """
    Schedule a job using cron syntax.
    Example cron: "0 8 * * *" (8 AM daily)
    """
    trigger = CronTrigger.from_crontab(cron)

    _scheduler.add_job(
        job_func,
        trigger=trigger,
        id=job_id,
        replace_existing=True
    )

    logger.info(f"Scheduled job '{job_id}' with cron '{cron}'")


def start_scheduler() -> None:
    """
    Start the scheduler.
    """
    if not _scheduler.running:
        _scheduler.start()
