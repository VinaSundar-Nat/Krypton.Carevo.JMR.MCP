from helpers.resource_register import ResourceRegister
from helpers.tools_register import ToolRegister
from utility import logprovider
from mcp.server.fastmcp import FastMCP
from typing import Optional
from urllib.parse import quote_plus
import uuid
from managers.http_context import http_app_lifespan
from components.tools.user_application import UserApplicationTool


logger = logprovider.get_logger()

applications_mcp = FastMCP(name="Application Service",
                 instructions="This HTTPX MCP serves as the API client for JMR User applications - Retrieval and management.",
                 stateless_http=True,
                 lifespan=http_app_lifespan
                 )

def setup_user_application_server(appsvc: FastMCP, correlation_id: Optional[str] = uuid.uuid4()):
    """Register all user application tools with the manager."""

    tool_manager = ToolRegister(appsvc)
    tool_manager.register_handler("user_application", UserApplicationTool(str(correlation_id)))
    
    logger.info("UMR user application tools and resources registered successfully")

