from mcp.types import Tool, TextContent
from abc import ABC, abstractmethod
from typing import Dict, List, Any

class BaseToolHandler(ABC):
    """Base class that all tool handlers"""

    @property
    @abstractmethod
    def tools(self) -> List[Tool]:
        """Return the Tool definition for this handler"""
        pass
   
    @abstractmethod
    async def execute(self, arguments: Dict[str, Any]) -> List[TextContent]:
        """Execute the tool with given arguments"""
        pass
    
    @property
    def name(self) -> str:
        """Get the tool name from the definition"""
        return self.tool_definition.name