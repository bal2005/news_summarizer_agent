import logging

from apscheduler.schedulers.blocking import BlockingScheduler

from .config import (
    TIMEZONE,
    DIGEST_INTERVAL_MINUTES,
    APP_NAME
)

from .graphs.news_digest_graph import run_news_digest


# ------------------------------------------------------
# LOGGING
# ------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s | %(levelname)s | %(message)s"
)
logger = logging.getLogger(__name__)


# ------------------------------------------------------
# MAIN
# ------------------------------------------------------
def main():
    logger.info(f"Starting {APP_NAME}")

    # Run once at startup
    run_news_digest()

    # Scheduler
    scheduler = BlockingScheduler(timezone=TIMEZONE)
    scheduler.add_job(
        run_news_digest,
        trigger="interval",
        minutes=DIGEST_INTERVAL_MINUTES,
        id="news_digest_job",
        replace_existing=True
    )

    logger.info(
        f"Scheduler started (runs every {DIGEST_INTERVAL_MINUTES} minutes)"
    )
    scheduler.start()


if __name__ == "__main__":
    main()
