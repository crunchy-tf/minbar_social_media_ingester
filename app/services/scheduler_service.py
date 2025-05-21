# APScheduler setup and job definition
# app/services/scheduler_service.py

import logging
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.interval import IntervalTrigger
from app.core.config import settings
from app.services.ingestion_service import run_ingestion_cycle

logger = logging.getLogger(__name__)

scheduler = AsyncIOScheduler(timezone="UTC") # Use UTC or your preferred timezone

async def start_scheduler():
    """Starts the scheduler, but automatic ingestion job is disabled for testing."""
    if scheduler.running:
        logger.info("Scheduler already running.")
        return

    try:
        # ======================================================================
        # AUTOMATIC JOB COMMENTED OUT FOR CREDIT CONSERVATION / MANUAL CONTROL
        # ======================================================================
        # The IntervalTrigger still uses settings.ingestion_interval_minutes,
        # which is set to 99999 in .env, so even if uncommented, it wouldn't run often.
        # But commenting it out provides clearer intent during testing.
        # scheduler.add_job(
        #     run_ingestion_cycle,
        #     trigger=IntervalTrigger(minutes=settings.ingestion_interval_minutes),
        #     id="ingestion_cycle_job",
        #     name="Run Social Media Ingestion Cycle",
        #     replace_existing=True,
        #     max_instances=1,
        #     misfire_grace_time=600
        # )
        # ======================================================================

        scheduler.start()
        # Updated log message
        logger.info(f"Scheduler started. Automatic ingestion job IS DISABLED (Commented out in code).")

    except Exception as e:
        logger.error(f"Error starting scheduler: {e}")

async def stop_scheduler():
    """Stops the scheduler gracefully."""
    if scheduler.running:
        logger.info("Stopping scheduler...")
        # Wait=False might be slightly faster for shutdown if no critical background task needs to finish
        scheduler.shutdown(wait=False)
        logger.info("Scheduler stopped.")