from pydantic import BaseModel, Field
from datetime import datetime
from typing import Any, Dict, Optional

class RawFacebookPost(BaseModel):
    ingestion_timestamp: datetime = Field(default_factory=datetime.utcnow)
    source_api: str = "Data365/Facebook"
    data_type: str = "post" # Could be 'comment' if fetching comments separately
    retrieved_by_keyword: str
    keyword_concept_id: Optional[str] = None # From Keyword Manager response
    keyword_language: str # 'ar', 'fr', 'en'
    data365_task_id: Optional[str] = None # Task ID from the POST update request
    original_post_data: Dict[str, Any] # Store the raw JSON object from Data365 here

    class Config:
        json_encoders = {
            datetime: lambda dt: dt.isoformat()
        }
        # Pydantic v2 and later configuration is typically done within model_config
        # model_config = {
        #     "json_encoders": {
        #         datetime: lambda dt: dt.isoformat()
        #     }
        # }# Pydantic models for stored data
