import httpx
import os
from models.context.httpxcontext import HttpxContext
from models.dto.application_request import ApplicationCreateDTO , ApplicationUpdateDTO
from utility import logprovider
from mcp.types import Tool, TextContent
from models.handler.base_tool_handler import BaseToolHandler
from typing import List, Any, Dict, Optional
import uuid
from datetime import datetime, timezone
from mcp.server.fastmcp import Context
from mcp.server.session import ServerSession
from components.tools.schemas import APPLICATION_CREATE_SCHEMA, APPLICATION_UPDATE_SCHEMA
from common import with_retry, with_circuit_breaker, CircuitBreakerError
import json

logger = logprovider.get_logger()

# Default configuration fallback (used if context doesn't provide config)
# DEFAULT_UMR_CONFIG = {
#     'URL': os.environ.get('UMR_SERVICE_URL', 'http://localhost:5138'),
#     'MAX_RETRIES': int(os.environ.get('UMR_MAX_RETRIES', '3')),
#     'RETRY_BACKOFF_FACTOR': float(os.environ.get('UMR_RETRY_BACKOFF', '0.5')),
#     'STATUS_FORCELIST': [500, 502, 503, 504]
# }

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
                        "application": APPLICATION_CREATE_SCHEMA
                    },
                    "required": ["application"]
                },
                tags=["carevo", "applications", "user", "UMR", "internal"]
            ),
            Tool(
                name="application_status_update",
                description="Update the status of a user application.",
                inputSchema={
                    "type": "object",
                    "properties": {
                        "application": APPLICATION_UPDATE_SCHEMA
                    },
                    "required": ["application"]
                },
                tags=["carevo", "applications", "management", "status", "UMR", "internal"]
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
            
            # Parse app_data to ApplicationCreateDTO
            application_obj = ApplicationCreateDTO(**app_data)
            
            result = await self._handle_user_application(application_obj, ctx)
            return [TextContent(type="text", text=json.dumps(result, default=str))]
        elif tool_name == "application_status_update":
            app_data = input_data.get("application")
            
            # Parse app_data to ApplicationUpdateDTO
            application_obj = ApplicationUpdateDTO(**app_data)
            
            result = await self._handle_application_update(application_obj, ctx)
            return [TextContent(type="text", text=json.dumps(result, default=str))]
        else:
            raise ValueError(f"Unknown tool: {tool_name}")

    def _get_retry_config(self, umr_config: Dict[str, Any]) -> tuple[int, float, list]:
        """Extract retry configuration parameters from UMR config.
        
        Args:
            umr_config: UMR service configuration
            
        Returns:
            Tuple of (max_retries, backoff_factor, status_forcelist)
        """
        max_retries = umr_config.get('MAX_RETRIES', 3)
        backoff_factor = umr_config.get('RETRY_BACKOFF_FACTOR', 0.5)
        status_forcelist = umr_config.get('STATUS_FORCELIST', [500, 502, 503, 504])
        return max_retries, backoff_factor, status_forcelist

    async def _handle_user_application(self, application: ApplicationCreateDTO, ctx: Context[ServerSession, HttpxContext]) -> Dict[str, Any]:
        """Handle user application logic."""
        client: httpx.AsyncClient = ctx.request_context.lifespan_context.http_client
        umr_config = ctx.request_context.lifespan_context.umr_config
        
        if not umr_config:
            raise ValueError("UMR configuration is missing in context")

        logger.info(f"Handling user application with input: {application.model_dump()}")
        
        # Register application with UMR service
        result = await self._do_register_application(client, application, umr_config)
        return result
    
    @with_circuit_breaker(
        failure_threshold=5,
        recovery_timeout=60,
        name="UMR_Application_Registration"
    )
    async def _do_register_application(self, client: httpx.AsyncClient, application: ApplicationCreateDTO, umr_config: Dict[str, Any]) -> Dict[str, Any]:
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
        max_retries, backoff_factor, status_forcelist = self._get_retry_config(umr_config)
        
        # Wrap in retry decorator
        retry_func = with_retry(
            max_retries=max_retries,
            backoff_factor=backoff_factor,
            status_forcelist=status_forcelist
        )(self._execute_registration)
        
        return await retry_func(client, application, umr_config)
    
    async def _execute_registration(self, client: httpx.AsyncClient, application: ApplicationCreateDTO, umr_config: Dict[str, Any]) -> Dict[str, Any]:
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
        if response.status_code == 201:
            logger.info(f"Application registered successfully: {response.headers.get('Location', '')}")
        
        return {
            "status": response.status_code,
            "correlation_id": self.correlation_id,
            "Location": response.headers.get("Location", "")
        }
    
    async def _handle_application_update(self, application: ApplicationUpdateDTO, ctx: Context[ServerSession, HttpxContext]) -> Dict[str, Any]:
        """Handle application status update logic."""
        client: httpx.AsyncClient = ctx.request_context.lifespan_context.http_client
        umr_config = ctx.request_context.lifespan_context.umr_config
        
        if not umr_config:
            raise ValueError("UMR configuration is missing in context")

        logger.info(f"Handling application update with input: {application.model_dump()}")
        
        # Update application with UMR service
        result = await self._do_update_application(client, application, umr_config)
        return result
    
    @with_circuit_breaker(
        failure_threshold=5,
        recovery_timeout=60,
        name="UMR_Application_Update"
    )
    async def _do_update_application(self, client: httpx.AsyncClient, application: ApplicationUpdateDTO, umr_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Internal update method with circuit breaker and retry logic.
        
        Args:
            client: The httpx async client
            application: Application update data
            umr_config: UMR service configuration
            
        Returns:
            Dict containing the update response
        """
        # Apply retry with config-driven parameters
        max_retries, backoff_factor, status_forcelist = self._get_retry_config(umr_config)
        
        # Wrap in retry decorator
        retry_func = with_retry(
            max_retries=max_retries,
            backoff_factor=backoff_factor,
            status_forcelist=status_forcelist
        )(self._execute_update)
        
        return await retry_func(client, application, umr_config)
    
    async def _execute_update(self, client: httpx.AsyncClient, application: ApplicationUpdateDTO, umr_config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Execute the actual application status update request.
        
        Args:
            client: The httpx async client
            application: Application update data
            umr_config: UMR service configuration
            
        Returns:
            Dict containing the update response
        """
        url = f"{umr_config.get('URL', 'http://localhost:5138')}/api/application/v1/{application.applicationId}/status"
        
        # Prepare request payload - only status fields
        payload = {
            "status": application.status,
            "StatusChangedDate": application.statusChangedDate,
            "notes": application.notes
        }
        
        # Remove None values from payload
        payload = {k: v for k, v in payload.items() if v is not None}
        
        # Add correlation ID and user ID to headers
        headers = {
            'Content-Type': 'application/json',
            'X-Correlation-ID': self.correlation_id,
            'X-User-Id': str(application.userId)
        }
        
        logger.info(f"Updating application status at {url}")
        logger.debug(f"Request payload: {json.dumps(payload, default=str)}")
        
        # Make PUT request
        response = await client.put(
            url,
            json=payload,
            headers=headers
        )
        
        # Raise for error status codes
        response.raise_for_status()
        
        # Parse and return response
        if response.status_code == 204:
            logger.info(f"Application status updated successfully for application ID: {application.applicationId}")
        
        return {
            "status": response.status_code,
            "correlation_id": self.correlation_id,
            "applicationId": application.applicationId
        }
