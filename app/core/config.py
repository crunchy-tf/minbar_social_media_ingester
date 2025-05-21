import os
from pydantic_settings import BaseSettings
from pydantic import Field, AnyHttpUrl
from typing import List, Literal

class Settings(BaseSettings):
    # MongoDB
    mongo_uri: str = Field(..., validation_alias='MONGO_URI')
    mongo_db_name: str = Field("minbar_raw_data", validation_alias='MONGO_DB_NAME')
    raw_data_collection: str = Field("facebook_posts", validation_alias='RAW_DATA_COLLECTION')

    # Keyword Manager
    keyword_manager_url: AnyHttpUrl = Field(..., validation_alias='KEYWORD_MANAGER_URL')

    # Data365
    data365_api_key: str = Field(..., validation_alias='DATA365_API_KEY')
    data365_base_url: AnyHttpUrl = Field("https://api.data365.co/v1.1", validation_alias='DATA365_BASE_URL')
    data365_search_type: Literal["top", "latest", "hashtag"] = Field("latest", validation_alias='DATA365_SEARCH_TYPE')
    data365_max_posts_per_keyword: int = Field(100, validation_alias='DATA365_MAX_POSTS_PER_KEYWORD') # Default if not in .env
    data365_load_comments: bool = Field(False, validation_alias='DATA365_LOAD_COMMENTS') # Default if not in .env
    data365_max_comments: int = Field(10, validation_alias='DATA365_MAX_COMMENTS') # Default if not in .env
    data365_poll_interval_seconds: int = Field(30, validation_alias='DATA365_POLL_INTERVAL_SECONDS')
    data365_max_poll_attempts: int = Field(20, validation_alias='DATA365_MAX_POLL_ATTEMPTS')

    # Ingestion Service
    ingestion_interval_minutes: int = Field(60, validation_alias='INGESTION_INTERVAL_MINUTES') # Default if not in .env
    keywords_per_cycle: int = Field(50, validation_alias='KEYWORDS_PER_CYCLE') # Default if not in .env
    target_languages: List[str] = Field(["ar", "fr", "en"], validation_alias='TARGET_LANGUAGES')

    # Logging
    log_level: str = Field("INFO", validation_alias='LOG_LEVEL')

    class Config:
        env_file = '.env'
        env_file_encoding = 'utf-8'
        extra = 'ignore' # Ignore extra fields from environment

settings = Settings()# Pydantic settings for environment variables
