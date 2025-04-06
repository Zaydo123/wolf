import os
import logging
import sys
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables
env_path = Path(__file__).parents[2] / '.env'
load_dotenv(dotenv_path=env_path)

logger = logging.getLogger(__name__)

# PostgreSQL connection string
# For Supabase, use the direct PostgreSQL connection
PG_CONNECTION_STRING = os.getenv(
    'DATABASE_URL',
    'postgresql://postgres:postgres@host.docker.internal:54322/postgres'  # Default for Supabase local dev
)

# Try to import asyncpg, provide helpful error if not available
try:
    import asyncpg
    HAS_ASYNCPG = True
except ImportError:
    logger.error("asyncpg module not found. Direct SQL operations will not work.")
    logger.error("Install asyncpg with: pip install asyncpg")
    HAS_ASYNCPG = False

async def execute_sql(query, params=None):
    """
    Execute a SQL query directly against the database.
    This bypasses Supabase's RLS policies.
    
    Args:
        query (str): SQL query to execute
        params (dict, optional): Parameters for the query
    
    Returns:
        The result of the query
    """
    if not HAS_ASYNCPG:
        raise ImportError("The asyncpg module is required for direct SQL operations. Install with: pip install asyncpg")
        
    try:
        conn = await asyncpg.connect(PG_CONNECTION_STRING)
        try:
            # Convert named parameters to positional parameters
            if params:
                # Replace :name with $1, $2, etc.
                param_names = []
                for name in params.keys():
                    param_names.append(name)
                    query = query.replace(f":{name}", f"${len(param_names)}")
                
                param_values = [params[name] for name in param_names]
                result = await conn.execute(query, *param_values)
            else:
                result = await conn.execute(query)
            return result
        finally:
            await conn.close()
    except Exception as e:
        logger.error(f"Database error in execute_sql: {e}")
        # Add additional connection info for debugging
        logger.error(f"Connection string: {PG_CONNECTION_STRING.replace('postgres:', '***:')}")
        raise

async def fetch_sql(query, params=None):
    """
    Execute a SQL query and fetch results directly from the database.
    
    Args:
        query (str): SQL query to execute
        params (dict, optional): Parameters for the query
    
    Returns:
        The fetched rows
    """
    if not HAS_ASYNCPG:
        raise ImportError("The asyncpg module is required for direct SQL operations. Install with: pip install asyncpg")
        
    try:
        conn = await asyncpg.connect(PG_CONNECTION_STRING)
        try:
            # Convert named parameters to positional parameters
            if params:
                # Replace :name with $1, $2, etc.
                param_names = []
                for name in params.keys():
                    param_names.append(name)
                    query = query.replace(f":{name}", f"${len(param_names)}")
                
                param_values = [params[name] for name in param_names]
                rows = await conn.fetch(query, *param_values)
            else:
                rows = await conn.fetch(query)
            return rows
        finally:
            await conn.close()
    except Exception as e:
        logger.error(f"Database error in fetch_sql: {e}")
        # Add additional connection info for debugging
        logger.error(f"Connection string: {PG_CONNECTION_STRING.replace('postgres:', '***:')}")
        raise

def test_db_connection():
    """
    Test the database connection and report status.
    """
    if not HAS_ASYNCPG:
        logger.error("Cannot test connection: asyncpg module not found")
        return False
        
    import asyncio
    
    async def _test():
        try:
            conn = await asyncpg.connect(PG_CONNECTION_STRING)
            await conn.execute("SELECT 1")
            await conn.close()
            logger.info("Database connection test successful")
            return True
        except Exception as e:
            logger.error(f"Database connection test failed: {e}")
            return False
    
    try:
        loop = asyncio.get_event_loop()
        return loop.run_until_complete(_test())
    except Exception as e:
        logger.error(f"Error testing database connection: {e}")
        return False 