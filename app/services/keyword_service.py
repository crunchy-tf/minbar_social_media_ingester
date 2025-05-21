import logging
import httpx
from typing import List, Dict, Any, Optional
from app.core.config import settings

logger = logging.getLogger(__name__)

async def fetch_active_keywords(language: str, limit: int) -> List[Dict[str, Any]]:
    """
    Fetches active keywords for a specific language from the Keyword Manager.

    Args:
        language: The language code ('ar', 'fr', 'en').
        limit: The maximum number of keywords to fetch (read from settings via calling function).

    Returns:
        A list of keyword dictionaries (e.g., [{'term': '...', 'concept_id': '...'}, ...])
        or an empty list if fetching fails or no keywords are found.
    """
    keyword_url = f"{settings.keyword_manager_url}/keywords"
    params = {
        "lang": language,
        "limit": limit,
        # Optionally add min_score if needed: "min_score": settings.some_threshold
    }
    logger.info(f"Fetching keywords from {keyword_url} with params: {params}")

    async with httpx.AsyncClient(timeout=30.0) as client:
        try:
            response = await client.get(keyword_url, params=params)
            response.raise_for_status()  # Raise an exception for bad status codes (4xx or 5xx)

            keywords_data = response.json()
            if isinstance(keywords_data, list):
                logger.info(f"Successfully fetched {len(keywords_data)} keywords for language '{language}'.")
                # Make sure the response format matches what process_keyword expects
                # Example expected item: {"term": "some term", "concept_id": "mongo_id_string", ...}
                return keywords_data
            else:
                logger.warning(f"Received non-list response from Keyword Manager: {keywords_data}")
                return []

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP error fetching keywords: {e.response.status_code} - {e.response.text}")
            return []
        except httpx.RequestError as e:
            logger.error(f"Network error fetching keywords: {e}")
            return []
        except Exception as e:
            logger.error(f"Unexpected error fetching keywords: {e}")
            return []