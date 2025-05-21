# app/services/ingestion_service.py

import logging
import asyncio
from typing import List, Dict, Any
from app.core.config import settings
# Assuming fetch_active_keywords is still used unless you hardcode keywords
from app.services.keyword_service import fetch_active_keywords
from app.services.data365_service import (
    initiate_facebook_post_search_task,
    poll_and_fetch_all_results,
)
from app.db.crud import insert_raw_facebook_posts
from app.models.data_models import RawFacebookPost

logger = logging.getLogger(__name__)

async def process_keyword(keyword_info: Dict[str, Any], language: str):
    """
    Processes a single keyword: MODIFIES search term with location,
    initiates task, polls, fetches, structures, and prepares for DB insert.
    """
    original_term = keyword_info.get("term") # Keep track of the original term
    concept_id = keyword_info.get("concept_id")
    if not original_term:
        logger.warning(f"Skipping keyword info due to missing term: {keyword_info}")
        return []

    # --- START MODIFICATION: Append Location ---
    location_append_map = {
        "en": "Tunisia",  # Or "Tunis" if you prefer city focus
        "fr": "Tunisie",  # Or "Tunis"
        "ar": "تونس"      # Tunis (City/Country are the same word here)
    }
    location_specifier = location_append_map.get(language)
    modified_search_term = original_term # Default to original if language not found

    if location_specifier:
        # Combine the original term and the location specifier
        modified_search_term = f"{original_term} {location_specifier}"
        logger.info(f"Processing keyword: '{original_term}' -> Modified to: '{modified_search_term}' (Lang: {language}, Concept: {concept_id})")
    else:
        # Log if location specifier wasn't found (shouldn't happen with controlled languages)
         logger.warning(f"No location specifier mapped for language '{language}'. Using original term: '{original_term}'")
         logger.info(f"Processing keyword: '{original_term}' (Lang: {language}, Concept: {concept_id})")
    # --- END MODIFICATION ---


    # Use the MODIFIED search term for initiating the task
    # initiate_facebook_post_search_task reads other limits (max_posts, comments) from settings
    task_id = await initiate_facebook_post_search_task(search_term=modified_search_term) # Use modified term

    if not task_id:
        logger.error(f"Failed to initiate search task for modified keyword: '{modified_search_term}'. Skipping.")
        return []

    # IMPORTANT: Use the SAME MODIFIED search term for polling and fetching results
    # because the term is part of the API path for status/results endpoints.
    raw_posts_data = await poll_and_fetch_all_results(search_term=modified_search_term, task_id=task_id) # Use modified term

    if not raw_posts_data:
         # Log based on the original keyword for clarity on which keyword yielded nothing
        logger.info(f"No posts found or fetched for original keyword: '{original_term}' (searched as: '{modified_search_term}').")
        return []

    # Structure data for insertion
    posts_to_insert = []
    for post_data in raw_posts_data:
        try:
            # Store the ORIGINAL keyword in the database for traceability
            structured_post = RawFacebookPost(
                retrieved_by_keyword=original_term, # Store original keyword
                keyword_concept_id=concept_id,
                keyword_language=language,
                data365_task_id=task_id,
                original_post_data=post_data
            )
            posts_to_insert.append(structured_post)
        except Exception as e: # Catch potential Pydantic validation errors
            logger.error(f"Error structuring post data for original keyword '{original_term}': {e}. Data: {post_data}")
            # Optionally store errored posts separately or log more details

    # Log preparation based on the original keyword
    logger.info(f"Prepared {len(posts_to_insert)} posts for insertion for original keyword: '{original_term}' (searched as: '{modified_search_term}').")
    return posts_to_insert


# --- run_ingestion_cycle function remains unchanged ---
# It will call the modified process_keyword function above
async def run_ingestion_cycle():
    """Runs a full ingestion cycle: fetches keywords for all target languages and processes them."""
    logger.info("Starting new ingestion cycle...")
    all_posts_for_cycle: List[RawFacebookPost] = []
    tasks = []

    for lang in settings.target_languages:
        logger.info(f"Fetching keywords for language: {lang}")
        # fetch_active_keywords uses settings.keywords_per_cycle
        keywords = await fetch_active_keywords(language=lang, limit=settings.keywords_per_cycle)

        if not keywords:
            logger.info(f"No keywords fetched for language: {lang}. Skipping.")
            continue

        # Create concurrent tasks for processing each keyword
        for kw_info in keywords:
            # Pass the original keyword info and language to process_keyword
            tasks.append(asyncio.create_task(process_keyword(kw_info, lang)))

    # Wait for all keyword processing tasks to complete
    results = await asyncio.gather(*tasks, return_exceptions=True)

    # Collect results and handle potential exceptions from gather
    for result in results:
        if isinstance(result, Exception):
            logger.error(f"An error occurred during keyword processing: {result}")
        elif isinstance(result, list):
            all_posts_for_cycle.extend(result)
        else:
            logger.warning(f"Unexpected result type from process_keyword task: {type(result)}")


    # Insert all collected posts into the database in one batch
    if all_posts_for_cycle:
        logger.info(f"Attempting to insert a total of {len(all_posts_for_cycle)} posts for this cycle.")
        try:
            await insert_raw_facebook_posts(all_posts_for_cycle)
        except Exception as e:
            logger.error(f"Failed to insert batch of posts into database: {e}")
    else:
        logger.info("No posts collected in this cycle to insert into the database.")

    logger.info("Ingestion cycle finished.")