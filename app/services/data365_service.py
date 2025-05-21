# Logic for Data365 API interaction
import logging
import httpx
import asyncio
import urllib.parse
from typing import Dict, Any, Optional, List, Tuple
from app.core.config import settings

logger = logging.getLogger(__name__)

# --- Private Helper ---
async def _make_data365_request(
    method: str,
    endpoint: str,
    params: Optional[Dict[str, Any]] = None,
    json_data: Optional[Dict[str, Any]] = None
) -> Dict[str, Any]:
    """Helper function to make requests to the Data365 API."""
    base_url = str(settings.data365_base_url).rstrip('/')
    url = f"{base_url}{endpoint}"
    headers = {"Accept": "application/json"}
    # Add access token to query parameters for all requests
    query_params = {"access_token": settings.data365_api_key}
    if params:
        query_params.update(params)

    async with httpx.AsyncClient(timeout=60.0) as client: # Longer timeout for potential data transfer
        try:
            logger.debug(f"Making Data365 request: {method} {url} PARAMS: {query_params} BODY: {json_data}")
            response = await client.request(method, url, params=query_params, json=json_data, headers=headers)
            response.raise_for_status() # Check for 4xx/5xx errors
            response_json = response.json()
            logger.debug(f"Data365 response status: {response.status_code}, data: {response_json}")

            # Basic check for Data365 specific errors in the response body
            if response_json.get("status") == "fail" or response_json.get("error"):
                error_info = response_json.get("error", {"code": "Unknown", "message": "No error details provided"})
                logger.error(f"Data365 API error in response: Code {error_info.get('code')}, Message: {error_info.get('message')}")
                # Raise a custom exception or return an error indicator if needed
                raise httpx.HTTPError(f"Data365 API Error: {error_info.get('message')}")

            return response_json

        except httpx.HTTPStatusError as e:
            logger.error(f"HTTP Status Error calling Data365 endpoint {endpoint}: {e.response.status_code} - {e.response.text}")
            raise  # Re-raise after logging
        except httpx.RequestError as e:
            logger.error(f"Network Error calling Data365 endpoint {endpoint}: {e}")
            raise # Re-raise after logging
        except Exception as e:
            logger.error(f"Unexpected error during Data365 API call to {endpoint}: {e}")
            raise # Re-raise after logging


# --- Public API Functions ---

async def initiate_facebook_post_search_task(
    search_term: str,
    search_type: str = settings.data365_search_type,
    max_posts: int = settings.data365_max_posts_per_keyword, # Reads from updated settings
    load_comments: bool = settings.data365_load_comments, # Reads from updated settings
    max_comments: int = settings.data365_max_comments # Reads from updated settings
) -> Optional[str]:
    """
    Initiates an asynchronous task on Data365 to search for Facebook posts.

    Args:
        search_term: The keyword or phrase to search for.
        search_type: 'top', 'latest', or 'hashtag'.
        max_posts: Max posts to fetch for this task.
        load_comments: Whether to fetch comments (costs more credits).
        max_comments: Max comments per post if load_comments is True.

    Returns:
        The task_id if successful, None otherwise.
    """
    # URL Encode the search term as it's part of the path
    encoded_search_term = urllib.parse.quote(search_term)
    endpoint = f"/facebook/search/{encoded_search_term}/posts/{search_type}/update"

    params = {
        "max_posts": max_posts,
        "load_comments": load_comments,
        "max_comments": max_comments,
        # Add other params like 'from_date', 'location_id' if needed
        # 'callback_url': 'YOUR_WEBHOOK_URL' # Alternative to polling
    }
    # Filter out None values if any optional params are added
    params = {k: v for k, v in params.items() if v is not None}


    logger.info(f"Initiating Data365 search task for term: '{search_term}' (type: {search_type}) with settings: max_posts={max_posts}, load_comments={load_comments}, max_comments={max_comments}")
    try:
        response_data = await _make_data365_request("POST", endpoint, params=params)
        task_id = response_data.get("data", {}).get("task_id")
        if task_id:
            logger.info(f"Data365 task initiated successfully for '{search_term}'. Task ID: {task_id}")
            return task_id
        else:
            logger.error(f"Failed to get task_id from Data365 response for '{search_term}': {response_data}")
            return None
    except Exception as e:
        logger.error(f"Failed to initiate Data365 search task for '{search_term}': {e}")
        return None


async def get_facebook_search_task_status(search_term: str, search_type: str) -> Optional[str]:
    """
    Checks the status of a previously initiated Data365 search task.

    Args:
        search_term: The original search term used to initiate the task.
        search_type: The original search type used.

    Returns:
        The status string ('created', 'pending', 'finished', 'fail', 'canceled', 'unknown')
        or None if the status check fails.
    """
    encoded_search_term = urllib.parse.quote(search_term)
    endpoint = f"/facebook/search/{encoded_search_term}/posts/{search_type}/update"
    # Note: According to docs, GET status uses the SAME update endpoint & identifying path params
    # Query params like max_posts etc. are NOT needed for GET status/data, only the path identifiers.

    logger.debug(f"Checking Data365 task status for term: '{search_term}' (type: {search_type})")
    try:
        response_data = await _make_data365_request("GET", endpoint)
        status = response_data.get("data", {}).get("status")
        if status:
            logger.debug(f"Data365 task status for '{search_term}' is: {status}")
            return status
        else:
            logger.warning(f"Could not determine task status for '{search_term}' from response: {response_data}")
            return "unknown" # Treat missing status as unknown
    except Exception as e:
        logger.error(f"Failed to get Data365 task status for '{search_term}': {e}")
        return None


async def fetch_facebook_search_results(
    search_term: str,
    search_type: str,
    cursor: Optional[str] = None,
    max_page_size: int = 100 # Max allowed by API per page
) -> Tuple[List[Dict[str, Any]], Optional[str]]:
    """
    Fetches a page of results for a completed Data365 search task.

    Args:
        search_term: The original search term used.
        search_type: The original search type used.
        cursor: The pagination cursor from the previous page, if any.
        max_page_size: How many items to request per page (max 100).

    Returns:
        A tuple containing:
        - A list of post dictionaries fetched from this page.
        - The cursor for the next page, or None if this is the last page or an error occurred.
    """
    encoded_search_term = urllib.parse.quote(search_term)
    endpoint = f"/facebook/search/{encoded_search_term}/posts/{search_type}/posts"

    params = {"max_page_size": max_page_size}
    if cursor:
        params["cursor"] = cursor

    logger.debug(f"Fetching Data365 results page for '{search_term}' (cursor: {cursor})")
    try:
        response_data = await _make_data365_request("GET", endpoint, params=params)

        items = response_data.get("data", {}).get("items", [])
        # Adjust based on actual API response for pagination cursor if needed
        next_cursor = response_data.get("data", {}).get("page_info", {}).get("next_cursor")
        # Some APIs use 'cursor' or other names in page_info

        logger.debug(f"Fetched {len(items)} items for '{search_term}'. Next cursor: {next_cursor}")
        return items, next_cursor

    except Exception as e:
        logger.error(f"Failed to fetch Data365 results page for '{search_term}': {e}")
        return [], None # Return empty list and no cursor on error


async def poll_and_fetch_all_results(search_term: str, task_id: str) -> List[Dict[str, Any]]:
    """
    Polls for task completion and fetches all paginated results.

    Args:
        search_term: The original search term.
        task_id: The ID of the task initiated (mostly for logging here).

    Returns:
        A list containing all fetched post dictionaries for the search term.
    """
    all_posts = []
    search_type = settings.data365_search_type # Use configured search type

    logger.info(f"Polling task status for '{search_term}' (Task ID: {task_id})")
    for attempt in range(settings.data365_max_poll_attempts):
        status = await get_facebook_search_task_status(search_term, search_type)

        if status == "finished":
            logger.info(f"Task for '{search_term}' finished. Fetching results...")
            current_cursor = None
            page_num = 1
            while True:
                logger.info(f"Fetching page {page_num} for '{search_term}'...")
                posts_page, next_cursor = await fetch_facebook_search_results(
                    search_term, search_type, cursor=current_cursor
                )
                if posts_page:
                    all_posts.extend(posts_page)
                    logger.info(f"Fetched {len(posts_page)} posts on page {page_num}. Total so far: {len(all_posts)}")
                else:
                    # Handle case where fetch fails mid-pagination or returns empty
                    logger.warning(f"Received empty page or error fetching page {page_num} for '{search_term}'. Stopping pagination.")
                    break # Stop if a page fetch fails or returns empty unexpectedly

                if next_cursor:
                    current_cursor = next_cursor
                    page_num += 1
                    await asyncio.sleep(1) # Small delay between page fetches
                else:
                    logger.info(f"No next cursor found. Finished fetching all pages for '{search_term}'.")
                    break # No more pages
            return all_posts # Return all collected posts

        elif status in ["fail", "canceled"]:
            logger.error(f"Task for '{search_term}' failed or was canceled (Status: {status}).")
            return [] # Return empty list

        elif status in ["created", "pending", "unknown"] or status is None:
            logger.info(f"Task for '{search_term}' status: {status}. Attempt {attempt + 1}/{settings.data365_max_poll_attempts}. Waiting...")
            await asyncio.sleep(settings.data365_poll_interval_seconds)

        else: # Should not happen with known statuses
             logger.warning(f"Unexpected task status '{status}' for '{search_term}'. Waiting...")
             await asyncio.sleep(settings.data365_poll_interval_seconds)


    logger.error(f"Task polling timed out for '{search_term}' after {settings.data365_max_poll_attempts} attempts.")
    return [] # Return empty list if polling times out