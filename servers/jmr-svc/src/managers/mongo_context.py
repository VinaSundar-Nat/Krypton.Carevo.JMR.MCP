from utility import logprovider
from pymongo import AsyncMongoClient
from pymongo.errors import ConnectionFailure, ServerSelectionTimeoutError
from config import env_configs, env
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from mcp.server.fastmcp import FastMCP
from typing import Optional, List, Type
from urllib.parse import quote_plus
from models.context.dbcontext import DbContext, initialize_beanie
from models.domain.jobs.job import Job

logger = logprovider.get_logger()


def build_mongo_connection_string(
    uri: str,
    username: str,
    password: str,
    db_name: str,
    **kwargs
) -> str:
    """
    Construct a MongoDB connection string with proper URL encoding.
    
    Args:
        uri: MongoDB server URI (host:port)
        username: MongoDB username
        password: MongoDB password
        db_name: Database name
        **kwargs: Additional connection options (e.g., authSource, retryWrites)
        
    Returns:
        str: Fully formatted MongoDB connection string
    """
    # URL-encode username and password to handle special characters
    encoded_username = quote_plus(username)
    encoded_password = quote_plus(password)
    
    # Build base connection string
    connection_string = f"mongodb://{encoded_username}:{encoded_password}@{uri}/{db_name}"
    
    # Add optional parameters
    if kwargs:
        params = "&".join([f"{key}={value}" for key, value in kwargs.items()])
        connection_string += f"?{params}"
    
    return connection_string


@asynccontextmanager
async def app_lifespan(server: FastMCP) -> AsyncIterator[DbContext]:
    """Manage application lifecycle with MongoDB connection."""
    # Initialize on startup
    config = env_configs.get(env, {})
    mongo_uri = config.get('MONGO_URI')
    mongo_username = config.get('MONGO_USERNAME')
    mongo_password = config.get('MONGO_PASSWORD')
    mongo_db = config.get('MONGO_DB')
    
    # Build connection string
    connection_string = build_mongo_connection_string(
        uri=mongo_uri,
        username=mongo_username,
        password=mongo_password,
        db_name=mongo_db,
        authSource='admin',
        retryWrites='false'
    )
    
    client: Optional[AsyncMongoClient] = None
    
    try:
        # Initialize MongoDB client
        client = AsyncMongoClient(
            connection_string,
            serverSelectionTimeoutMS=5000,
            connectTimeoutMS=10000
        )

        await initialize_beanie(
            client=client,
            db_name=mongo_db,
            document_models=[Job]
        )
        
        # Test connection
        client.admin.command('ping')
        logger.info(f"MongoDB client connected successfully to database: {mongo_db}")
        
        # Yield database context
        yield DbContext(client=client, db_name=mongo_db)
        
    except ConnectionFailure as e:
        logger.error(f"MongoDB connection failed: {str(e)}")
        raise
    except ServerSelectionTimeoutError as e:
        logger.error(f"MongoDB server selection timeout: {str(e)}")
        raise
    except Exception as e:
        logger.error(f"Unexpected error during MongoDB initialization: {str(e)}")
        raise
    finally:
        if client is not None:
            await client.close()
            logger.info("MongoDB client closed")






