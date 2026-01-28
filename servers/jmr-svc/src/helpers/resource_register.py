from utility import logprovider
from mcp.server.fastmcp import FastMCP, Context
from mcp.types import Resource, ResourceTemplate, TextContent
from models.handler.base_resource_handler import BaseResourceHandler
from typing import List, Any, Dict, Optional
import re

class ResourceRegister:
    """Resource helper to attach resources to a server."""
    
    def __init__(self, server: FastMCP):
        self.server = server
        self.logger = logprovider.get_logger()
        self.resource_handlers: Dict[str, BaseResourceHandler] = {}
        self.direct_resources_registry: Dict[str, str] = {}  # Maps direct resource URI to handler name
        self.template_resources_registry: Dict[str, str] = {}  # Maps template URI to handler name
        self.uri_patterns: Dict[str, tuple] = {}  # Maps regex patterns to (template_uri, handler)
    
    def register_handler(self, handler_name: str, handler: BaseResourceHandler):
        """Register a resource handler with the manager."""
        self.resource_handlers[handler_name] = handler
        
        # Register direct resources (static URIs)
        if hasattr(handler, 'direct_resources'):
            for resource in handler.direct_resources:
                uri_str = str(resource.uri)
                self.direct_resources_registry[uri_str] = handler_name
                self._register_direct_resource(resource, handler)
        
        # Register resource templates (dynamic URIs with parameters)
        if hasattr(handler, 'resource_templates'):
            for resource in handler.resource_templates:
                uri_str = str(resource.uriTemplate)
                self.template_resources_registry[uri_str] = handler_name
                self._register_resource_template(resource, handler)
        
        total_resources = len(getattr(handler, 'direct_resources', [])) + len(getattr(handler, 'resource_templates', []))
        self.logger.info(f"Registered handler '{handler_name}' with {total_resources} resources ({len(getattr(handler, 'direct_resources', []))} direct, {len(getattr(handler, 'resource_templates', []))} templates)")
    
    def _register_direct_resource(self, resource: Resource, handler: BaseResourceHandler):
        """Register a direct resource (static URI) with the FastMCP server."""
        uri_str = str(resource.uri)
        description = resource.description or ""
        name = resource.name or uri_str
        
        # Static URI without parameters
        async def resource_wrapper() -> str:
            return await handler.read_resource(uri_str)
        
        # Set function name to the resource name
        resource_wrapper.__name__ = name
        
        resource_func = self.server.resource(uri_str, name=name, description=description)(resource_wrapper)
        
        # Store reference to avoid GC
        attr_name = uri_str.replace("://", "_").replace("/", "_")
        setattr(handler, f"_direct_{attr_name}_wrapper", resource_func)
    
    def _register_resource_template(self, resource: ResourceTemplate, handler: BaseResourceHandler):
        """Register a resource template (dynamic URI with parameters) with the FastMCP server."""
        import inspect
        
        # Convert AnyUrl to string
        uri_str = str(resource.uriTemplate)
        description = resource.description or ""
        name = resource.name or uri_str
        
        # Extract parameter names from URI template
        param_names = re.findall(r'\{(\w+)\}', uri_str)
        
        # Create a regex pattern to match URIs against this template
        pattern = re.escape(uri_str)
        for param_name in param_names:
            # Replace escaped braces with capture group
            pattern = pattern.replace(re.escape(f"{{{param_name}}}"), f"(?P<{param_name}>[^/]+)")
        pattern = f"^{pattern}$"
        
        # Store the pattern for URI matching
        self.uri_patterns[pattern] = (uri_str, handler)
        
        # Create wrapper with dynamic signature for parameterized resources
        async def resource_wrapper(**kwargs) -> str:
            actual_uri = uri_str
            for param_name, param_value in kwargs.items():
                actual_uri = actual_uri.replace(f"{{{param_name}}}", param_value)
            return await handler.read_resource(actual_uri)
        
        # Set function name to the resource name
        resource_wrapper.__name__ = name
        
        # Set the correct signature
        params = [
            inspect.Parameter(name_param, inspect.Parameter.POSITIONAL_OR_KEYWORD, annotation=str)
            for name_param in param_names
        ]
        resource_wrapper.__signature__ = inspect.Signature(params, return_annotation=str)
        
        # Set annotations for Pydantic validation
        resource_wrapper.__annotations__ = {name_param: str for name_param in param_names}
        resource_wrapper.__annotations__['return'] = str
        
        resource_func = self.server.resource(uri_str, name=name, description=description)(resource_wrapper)
        
        # Store reference to avoid GC
        attr_name = uri_str.replace("://", "_").replace("/", "_").replace("{", "").replace("}", "")
        setattr(handler, f"_template_{attr_name}_wrapper", resource_func)
   
    def unregister_handler(self, handler_name: str):
        """Unregister a resource handler and all its resources."""
        if handler_name not in self.resource_handlers:
            self.logger.warning(f"Handler '{handler_name}' not found")
            return
        
        handler = self.resource_handlers[handler_name]
        
        # Remove direct resources from registry
        direct_resources_to_remove = [uri for uri, h_name in self.direct_resources_registry.items() if h_name == handler_name]
        for resource_uri in direct_resources_to_remove:
            del self.direct_resources_registry[resource_uri]
        
        # Remove template resources from registry
        template_resources_to_remove = [uri for uri, h_name in self.template_resources_registry.items() if h_name == handler_name]
        for resource_uri in template_resources_to_remove:
            del self.template_resources_registry[resource_uri]
        
        # Remove handler
        del self.resource_handlers[handler_name]
        
        total_removed = len(direct_resources_to_remove) + len(template_resources_to_remove)
        self.logger.info(f"Unregistered handler '{handler_name}' and {total_removed} resources ({len(direct_resources_to_remove)} direct, {len(template_resources_to_remove)} templates)")
    
    def get_handler(self, handler_name: str) -> Optional[BaseResourceHandler]:
        """Get a registered resource handler by name."""
        return self.resource_handlers.get(handler_name)
    
    def get_handler_for_resource(self, uri: str) -> Optional[BaseResourceHandler]:
        """Get the handler responsible for a specific resource URI."""
        # First check direct resources for exact match
        handler_name = self.direct_resources_registry.get(uri)
        if handler_name:
            return self.resource_handlers.get(handler_name)
        
        # Then check template resources by pattern matching
        for pattern, (template_uri, handler) in self.uri_patterns.items():
            if re.match(pattern, uri):
                return handler
        
        return None
        """List all registered handler names."""
        return list(self.resource_handlers.keys())
    
    def list_resources(self) -> Dict[str, Dict[str, str]]:
        """List all registered resources and their associated handlers."""
        return {
            "direct": self.direct_resources_registry.copy(),
            "templates": self.template_resources_registry.copy()
        }
    
    async def read_resource(self, uri: str, ctx: Context) -> str:
        """Read a resource by URI with given context."""
        handler = self.get_handler_for_resource(uri)
        if not handler:
            raise ValueError(f"No handler found for resource: {uri}")
        
        return await handler.read_resource(uri)

