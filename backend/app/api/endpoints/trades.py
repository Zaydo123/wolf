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
        logger.info(f"Starting trade execution for user {user_id}: {action} {quantity} {ticker}")
        
        # Validate the action
        if action.lower() not in ["buy", "sell"]:
            raise HTTPException(status_code=400, detail="Action must be 'buy' or 'sell'")
        
        # Execute the trade
        result = await trading_service.execute_paper_trade(user_id, action, ticker, quantity)
        
        if result.get("status") == "error":
            logger.error(f"Trade execution failed: {result.get('message')}")
            raise HTTPException(status_code=400, detail=result.get("message", "Unknown error"))
        
        logger.info(f"Trade successfully executed: {result}")
        
        # Verify the trade was recorded in the database
        try:
            supabase = get_supabase_client()
            recent_trade = supabase.table('trades').select('*')\
                .eq('user_id', user_id)\
                .order('timestamp', desc=True)\
                .limit(1)\
                .execute()
                
            if recent_trade.data:
                logger.info(f"Verified trade was recorded: {recent_trade.data[0]}")
            else:
                logger.warning(f"Trade execution reported success but no trade record found for user {user_id}")
        except Exception as verify_err:
            logger.error(f"Error verifying trade was recorded: {verify_err}")
        
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
        logger.info(f"Fetching trade history for user: {user_id}, limit: {limit}")
        supabase = get_supabase_client(use_service_role=True)  # Use service role to bypass RLS
        
        # Get the user's trade history
        trades_query = supabase.table('trades').select('*')\
            .eq('user_id', user_id)\
            .order('timestamp', desc=True)\
            .limit(limit)
            
        logger.info(f"Executing trade history query: {trades_query}")
        trades_result = trades_query.execute()
        
        # Log the result details
        logger.info(f"Trade history query returned {len(trades_result.data)} trades")
        if not trades_result.data:
            logger.warning(f"No trades found for user {user_id}")
            
            # Do a count of all trades in the system for debugging
            total_trades = supabase.table('trades').select('count', count='exact').execute()
            logger.info(f"Total trades in the system: {total_trades.count if hasattr(total_trades, 'count') else 'unknown'}")
            
            # Try a more general query to see if there are any trades at all - without group_by
            try:
                # Just get all trades for the user without grouping
                user_trades_count = supabase.table('trades').select('*', count='exact')\
                    .eq('user_id', user_id)\
                    .execute()
                logger.info(f"User {user_id} has {user_trades_count.count if hasattr(user_trades_count, 'count') else 0} trades")
            except Exception as e:
                logger.error(f"Error counting user trades: {e}")
        
        return {"trades": trades_result.data}
    except Exception as e:
        logger.error(f"Error getting trade history: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=str(e))

@router.get("/portfolio/{user_id}")
async def get_portfolio(user_id: str, fresh: bool = False):
    """
    Get the current portfolio for a user.
    
    Parameters:
        user_id: User ID
        fresh: If True, bypass any caching and get fresh price data
    """
    try:
        # Use the trading service to get the user portfolio directly
        logger.info(f"Fetching portfolio via endpoint for user: {user_id} (fresh={fresh})")
        portfolio = await trading_service.get_user_portfolio(user_id, fresh=fresh)
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
async def get_market_summary(fresh: bool = False):
    """
    Get a summary of the current market state.
    
    Parameters:
        fresh: If True, bypass any caching and get fresh data
    """
    try:
        # Use the trading service to get the market summary with fresh option
        market_summary = await trading_service.get_market_summary(fresh=fresh)
        
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

@router.post("/portfolio/{user_id}/update-prices")
async def update_portfolio_prices(user_id: str):
    """
    Update portfolio positions with current market prices and save to database.
    
    This endpoint is now just a wrapper around get_user_portfolio with fresh=True,
    maintained for backward compatibility.
    
    Parameters:
        user_id: User ID
    """
    try:
        logger.info(f"Updating portfolio prices for user: {user_id} (using fresh=True)")
        
        # Just get the portfolio with fresh data
        portfolio = await trading_service.get_user_portfolio(user_id, fresh=True)
        
        return {
            "update_result": {"status": "success", "message": "Portfolio updated with fresh prices"},
            "portfolio": portfolio
        }
    except ValueError as ve:
        logger.error(f"Value error updating portfolio prices for {user_id}: {ve}")
        if "not found" in str(ve).lower():
            raise HTTPException(status_code=404, detail=str(ve))
        else:
            raise HTTPException(status_code=500, detail=str(ve))
    except Exception as e:
        logger.error(f"Error updating portfolio prices: {e}")
        raise HTTPException(status_code=500, detail=str(e))

@router.post("/create_test_trade/{user_id}")
async def create_test_trade(user_id: str):
    """
    Create a test trade for debugging purposes.
    
    Parameters:
        user_id: User ID
    """
    logger.info(f"Creating test trade for user {user_id}")
    
    try:
        supabase = get_supabase_client()
        
        # Generate random test trade data
        import random
        from datetime import datetime
        
        tickers = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA"]
        actions = ["buy", "sell"]
        
        test_trade = {
            "user_id": user_id,
            "ticker": random.choice(tickers),
            "action": random.choice(actions),
            "quantity": random.randint(1, 10),
            "price": round(random.uniform(50, 500), 2),
            "timestamp": datetime.now().isoformat()
        }
        
        # Calculate total value
        test_trade["total_value"] = round(test_trade["quantity"] * test_trade["price"], 2)
        
        logger.info(f"Inserting test trade: {test_trade}")
        
        # Insert the test trade
        result = supabase.table('trades').insert(test_trade).execute()
        
        # Verify the trade exists
        verify = supabase.table('trades').select('*')\
            .eq('user_id', user_id)\
            .order('timestamp', desc=True)\
            .limit(1)\
            .execute()
            
        if verify.data:
            logger.info(f"Test trade successfully verified: {verify.data[0]}")
            return {"status": "success", "message": "Test trade created", "trade": verify.data[0]}
        else:
            logger.error("Test trade creation verification failed - no trade found after insert")
            return {"status": "error", "message": "Test trade insert succeeded but verification failed"}
            
    except Exception as e:
        logger.error(f"Error creating test trade: {e}", exc_info=True)
        return {"status": "error", "message": str(e)}

@router.post("/import_sample_trades/{user_id}")
async def import_sample_trades(user_id: str, count: int = 5):
    """
    Import sample historical trades for a user.
    This helps initialize the trade history for new users
    or restore trades for testing.
    
    Parameters:
        user_id: User ID
        count: Number of sample trades to create (default: 5)
    """
    logger.info(f"Importing {count} sample trades for user {user_id}")
    
    try:
        supabase = get_supabase_client()
        
        # First verify the user exists
        user_check = supabase.table('users').select('id').eq('id', user_id).execute()
        if not user_check.data:
            logger.error(f"User {user_id} not found")
            return {"status": "error", "message": "User not found"}
        
        # Generate realistic sample trades over past few days
        import random
        from datetime import datetime, timedelta
        import uuid
        
        # Real tickers with realistic prices
        stock_data = [
            {"ticker": "AAPL", "price_range": (180, 195)},
            {"ticker": "MSFT", "price_range": (405, 425)},
            {"ticker": "GOOGL", "price_range": (165, 180)},
            {"ticker": "AMZN", "price_range": (175, 190)},
            {"ticker": "NVDA", "price_range": (90, 105)},
            {"ticker": "META", "price_range": (460, 485)},
            {"ticker": "TSLA", "price_range": (185, 200)},
            {"ticker": "JPM", "price_range": (195, 205)},
            {"ticker": "V", "price_range": (265, 280)},
            {"ticker": "WMT", "price_range": (65, 70)}
        ]
        
        actions = ["buy", "sell"]
        current_time = datetime.now()
        
        sample_trades = []
        for i in range(count):
            # Select a random stock
            stock = random.choice(stock_data)
            
            # Generate trade data
            trade_time = current_time - timedelta(days=i, hours=random.randint(0, 8))
            price = round(random.uniform(stock["price_range"][0], stock["price_range"][1]), 2)
            quantity = random.randint(1, 10)
            action = random.choice(actions)
            
            trade = {
                "id": str(uuid.uuid4()),  # Generate a UUID for the trade
                "user_id": user_id,  # user_id is already a UUID string
                "ticker": stock["ticker"],
                "action": action,
                "quantity": quantity,
                "price": price,
                "total_value": round(quantity * price, 2),
                "timestamp": trade_time.isoformat()
            }
            
            sample_trades.append(trade)
            logger.info(f"Generated sample trade: {trade}")
        
        # Insert the sample trades
        result = supabase.table('trades').insert(sample_trades).execute()
        
        # Verify trades were added
        verify = supabase.table('trades').select('*', count='exact')\
            .eq('user_id', user_id)\
            .execute()
            
        return {
            "status": "success", 
            "message": f"Successfully imported {len(sample_trades)} sample trades", 
            "count": verify.count if hasattr(verify, 'count') else 0
        }
            
    except Exception as e:
        logger.error(f"Error importing sample trades: {e}", exc_info=True)
        return {"status": "error", "message": str(e)} 