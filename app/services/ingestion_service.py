# app/services/ingestion_service.py

import logging
import asyncio
import json # For file-based cache
from datetime import datetime, timedelta, timezone # For cache TTL and timezone awareness
from pathlib import Path # For cache file path
from typing import List, Dict, Any

from app.core.config import settings
from app.services.keyword_service import fetch_active_keywords
from app.services.data365_service import (
    initiate_facebook_post_search_task,
    poll_and_fetch_all_results,
)
from app.db.crud import insert_raw_facebook_posts
from app.models.data_models import RawFacebookPost

logger = logging.getLogger(__name__)

# --- Cache Configuration & Helpers ---
# Place cache inside the 'app' directory if WORKDIR is /app, or adjust as needed.
# Assuming current working directory of the app process is /app (as in Dockerfile)
# If ingestion_service.py is in /app/app/services, Path.cwd() might be /app.
# To be safer, make it relative to this file's location or a known app root.
APP_ROOT_DIR = Path(__file__).resolve().parent.parent # This should point to /app/app
INGESTER_CACHE_DIR = APP_ROOT_DIR / "cache_data" # Creates /app/app/cache_data
INGESTER_CACHE_DIR.mkdir(parents=True, exist_ok=True) # Ensure directory exists
CACHE_FILE_PATH = INGESTER_CACHE_DIR / "social_media_ingester_cache.json"

KEYWORD_REPROCESS_INTERVAL = timedelta(hours=settings.keyword_reprocess_hours)

def load_ingester_cache() -> Dict[str, str]: # Stores ISO string timestamps
    """Loads the ingester cache from a JSON file."""
    if CACHE_FILE_PATH.exists():
        try:
            with open(CACHE_FILE_PATH, "r", encoding="utf-8") as f:
                cache_content = json.load(f)
                if isinstance(cache_content, dict):
                    return cache_content
                else:
                    logger.warning(f"Cache file {CACHE_FILE_PATH} content is not a dictionary. Re-initializing cache.")
                    return {}
        except (json.JSONDecodeError, IOError) as e:
            logger.error(f"Error loading ingester cache from {CACHE_FILE_PATH}: {e}. Starting with an empty cache.")
    return {}

def save_ingester_cache(cache: Dict[str, str]):
    """Saves the ingester cache to a JSON file."""
    try:
        with open(CACHE_FILE_PATH, "w", encoding="utf-8") as f:
            json.dump(cache, f, indent=2)
        logger.debug(f"Ingester cache saved to {CACHE_FILE_PATH}")
    except IOError as e:
        logger.error(f"Error saving ingester cache to {CACHE_FILE_PATH}: {e}")

async def process_keyword(
    keyword_info: Dict[str, Any],
    language: str,
    ingester_cache: Dict[str, str] # Pass the cache to be updated
):
    """
    Processes a single keyword: MODIFIES search term with location,
    initiates task, polls, fetches, structures, and prepares for DB insert.
    Returns list of RawFacebookPost or empty list if skipped/failed.
    Updates ingester_cache if an external API call is made.
    """
    original_term = keyword_info.get("term")
    concept_id = keyword_info.get("concept_id")

    # Cache check is done in run_ingestion_cycle before calling this function
    # This function now assumes it *should* process externally.

    if not original_term or not concept_id: # Should not happen if selected properly
        logger.warning(f"process_keyword called with missing term or concept_id: {keyword_info}")
        return []

    # --- START MODIFICATION: Append Location (existing logic) ---
    location_append_map = {
        "en": "Tunisia",
        "fr": "Tunisie",
        "ar": "تونس"
    }
    location_specifier = location_append_map.get(language)
    modified_search_term = original_term
    if location_specifier:
        modified_search_term = f"{original_term} {location_specifier}"
    # --- END MODIFICATION ---

    logger.info(f"EXTERNALLY PROCESSING keyword: '{original_term}' -> Modified to: '{modified_search_term}' (Lang: {language}, Concept: {concept_id}).")

    task_id = await initiate_facebook_post_search_task(search_term=modified_search_term)

    if not task_id:
        logger.error(f"Failed to initiate Data365 search task for modified keyword: '{modified_search_term}'. Skipping.")
        return []

    # --- Update Cache ON SUCCESSFUL TASK INITIATION ---
    now_utc = datetime.now(timezone.utc)
    ingester_cache[concept_id] = now_utc.isoformat().replace("+00:00", "Z")
    # The cache will be saved in bulk at the end of run_ingestion_cycle

    raw_posts_data = await poll_and_fetch_all_results(search_term=modified_search_term, task_id=task_id)

    if not raw_posts_data:
        logger.info(f"No posts found or fetched for original keyword: '{original_term}' (searched as: '{modified_search_term}').")
        return []

    posts_to_insert = []
    for post_data in raw_posts_data:
        try:
            structured_post = RawFacebookPost(
                retrieved_by_keyword=original_term,
                keyword_concept_id=concept_id,
                keyword_language=language,
                data365_task_id=task_id,
                original_post_data=post_data
            )
            posts_to_insert.append(structured_post)
        except Exception as e:
            logger.error(f"Error structuring post data for original keyword '{original_term}': {e}. Data: {post_data}")

    logger.info(f"Prepared {len(posts_to_insert)} posts for insertion for original keyword: '{original_term}'.")
    return posts_to_insert


async def run_ingestion_cycle():
    """Runs a full ingestion cycle: loads cache, fetches keywords, processes them (respecting cache and limits), and saves cache."""
    logger.info(f"Starting new ingestion cycle... Reprocess interval: {KEYWORD_REPROCESS_INTERVAL}")
    current_ingester_cache = load_ingester_cache()
    all_posts_for_cycle: List[RawFacebookPost] = []
    
    # List to store items that need actual external processing
    # Each item: {'kw_info': Dict[str, Any], 'language': str}
    items_for_external_processing: List[Dict[str, Any]] = []
    external_api_calls_to_make_count = 0

    for lang in settings.target_languages:
        if external_api_calls_to_make_count >= settings.keywords_per_cycle:
            logger.info(f"Target for external API calls ({settings.keywords_per_cycle}) reached for this cycle. Skipping further languages.")
            break

        logger.info(f"Fetching candidate keywords for language: {lang}")
        # Fetch more candidates than keywords_per_cycle to account for cache skips.
        candidate_limit = max(settings.keywords_per_cycle * 3, 15) # Fetch at least 15 or 3x target
        
        candidate_keywords = await fetch_active_keywords(language=lang, limit=candidate_limit)

        if not candidate_keywords:
            logger.info(f"No candidate keywords fetched for language: {lang}. Skipping.")
            continue

        logger.info(f"Fetched {len(candidate_keywords)} candidate keywords for {lang}.")
        
        for kw_info in candidate_keywords:
            if external_api_calls_to_make_count >= settings.keywords_per_cycle:
                logger.debug(f"Target for external API calls ({settings.keywords_per_cycle}) reached within language {lang}. Not considering more candidates.")
                break # Stop considering more candidates for this language

            concept_id = kw_info.get("concept_id")
            if not concept_id:
                logger.warning(f"Skipping candidate kw_info due to missing concept_id: {kw_info}")
                continue

            # Check cache for this candidate
            now_utc = datetime.now(timezone.utc)
            last_processed_iso = current_ingester_cache.get(concept_id)
            should_process_externally = True # Assume we will process unless cache says no

            if last_processed_iso:
                try:
                    last_processed_dt = datetime.fromisoformat(last_processed_iso.replace("Z", "+00:00")).astimezone(timezone.utc)
                    if (now_utc - last_processed_dt) < KEYWORD_REPROCESS_INTERVAL:
                        should_process_externally = False 
                        logger.debug(f"CACHE HIT: Concept ID '{concept_id}' (Term: '{kw_info.get('term')}') processed at {last_processed_dt}. Will not initiate external API call.")
                    else:
                        logger.debug(f"CACHE STALE: Concept ID '{concept_id}' (Term: '{kw_info.get('term')}') last processed at {last_processed_dt}. Will be considered for reprocessing.")
                except ValueError:
                    logger.warning(f"Invalid cache timestamp for {concept_id} ('{last_processed_iso}'). Will be considered for processing.")
            else:
                 logger.debug(f"CACHE MISS: Concept ID '{concept_id}' (Term: '{kw_info.get('term')}') not in cache. Will be considered for processing.")
            
            if should_process_externally:
                items_for_external_processing.append({'kw_info': kw_info, 'language': lang})
                external_api_calls_to_make_count += 1
                logger.debug(f"Concept ID '{concept_id}' added to external processing list. API calls to make this cycle: {external_api_calls_to_make_count}/{settings.keywords_per_cycle}")
    
    # Create tasks only for the selected items
    processing_tasks = []
    for item in items_for_external_processing:
        # process_keyword will update the cache internally if successful
        processing_tasks.append(
            asyncio.create_task(process_keyword(item['kw_info'], item['language'], current_ingester_cache))
        )
    
    if not processing_tasks:
        logger.info("No keywords to process externally in this cycle after cache checks and limits.")
    else:
        logger.info(f"Gathering results for {len(processing_tasks)} keyword processing tasks...")
        results = await asyncio.gather(*processing_tasks, return_exceptions=True)

        for result in results:
            if isinstance(result, Exception):
                logger.error(f"An error occurred during a keyword processing task: {result}", exc_info=True)
            elif isinstance(result, list): 
                all_posts_for_cycle.extend(result)
            # process_keyword returns empty list [] on skip or no data

    save_ingester_cache(current_ingester_cache) 

    if all_posts_for_cycle:
        logger.info(f"Attempting to insert a total of {len(all_posts_for_cycle)} posts for this cycle.")
        try:
            await insert_raw_facebook_posts(all_posts_for_cycle)
        except Exception as e:
            logger.error(f"Failed to insert batch of posts into database: {e}")
    else:
        logger.info("No posts collected in this cycle to insert into the database.")

    logger.info("Ingestion cycle finished.")