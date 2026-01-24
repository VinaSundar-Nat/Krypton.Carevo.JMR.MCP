import os
import json
import boto3
from botocore.exceptions import ClientError

env = os.environ.get('ENV', 'local')
dev_password = ''
prod_password = ''

# Secrets Manager ARNs
DEV_SECRET_ARN = ''  # To be added later
PROD_SECRET_ARN = ''  # To be added later

def get_secret(secret_arn: str) -> dict:
    """
    Retrieve secret from AWS Secrets Manager.
    
    Args:
        secret_arn: The ARN of the secret to retrieve
        
    Returns:
        dict: The secret values as a dictionary
    """
    if not secret_arn:
        return {}
    
    session = boto3.session.Session()
    client = session.client(service_name='secretsmanager')
    
    try:
        get_secret_value_response = client.get_secret_value(SecretId=secret_arn)
        secret = get_secret_value_response['SecretString']
        return json.loads(secret)
    except ClientError as e:
        raise e

if env == 'development':
    secrets = get_secret(DEV_SECRET_ARN)
    dev_password = secrets.get('MONGO_PASSWORD', '') if secrets else ''
elif env == 'production':
    secrets = get_secret(PROD_SECRET_ARN)
    prod_password = secrets.get('MONGO_PASSWORD', '') if secrets else ''

env_configs = {
    'local': {
        'MONGO_URI': 'localhost:27017',
        'MONGO_USERNAME': 'admin',
        'MONGO_PASSWORD': '$ccat0.Nest',
        'MONGO_DB': 'jmr',
        'API_ENDPOINT': 'localhost',
        'MCP_TRANSPORT': 'streamable-http',
        'ORIGINS': ['*'],
        'HTTPX_SETTINGS': {
            'max_connections': 50,
            'max_keepalive_connections': 10,
            'keepalive_expiry': 5.0,
            'http2': False,
            'timeout': 30.0,
            'connect_timeout': 10.0,
            'follow_redirects': True,
            'verify': False
        },
        "UMR_SERVICE": {
            "URL": "http://localhost:5138" ,
            "MAX_RETRIES": 3,
            "RETRY_BACKOFF_FACTOR": 0.5,
            "STATUS_FORCELIST": [500, 502, 503, 504]
        }
    },
    'development': {
        'MONGO_URI': 'dev-db.example.com:27017',
        'MONGO_USERNAME': 'dev_user',
        'MONGO_PASSWORD': f'{dev_password}',
        'MONGO_DB': 'jmr',
        'API_ENDPOINT': 'http://localhost:8000',
        'MCP_TRANSPORT': 'streamable-http',
        'ORIGINS': ['http://localhost:3000', 'http://localhost:8000'],
        'HTTPX_SETTINGS': {
            'max_connections': 50,
            'max_keepalive_connections': 10,
            'keepalive_expiry': 5.0,
            'http2': False,
            'timeout': 30.0,
            'connect_timeout': 10.0,
            'follow_redirects': True,
            'verify': False
        }   
    },
    'production': {
        'MONGO_URI': 'prod-db.example.com:27017',
        'MONGO_USERNAME': 'prod_user',
        'MONGO_PASSWORD': f'{prod_password}',
        'MONGO_DB': 'jmr',
        'API_ENDPOINT': 'https://api.mcpdomain.com',
        'MCP_TRANSPORT': 'https',
        'ORIGINS': ['https://app.domain.com', 'https://api.mcpdomain.com'],
        'HTTPX_SETTINGS': {
            'max_connections': 100,
            'max_keepalive_connections': 20,
            'keepalive_expiry': 10.0,
            'http2': True,
            'timeout': 60.0,
            'connect_timeout': 15.0,
            'follow_redirects': True,
            'verify': True
        }  
    }
}

config = env_configs.get(env, {})
