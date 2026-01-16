"""Schema definitions for MCP tools."""
import json
from pathlib import Path
from typing import Dict, Any


def load_schema(schema_name: str) -> Dict[str, Any]:
    """Load a JSON schema from the schemas directory.
    
    Args:
        schema_name: Name of the schema file (without .json extension)
        
    Returns:
        Dict containing the schema definition
    """
    schema_path = Path(__file__).parent / f"{schema_name}.json"
    with open(schema_path, 'r') as f:
        return json.load(f)


# Pre-load commonly used schemas
JOB_FILTER_SCHEMA = load_schema("job_filter_schema")
JOB_SCHEMA = load_schema("job_schema")
JOB_VIEW_SCHEMA = load_schema("job_view_schema")
