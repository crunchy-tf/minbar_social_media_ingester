import logging
from typing import List, Dict, Any
from app.db.database import get_raw_data_collection
from app.models.data_models import RawFacebookPost
from pymongo.errors import BulkWriteError

logger = logging.getLogger(__name__)

async def insert_raw_facebook_posts(posts: List[RawFacebookPost]):
    """
    Inserts a list of raw Facebook post data into the database.

    Args:
        posts: A list of RawFacebookPost Pydantic models.
    """
    collection = get_raw_data_collection()
    if not posts:
        logger.info("No posts provided to insert.")
        return

    # Convert Pydantic models to dictionaries for MongoDB insertion
    # Use exclude_unset=True if you want to avoid storing None values explicitly
    documents = [post.model_dump(by_alias=True, exclude_unset=False) for post in posts]

    logger.info(f"Attempting to insert {len(documents)} documents into '{collection.name}' collection.")
    try:
        # Use insert_many for better performance
        # ordered=False allows inserts to continue even if some fail (e.g., duplicate key)
        result = await collection.insert_many(documents, ordered=False)
        logger.info(f"Successfully inserted {len(result.inserted_ids)} documents.")
    except BulkWriteError as bwe:
        # This can happen if ordered=False and there are duplicates (if an index exists)
        # or other write errors. We log the details.
        logger.warning(f"Bulk write error during insertion: {len(bwe.details.get('writeErrors', []))} errors.")
        logger.debug(f"BulkWriteError details: {bwe.details}")
        # Depending on requirements, you might want to handle specific errors differently
    except Exception as e:
        logger.error(f"An unexpected error occurred during database insertion: {e}")
        # Depending on severity, you might want to raise this error# Functions to interact with the DB (insert raw data)
