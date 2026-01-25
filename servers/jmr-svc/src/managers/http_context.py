from utility import logprovider
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from mcp.server.fastmcp import FastMCP
from typing import Optional
from config import env_configs, env
import httpx
from models.context.httpxcontext import HttpxContext

logger = logprovider.get_logger()


@asynccontextmanager
async def http_app_lifespan(server: FastMCP) -> AsyncIterator[HttpxContext]:
    """
    Manage application HTTP client lifecycle with optimized connection pooling.
    
    This lifespan manager creates an HTTPX AsyncClient with environment-specific
    configuration for connection pooling and resource management.
    
    Args:
        server: FastMCP server instance
        
    Yields:
        HttpxContext: Context containing configured HTTP client
        
    Configuration loaded from env_configs based on current environment (local/development/production):
        - max_connections: Maximum number of concurrent connections
        - max_keepalive_connections: Number of idle connections to maintain
        - keepalive_expiry: Time before closing idle connections (default: 5.0s)
        - http2: HTTP/2 protocol support
        - timeout: Request timeout (default: 30s with 10s connect timeout)
    """
    # Initialize from configuration
    config = env_configs.get(env, {})
    httpx_settings = config.get('HTTPX_SETTINGS', {})
    
    # Extract settings with defaults
    max_connections = httpx_settings.get('max_connections', 100)
    max_keepalive_connections = httpx_settings.get('max_keepalive_connections', 20)
    keepalive_expiry = httpx_settings.get('keepalive_expiry', 5.0)
    http2_enabled = httpx_settings.get('http2', True)
    timeout_seconds = httpx_settings.get('timeout', 30.0)
    connect_timeout = httpx_settings.get('connect_timeout', 10.0)
    follow_redirects = httpx_settings.get('follow_redirects', True)
    verify_ssl = httpx_settings.get('verify', True)
    
    # Configure connection limits from config
    limits = httpx.Limits(
        max_connections=max_connections,
        max_keepalive_connections=max_keepalive_connections,
        keepalive_expiry=keepalive_expiry
    )
    
    # Configure timeout settings
    timeout_config = httpx.Timeout(timeout_seconds, connect=connect_timeout)
    
    client: Optional[httpx.AsyncClient] = None
    
    try:
        # Initialize HTTPX AsyncClient with connection pooling
        client = httpx.AsyncClient(
            limits=limits,
            timeout=timeout_config,
            http2=http2_enabled,
            follow_redirects=follow_redirects,
            verify=verify_ssl
        )
        
        logger.info(
            f"HTTPX AsyncClient initialized for '{env}' environment - "
            f"max_connections: {max_connections}, "
            f"max_keepalive: {max_keepalive_connections}, "
            f"http2: {http2_enabled}"
        )
        
        # Get UMR service configuration
        umr_config = config.get('UMR_SERVICE', {})
        
        # Yield HTTP context with client and service configs
        yield HttpxContext(http_client=client, umr_config=umr_config)
        
    except Exception as e:
        logger.error(f"Error initializing HTTPX client: {str(e)}")
        raise
    finally:
        # Ensure proper cleanup of connection pool
        if client is not None:
            await client.aclose()
            logger.info("HTTPX AsyncClient closed and connection pool cleaned up")





