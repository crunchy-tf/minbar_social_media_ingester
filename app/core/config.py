import os
from pydantic_settings import BaseSettings
from pydantic import Field, AnyHttpUrl, field_validator
from typing import List, Literal, Union
import json # For TARGET_LANGUAGES parsing

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
    data365_max_posts_per_keyword: int = Field(100, validation_alias='DATA365_MAX_POSTS_PER_KEYWORD')
    data365_load_comments: bool = Field(False, validation_alias='DATA365_LOAD_COMMENTS')
    data365_max_comments: int = Field(10, validation_alias='DATA365_MAX_COMMENTS')
    data365_poll_interval_seconds: int = Field(30, validation_alias='DATA365_POLL_INTERVAL_SECONDS')
    data365_max_poll_attempts: int = Field(20, validation_alias='DATA365_MAX_POLL_ATTEMPTS')

    # Ingestion Service
    ingestion_interval_minutes: int = Field(60, validation_alias='INGESTION_INTERVAL_MINUTES')
    keywords_per_cycle: int = Field(50, validation_alias='KEYWORDS_PER_CYCLE')
    target_languages: List[str] = Field(["ar", "fr", "en"], validation_alias='TARGET_LANGUAGES')
    keyword_reprocess_hours: int = Field(6, validation_alias='KEYWORD_REPROCESS_HOURS')

    # Logging
    log_level: str = Field("INFO", validation_alias='LOG_LEVEL')

    @field_validator("target_languages", mode='before')
    @classmethod
    def parse_target_languages(cls, v: Union[str, List[str]]) -> List[str]:
        if isinstance(v, list):
            return v
        if isinstance(v, str):
            try:
                parsed_list = json.loads(v)
                if not isinstance(parsed_list, list):
                    raise ValueError("TARGET_LANGUAGES must be a JSON list of strings.")
                if not all(isinstance(item, str) for item in parsed_list):
                    raise ValueError("All items in TARGET_LANGUAGES list must be strings.")
                return parsed_list
            except json.JSONDecodeError:
                raise ValueError("Invalid JSON string for TARGET_LANGUAGES.")
        raise ValueError("Invalid type for TARGET_LANGUAGES.")

    class Config:
        env_file = '.env'
        env_file_encoding = 'utf-8'
        extra = 'ignore' # Ignore extra fields from environment

settings = Settings()