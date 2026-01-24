import pydantic 
from typing import Dict, Any, Optional
from datetime import datetime, timezone

class ApplicationRequestDTO(pydantic.BaseModel):
    """Data Transfer Object for user application requests."""
    
    userId: str
    jobId: str
    status: str
    appliedDate: str
    notes: Optional[str] = None