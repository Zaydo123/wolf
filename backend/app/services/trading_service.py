import logging
import asyncio
import datetime
import httpx
import os
import time
import json
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

# Yahoo Finance API (RapidAPI) settings
YAHOO_FINANCE_API_KEY = os.getenv("YAHOO_FINANCE_API_KEY", "")  # Optional
YAHOO_FINANCE_HOST = "yahoo-finance15.p.rapidapi.com"
YAHOO_FINANCE_BASE_URL = "https://yahoo-finance15.p.rapidapi.com/api/yahoo/qu/quote"

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
        """Get data from cache - DISABLED, always returns None for fresh data"""
        return None
        
    def _cache_data(self, key, data):
        """Store data in cache - DISABLED, does nothing"""
        # Caching disabled
        pass
    
    async def get_stock_price(self, ticker, fresh=True):
        """
        Get the current price for a stock.
        
        Parameters:
            ticker (str): The stock ticker symbol
            fresh (bool): Kept for compatibility, data is always fresh
            
        Returns:
            float: Current stock price
        """
        logger.debug(f"Getting price for {ticker}")
        
        # Always fetch from API - no caching
        await self._rate_limit_request()
        
        # Try Alpha Vantage first
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
                    logger.info(f"Got price for {ticker} from Alpha Vantage: ${price}")
                    return price
            
            # Check for API limits
            if "Note" in data and "API call frequency" in data["Note"]:
                logger.warning(f"Alpha Vantage API limit reached: {data['Note']}")
                # Try Yahoo Finance API as fallback
                if YAHOO_FINANCE_API_KEY:
                    yahoo_data = await self._get_yahoo_finance_data(ticker)
                    if yahoo_data:
                        price = yahoo_data['price']
                        logger.info(f"Got price for {ticker} from Yahoo Finance API: ${price}")
                        return price
            
            # If all API methods fail, provide fallback values for common stocks
            logger.warning(f"All API methods failed for {ticker}, using fallback values if available")
            
            # Emergency fallback values for common stocks
            fallback_prices = {
                "AAPL": 188.38,
                "MSFT": 418.12,
                "GOOGL": 153.75,
                "AMZN": 179.55,
                "META": 474.97,
                "NVDA": 94.31,
                "TSLA": 173.80,
                "JPM": 199.95,
                "V": 275.42,
                "NFLX": 608.14
            }
            
            if ticker in fallback_prices:
                price = fallback_prices[ticker]
                logger.info(f"Using emergency fallback price for {ticker}: ${price}")
                return price
            
            logger.warning(f"No price data available for {ticker} from any source")
            return None
                
        except Exception as e:
            logger.error(f"Error getting stock price for {ticker}: {e}")
            return None
    
    async def get_market_summary(self, fresh=True):
        """
        Get a summary of the current market state using Alpha Vantage.
        
        Parameters:
            fresh (bool): Kept for compatibility, data is always fresh
        
        Returns:
            dict: Market summary data including major indices and news
        """
        # No caching - always fetch fresh data
        try:
            # Define function to get index data with multiple fallbacks
            async def get_index_data(symbol):
                # Define index cache key here for proper scope
                index_cache_key = f"index_{symbol}"
                
                # Always fetch fresh data
                await self._rate_limit_request()
                
                # Try Alpha Vantage first
                alpha_vantage_result = await self._get_alpha_vantage_data(symbol)
                if alpha_vantage_result:
                    return alpha_vantage_result
                    
                # If Alpha Vantage fails, try Yahoo Finance API
                if YAHOO_FINANCE_API_KEY:
                    logger.info(f"Alpha Vantage failed for {symbol}, trying Yahoo Finance API")
                    yahoo_result = await self._get_yahoo_finance_data(symbol)
                    if yahoo_result:
                        return yahoo_result
                
                # All API methods failed, use hardcoded fallback values
                logger.warning(f"All API methods failed for {symbol}, using hardcoded fallback values")
                
                # Use hardcoded values for emergencies - fix to avoid "Unknown" message
                fallback_result = None
                if symbol == "SPY":  # S&P 500 ETF
                    fallback_result = {'price': 478.33, 'change': 0.0, 'change_percent': 0.0}
                elif symbol == "DIA":  # Dow Jones ETF
                    fallback_result = {'price': 389.27, 'change': 0.0, 'change_percent': 0.0}
                elif symbol == "QQQ":  # NASDAQ ETF
                    fallback_result = {'price': 445.90, 'change': 0.0, 'change_percent': 0.0}
                
                return fallback_result
            
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
            
            return summary
            
        except Exception as e:
            logger.error(f"Error getting market summary: {e}")
            # Create a fallback summary
            fallback_summary = {
                'sp500': format_index(sp500) if 'sp500' in locals() and sp500 else 'Unknown',
                'dow': format_index(dow) if 'dow' in locals() and dow else 'Unknown',
                'nasdaq': format_index(nasdaq) if 'nasdaq' in locals() and nasdaq else 'Unknown',
                'top_news': 'No major news available at this time.'
            }
            return fallback_summary
    
    async def _get_alpha_vantage_data(self, symbol):
        """Helper method to get data from Alpha Vantage"""
        try:
            # First try TIME_SERIES_DAILY
            params = {
                "function": "TIME_SERIES_DAILY",
                "symbol": symbol,
                "outputsize": "compact",
                "apikey": ALPHA_VANTAGE_API_KEY
            }
            
            response = await self.session.get(ALPHA_VANTAGE_BASE_URL, params=params)
            data = response.json()
            
            # Check for API limit messages
            if "Note" in data and "API call frequency" in data["Note"]:
                logger.warning(f"Alpha Vantage API limit reached: {data['Note']}")
                return None
            
            # The response format for TIME_SERIES_DAILY is different
            if "Time Series (Daily)" in data:
                time_series = data["Time Series (Daily)"]
                # Get the most recent date (first key)
                dates = list(time_series.keys())
                if not dates:
                    logger.warning(f"No dates found in response for {symbol}")
                    return None
                    
                latest_date = dates[0]
                previous_date = dates[1] if len(dates) > 1 else latest_date
                
                latest_data = time_series[latest_date]
                previous_data = time_series[previous_date]
                
                current = float(latest_data["4. close"])
                previous = float(previous_data["4. close"])
                change = current - previous
                change_percent = (change / previous) * 100
                
                result = {
                    'price': current,
                    'change': change,
                    'change_percent': change_percent
                }
                
                logger.info(f"Successfully fetched {symbol} data from Alpha Vantage TIME_SERIES_DAILY: {current:.2f}")
                return result
            
            # Try GLOBAL_QUOTE as a fallback
            logger.warning(f"TIME_SERIES_DAILY didn't work for {symbol}, trying GLOBAL_QUOTE")
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
                
                logger.info(f"Successfully fetched {symbol} data using Alpha Vantage GLOBAL_QUOTE")
                return result
            
            logger.warning(f"Alpha Vantage: No data available for {symbol}")
            return None
        except Exception as e:
            logger.error(f"Error fetching data from Alpha Vantage for {symbol}: {str(e)}")
            return None
        
    async def _get_yahoo_finance_data(self, symbol):
        """Helper method to get data from Yahoo Finance API"""
        try:
            if not YAHOO_FINANCE_API_KEY:
                logger.warning("Yahoo Finance API key not set")
                return None
            
            headers = {
                "X-RapidAPI-Key": YAHOO_FINANCE_API_KEY,
                "X-RapidAPI-Host": YAHOO_FINANCE_HOST
            }
            
            url = f"{YAHOO_FINANCE_BASE_URL}/{symbol}"
            
            response = await self.session.get(url, headers=headers)
            data = response.json()
            
            if data and isinstance(data, list) and len(data) > 0:
                item = data[0]
                if 'regularMarketPrice' in item and 'regularMarketPreviousClose' in item:
                    current = float(item['regularMarketPrice'])
                    previous = float(item['regularMarketPreviousClose'])
                    change = current - previous
                    change_percent = (change / previous) * 100
                    
                    result = {
                        'price': current,
                        'change': change,
                        'change_percent': change_percent
                    }
                    
                    logger.info(f"Successfully fetched {symbol} data from Yahoo Finance API: {current:.2f}")
                    return result
            
            logger.warning(f"Yahoo Finance API: No data available for {symbol}")
            return None
        except Exception as e:
            logger.error(f"Error fetching data from Yahoo Finance API for {symbol}: {str(e)}")
            return None
    
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
        
        # Ensure quantity is positive
        quantity = abs(quantity)
        if quantity <= 0:
            return {"status": "error", "message": "Quantity must be greater than 0"}
        
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
            
            # Record the trade with positive quantity and correct total value
            trade = {
                'user_id': user_id,
                'ticker': ticker,
                'action': action.lower(),
                'quantity': quantity,  # Always positive
                'price': price,
                'total_value': trade_value,  # Price * quantity
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
    
    async def get_user_portfolio(self, user_id, fresh=True):
        """
        Get a user's portfolio.
        
        Parameters:
            user_id (str): The user's ID
            fresh (bool): Kept for compatibility, data is always fresh
            
        Returns:
            dict: User portfolio
            
        Raises:
            ValueError: If the user is not found or portfolio cannot be fetched.
        """
        try:
            logger.info(f"Fetching portfolio for user: {user_id} (always fresh data)")
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
                price_tasks.append(self.get_stock_price(position['ticker'], fresh=fresh))
                
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
    
    async def get_user_summary(self, user_id, fresh=False):
        """
        Get a summary of a user's portfolio, cash balance, and recent trades.
        
        Parameters:
            user_id (str): The user's ID
            fresh (bool): If True, bypass any caching and get fresh price data
            
        Returns:
            dict: A dictionary containing user data
        """
        try:
            # Get the Supabase client
            supabase = get_supabase_client()
            
            # Get user details
            user = await self._get_user_data(user_id)
            if not user:
                logger.error(f"User {user_id} not found")
                return None
                
            # Get portfolio with fresh parameter
            portfolio = await self._get_portfolio(user_id, fresh=fresh)
            
            # Get recent trades
            recent_trades = await self._get_recent_trades(user_id)
            
            # Format recent trades for display
            formatted_trades = "No recent trades."
            if recent_trades:
                trade_lines = []
                for trade in recent_trades:
                    timestamp = datetime.datetime.fromisoformat(trade['timestamp'].replace('Z', '+00:00')).strftime('%Y-%m-%d')
                    trade_lines.append(f"{timestamp}: {trade['action']} {trade['quantity']} {trade['ticker']} @ ${trade['price']}")
                formatted_trades = "\n".join(trade_lines)
            
            # Get user's watchlist
            watchlist = await self._get_watchlist(user_id)
            
            # Get previous call history (last 3 calls)
            previous_calls = []
            try:
                # Get the user's previous calls
                past_calls = supabase.table('calls').select('id,call_sid,started_at,status')\
                    .eq('user_id', user_id)\
                    .order('started_at', desc=True)\
                    .limit(3)\
                    .execute()
                    
                if past_calls.data:
                    for call in past_calls.data:
                        # For each call, get a sample of the logs
                        call_summary = {
                            'date': datetime.datetime.fromisoformat(call['started_at'].replace('Z', '+00:00')).strftime('%Y-%m-%d'),
                            'highlights': []
                        }
                        
                        # Get important logs from this call (e.g., trades, recommendations)
                        call_logs = supabase.table('call_logs').select('*')\
                            .eq('call_sid', call['call_sid'])\
                            .order('timestamp')\
                            .execute()
                        
                        if call_logs.data:
                            # Find any trade actions or recommendations
                            for log in call_logs.data:
                                content = log['content'].upper()
                                if 'BUY' in content or 'SELL' in content or 'RECOMMEND' in content:
                                    call_summary['highlights'].append({
                                        'speaker': 'Broker' if log['direction'] == 'outbound' else 'User',
                                        'content': log['content']
                                    })
                                    
                            # Get at least one exchange (first broker message and user response)
                            if not call_summary['highlights'] and len(call_logs.data) >= 2:
                                for i, log in enumerate(call_logs.data):
                                    if log['direction'] == 'outbound' and i < len(call_logs.data) - 1:
                                        call_summary['highlights'].append({
                                            'speaker': 'Broker',
                                            'content': log['content']
                                        })
                                        # Get next user response
                                        next_log = call_logs.data[i+1]
                                        if next_log['direction'] == 'inbound':
                                            call_summary['highlights'].append({
                                                'speaker': 'User',
                                                'content': next_log['content']
                                            })
                                        break
                                        
                        if call_summary['highlights']:
                            previous_calls.append(call_summary)
                    
                    logger.info(f"Retrieved highlights from {len(previous_calls)} previous calls")
            except Exception as e:
                logger.error(f"Error retrieving previous call history: {e}")
                # Continue without previous calls if there's an error
            
            # Calculate portfolio value
            portfolio_value = sum(position['value'] for position in portfolio)
            
            # Return the user summary
            user_name = user.get('name', 'buddy')
            user_data = {
                'name': user_name,
                'cash_balance': user.get('cash_balance', 0),
                'portfolio_value': portfolio_value,
                'positions': portfolio,
                'recent_trades': formatted_trades,
                'watchlist': watchlist,
                'previous_calls': previous_calls
            }
            
            logger.info(f"Generated user summary for {user_id}")
            return user_data
            
        except Exception as e:
            logger.error(f"Error generating user summary: {e}")
            return None
    
    async def _get_user_data(self, user_id):
        """
        Get user details from the database.
        
        Parameters:
            user_id (str): The user's ID
            
        Returns:
            dict: User data or None if not found
        """
        try:
            user_info = self.supabase.table('users').select('*').eq('id', user_id).execute()
            
            if not user_info.data:
                logger.error(f"User {user_id} not found in database")
                return None
            
            return user_info.data[0]
        except Exception as e:
            logger.error(f"Error getting user data: {e}")
            return None
            
    async def _get_portfolio(self, user_id, fresh=False):
        """
        Get user's portfolio positions.
        
        Parameters:
            user_id (str): The user's ID
            fresh (bool): If True, bypass any caching and get fresh data
            
        Returns:
            list: Portfolio positions
        """
        try:
            portfolio_data = self.supabase.table('portfolios').select('*').eq('user_id', user_id).execute()
            
            positions = []
            for position in portfolio_data.data:
                # Get current price for this stock
                current_price = await self.get_stock_price(position['ticker'], fresh=fresh)
                
                if current_price:
                    # Calculate current value and profit/loss
                    quantity = position['quantity']
                    avg_price = position['avg_price']
                    current_value = quantity * current_price
                    profit_loss_pct = ((current_price - avg_price) / avg_price) * 100 if avg_price > 0 else 0
                    
                    positions.append({
                        'ticker': position['ticker'],
                        'quantity': quantity,
                        'avg_price': avg_price,
                        'current_price': current_price,
                        'value': current_value,
                        'profit_loss': profit_loss_pct
                    })
                else:
                    # If we can't get current price, use avg_price
                    quantity = position['quantity']
                    avg_price = position['avg_price']
                    current_value = quantity * avg_price
                    
                    positions.append({
                        'ticker': position['ticker'],
                        'quantity': quantity,
                        'avg_price': avg_price,
                        'current_price': avg_price,
                        'value': current_value,
                        'profit_loss': 0
                    })
            
            return positions
        except Exception as e:
            logger.error(f"Error getting portfolio data: {e}")
            return []
            
    async def _get_recent_trades(self, user_id):
        """
        Get user's recent trades.
        
        Parameters:
            user_id (str): The user's ID
            
        Returns:
            list: Recent trades
        """
        try:
            trades_data = self.supabase.table('trades').select('*')\
                .eq('user_id', user_id)\
                .order('timestamp', desc=True)\
                .limit(5)\
                .execute()
                
            return trades_data.data if trades_data.data else []
        except Exception as e:
            logger.error(f"Error getting recent trades: {e}")
            return []
            
    async def _get_watchlist(self, user_id):
        """
        Get user's watchlist.
        
        Parameters:
            user_id (str): The user's ID
            
        Returns:
            list: Watchlist tickers
        """
        try:
            watchlist_data = self.supabase.table('watchlists').select('*')\
                .eq('user_id', user_id)\
                .execute()
                
            return [item['ticker'] for item in watchlist_data.data] if watchlist_data.data else []
        except Exception as e:
            logger.error(f"Error getting watchlist: {e}")
            return []
    
    async def update_portfolio_prices(self, user_id):
        """
        Update portfolio positions with current prices and save to the database.
        
        Parameters:
            user_id (str): The user's ID
            
        Returns:
            dict: Updated portfolio with status information
        """
        try:
            logger.info(f"Updating portfolio prices for user: {user_id}")
            
            # Get portfolio positions
            portfolio_data = self.supabase.table('portfolios').select('*').eq('user_id', user_id).execute()
            
            if not portfolio_data.data:
                logger.info(f"No portfolio positions found for user {user_id}")
                return {"status": "success", "message": "No positions to update", "updated": 0}
            
            updated_count = 0
            
            # Update each position with current price
            for position in portfolio_data.data:
                ticker = position['ticker']
                quantity = position['quantity']
                avg_price = position['avg_price']
                
                # Get current price
                current_price = await self.get_stock_price(ticker)
                
                if current_price:
                    # Calculate current value and profit/loss
                    current_value = quantity * current_price
                    profit_loss_pct = ((current_price - avg_price) / avg_price) * 100 if avg_price > 0 else 0
                    
                    # Update the position in the database
                    self.supabase.table('portfolios').update({
                        'current_price': current_price,
                        'current_value': current_value,
                        'profit_loss': profit_loss_pct,
                        'updated_at': datetime.datetime.utcnow().isoformat()
                    }).eq('id', position['id']).execute()
                    
                    updated_count += 1
                    logger.info(f"Updated position for {ticker}: price={current_price}, profit_loss={profit_loss_pct:.2f}%")
                else:
                    logger.warning(f"Could not get current price for {ticker}, skipping update")
            
            logger.info(f"Successfully updated {updated_count} positions for user {user_id}")
            return {
                "status": "success", 
                "message": f"Updated {updated_count} positions", 
                "updated": updated_count
            }
        except Exception as e:
            logger.error(f"Error updating portfolio prices: {e}")
            return {"status": "error", "message": str(e), "updated": 0} 