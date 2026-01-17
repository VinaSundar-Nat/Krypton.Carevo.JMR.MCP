from mcp.types import Resource, TextContent
from abc import ABC, abstractmethod
from typing import Dict, List, Any


class BaseResourceHandler(ABC):
    """Base class for all resource handlers.
    
    Resources provide read-only access to data that the LLM can reference.
    Unlike tools, resources don't perform actions but expose structured data.
    """

    @property
    @abstractmethod
    def resources(self) -> List[Resource]:
        """Return the Resource definitions for this handler"""
        pass
   
    @abstractmethod
    async def read_resource(self, uri: str) -> str:
        """Read resource content by URI and return as string"""
        pass
