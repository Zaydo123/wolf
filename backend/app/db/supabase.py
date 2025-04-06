from supabase import create_client
import logging
import os
import sys
import time
import httpx
import asyncio
from functools import wraps

# Import the central path setup module
from app.core.imports import APP_DIR, BACKEND_DIR

# Import configuration (with fallback to environment variables)
try:
    from app.core.config import SUPABASE_URL, SUPABASE_KEY, SUPABASE_SERVICE_KEY
except ImportError:
    SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
    SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")
    SUPABASE_SERVICE_KEY = os.environ.get("SUPABASE_SERVICE_KEY", "")

# Retry decorator for API calls
def retry_with_backoff(retries=3, backoff_in_seconds=1):
    def wrapper(func):
        @wraps(func)
        def wrapped(*args, **kwargs):
            attempt = 0
            while attempt < retries:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    attempt += 1
                    wait_time = backoff_in_seconds * (2 ** attempt)
                    if attempt == retries:
                        logging.error(f"All {retries} retries failed for {func.__name__}. Error: {str(e)}")
                        raise
                    logging.warning(f"Retry {attempt} for {func.__name__} after error: {str(e)}. Waiting {wait_time}s...")
                    time.sleep(wait_time)
        return wrapped
    return wrapper

# Retry decorator for async API calls
def async_retry_with_backoff(retries=3, backoff_in_seconds=1):
    def wrapper(func):
        @wraps(func)
        async def wrapped(*args, **kwargs):
            attempt = 0
            while attempt < retries:
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    attempt += 1
                    wait_time = backoff_in_seconds * (2 ** attempt)
                    if attempt == retries:
                        logging.error(f"All {retries} retries failed for {func.__name__}. Error: {str(e)}")
                        raise
                    logging.warning(f"Retry {attempt} for {func.__name__} after error: {str(e)}. Waiting {wait_time}s...")
                    await asyncio.sleep(wait_time)
        return wrapped
    return wrapper

logger = logging.getLogger(__name__)

# Mock response
class MockResponse:
    def __init__(self, mock_data=None):
        self.data = mock_data or []
        self.user = None
        self.session = None
        # Add a mock user for testing
        if not mock_data:
            self.user = MockUser()

# Mock user
class MockUser:
    def __init__(self):
        self.id = "mock-user-id"
        self.email = "mock@example.com"
        self.user_metadata = {"name": "Mock User", "phone_number": "+15555555555"}

# Mock admin
class MockAdmin:
    def __init__(self):
        logger.info("[MOCK] Admin initialized")
        
    def list_users(self):
        logger.info("[MOCK] Admin list_users called")
        users = [MockUser()]
        mock_resp = type('obj', (object,), {
            'users': users
        })
        return mock_resp

# Mock auth
class MockAuth:
    def __init__(self):
        self.admin = MockAdmin()
        self.headers = {}
        
    def sign_up(self, credentials):
        logger.info(f"[MOCK] Sign up: {credentials}")
        return MockResponse()
    
    def sign_in_with_password(self, credentials):
        logger.info(f"[MOCK] Sign in: {credentials}")
        return MockResponse()

# Create a mock SupabaseClient class for testing/fallback
class MockSupabaseClient:
    """A mock Supabase client that logs operations instead of performing them."""
    
    def __init__(self):
        logger.warning("Using MockSupabaseClient - no actual database operations will be performed")
        self.auth = MockAuth()
        self.headers = {}
        self.postgrest = type('obj', (object,), {'headers': {}})
    
    def table(self, table_name):
        logger.info(f"[MOCK] Accessing table: {table_name}")
        return self
    
    def select(self, *args):
        logger.info(f"[MOCK] Select operation: {args}")
        return self
    
    def insert(self, data):
        logger.info(f"[MOCK] Insert operation: {data}")
        return self
    
    def update(self, data):
        logger.info(f"[MOCK] Update operation: {data}")
        return self
    
    def delete(self):
        logger.info("[MOCK] Delete operation")
        return self
    
    def eq(self, column, value):
        logger.info(f"[MOCK] Filter by {column} = {value}")
        # For user queries, return a mock user with cash_balance if querying by ID
        if column == 'id' and value:
            mock_user = {
                'id': value,
                'email': 'mock@example.com',
                'name': 'Mock User',
                'phone_number': '+15555555555',
                'cash_balance': 10000.0,
                'created_at': '2023-01-01T00:00:00',
                'updated_at': '2023-01-01T00:00:00'
            }
            return MockQueryWithResult([mock_user])
        return self
    
    def order(self, column, desc=False):
        logger.info(f"[MOCK] Order by {column}, desc={desc}")
        return self
    
    def limit(self, n):
        logger.info(f"[MOCK] Limit {n}")
        return self
    
    def execute(self):
        logger.info("[MOCK] Execute query")
        return MockResponse()

    def upsert(self, data):
        logger.info(f"[MOCK] Upsert operation: {data}")
        return self

# Mock query with predefined result
class MockQueryWithResult:
    def __init__(self, result_data):
        self.result_data = result_data
    
    def execute(self):
        return MockResponse(self.result_data)
    
    def order(self, column, desc=False):
        return self
    
    def limit(self, n):
        return self

def get_supabase_client(use_service_role: bool = True):
    """
    Get a Supabase client instance.
    
    Parameters:
        use_service_role (bool): If True, use the service role key for admin access
    
    Returns:
        SupabaseClient: A configured Supabase client
    """
    try:
        # Get the appropriate key based on the role
        key = SUPABASE_SERVICE_KEY if use_service_role else SUPABASE_KEY
        
        # Create and return the client
        client = create_client(SUPABASE_URL, key)
        logger.info(f"Created Supabase client with {'service' if use_service_role else 'anon'} role")
        return client
    except Exception as e:
        logger.error(f"Error creating Supabase client: {e}")
        # Return mock client as fallback
        return MockSupabaseClient()

def create_mock_client():
    """Create a fully configured mock client"""
    mock_client = MockSupabaseClient()
    return mock_client 