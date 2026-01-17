from pymongo import AsyncMongoClient
from utility import logprovider
from mcp.types import Tool, TextContent
from models.handler.base_tool_handler import BaseToolHandler
from typing import List, Any, Dict, Optional
import uuid
from datetime import datetime, timezone
from mcp.server.fastmcp import Context
from mcp.server.session import ServerSession
from models.context.dbcontext import DbContext
from models.domain.jobs.job import Job, JobFilter , JobFilterHelpers, View
from components.tools.schemas import JOB_FILTER_SCHEMA, JOB_SCHEMA, JOB_VIEW_SCHEMA
import json

logger = logprovider.get_logger()


class JobListingTool(BaseToolHandler):
    """A tool for managing job listings."""

    def __init__(self, correlation_id: Optional[str] = None):
        self.correlation_id = correlation_id or str(uuid.uuid4())

    @property
    def tools(self) -> List[Tool]:
        return [
            Tool(
                name="fetch_job_listings",
                description="Fetch job listings from the database based on criteria.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "filter": JOB_FILTER_SCHEMA
                    },
                    "required": []
                },
                tags=["carevo", "jobs", "filter", "nosql", "internal"]
            ),
            Tool(
                name="create_job_listing",
                description="Create a new job listing in the database.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "job": JOB_SCHEMA
                    },
                    "required": ["job"]
                },
                tags=["carevo", "job", "user", "nosql", "internal"]
            ),
            Tool(
                name="get_job_views",
                description="Get views for a specific job listing.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "jobid": {"type": "string", "description": "Data for the new job listing"}
                    },
                    "required": ["jobid"]
                },
                tags=["carevo", "jobviews", "jobid", "nosql", "internal"]
            ),
            Tool(
                name="create_job_view",
                description="Create or update a view for a job listing. Updates view_date if user has already viewed the job.",
                inputSchema=JOB_VIEW_SCHEMA,
                tags=["carevo", "job", "view", "nosql", "internal"]
            )
        ]
    

    async def execute(self, arguments: Dict[str, Any]) -> List[TextContent]:
        tool_name = arguments["tool_name"]
        input_data = arguments["input_data"]
        ctx: Context[ServerSession, DbContext] = arguments.get("ctx")
        
        if not ctx:
            raise ValueError("Context is required for tool execution")
        
        if tool_name == "fetch_job_listings":
            filter_data = input_data.get("filter")
            filter_obj = JobFilter(**filter_data) if filter_data else JobFilter()
            result = await self.fetch_job_listings(filter_obj, ctx)
            # Convert Job objects to dictionaries, exclude views for privacy (only expose view_count)
            jobs_data = [job.model_dump(exclude={'views'}) for job in result]
            return [TextContent(type="text", text=json.dumps(jobs_data, default=str))]
        
        elif tool_name == "create_job_listing":
            job_data = input_data.get("job")
            job_obj = Job(**job_data) if job_data else None
            result = await self.create_job_listing(job_obj, ctx)
            # Exclude views for privacy (only expose view_count)
            return [TextContent(type="text", text=json.dumps(result.model_dump(exclude={'views'}), default=str))]
        
        elif tool_name == "get_job_views":
            job_id = input_data.get("jobid")
            result = await self.get_job_views(job_id, ctx)
            # Convert View objects to dictionaries
            views_data = [view.model_dump() for view in result]
            return [TextContent(type="text", text=json.dumps(views_data, default=str))]
        
        elif tool_name == "create_job_view":
            job_id = input_data.get("job_id")
            user_id = input_data.get("user_id")
            result = await self.create_job_view(job_id, user_id, ctx)
            # Result is already a dictionary
            return [TextContent(type="text", text=json.dumps(result, default=str))]
        
        else:
            raise ValueError(f"Unknown tool: {tool_name}")
    
    async def fetch_job_listings(self, filter: JobFilter, ctx: Context[ServerSession, DbContext]) -> List[Job]:
        """Fetch school details by name."""
        try:
             # Access the async driver from the lifespan context
            # client: AsyncMongoClient = ctx.request_context.lifespan_context.client 

            query = JobFilterHelpers().build_filter_query(filter)
            logger.info(f"Fetching job listings with filter: {filter} - correlation_id: {self.correlation_id}")
            
            jobs = await Job.find(query).to_list()
            logger.info(f"Fetched {len(jobs)} job listings with filter: {filter} - correlation_id: {self.correlation_id}")
            return jobs
        except Exception as e:
            logger.error(f"Error fetching job listings: {str(e)} - correlation_id: {self.correlation_id}")
            raise
        finally:
            logger.info(f"Completed fetch_job_listings operation - correlation_id: {self.correlation_id}")

    async def create_job_listing(self, job: Job, ctx: Context[ServerSession, DbContext]) -> Job:
        """Create a new job listing in the database."""
        try:
            # Access the async driver from the lifespan context
            # client: AsyncMongoClient = ctx.request_context.lifespan_context.client
            
            if not job:
                raise ValueError("Job data is required to create a job listing")
            
            logger.info(f"Creating job listing: {job.title} at {job.company} - correlation_id: {self.correlation_id}")
            
            # Insert the job document using Beanie
            await job.insert()
            
            logger.info(f"Successfully created job listing with ID: {job.id} - correlation_id: {self.correlation_id}")
            return job
        except Exception as e:
            logger.error(f"Error creating job listing: {str(e)} - correlation_id: {self.correlation_id}")
            raise
        finally:
            logger.info(f"Completed create_job_listing operation - correlation_id: {self.correlation_id}")

    async def get_job_views(self, job_id: str, ctx: Context[ServerSession, DbContext]) -> List[View]:
        """Dedicated method to fetch views for a specific job."""
        try:
            # client: AsyncMongoClient = ctx.request_context.lifespan_context.client
            
            logger.info(f"Fetching views for job ID: {job_id} - correlation_id: {self.correlation_id}")
            
            job = await Job.find_one(Job.job_id == job_id)
            if not job:
                logger.warning(f"Job not found with ID: {job_id} - correlation_id: {self.correlation_id}")
                return []
            
            logger.info(f"Retrieved {len(job.views)} views for job ID: {job_id} - correlation_id: {self.correlation_id}")
            return job.views if job else []
        except Exception as e:
            logger.error(f"Error fetching job views: {str(e)} - correlation_id: {self.correlation_id}")
            raise
        finally:
            logger.info(f"Completed get_job_views operation - correlation_id: {self.correlation_id}")

    async def create_job_view(self, job_id: str, user_id: str, ctx: Context[ServerSession, DbContext]) -> Dict[str, Any]:
        """Create or update a view for a job listing."""
        try:
            # client: AsyncMongoClient = ctx.request_context.lifespan_context.client
            
            if not job_id or not user_id:
                raise ValueError("job_id and user_id are required")
            
            logger.info(f"Creating/updating view for job ID: {job_id}, user ID: {user_id} - correlation_id: {self.correlation_id}")
            
            # Find the job
            job = await Job.find_one(Job.job_id == job_id)
            if not job:
                raise ValueError(f"Job not found with ID: {job_id}")
            
            # Get current UTC datetime
            current_utc = datetime.now(timezone.utc).isoformat()
            
            # Check if user has already viewed this job
            existing_view = next((view for view in job.views if view.user_id == user_id), None)
            
            if existing_view is not None:
                # Update existing view
                existing_view.view_date = current_utc
                action = "updated"
                logger.info(f"Updated existing view for user {user_id} on job {job_id} - correlation_id: {self.correlation_id}")
            else:
                # Create new view
                new_view = View(user_id=user_id, view_date=current_utc)
                job.views.append(new_view)
                logger.info(f"Created new view for user {user_id} on job {job_id} - correlation_id: {self.correlation_id}")
                action = "created"
            
            # Save the updated job
            await job.save()
            
            result = {
                "job_id": job_id,
                "user_id": user_id,
                "view_date": current_utc,
                "action": action,
                "total_job_views": len(job.views)
            }
            
            logger.info(f"Successfully {action} view for job {job_id} - correlation_id: {self.correlation_id}")
            return result
            
        except Exception as e:
            logger.error(f"Error creating job view: {str(e)} - correlation_id: {self.correlation_id}")
            raise
        finally:
            logger.info(f"Completed create_job_view operation - correlation_id: {self.correlation_id}")
