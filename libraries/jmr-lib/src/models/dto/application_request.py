import pydantic 
from typing import Dict, Any, Optional

class ApplicationCreateDTO(pydantic.BaseModel):
    """Data Transfer Object for user application requests."""
    
    userId: str
    jobId: str
    status: str
    appliedDate: str
    notes: Optional[str] = None

class ApplicationUpdateDTO(pydantic.BaseModel):
    """Data Transfer Object for updating user application status."""
    
    applicationId: int
    userId: int
    status: str
    statusChangedDate: str
    notes: Optional[str] = None