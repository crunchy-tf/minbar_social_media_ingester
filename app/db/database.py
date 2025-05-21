import logging
from motor.motor_asyncio import AsyncIOMotorClient, AsyncIOMotorDatabase, AsyncIOMotorCollection
from app.core.config import settings

logger = logging.getLogger(__name__)

class DataBase:
    client: AsyncIOMotorClient | None = None
    db: AsyncIOMotorDatabase | None = None
    raw_data_collection: AsyncIOMotorCollection | None = None

db = DataBase()

async def connect_db():
    """Establishes connection to MongoDB."""
    logger.info("Connecting to MongoDB...")
    try:
        db.client = AsyncIOMotorClient(settings.mongo_uri)
        db.db = db.client[settings.mongo_db_name]
        db.raw_data_collection = db.db[settings.raw_data_collection]
        # Ping the server to ensure connection
        await db.client.admin.command('ping')
        logger.info("Successfully connected to MongoDB.")
    except Exception as e:
        logger.error(f"Failed to connect to MongoDB: {e}")
        db.client = None
        db.db = None
        db.raw_data_collection = None
        raise # Re-raise exception to prevent app startup if DB fails

async def close_db():
    """Closes MongoDB connection."""
    if db.client:
        logger.info("Closing MongoDB connection...")
        db.client.close()
        logger.info("MongoDB connection closed.")

def get_raw_data_collection() -> AsyncIOMotorCollection:
    """Provides access to the raw data collection."""
    if db.raw_data_collection is None:
         # This should ideally not happen if connect_db was successful
        raise Exception("Database not initialized. Call connect_db first.")
    return db.raw_data_collection# MongoDB connection setup
