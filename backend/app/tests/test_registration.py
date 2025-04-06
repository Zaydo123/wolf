import os
import sys
import logging
import uuid
import random
import string
import time
from pathlib import Path
import asyncio

# Add the parent directory to the path so we can import the app
sys.path.insert(0, str(Path(__file__).parents[2]))

from app.db.supabase import get_supabase_client
from app.core.config import SUPABASE_SERVICE_KEY

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger(__name__)

def generate_random_email():
    """Generate a random email for testing"""
    random_str = ''.join(random.choices(string.ascii_lowercase + string.digits, k=8))
    return f"test_{random_str}@example.com"

def generate_random_phone():
    """Generate a random phone number for testing"""
    return f"+1555{random.randint(1000000, 9999999)}"

async def test_registration_direct():
    """Test user registration directly with Supabase"""
    logger.info("Testing direct registration with Supabase")
    
    # Generate random test data
    email = generate_random_email()
    password = "Password123!"
    name = "Test User"
    phone_number = generate_random_phone()
    
    logger.info(f"Test data: {email=}, {name=}, {phone_number=}")
    
    # Get client with service role
    logger.info("Getting Supabase client with service role")
    supabase = get_supabase_client(use_service_role=True)
    
    # Step 1: Sign up with Auth
    logger.info("Step 1: Creating user with Auth")
    try:
        auth_response = supabase.auth.sign_up({
            "email": email,
            "password": password,
            "phone": phone_number,
            "user_metadata": {
                "name": name,
                "phone_number": phone_number
            }
        })
        logger.info(f"Auth response: {auth_response}")
        
        if not auth_response.user:
            logger.error("Auth response doesn't contain user")
            return
        
        user_id = auth_response.user.id
        logger.info(f"User created in Auth with ID: {user_id}")
    except Exception as auth_error:
        logger.error(f"Auth signup error: {auth_error}")
        return
    
    # Step 2: Create user profile in database
    logger.info("Step 2: Creating user profile in database")
    user_data = {
        'id': user_id,
        'email': email,
        'name': name,
        'phone_number': phone_number,
        'cash_balance': 10000.0,
        'created_at': time.strftime('%Y-%m-%dT%H:%M:%SZ'),
        'updated_at': time.strftime('%Y-%m-%dT%H:%M:%SZ')
    }
    
    try:
        result = supabase.table('users').insert(user_data).execute()
        logger.info(f"Insert result: {result}")
        
        if not result.data:
            logger.error("Insert result doesn't contain data")
            return
        
        logger.info(f"User profile created: {result.data}")
    except Exception as db_error:
        logger.error(f"Database error: {db_error}")
        return
    
    # Step 3: Verify user exists in both tables
    logger.info("Step 3: Verifying user exists")
    try:
        # Check in users table
        users_result = supabase.table('users').select('*').eq('email', email).execute()
        logger.info(f"Users query result: {users_result.data}")
        
        if not users_result.data:
            logger.error("User not found in users table")
        else:
            logger.info("User found in users table")
    except Exception as query_error:
        logger.error(f"Query error: {query_error}")
    
    logger.info("Test completed")

if __name__ == "__main__":
    asyncio.run(test_registration_direct()) 