import os
import sys
import logging
import random
import string
import time
import asyncio
from pathlib import Path

# Add the parent directory to the path so we can import the app
sys.path.insert(0, str(Path(__file__).parents[2]))

from app.db.supabase import get_supabase_client
from app.db.db_utils import execute_sql, fetch_sql

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

async def test_registration_with_sql():
    """Test user registration with direct SQL"""
    logger.info("Testing registration with direct SQL")
    
    # Generate random test data
    email = generate_random_email()
    password = "Password123!"
    name = "Test User"
    phone_number = generate_random_phone()
    
    logger.info(f"Test data: {email=}, {name=}, {phone_number=}")
    
    # Step 1: Sign up with Auth using anon key
    logger.info("Step 1: Creating user with Auth")
    supabase = get_supabase_client(use_service_role=False)
    
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
        logger.info(f"Auth response user ID: {auth_response.user.id}")
        
        user_id = auth_response.user.id
    except Exception as auth_error:
        logger.error(f"Auth signup error: {auth_error}")
        return
    
    # Step 2: Insert user with direct SQL
    logger.info("Step 2: Inserting user with direct SQL")
    
    sql = """
    INSERT INTO users (id, email, name, phone_number, cash_balance, created_at, updated_at)
    VALUES (:id, :email, :name, :phone, :balance, NOW(), NOW())
    """
    
    params = {
        "id": user_id,
        "email": email,
        "name": name,
        "phone": phone_number,
        "balance": 10000.0
    }
    
    try:
        result = await execute_sql(sql, params)
        logger.info(f"SQL insert result: {result}")
    except Exception as db_error:
        logger.error(f"Database error: {db_error}")
        return
    
    # Step 3: Verify user exists
    logger.info("Step 3: Verifying user exists with direct SQL")
    
    check_sql = """
    SELECT * FROM users WHERE id = :id
    """
    
    try:
        rows = await fetch_sql(check_sql, {"id": user_id})
        if rows:
            logger.info(f"User found in database: {rows[0]}")
        else:
            logger.error("User not found in database")
    except Exception as query_error:
        logger.error(f"Query error: {query_error}")
    
    logger.info("Test completed successfully")

if __name__ == "__main__":
    asyncio.run(test_registration_with_sql()) 