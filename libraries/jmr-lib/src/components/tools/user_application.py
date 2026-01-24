import httpx
import os
from models.context.httpxcontext import HttpxContext
from models.dto.application_request import ApplicationRequestDTO
from utility import logprovider
from mcp.types import Tool, TextContent
from models.handler.base_tool_handler import BaseToolHandler
from typing import List, Any, Dict, Optional
import uuid
from datetime import datetime, timezone
from mcp.server.fastmcp import Context
from mcp.server.session import ServerSession
from components.tools.schemas import APPLICATION_FILTER_SCHEMA
from common import with_retry, with_circuit_breaker, CircuitBreakerError
import json

logger = logprovider.get_logger()

# Default configuration fallback (used if context doesn't provide config)
DEFAULT_UMR_CONFIG = {
    'URL': os.environ.get('UMR_SERVICE_URL', 'http://localhost:5138'),
    'MAX_RETRIES': int(os.environ.get('UMR_MAX_RETRIES', '3')),
    'RETRY_BACKOFF_FACTOR': float(os.environ.get('UMR_RETRY_BACKOFF', '0.5')),
    'STATUS_FORCELIST': [500, 502, 503, 504]
}

class UserApplicationTool(BaseToolHandler):
    """A tool handler for user application management."""

    def __init__(self, correlation_id: Optional[str] = None):
        self.correlation_id = correlation_id or str(uuid.uuid4())

    @property
    def tools(self) -> List[Tool]:
        return [
            Tool(
                name="user_application",
                description="Create user applications for a job.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "application": APPLICATION_FILTER_SCHEMA
                    },
                    "required": ["application"]
                },
                tags=["carevo", "applications", "user", "UMR", "internal"]
            )
        ]

    async def execute(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Execute the specified tool with the given input data."""
        tool_name = arguments["tool_name"]
        input_data = arguments["input_data"]
        ctx: Context[ServerSession, HttpxContext] = arguments.get("ctx")
        
        if not ctx:
            raise ValueError("Context is required for tool execution")
        
        if ctx.request_context.lifespan_context.http_client is None:
            return [TextContent(
                type="text",
                text="Error: HTTP client not initialized"
            )]


        if tool_name == "user_application":
            app_data = input_data.get("application")
            
            # Parse app_data to ApplicationRequestDTO
            application_obj = ApplicationRequestDTO(**app_data)
            
            result = await self._handle_user_application(application_obj, ctx)
            return [TextContent(type="text", text=json.dumps(result, default=str))]
        else:
            raise ValueError(f"Unknown tool: {tool_name}")

    async def _handle_user_application(self, application: ApplicationRequestDTO, ctx: Context[ServerSession, HttpxContext]) -> Dict[str, Any]:
        """Handle user application logic."""
        client: httpx.AsyncClient = ctx.request_context.lifespan_context.http_client
        umr_config = ctx.request_context.lifespan_context.umr_config or DEFAULT_UMR_CONFIG

        logger.info(f"Handling user application with input: {application.model_dump()}")
        
        # Register application with UMR service
        result = await self._register_application(client, application, umr_config)
        return result
    
    async def _register_application(self, client: httpx.AsyncClient, application: ApplicationRequestDTO, umr_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Register user application with UMR service.
        
        This method uses retry and circuit breaker patterns for resilience.
        
        Args:
            client: The httpx async client
            application: Application data to register
            umr_config: UMR service configuration
            
        Returns:
            Dict containing the registration response
            
        Raises:
            httpx.HTTPError: If the request fails
            CircuitBreakerError: If the circuit breaker is open
        """
        # Apply decorators dynamically with config values
        return await self._do_register_application(client, application, umr_config)
    
    @with_circuit_breaker(
        failure_threshold=5,
        recovery_timeout=60,
        name="UMR_Application_Registration"
    )
    async def _do_register_application(self, client: httpx.AsyncClient, application: ApplicationRequestDTO, umr_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Internal registration method with circuit breaker and retry logic.
        
        Args:
            client: The httpx async client
            application: Application data to register
            umr_config: UMR service configuration
            
        Returns:
            Dict containing the registration response
        """
        # Apply retry with config-driven parameters
        max_retries = umr_config.get('MAX_RETRIES', 3)
        backoff_factor = umr_config.get('RETRY_BACKOFF_FACTOR', 0.5)
        status_forcelist = umr_config.get('STATUS_FORCELIST', [500, 502, 503, 504])
        
        # Wrap in retry decorator
        retry_func = with_retry(
            max_retries=max_retries,
            backoff_factor=backoff_factor,
            status_forcelist=status_forcelist
        )(self._execute_registration)
        
        return await retry_func(client, application, umr_config)
    
    async def _execute_registration(self, client: httpx.AsyncClient, application: ApplicationRequestDTO, umr_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the actual registration request.
        
        Args:
            client: The httpx async client
            application: Application data to register
            umr_config: UMR service configuration
            
        Returns:
            Dict containing the registration response
        """
        url = f"{umr_config.get('URL', 'http://localhost:5138')}/api/application/v1/register"
        
        # Prepare request payload
        payload = application.model_dump()
        
        # Add correlation ID for tracking
        headers = {
            'Content-Type': 'application/json',
            'X-Correlation-ID': self.correlation_id
        }
        
        logger.info(f"Registering application with UMR service at {url}")
        logger.debug(f"Request payload: {json.dumps(payload, default=str)}")
        
        # Make POST request
        response = await client.post(
            url,
            json=payload,
            headers=headers
        )
        
        # Raise for error status codes
        response.raise_for_status()
        
        # Parse and return response
        result = response.json()
        logger.info(f"Application registered successfully: {result.get('id', 'unknown')}")
        
        return {
            "status": response.status_code,
            "data": result,
            "correlation_id": self.correlation_id,
            "Location": response.headers.get("Location", "")
        }

