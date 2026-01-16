from utility import logprovider
from pymongo import MongoClient
from mcp.server.fastmcp import FastMCP
from typing import Optional
from urllib.parse import quote_plus
from helpers.tools_register import ToolRegister
import uuid
from managers.mongo_context import app_lifespan
from components.tools.job_listing import JobListingTool


logger = logprovider.get_logger()

job_listing_mcp = FastMCP(name="JMRService",
                 instructions="This MongoDB MCP provides database - JMR search and CRUD functionalities.",
                 stateless_http=True,
                 lifespan=app_lifespan
                 )
def setup_joblisting_server(jmrsvc: FastMCP, correlation_id: Optional[str] = uuid.uuid4()):
    """Register all DB tools with the manager."""

    joblisting_tool_handler = JobListingTool(str(correlation_id))
    tool_manager = ToolRegister(jmrsvc)
    tool_manager.register_handler("job_listing", joblisting_tool_handler)
    logger.info("JMR Database tools and resources registered successfully")