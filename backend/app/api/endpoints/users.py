from fastapi import APIRouter, HTTPException, Depends, Body
import logging
from typing import Optional
import datetime
import os
import sys

# Import the central path setup module
from app.core.imports import APP_DIR, BACKEND_DIR

# Import services
from app.db.supabase import get_supabase_client

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/users", tags=["users"])

@router.post("/register")
async def register_user(
    email: str,
    password: str,
    name: str,
    phone_number: str = None,
    initial_balance: float = 10000.0  # Default initial balance for paper trading
):
    """
    Register a new user.
    
    Parameters:
        email: User's email
        password: User's password
        name: User's name
        phone_number: User's phone number (optional)
        initial_balance: Initial cash balance for paper trading
    """
    try:
        supabase = get_supabase_client()
        
        # Sign up the user with Supabase Auth
        auth_response = supabase.auth.sign_up({
            "email": email,
            "password": password
        })
        
        if not auth_response.user:
            raise HTTPException(status_code=400, detail="Failed to register user")
        
        user_id = auth_response.user.id
        
        # Create the user profile with initial balance
        user_data = {
            'id': user_id,
            'email': email,
            'name': name,
            'phone_number': phone_number,
            'cash_balance': initial_balance,
            'created_at': datetime.datetime.now().isoformat(),
            'updated_at': datetime.datetime.now().isoformat()
        }
        
        supabase.table('users').insert(user_data).execute()
        
        return {
            "status": "success",
            "user_id": user_id,
            "message": "User registered successfully"
        }
    except Exception as e:
        logger.error(f"Error registering user: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/login")
async def login_user(
    email: str,
    password: str
):
    """
    Login a user.
    
    Parameters:
        email: User's email
        password: User's password
    """
    try:
        supabase = get_supabase_client()
        
        # Sign in the user with Supabase Auth
        auth_response = supabase.auth.sign_in_with_password({
            "email": email,
            "password": password
        })
        
        if not auth_response.user:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        
        return {
            "status": "success",
            "user_id": auth_response.user.id,
            "access_token": auth_response.session.access_token,
            "refresh_token": auth_response.session.refresh_token
        }
    except Exception as e:
        logger.error(f"Error logging in user: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{user_id}")
async def get_user(user_id: str):
    """
    Get user profile information.
    
    Parameters:
        user_id: The user's ID
    """
    try:
        supabase = get_supabase_client()
        
        # Get the user profile
        user = supabase.table('users').select('*').eq('id', user_id).execute()
        
        if not user.data:
            raise HTTPException(status_code=404, detail="User not found")
        
        # Don't return sensitive information
        user_data = user.data[0]
        user_data.pop('password_hash', None)
        
        return user_data
    except Exception as e:
        logger.error(f"Error getting user: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.put("/{user_id}")
async def update_user(
    user_id: str,
    name: Optional[str] = None,
    phone_number: Optional[str] = None,
    call_preferences: Optional[dict] = None
):
    """
    Update user profile information.
    
    Parameters:
        user_id: The user's ID
        name: User's name (optional)
        phone_number: User's phone number (optional)
        call_preferences: User's call preferences (optional)
    """
    try:
        supabase = get_supabase_client()
        
        # Build the update data
        update_data = {}
        if name:
            update_data['name'] = name
        if phone_number:
            update_data['phone_number'] = phone_number
        if call_preferences:
            update_data['call_preferences'] = call_preferences
        
        if not update_data:
            return {"status": "success", "message": "No updates provided"}
        
        update_data['updated_at'] = datetime.datetime.now().isoformat()
        
        # Update the user profile
        result = supabase.table('users').update(update_data).eq('id', user_id).execute()
        
        if not result.data:
            raise HTTPException(status_code=404, detail="User not found")
        
        return {
            "status": "success",
            "message": "User updated successfully",
            "updated_fields": list(update_data.keys())
        }
    except Exception as e:
        logger.error(f"Error updating user: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/{user_id}/watchlist")
async def get_watchlist(user_id: str):
    """
    Get a user's watchlist.
    
    Parameters:
        user_id: The user's ID
    """
    try:
        supabase = get_supabase_client()
        
        # Get the user's watchlist
        watchlist = supabase.table('watchlists').select('*').eq('user_id', user_id).execute()
        
        return {"watchlist": watchlist.data}
    except Exception as e:
        logger.error(f"Error getting watchlist: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/{user_id}/watchlist")
async def add_to_watchlist(
    user_id: str,
    ticker: str
):
    """
    Add a stock to a user's watchlist.
    
    Parameters:
        user_id: The user's ID
        ticker: Stock ticker symbol
    """
    try:
        supabase = get_supabase_client()
        
        # Check if the stock is already in the watchlist
        existing = supabase.table('watchlists').select('*').eq('user_id', user_id).eq('ticker', ticker).execute()
        
        if existing.data:
            return {"status": "success", "message": f"{ticker} is already in your watchlist"}
        
        # Add the stock to the watchlist
        watchlist_item = {
            'user_id': user_id,
            'ticker': ticker,
            'added_at': datetime.datetime.now().isoformat()
        }
        
        supabase.table('watchlists').insert(watchlist_item).execute()
        
        return {
            "status": "success",
            "message": f"{ticker} added to your watchlist"
        }
    except Exception as e:
        logger.error(f"Error adding to watchlist: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.delete("/{user_id}/watchlist/{ticker}")
async def remove_from_watchlist(
    user_id: str,
    ticker: str
):
    """
    Remove a stock from a user's watchlist.
    
    Parameters:
        user_id: The user's ID
        ticker: Stock ticker symbol
    """
    try:
        supabase = get_supabase_client()
        
        # Remove the stock from the watchlist
        result = supabase.table('watchlists').delete().eq('user_id', user_id).eq('ticker', ticker).execute()
        
        if not result.data:
            return {"status": "success", "message": f"{ticker} was not in your watchlist"}
        
        return {
            "status": "success",
            "message": f"{ticker} removed from your watchlist"
        }
    except Exception as e:
        logger.error(f"Error removing from watchlist: {e}")
        raise HTTPException(status_code=500, detail=str(e)) 