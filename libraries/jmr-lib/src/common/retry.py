"""Retry decorator with exponential backoff for resilient HTTP calls."""
import asyncio
from functools import wraps
from typing import Callable, Any, Optional, Sequence
from utility import logprovider
import httpx

logger = logprovider.get_logger()


def with_retry(
    max_retries: int = 3,
    backoff_factor: float = 0.5,
    status_forcelist: Optional[Sequence[int]] = None,
    exceptions: tuple = (httpx.HTTPError, httpx.TimeoutException, httpx.ConnectError)
):
    """
    Decorator that implements retry logic with exponential backoff.
    
    Args:
        max_retries: Maximum number of retry attempts
        backoff_factor: Multiplier for exponential backoff (delay = backoff_factor * (2 ** attempt))
        status_forcelist: HTTP status codes that should trigger a retry
        exceptions: Tuple of exceptions that should trigger a retry
        
    Usage:
        @with_retry(max_retries=3, backoff_factor=0.5, status_forcelist=[500, 502, 503, 504])
        async def my_http_call():
            ...
    """
    if status_forcelist is None:
        status_forcelist = [500, 502, 503, 504]
    
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> Any:
            last_exception = None
            
            for attempt in range(max_retries + 1):
                try:
                    response = await func(*args, **kwargs)
                    
                    # Check if response has status_code attribute (httpx.Response)
                    if hasattr(response, 'status_code') and response.status_code in status_forcelist:
                        if attempt < max_retries:
                            delay = backoff_factor * (2 ** attempt)
                            logger.warning(
                                f"Attempt {attempt + 1}/{max_retries + 1} failed with status {response.status_code}. "
                                f"Retrying in {delay}s..."
                            )
                            await asyncio.sleep(delay)
                            continue
                        else:
                            logger.error(
                                f"Max retries ({max_retries}) reached for {func.__name__}. "
                                f"Last status: {response.status_code}"
                            )
                            return response
                    
                    # Success
                    if attempt > 0:
                        logger.info(f"{func.__name__} succeeded on attempt {attempt + 1}")
                    return response
                    
                except exceptions as e:
                    last_exception = e
                    
                    if attempt < max_retries:
                        delay = backoff_factor * (2 ** attempt)
                        logger.warning(
                            f"Attempt {attempt + 1}/{max_retries + 1} failed with {type(e).__name__}: {str(e)}. "
                            f"Retrying in {delay}s..."
                        )
                        await asyncio.sleep(delay)
                    else:
                        logger.error(
                            f"Max retries ({max_retries}) reached for {func.__name__}. "
                            f"Last exception: {type(e).__name__}: {str(e)}"
                        )
                        raise
            
            # This should not be reached, but just in case
            if last_exception:
                raise last_exception
                
        return wrapper
    return decorator
