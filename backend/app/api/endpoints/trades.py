from fastapi import APIRouter, HTTPException, WebSocket, Depends, Body
import logging
from typing import Optional, List
import os
import sys

# Import the central path setup module
from app.core.imports import APP_DIR, BACKEND_DIR

# Import services
from app.services.trading_service import TradingService
from app.services.news_service import NewsService
from app.db.supabase import get_supabase_client

logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api/trades", tags=["trades"])

# Initialize services
trading_service = TradingService()
news_service = NewsService()

# Simple function to access the WebSocket manager
def get_manager():
    """Get the WebSocket manager from main.py on demand to avoid circular imports"""
    from app.main import manager
    return manager

@router.post("/execute")
async def execute_trade(
    user_id: str,
    action: str,
    ticker: str,
    quantity: int
):
    """
    Execute a paper trade on behalf of a user.
    
    Parameters:
        user_id: User ID
        action: "buy" or "sell"
        ticker: Stock ticker symbol
        quantity: Number of shares
    """
    try:
        # Validate the action
        if action.lower() not in ["buy", "sell"]:
            raise HTTPException(status_code=400, detail="Action must be 'buy' or 'sell'")
        
        # Execute the trade
        result = await trading_service.execute_paper_trade(user_id, action, ticker, quantity)
        
        if result.get("status") == "error":
            raise HTTPException(status_code=400, detail=result.get("message", "Unknown error"))
        
        # Broadcast the trade to WebSocket clients
        manager = get_manager()
        await manager.broadcast({
            "type": "trade_executed",
            "user_id": user_id,
            "trade": result["trade"]
        })
        
        return result
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error executing trade: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/history/{user_id}")
async def get_trade_history(user_id: str, limit: int = 20):
    """
    Get the trade history for a user.
    
    Parameters:
        user_id: User ID
        limit: Maximum number of trades to return
    """
    try:
        supabase = get_supabase_client()
        
        # Get the user's trade history
        trades = supabase.table('trades').select('*')\
            .eq('user_id', user_id)\
            .order('timestamp', desc=True)\
            .limit(limit)\
            .execute()
        
        return {"trades": trades.data}
    except Exception as e:
        logger.error(f"Error getting trade history: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/portfolio/{user_id}")
async def get_portfolio(user_id: str):
    """
    Get the current portfolio for a user.
    
    Parameters:
        user_id: User ID
    """
    try:
        # Use the trading service to get the user portfolio directly
        logger.info(f"Fetching portfolio via endpoint for user: {user_id}")
        portfolio = await trading_service.get_user_portfolio(user_id)
        logger.info(f"Successfully fetched portfolio via endpoint for user: {user_id}")
        return portfolio
    except ValueError as ve:
        # Handle specific ValueErrors from the service (like user not found)
        logger.error(f"Value error getting portfolio for {user_id}: {ve}")
        # If the error indicates user not found, return 404
        if "not found" in str(ve).lower():
            raise HTTPException(status_code=404, detail=str(ve))
        else:
            # Other ValueErrors (like DB connection issues) should be 500
            raise HTTPException(status_code=500, detail=f"Failed to retrieve portfolio: {str(ve)}")
    except Exception as e:
        # Catch any other unexpected errors
        logger.error(f"Unexpected error getting portfolio for {user_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"An unexpected server error occurred: {str(e)}")

@router.get("/market/summary")
async def get_market_summary():
    """
    Get a summary of the current market state.
    """
    try:
        # Use the trading service to get the market summary
        market_summary = await trading_service.get_market_summary()
        
        return market_summary
    except Exception as e:
        logger.error(f"Error getting market summary: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/market/news")
async def get_market_news(max_items: int = 10):
    """
    Get the latest financial news from RSS feeds.
    
    Parameters:
        max_items: Maximum number of news items to return
    """
    try:
        # Get news directly from the news service
        news_items = await news_service.get_financial_news(max_items=max_items)
        
        return {"news": news_items}
    except Exception as e:
        logger.error(f"Error getting market news: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/quote/{ticker}")
async def get_stock_quote(ticker: str):
    """
    Get a quote for a specific stock.
    
    Parameters:
        ticker: Stock ticker symbol
    """
    try:
        # Get the current price
        price = await trading_service.get_stock_price(ticker)
        
        if price is None:
            raise HTTPException(status_code=404, detail=f"Could not get price for {ticker}")
        
        return {
            "ticker": ticker,
            "price": price
        }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error getting stock quote: {e}")
        raise HTTPException(status_code=500, detail=str(e)) 