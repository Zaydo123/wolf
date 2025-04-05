from supabase import create_client
import logging
import os
import sys

# Import the central path setup module
from app.core.imports import APP_DIR, BACKEND_DIR

# Import configuration (with fallback to environment variables)
try:
    from app.core.config import SUPABASE_URL, SUPABASE_KEY
except ImportError:
    SUPABASE_URL = os.environ.get("SUPABASE_URL", "")
    SUPABASE_KEY = os.environ.get("SUPABASE_KEY", "")

logger = logging.getLogger(__name__)

# Create a mock SupabaseClient class for testing/fallback
class MockSupabaseClient:
    """A mock Supabase client that logs operations instead of performing them."""
    
    def __init__(self):
        logger.warning("Using MockSupabaseClient - no actual database operations will be performed")
    
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

# Mock response
class MockResponse:
    def __init__(self):
        self.data = []
        self.user = None
        self.session = None

# Mock auth
class MockAuth:
    def __init__(self):
        pass
        
    def sign_up(self, credentials):
        logger.info(f"[MOCK] Sign up: {credentials}")
        return MockResponse()
    
    def sign_in_with_password(self, credentials):
        logger.info(f"[MOCK] Sign in: {credentials}")
        return MockResponse()

def get_supabase_client():
    """
    Create and return a Supabase client or a mock client if not available.
    """
    try:
        if not SUPABASE_URL or not SUPABASE_KEY:
            logger.warning("Supabase URL or key is missing, using mock client")
            mock_client = MockSupabaseClient()
            mock_client.auth = MockAuth()
            return mock_client
        
        client = create_client(SUPABASE_URL, SUPABASE_KEY)
        return client
    except Exception as e:
        logger.error(f"Error creating Supabase client: {e}")
        logger.warning("Falling back to mock Supabase client")
        mock_client = MockSupabaseClient()
        mock_client.auth = MockAuth()
        return mock_client 