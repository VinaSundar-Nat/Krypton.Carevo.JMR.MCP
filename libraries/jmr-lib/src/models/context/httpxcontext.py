from dataclasses import dataclass
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Optional, Dict, Any
import httpx
from mcp.server.fastmcp import FastMCP


@dataclass
class HttpxContext:
    """HTTP context holding HTTP client session and service configurations."""
    
    def __init__(self, http_client: httpx.AsyncClient | None = None, umr_config: Dict[str, Any] | None = None):
        self.http_client = http_client
        self.umr_config = umr_config or {}


