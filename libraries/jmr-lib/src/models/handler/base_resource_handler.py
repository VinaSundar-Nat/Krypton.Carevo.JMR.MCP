from mcp.types import Resource, ResourceTemplate, TextContent
from abc import ABC, abstractmethod
from typing import Dict, List, Any, Union


class BaseResourceHandler(ABC):
    """Base class for all resource handlers.
    
    Resources provide read-only access to data that the LLM can reference.
    Unlike tools, resources don't perform actions but expose structured data.
    
    According to MCP specification:
    - Direct Resources: Use 'uri' for static URIs (e.g., "jobs://today")
    - Resource Templates: Use 'uriTemplate' for dynamic URIs with parameters (e.g., "jobs://details/{job_id}")
    """

    @property
    def direct_resources(self) -> List[Resource]:
        """Return direct resources with static URIs.
        Override this method to provide direct resources.
        """
        return []
    
    @property
    def resource_templates(self) -> List[ResourceTemplate]:
        """Return resource templates with dynamic URI parameters.
        Override this method to provide resource templates.
        """
        return []

    @property
    def resources(self) -> List[Union[Resource, ResourceTemplate]]:
        """Return the combined list of all Resource definitions (direct + templates).
        Default implementation combines direct_resources and resource_templates.
        Override if custom behavior is needed.
        """
        return self.direct_resources + self.resource_templates
   
    @abstractmethod
    async def read_resource(self, uri: str) -> str:
        """Read resource content by URI and return as string"""
        pass
