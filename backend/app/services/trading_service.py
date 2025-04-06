import logging
import asyncio
import datetime
import httpx
import os
import time
from functools import lru_cache

# Try both import approaches
try:
    # Absolute imports (when running from backend/)
    from app.db.supabase import get_supabase_client
    from app.services.news_service import NewsService
except ImportError:
    # Relative imports (when running from app/)
    from ..db.supabase import get_supabase_client
    from ..services.news_service import NewsService

logger = logging.getLogger(__name__)

# Alpha Vantage settings
ALPHA_VANTAGE_API_KEY = os.getenv("ALPHA_VANTAGE_API_KEY")
if not ALPHA_VANTAGE_API_KEY:
    raise ValueError("ALPHA_VANTAGE_API_KEY environment variable is not set")
ALPHA_VANTAGE_BASE_URL = "https://www.alphavantage.co/query"

# Simple in-memory cache for stock and index data
CACHE = {}
CACHE_EXPIRY = {}  # Store expiry timestamps for cache entries
CACHE_DURATION = 60 * 30  # Cache data for 30 minutes (in seconds)

# Rate limiting settings
LAST_REQUEST_TIME = time.time()
MIN_REQUEST_INTERVAL = 1.0  # 1 second between requests (Alpha Vantage has better rate limits)

class TradingService:
    def __init__(self):
        self.supabase = get_supabase_client(use_service_role=True)
        self.session = httpx.AsyncClient(timeout=30.0)
        self.stock_cache = {}
        self.cache_timeout = 300  # 5 minutes
        self.news_service = NewsService()  # Initialize the news service
    
    async def _rate_limit_request(self):
        """
        Implement rate limiting to avoid hitting Alpha Vantage's rate limits.
        """
        global LAST_REQUEST_TIME
        
        current_time = time.time()
        time_since_last_request = current_time - LAST_REQUEST_TIME
        
        if time_since_last_request < MIN_REQUEST_INTERVAL:
            wait_time = MIN_REQUEST_INTERVAL - time_since_last_request
            logger.debug(f"Rate limiting: waiting {wait_time:.2f} seconds")
            await asyncio.sleep(wait_time)
        
        LAST_REQUEST_TIME = time.time()
    
    def _get_cached_data(self, key):
        """Get data from cache if it exists and hasn't expired"""
        if key in CACHE and key in CACHE_EXPIRY:
            if time.time() < CACHE_EXPIRY[key]:
                logger.info(f"Using cached data for {key}")
                return CACHE[key]
            else:
                # Clean up expired cache entry
                del CACHE[key]
                del CACHE_EXPIRY[key]
        return None
        
    def _cache_data(self, key, data):
        """Store data in cache with expiry time"""
        CACHE[key] = data
        CACHE_EXPIRY[key] = time.time() + CACHE_DURATION
        logger.info(f"Cached data for {key} (expires in {CACHE_DURATION/60} minutes)")
    
    async def get_stock_price(self, ticker):
        """
        Get the current price of a stock using Alpha Vantage.
        
        Parameters:
            ticker (str): The stock ticker symbol
            
        Returns:
            float: The current stock price or None if not found
        """
        # Check cache first
        cache_key = f"price_{ticker}"
        cached_price = self._get_cached_data(cache_key)
        if cached_price is not None:
            return cached_price
        
        await self._rate_limit_request()
        
        try:
            # Get global quote
            params = {
                "function": "GLOBAL_QUOTE",
                "symbol": ticker,
                "apikey": ALPHA_VANTAGE_API_KEY
            }
            
            response = await self.session.get(ALPHA_VANTAGE_BASE_URL, params=params)
            data = response.json()
            
            if "Global Quote" in data and data["Global Quote"]:
                price = float(data["Global Quote"]["05. price"])
                if price > 0:
                    logger.info(f"Got price for {ticker}: ${price}")
                    self._cache_data(cache_key, price)
                    return price
            
            logger.warning(f"No price data available for {ticker}")
            return None
                
        except Exception as e:
            logger.error(f"Error getting stock price for {ticker}: {e}")
            return None
    
    async def get_market_summary(self):
        """
        Get a summary of the current market state using Alpha Vantage.
        
        Returns:
            dict: Market summary data including major indices and news
        """
        # Check cache first for the entire market summary
        cache_key = "market_summary"
        cached_summary = self._get_cached_data(cache_key)
        if cached_summary is not None:
            return cached_summary
            
        try:
            # Define function to get index data
            async def get_index_data(symbol):
                # Check cache for this specific index
                index_cache_key = f"index_{symbol}"
                cached_index = self._get_cached_data(index_cache_key)
                if cached_index is not None:
                    return cached_index
                    
                await self._rate_limit_request()
                
                try:
                    # Get global quote for the index
                    params = {
                        "function": "GLOBAL_QUOTE",
                        "symbol": symbol,
                        "apikey": ALPHA_VANTAGE_API_KEY
                    }
                    
                    response = await self.session.get(ALPHA_VANTAGE_BASE_URL, params=params)
                    data = response.json()
                    
                    if "Global Quote" in data and data["Global Quote"]:
                        current = float(data["Global Quote"]["05. price"])
                        previous = float(data["Global Quote"]["08. previous close"])
                        change = float(data["Global Quote"]["09. change"])
                        change_percent = float(data["Global Quote"]["10. change percent"].rstrip("%"))
                        
                        result = {
                            'price': current,
                            'change': change,
                            'change_percent': change_percent
                        }
                        
                        self._cache_data(index_cache_key, result)
                        logger.info(f"Successfully fetched {symbol} data")
                        return result
                    
                    logger.warning(f"No data available for {symbol}")
                    return None
                    
                except Exception as e:
                    logger.error(f"Error fetching data for {symbol}: {str(e)}")
                    return None
            
            # Define index symbols
            index_symbols = {
                "S&P 500": "SPY",  # SPDR S&P 500 ETF
                "Dow Jones": "DIA",  # SPDR Dow Jones Industrial Average ETF
                "NASDAQ": "QQQ"   # Invesco QQQ Trust
            }
            
            # Get data for each index
            sp500 = await get_index_data(index_symbols["S&P 500"])
            dow = await get_index_data(index_symbols["Dow Jones"])
            nasdaq = await get_index_data(index_symbols["NASDAQ"])
            
            # Log success or failure for each index
            logger.info(f"Market data fetch results - S&P 500: {'Success' if sp500 else 'Failed'}, "
                      f"Dow: {'Success' if dow else 'Failed'}, "
                      f"Nasdaq: {'Success' if nasdaq else 'Failed'}")
            
            # Get real market news from feeds
            try:
                # Get real news items
                news_headlines = await self.news_service.get_market_news_summary(max_items=5)
                news = [{"headline": line.strip()} for line in news_headlines.split("\n") if line.strip()]
                
                # If no news is available, just leave it empty
                if not news:
                    news = [{"headline": "No market news available at this time"}]
            except Exception as news_error:
                logger.error(f"Error fetching market news: {news_error}")
                # Simple fallback with no fake news
                news = [{"headline": "Unable to retrieve market news at this time"}]
            
            # Helper function to safely format index data
            def format_index(index_data):
                if not index_data:
                    return "Unknown (N/A)"
                    
                price = index_data.get('price')
                change = index_data.get('change_percent')
                
                if isinstance(price, (int, float)) and isinstance(change, (int, float)):
                    return f"{price:.2f} ({change:.2f}%)"
                elif isinstance(change, (int, float)):
                    return f"Unknown ({change:.2f}%)"
                else:
                    return "Unknown (N/A)"
            
            # Create the market summary
            news_text = ""
            for item in news:
                headline = item.get('headline', '')
                summary_text = item.get('summary', '')
                if headline:
                    if summary_text:
                        news_text += f"{headline}: {summary_text}\n"
                    else:
                        news_text += f"{headline}\n"
            
            summary = {
                'sp500': format_index(sp500),
                'dow': format_index(dow),
                'nasdaq': format_index(nasdaq),
                'top_news': news_text.strip()
            }
            
            # Cache the entire summary
            self._cache_data(cache_key, summary)
            
            return summary
            
        except Exception as e:
            logger.error(f"Error getting market summary: {e}")
            return {
                'sp500': 'Unknown',
                'dow': 'Unknown',
                'nasdaq': 'Unknown',
                'top_news': 'No major news available at this time.'
            }
    
    async def execute_paper_trade(self, user_id, action, ticker, quantity):
        """
        Execute a paper trade for a user.
        
        Parameters:
            user_id (str): The user's ID
            action (str): 'buy' or 'sell'
            ticker (str): The stock ticker symbol
            quantity (int): The number of shares
            
        Returns:
            dict: The result of the trade execution
        """
        if not all([user_id, action, ticker, quantity]):
            return {"status": "error", "message": "Missing required trade parameters"}
        
        # Convert quantity to int if it's a string
        if isinstance(quantity, str):
            try:
                quantity = int(quantity)
            except ValueError:
                return {"status": "error", "message": "Invalid quantity"}
        
        # Get the current price
        price = await self.get_stock_price(ticker)
        if price is None:
            return {"status": "error", "message": f"Could not get price for {ticker}"}
        
        try:
            # Get user's current portfolio
            user_portfolio = self.supabase.table('portfolios').select('*').eq('user_id', user_id).execute()
            
            # Calculate the trade value
            trade_value = price * quantity
            
            # Check if the user has enough cash or shares
            if action.lower() == 'buy':
                # Get user's cash balance
                user_cash = self.supabase.table('users').select('cash_balance').eq('id', user_id).execute()
                
                if not user_cash.data:
                    return {"status": "error", "message": "User not found"}
                
                cash_balance = user_cash.data[0]['cash_balance']
                
                if cash_balance < trade_value:
                    return {"status": "error", "message": "Insufficient funds for this trade"}
                
                # Update user's cash balance
                self.supabase.table('users').update({'cash_balance': cash_balance - trade_value}).eq('id', user_id).execute()
                
                # Check if the stock is already in the portfolio
                existing_position = None
                for position in user_portfolio.data:
                    if position['ticker'] == ticker:
                        existing_position = position
                        break
                
                if existing_position:
                    # Update existing position
                    new_quantity = existing_position['quantity'] + quantity
                    new_avg_price = ((existing_position['quantity'] * existing_position['avg_price']) + trade_value) / new_quantity
                    
                    self.supabase.table('portfolios').update({
                        'quantity': new_quantity,
                        'avg_price': new_avg_price,
                        'updated_at': datetime.datetime.now().isoformat()
                    }).eq('id', existing_position['id']).execute()
                else:
                    # Create new position
                    self.supabase.table('portfolios').insert({
                        'user_id': user_id,
                        'ticker': ticker,
                        'quantity': quantity,
                        'avg_price': price,
                        'created_at': datetime.datetime.now().isoformat(),
                        'updated_at': datetime.datetime.now().isoformat()
                    }).execute()
                
            elif action.lower() == 'sell':
                # Check if the user has the stock and enough shares
                has_stock = False
                stock_position = None
                
                for position in user_portfolio.data:
                    if position['ticker'] == ticker:
                        has_stock = True
                        stock_position = position
                        break
                
                if not has_stock:
                    return {"status": "error", "message": f"You don't own any shares of {ticker}"}
                
                if stock_position['quantity'] < quantity:
                    return {"status": "error", "message": f"You only have {stock_position['quantity']} shares of {ticker}"}
                
                # Update user's cash balance
                user_cash = self.supabase.table('users').select('cash_balance').eq('id', user_id).execute()
                cash_balance = user_cash.data[0]['cash_balance']
                self.supabase.table('users').update({'cash_balance': cash_balance + trade_value}).eq('id', user_id).execute()
                
                # Update the portfolio
                new_quantity = stock_position['quantity'] - quantity
                
                if new_quantity == 0:
                    # Remove the position if no shares left
                    self.supabase.table('portfolios').delete().eq('id', stock_position['id']).execute()
                else:
                    # Update the position
                    self.supabase.table('portfolios').update({
                        'quantity': new_quantity,
                        'updated_at': datetime.datetime.now().isoformat()
                    }).eq('id', stock_position['id']).execute()
            
            # Record the trade
            trade = {
                'user_id': user_id,
                'ticker': ticker,
                'action': action.lower(),
                'quantity': quantity,
                'price': price,
                'total_value': trade_value,
                'timestamp': datetime.datetime.now().isoformat()
            }
            
            self.supabase.table('trades').insert(trade).execute()
            
            return {
                "status": "success",
                "trade": trade,
                "price": price,
                "total_value": trade_value,
                "message": f"Successfully {action.lower()}ed {quantity} shares of {ticker} at ${price}"
            }
            
        except Exception as e:
            logger.error(f"Error executing paper trade: {e}")
            return {"status": "error", "message": str(e)}
    
    async def get_user_portfolio(self, user_id):
        """
        Get a user's portfolio.
        
        Parameters:
            user_id (str): The user's ID
            
        Returns:
            dict: User portfolio
            
        Raises:
            ValueError: If the user is not found or portfolio cannot be fetched.
        """
        try:
            logger.info(f"Fetching portfolio for user: {user_id}")
            supabase = self.supabase
            
            # Get user info using maybe_single()
            user_info_response = supabase.table('users').select('id, cash_balance').eq('id', user_id).maybe_single().execute()
            
            # Error handling for maybe_single(): Check for data directly
            # The client might raise exceptions for connection errors, caught by outer try/except
            if not user_info_response.data:
                logger.error(f"User {user_id} not found in database (using maybe_single)." )
                raise ValueError(f"User {user_id} not found")
            
            user = user_info_response.data
            cash_balance = user.get('cash_balance', 0)
            logger.info(f"User {user_id} found with cash balance: {cash_balance}")
            
            # Get portfolio positions (standard execute)
            portfolio_response = supabase.table('portfolios').select('ticker, quantity, avg_price').eq('user_id', user_id).execute()
            
            # Standard error handling for execute()
            # APIResponse doesn't have .error attribute in newer Supabase client versions
            # Just use the data directly
            portfolio_data = portfolio_response.data
            
            if portfolio_data is None:
                logger.error(f"Supabase error fetching portfolio for user {user_id}: Portfolio data is None")
                raise ValueError(f"Database error fetching portfolio: No data returned")
            logger.info(f"Fetched {len(portfolio_data)} positions for user {user_id}")
            
            # Use asyncio.gather for concurrent price fetching
            price_tasks = []
            for position in portfolio_data:
                price_tasks.append(self.get_stock_price(position['ticker']))
                
            current_prices = await asyncio.gather(*price_tasks, return_exceptions=True)
            
            positions = []
            portfolio_value = cash_balance
            
            for i, position in enumerate(portfolio_data):
                ticker = position['ticker']
                quantity = position['quantity']
                avg_price = position['avg_price']
                
                # Get current price result
                current_price_result = current_prices[i]
                
                if isinstance(current_price_result, Exception):
                    logger.error(f"Error getting price for {ticker} during portfolio calculation: {current_price_result}")
                    current_price = avg_price # Fallback
                elif current_price_result is None:
                    logger.warning(f"Could not get current price for {ticker}, using avg price: {avg_price}")
                    current_price = avg_price # Fallback
                else:
                    current_price = current_price_result
                
                position_value = current_price * quantity
                portfolio_value += position_value
                
                positions.append({
                    'ticker': ticker,
                    'quantity': quantity,
                    'avg_price': avg_price,
                    'current_price': current_price,
                    'value': position_value,
                    'profit_loss': ((current_price - avg_price) / avg_price * 100) if avg_price and avg_price > 0 else 0
                })
            
            logger.info(f"Successfully processed portfolio for user {user_id}. Total value: {portfolio_value}")
            return {
                'portfolio_value': round(portfolio_value, 2),
                'cash_balance': round(cash_balance, 2),
                'positions': positions
            }
        except ValueError as ve:
            logger.error(f"ValueError getting portfolio for {user_id}: {ve}")
            raise
        except Exception as e:
            logger.error(f"Unexpected error getting portfolio for {user_id}: {e}", exc_info=True)
            raise ValueError(f"Failed to get portfolio due to an unexpected error: {str(e)}")
    
    async def get_user_summary(self, user_id):
        """
        Get a summary of a user's portfolio and recent trades.
        
        Parameters:
            user_id (str): The user's ID
            
        Returns:
            dict: User portfolio summary
        """
        try:
            # Get user info
            user_info = self.supabase.table('users').select('*').eq('id', user_id).execute()
            
            if not user_info.data:
                logger.error(f"User {user_id} not found in database")
                raise ValueError(f"User {user_id} not found")
            
            user = user_info.data[0]
            user_name = user.get('name', 'buddy')  # Default to 'buddy' if name is empty
            
            # Get user portfolio
            portfolio = await self.get_user_portfolio(user_id)
            
            # Get recent trades
            recent_trades = self.supabase.table('trades').select('*').eq('user_id', user_id).order('timestamp', desc=True).limit(3).execute()
            
            # Format recent trades
            formatted_trades = []
            for trade in recent_trades.data:
                formatted_trades.append(
                    f"{trade['action'].capitalize()} {trade['quantity']} {trade['ticker']} @ ${trade['price']}"
                )
            
            return {
                'name': user_name,
                'portfolio_value': portfolio['portfolio_value'],
                'cash_balance': portfolio['cash_balance'],
                'positions': portfolio['positions'],
                'recent_trades': "; ".join(formatted_trades) if formatted_trades else "No recent trades."
            }
            
        except ValueError:
            # Re-raise user not found error
            raise
        except Exception as e:
            logger.error(f"Error getting user summary: {e}")
            raise ValueError(f"Failed to get user summary: {str(e)}") 