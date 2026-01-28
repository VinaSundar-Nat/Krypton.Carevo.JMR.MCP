# from ast import And
from utility import logprovider
from mcp.types import Resource, ResourceTemplate, TextContent
from models.handler.base_resource_handler import BaseResourceHandler
from typing import List, Any, Dict, Optional, Union
import uuid
import json
from mcp.server.fastmcp import Context
from mcp.server.session import ServerSession
from models.context.dbcontext import DbContext
from models.domain.jobs.job import Job
from datetime import datetime, timezone
from beanie.operators import GTE, And
from urllib.parse import unquote

logger = logprovider.get_logger()


class JobListingResource(BaseResourceHandler):
    """A resource handler for exposing job listings."""

    def __init__(self, correlation_id: Optional[str] = None):
        self.correlation_id = correlation_id or str(uuid.uuid4())

    @property
    def direct_resources(self) -> List[Resource]:
        """Direct resources with static URIs."""
        return [
            Resource(
                uri="jobs://today",
                name="Active Job Listings",
                description="Access only active job listings (non-closed positions).",
                mimeType="application/json"
            )
        ]
    
    @property
    def resource_templates(self) -> List[ResourceTemplate]:
        """Resource templates with dynamic URI parameters."""
        return [
            ResourceTemplate(
                uriTemplate="jobs://details/{job_id}",
                name="Job Listing Details",
                description="Access detailed information for a specific job listing by ID.",
                mimeType="application/json"
            ),
            ResourceTemplate(
                uriTemplate="jobs://views/{job_id}",
                name="Listed Job view count",
                description="get view count for a specific job listing by ID.",
                mimeType="application/json"
            )
        ]
    
    @property
    def resources(self) -> List[Union[Resource, ResourceTemplate]]:
        """Combined list of all resources (direct and templates)."""
        combined = self.direct_resources + self.resource_templates
        return combined

    async def read_resource(self, uri: str) -> str:
        """Read resource content by URI."""
               
        # Decode the URI to handle any URL-encoded characters
        decoded_uri = unquote(uri)
        
        if decoded_uri == "jobs://today":
            return await self._fetch_active_jobs()
        elif decoded_uri.startswith("jobs://views/"):
            job_id = decoded_uri.replace("jobs://views/", "")
            return await self._fetch_job_views(job_id)
        elif decoded_uri.startswith("jobs://details/"):
            job_id = decoded_uri.replace("jobs://details/", "")
            return await self._fetch_job_by_id(job_id)
        else:
            raise ValueError(f"Unknown resource URI: {uri}")

    async def _fetch_active_jobs(self) -> str:
        """Fetch only todays active job listings."""
        try:
            logger.info(f"Fetching active job listings - correlation_id: {self.correlation_id}")
            
            # Get active jobs posted today (compare date only, not time)
            # Since posted_date is a string, we compare with date string format
            today_date_str = datetime.now(timezone.utc).date().isoformat()
            jobs = await Job.find(GTE(Job.posted_date, today_date_str)).to_list()
            
            # Convert to dictionaries, exclude views for privacy
            jobs_data = [job.model_dump(exclude={'views'}) for job in jobs]
        
            logger.info(f"Retrieved {len(jobs_data)} active job listings - correlation_id: {self.correlation_id}")
            return json.dumps(jobs_data, default=str)
        except Exception as e:
            logger.error(f"Error fetching active jobs: {str(e)} - correlation_id: {self.correlation_id}")
            raise
        finally:
            logger.info(f"Completed _fetch_active_jobs operation - correlation_id: {self.correlation_id}")

    async def _fetch_job_by_id(self, job_id: str) -> str:
        """Fetch a specific job listing by ID."""
        try:
            if not job_id:
                raise ValueError("job_id is required")
            
            logger.info(f"Fetching job listing by ID: {job_id} - correlation_id: {self.correlation_id}")
            
            job = await Job.find_one(Job.job_id == job_id)
            
            if not job:
                logger.warning(f"Job not found with ID: {job_id} - correlation_id: {self.correlation_id}")
                return json.dumps({"error": f"Job not found with ID: {job_id}"})
            
            # Convert to dictionary, exclude views for privacy
            job_data = job.model_dump(exclude={'views'})
            job_data['view_count'] = len(job.views) if job.views else 0
            
            logger.info(f"Retrieved job listing with ID: {job_id} - correlation_id: {self.correlation_id}")
            return json.dumps(job_data, default=str)
        except Exception as e:
            logger.error(f"Error fetching job by ID: {str(e)} - correlation_id: {self.correlation_id}")
            raise
        finally:
            logger.info(f"Completed _fetch_job_by_id operation - correlation_id: {self.correlation_id}")

    async def _fetch_job_views(self, job_id: str) -> str:
        """Fetch view count for a specific job listing by ID."""
        try:
            if not job_id:
                raise ValueError("job_id is required")
            
            logger.info(f"Fetching view count for job ID: {job_id} - correlation_id: {self.correlation_id}")
            
            job = await Job.find_one(Job.job_id == job_id)
            
            if not job:
                logger.warning(f"Job not found with ID: {job_id} - correlation_id: {self.correlation_id}")
                return json.dumps({"error": f"Job not found with ID: {job_id}", "job_id": job_id, "view_count": 0})
            
            view_count = len(job.views) if job.views else 0
            
            result = {
                "job_id": job_id,
                "view_count": view_count
            }
            
            logger.info(f"Retrieved {view_count} views for job ID: {job_id} - correlation_id: {self.correlation_id}")
            return json.dumps(result, default=str)
        except Exception as e:
            logger.error(f"Error fetching job views: {str(e)} - correlation_id: {self.correlation_id}")
            raise
        finally:
            logger.info(f"Completed _fetch_job_views operation - correlation_id: {self.correlation_id}")
