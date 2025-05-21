# app/main.py

import logging
import asyncio # <--- Added import
from contextlib import asynccontextmanager
from fastapi import FastAPI

from app.core.config import settings
from app.utils.logging_config import setup_logging
from app.db.database import connect_db, close_db
from app.services.scheduler_service import start_scheduler, stop_scheduler
# Import the function to be triggered
from app.services.ingestion_service import run_ingestion_cycle


setup_logging()
logger = logging.getLogger(__name__)

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup actions
    logger.info("Application startup...")
    try:
        await connect_db()
        # Scheduler starts but has no automatic ingestion job added
        await start_scheduler()
        logger.info("Startup complete.")
        yield # Application runs here
    finally:
        # Shutdown actions
        logger.info("Application shutdown...")
        await stop_scheduler()
        await close_db()
        logger.info("Shutdown complete.")


app = FastAPI(
    title="Minbar - Social Media Ingester",
    description="Ingests Facebook data from Data365 based on keywords and stores it.",
    version="1.0.0",
    lifespan=lifespan
)

@app.get("/", tags=["Status"])
async def read_root():
    """Root endpoint providing basic service info."""
    return {"message": "Minbar Social Media Ingester is running."}

@app.get("/health", tags=["Status"])
async def health_check():
    """Basic health check endpoint."""
    # Could add DB ping check here later if needed
    return {"status": "ok"}

# ======================================================================
# MANUAL TRIGGER ENDPOINT ADDED
# ======================================================================
@app.post("/trigger-ingestion", tags=["Actions"], status_code=202)
async def trigger_manual_ingestion():
    """
    Manually triggers one background ingestion cycle using current .env settings.
    Be mindful of Data365 credit limits during testing!
    """
    logger.warning("Manual ingestion cycle triggered via API.")
    # Run in the background so the API call returns immediately
    asyncio.create_task(run_ingestion_cycle())
    return {"message": "Manual ingestion cycle initiated in the background."}
# ======================================================================


if __name__ == "__main__":
    import uvicorn
    # Run on port 8001 by default if started directly
    uvicorn.run("app.main:app", host="0.0.0.0", port=8001, reload=True)