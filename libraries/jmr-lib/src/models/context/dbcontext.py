
from dataclasses import dataclass
from pymongo import AsyncMongoClient
from typing import List, Type
from beanie import init_beanie, Document
from utility import logprovider

logger = logprovider.get_logger()


async def initialize_beanie(
    client: AsyncMongoClient,
    db_name: str,
    document_models: List[Type[Document]]
) -> None:
    """
    Initialize Beanie ODM with the provided document models.
    
    Args:
        client: AsyncMongoClient instance
        db_name: Name of the database to use
        document_models: List of Beanie Document model classes to initialize
        
    Example:
        await initialize_beanie(client, "my_db", [User, Product, Order])
    """
    try:
        await init_beanie(
            database=client[db_name],
            document_models=document_models
        )
        model_names = [model.__name__ for model in document_models]
        logger.info(f"Beanie initialized successfully with models: {', '.join(model_names)}")
    except Exception as e:
        logger.error(f"Failed to initialize Beanie: {str(e)}")
        raise


@dataclass
class DbContext:
    """Database context holding MongoDB client and database references."""
    def __init__(self, client: AsyncMongoClient, db_name: str):
        self.client = client
        self.db = client[db_name]