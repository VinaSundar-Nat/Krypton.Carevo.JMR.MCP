from abc import ABC, abstractmethod
from typing import Dict, List, Any, Optional
from dataclasses import dataclass
from typing_extensions import Annotated
from beanie import Document, Indexed
from beanie.operators import GTE, LTE, In, Or, And
from pydantic import BaseModel, Field, computed_field
from enum import Enum

class View(BaseModel):
    """A view record for a job listing."""
    
    user_id: str
    view_date: str

class JobType(str, Enum):
    FULL_TIME = "Full Time"
    PART_TIME = "Part Time"
    CONTRACT = "Contract"
    INTERN = "Intern"
    TEMPORARY = "Temporary"

class ConnectionType(str, Enum):
    ONSITE = "Onsite"
    REMOTE = "Remote"
    HYBRID = "Hybrid"

class FilterOperator(str, Enum):
    AND = "AND"
    OR = "OR"
    
class Job(Document):
    """A job listing document in the database."""
    job_id: Annotated[str, Indexed(unique=True)]
    title: str
    description: str
    company: str
    location: str
    job_type: JobType
    connection_type: ConnectionType
    salary_range: Dict[str, Any]
    posted_date: str
    skills: List[str]
    views: List[View] = Field(default=[])
    source: str
    created_at: str
    updated_at: str
    
    @computed_field
    @property
    def view_count(self) -> int:
        """Return the count of views instead of the full view data."""
        return len(self.views) if self.views else 0

class JobFilter:

    """Filter criteria for querying job listings."""
    
    def __init__(
        self,
        job_id: str = None,
        company: str = None,
        location: str = None,
        job_type: JobType = None,
        connection_type: ConnectionType = None,
        skills: List[str] = None,
        posted_from: str = None,
        posted_to: str = None,
        operator: FilterOperator = FilterOperator.AND
    ):
        self.job_id = job_id
        self.company = company
        self.location = location
        self.job_type = job_type
        self.connection_type = connection_type
        self.skills = skills
        self.posted_from = posted_from
        self.posted_to = posted_to
        self.operator = operator
    
class JobFilterHelpers():

    def build_filter_query(self, job_filter: JobFilter):
        """
        Build a Beanie query using operators from the JobFilter object.
        
        Args:
            job_filter: JobFilter instance with filter criteria
            
        Returns:
            Beanie query expression (And/Or) or None if no filters
        """
        conditions = []

        if job_filter.job_id:
            conditions.append(Job.job_id == job_filter.job_id)
        
        if job_filter.company:
            conditions.append(Job.company == job_filter.company)
        
        if job_filter.location:
            conditions.append(Job.location == job_filter.location)
        
        if job_filter.job_type:
            conditions.append(Job.job_type == job_filter.job_type)
        
        if job_filter.connection_type:
            conditions.append(Job.connection_type == job_filter.connection_type)
        
        if job_filter.skills:
            # Match jobs that have all specified skills
            conditions.append(In(Job.skills, job_filter.skills))
        
        # Date range queries using GTE and LTE operators
        if job_filter.posted_from:
            conditions.append(GTE(Job.posted_date, job_filter.posted_from))
        
        if job_filter.posted_to:
            conditions.append(LTE(Job.posted_date, job_filter.posted_to))
        
        # Return None if no conditions
        if not conditions:
            return None
        
        # Apply operator (AND or OR)
        if job_filter.operator == FilterOperator.OR:
            return Or(*conditions)
        else:
            return And(*conditions)
        
    





