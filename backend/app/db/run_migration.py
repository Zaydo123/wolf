#!/usr/bin/env python
import asyncio
import os
import sys
import logging
from pathlib import Path

# Add the parent directory to the path so we can import modules
parent_dir = Path(__file__).parent.parent.parent
sys.path.append(str(parent_dir))

# Import the database functions
from app.db.db_utils import execute_sql

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

async def run_migration(migration_file):
    """Run a specific migration file"""
    migration_path = Path(migration_file)
    
    if not migration_path.exists():
        logger.error(f"Migration file {migration_path} does not exist")
        return False
    
    try:
        # Read the SQL from the file
        with open(migration_path, 'r') as f:
            sql = f.read()
        
        # Execute the SQL
        logger.info(f"Running migration {migration_path.name}")
        await execute_sql(sql)
        logger.info(f"Migration {migration_path.name} completed successfully")
        return True
    except Exception as e:
        logger.error(f"Error running migration {migration_path.name}: {e}")
        return False

async def main():
    """Run all migrations or a specific migration file"""
    # Define the migration files to run
    migrations_dir = Path(__file__).parent / "migrations"
    migration_files = [
        migrations_dir / "20240406000002_fix_calls_direction.sql",
        migrations_dir / "20240406000003_fix_call_logs_rls.sql"
    ]
    
    success = True
    for migration_file in migration_files:
        migration_success = await run_migration(migration_file)
        if not migration_success:
            success = False
    
    if success:
        logger.info("All migrations completed successfully")
    else:
        logger.error("One or more migrations failed")
        sys.exit(1)

if __name__ == "__main__":
    asyncio.run(main())