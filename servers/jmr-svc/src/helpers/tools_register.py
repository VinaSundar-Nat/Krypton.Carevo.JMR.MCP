from utility import logprovider
from mcp.server.fastmcp import FastMCP, Context
from mcp.types import Tool, TextContent
from models.handler.base_tool_handler import BaseToolHandler
from typing import List, Any, Dict, Optional, get_origin, get_args
import inspect
import types

class ToolRegister:
    """ Tool helper to attach tools to a server."""
    
    def __init__(self, server: FastMCP):
        self.server = server
        self.logger = logprovider.get_logger()
        self.tool_handlers: Dict[str, BaseToolHandler] = {}
        self.tools_registry: Dict[str, str] = {}
    
    def register_handler(self, handler_name: str, handler: BaseToolHandler):
        """Register a tool handler with the manager."""
        self.tool_handlers[handler_name] = handler
        
        # Register all tools from the handler
        for tool in handler.tools:
            self.tools_registry[tool.name] = handler_name
            self._register_tool_with_server(tool, handler)
        
        self.logger.info(f"Registered handler '{handler_name}' with {len(handler.tools)} tools")
    
    def _register_tool_with_server(self, tool: Tool, handler: BaseToolHandler):
        """Register a single tool with the FastMCP server using a dynamic signature."""

        props = tool.inputSchema.get("properties", {}) if tool.inputSchema else {}
        required = set(tool.inputSchema.get("required", [])) if tool.inputSchema else set()

        # Build parameter objects for inspect.Signature
        # ONLY include the tool's actual parameters, NOT ctx
        parameters = []
        
        for name, schema in props.items():
            # Convert JSON schema type to Python type annotation
            param_type = self._json_schema_to_python_type(schema)
            
            if name in required:
                parameters.append(
                    inspect.Parameter(name, inspect.Parameter.POSITIONAL_OR_KEYWORD, annotation=param_type)
                )
            else:
                parameters.append(
                    inspect.Parameter(name, inspect.Parameter.POSITIONAL_OR_KEYWORD, default=None, annotation=param_type)
                )

        sig = inspect.Signature(parameters)

        # Define a generic async function that receives ctx automatically from FastMCP
        # ctx is NOT in the signature - FastMCP injects it automatically
        async def tool_wrapper(ctx: Context, **kwargs):
            return await handler.execute({
                "tool_name": tool.name,
                "input_data": kwargs,
                "ctx": ctx  # Pass the context to the handler
            })

        # Replace the __signature__ attribute with ONLY the user-facing params
        # This is what clients see - ctx is hidden
        tool_wrapper.__signature__ = sig

        # Register with MCP
        tool_wrapper = self.server.tool(tool.name, description=tool.description)(tool_wrapper)

        # Store reference to avoid GC
        setattr(handler, f"_{tool.name}_wrapper", tool_wrapper)
    
    def _json_schema_to_python_type(self, schema: Dict[str, Any]) -> type:
        """Convert JSON schema type to Python type annotation."""
        json_type = schema.get("type", "string")
        
        if json_type == "object":
            return Dict[str, Any]
        elif json_type == "array":
            items_schema = schema.get("items", {})
            item_type = self._json_schema_to_python_type(items_schema) if items_schema else Any
            return List[item_type]
        elif json_type == "string":
            return str
        elif json_type == "integer":
            return int
        elif json_type == "number":
            return float
        elif json_type == "boolean":
            return bool
        else:
            return Any

    
    def unregister_handler(self, handler_name: str):
        """Unregister a tool handler and all its tools."""
        if handler_name not in self.tool_handlers:
            self.logger.warning(f"Handler '{handler_name}' not found")
            return
        
        handler = self.tool_handlers[handler_name]
        
        # Remove tools from registry
        tools_to_remove = [name for name, h_name in self.tools_registry.items() if h_name == handler_name]
        for tool_name in tools_to_remove:
            del self.tools_registry[tool_name]
        
        # Remove handler
        del self.tool_handlers[handler_name]
        
        self.logger.info(f"Unregistered handler '{handler_name}' and {len(tools_to_remove)} tools")
    
    def get_handler(self, handler_name: str) -> Optional[BaseToolHandler]:
        """Get a registered tool handler by name."""
        return self.tool_handlers.get(handler_name)
    
    def get_handler_for_tool(self, tool_name: str) -> Optional[BaseToolHandler]:
        """Get the handler responsible for a specific tool."""
        handler_name = self.tools_registry.get(tool_name)
        return self.tool_handlers.get(handler_name) if handler_name else None
    
    def list_handlers(self) -> List[str]:
        """List all registered handler names."""
        return list(self.tool_handlers.keys())
    
    def list_tools(self) -> Dict[str, str]:
        """List all registered tools and their associated handlers."""
        return self.tools_registry.copy()
    
    async def execute_tool(self, tool_name: str, arguments: Dict[str, Any], ctx: Context) -> List[TextContent]:
        """Execute a tool by name with given arguments."""
        handler = self.get_handler_for_tool(tool_name)
        if not handler:
            raise ValueError(f"No handler found for tool: {tool_name}")
        
        return await handler.execute({
            "tool_name": tool_name,
            "input_data": arguments,
            "ctx": ctx
        })