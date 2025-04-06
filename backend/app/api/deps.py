from fastapi import Depends, HTTPException, status
from fastapi.security import OAuth2PasswordBearer
from jose import JWTError, jwt
from datetime import datetime
from typing import Optional
import os
from app.models.user import User
from app.db.supabase import get_supabase_client
import logging

logger = logging.getLogger(__name__)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login")

async def get_current_user(token: str = Depends(oauth2_scheme)) -> User:
    credentials_exception = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Could not validate credentials",
        headers={"WWW-Authenticate": "Bearer"},
    )
    
    try:
        # Initialize Supabase client WITHOUT service role to use the provided token
        supabase = get_supabase_client(use_service_role=False)
        
        # Get user data using the provided token
        auth_response = supabase.auth.get_user(token)
        
        if not auth_response or not auth_response.user:
            logger.warning(f"Token validation failed. Token: {token[:10]}...")
            raise credentials_exception
            
        auth_user = auth_response.user
        logger.info(f"Successfully validated token for user: {auth_user.id}")
            
        # Initialize service role client for database operations
        db_client = get_supabase_client(use_service_role=True)
        
        # Ensure user exists in the database table
        db_user = db_client.table('users').select('*').eq('id', auth_user.id).execute()
        
        if not db_user.data:
            logger.info(f"User {auth_user.id} not found in database, creating...")
            # Create user in database if they don't exist
            user_metadata = auth_user.user_metadata if auth_user.user_metadata else {}
            user_data = {
                'id': auth_user.id,
                'email': auth_user.email,
                'name': user_metadata.get('name', ''),
                'phone_number': auth_user.phone,
                'cash_balance': 10000.0,  # Default initial balance
                'created_at': datetime.utcnow().isoformat(),
                'updated_at': datetime.utcnow().isoformat()
            }
            insert_response = db_client.table('users').insert(user_data).execute()
            
            # Check for None data instead of error
            if not insert_response.data:
                logger.error(f"Failed to create user {auth_user.id} in database: No data returned")
                raise HTTPException(
                    status_code=500,
                    detail="Failed to create user record in database"
                )
                
            # Fetch the newly created user data
            db_user = db_client.table('users').select('*').eq('id', auth_user.id).execute()
            if not db_user.data:
                logger.error(f"Verification failed after creating user {auth_user.id}")
                raise HTTPException(
                    status_code=500,
                    detail="User creation verification failed"
                )
            logger.info(f"User {auth_user.id} created in database successfully.")
            
        # Create a User object from the database data
        user_db_data = db_user.data[0]
        user = User(
            id=user_db_data['id'],
            email=user_db_data['email'],
            phone_number=user_db_data.get('phone_number'),
            created_at=datetime.fromisoformat(user_db_data['created_at'].replace('Z', '+00:00')),
            updated_at=datetime.fromisoformat(user_db_data['updated_at'].replace('Z', '+00:00'))
        )
        
        return user
        
    except JWTError as e:
        logger.error(f"JWT Error validating token: {e}")
        raise credentials_exception
    except Exception as e:
        logger.error(f"Exception in get_current_user: {e}")
        # Reraise specific credentials exception if it's a known auth issue
        if isinstance(e, HTTPException) and e.status_code == 401:
            raise e
        # Otherwise, raise the general credentials exception
        raise credentials_exception 