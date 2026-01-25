# HTTPX AsyncContextManager Usage Guide

## Overview

The HTTPX context manager implementation provides connection pooling and resource management for optimal HTTP client performance in the JMR MCP system.

## Key Features

### 1. Connection Pooling
- **max_connections**: 100 concurrent connections
- **max_keepalive_connections**: 20 idle connections kept alive
- **keepalive_expiry**: 5 seconds before idle connections are closed

### 2. Performance Optimizations
- **HTTP/2 Support**: Enabled by default for multiplexing
- **Connection Reuse**: Reduces overhead of creating new connections
- **Timeout Configuration**: 30s total timeout, 10s connect timeout

### 3. Resource Management
- Automatic cleanup in finally block
- Proper connection pool shutdown
- Logging for monitoring and debugging

## Usage Examples

### Basic Usage (Library Level)

```python
from models.context.httpxcontext import http_lifespan

async def make_api_request():
    async with http_lifespan() as ctx:
        response = await ctx.http_client.get("https://api.example.com/data")
        return response.json()
```

### Custom Configuration

```python
from models.context.httpxcontext import http_lifespan

async def make_request_custom():
    async with http_lifespan(
        timeout=60.0,
        max_connections=200,
        max_keepalive_connections=50,
        http2=True,
        verify=True
    ) as ctx:
        response = await ctx.http_client.post(
            "https://api.example.com/submit",
            json={"key": "value"}
        )
        return response.json()
```

### Service Level (FastMCP Integration)

```python
from managers.http_context import http_app_lifespan
from mcp.server.fastmcp import FastMCP

# Create MCP server with HTTP lifespan
mcp_server = FastMCP(
    name="my-service",
    lifespan=http_app_lifespan
)

@mcp_server.tool()
async def fetch_external_data(ctx) -> str:
    """Fetch data from external API using pooled HTTP client."""
    http_ctx = ctx.request_context.lifespan_context
    
    response = await http_ctx.http_client.get(
        "https://api.example.com/data"
    )
    return response.text
```

### Multiple Concurrent Requests

```python
import asyncio
from models.context.httpxcontext import http_lifespan

async def fetch_multiple_urls():
    urls = [
        "https://api.example.com/endpoint1",
        "https://api.example.com/endpoint2",
        "https://api.example.com/endpoint3",
    ]
    
    async with http_lifespan() as ctx:
        # All requests share the same connection pool
        tasks = [
            ctx.http_client.get(url) for url in urls
        ]
        responses = await asyncio.gather(*tasks)
        return [r.json() for r in responses]
```

## Integration with Main Application

Update your main.py to include HTTP lifespan alongside MongoDB:

```python
import contextlib
from starlette.applications import Starlette
from managers.mongo_context import app_lifespan as mongo_lifespan
from managers.http_context import http_app_lifespan

@contextlib.asynccontextmanager
async def combined_lifespan(app: Starlette):
    async with contextlib.AsyncExitStack() as stack:
        # Initialize both MongoDB and HTTP clients
        db_ctx = await stack.enter_async_context(mongo_lifespan(mcp_server))
        http_ctx = await stack.enter_async_context(http_app_lifespan(mcp_server))
        
        # Store in app state for access across the application
        app.state.db = db_ctx
        app.state.http = http_ctx
        
        yield
```

## Best Practices

### 1. Reuse Clients
Always use the context manager to ensure proper connection pooling:
```python
# ✅ Good - reuses connections
async with http_lifespan() as ctx:
    for i in range(100):
        await ctx.http_client.get(f"https://api.example.com/item/{i}")

# ❌ Bad - creates new client each time
for i in range(100):
    async with httpx.AsyncClient() as client:
        await client.get(f"https://api.example.com/item/{i}")
```

### 2. Error Handling
```python
from httpx import HTTPError, TimeoutException

async with http_lifespan() as ctx:
    try:
        response = await ctx.http_client.get("https://api.example.com/data")
        response.raise_for_status()
        return response.json()
    except TimeoutException:
        logger.error("Request timed out")
        raise
    except HTTPError as e:
        logger.error(f"HTTP error occurred: {e}")
        raise
```

### 3. Monitoring
The context manager logs key events:
- Client initialization with configuration
- Connection pool cleanup
- Errors during setup or teardown

Check logs for:
```
INFO: HTTPX AsyncClient initialized - max_connections: 100, max_keepalive: 20, http2: enabled
INFO: HTTPX AsyncClient closed and connection pool cleaned up
```

## Performance Benefits

### Connection Pooling Impact
- **Without pooling**: ~100-200ms overhead per request (connection setup)
- **With pooling**: ~5-10ms overhead per request (reuse existing connection)

### HTTP/2 Multiplexing
- Multiple concurrent requests over single TCP connection
- Reduced latency for parallel requests
- Lower resource usage on both client and server

### Keepalive Connections
- Eliminates TCP handshake for subsequent requests
- Reduces average request latency by 30-50%
- Optimal for high-frequency API calls

## Configuration Guidelines

### Low Traffic (< 10 req/s)
```python
max_connections=20
max_keepalive_connections=5
keepalive_expiry=5.0
```

### Medium Traffic (10-100 req/s)
```python
max_connections=100  # Default
max_keepalive_connections=20  # Default
keepalive_expiry=5.0  # Default
```

### High Traffic (> 100 req/s)
```python
max_connections=200
max_keepalive_connections=50
keepalive_expiry=10.0
```

## Troubleshooting

### Connection Pool Exhausted
If you see connection timeout errors:
1. Increase `max_connections`
2. Review concurrent request patterns
3. Check for connection leaks (ensure proper cleanup)

### High Memory Usage
If memory usage is high:
1. Reduce `max_keepalive_connections`
2. Decrease `keepalive_expiry`
3. Monitor number of idle connections

### Slow Performance
If requests are slow:
1. Enable HTTP/2: `http2=True`
2. Increase `max_keepalive_connections`
3. Review timeout settings
4. Check network latency to target API
