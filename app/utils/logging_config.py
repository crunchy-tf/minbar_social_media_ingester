import logging
import sys
from app.core.config import settings

def setup_logging():
    log_level = settings.log_level.upper()
    logging.basicConfig(
        level=log_level,
        format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
        handlers=[
            logging.StreamHandler(sys.stdout)
            # Add FileHandler here if needed
        ]
    )
    # Suppress noisy logs from libraries if necessary
    # logging.getLogger("httpx").setLevel(logging.WARNING)
    # logging.getLogger("apscheduler").setLevel(logging.WARNING)

    logger = logging.getLogger(__name__)
    logger.info(f"Logging configured with level: {log_level}")