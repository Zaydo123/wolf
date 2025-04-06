import logging
import asyncio
import datetime
import httpx
import os

# Try both import approaches
try:
    # Absolute imports (when running from backend/)
    from app.db.supabase import get_supabase_client
except ImportError:
    # Relative imports (when running from app/)
    from ..db.supabase import get_supabase_client

logger = logging.getLogger(__name__)

class TradingService:
    def __init__(self):
        self.supabase = get_supabase_client()
    
    async def get_stock_price(self, ticker):
        """
        Get the current price of a stock using yfinance.
        
        Parameters:
            ticker (str): The stock ticker symbol
            
        Returns:
            float: The current stock price or None if not found
        """
        try:
            import yfinance as yf
            import requests.exceptions
            import json.decoder
            
            # This is a synchronous call, so we'll run it in a thread pool
            loop = asyncio.get_event_loop()
            
            # Define the function to run in the thread pool with better error handling
            def fetch_price():
                try:
                    stock = yf.Ticker(ticker)
                    
                    # Method 1: Try fast_info.last_price (newest and fastest method)
                    try:
                        price = stock.fast_info.last_price
                        if price and price > 0:
                            logger.info(f"Got price for {ticker} using fast_info: ${price}")
                            return price
                    except (AttributeError, KeyError) as e:
                        logger.debug(f"fast_info not available for {ticker}: {e}")
                    
                    # Method 2: Try info dictionary with fallbacks
                    try:
                        info = stock.info
                        # Try multiple keys as they can change between API versions
                        price = info.get('regularMarketPrice') or info.get('currentPrice') or info.get('price')
                        if price and price > 0:
                            logger.info(f"Got price for {ticker} using info dict: ${price}")
                            return price
                    except (AttributeError, KeyError, ValueError) as e:
                        logger.debug(f"Info dict not available for {ticker}: {e}")
                    
                    # Method 3: Try 1-minute interval data for most recent price
                    try:
                        minute_data = stock.history(period="1d", interval="1m")
                        if not minute_data.empty:
                            price = minute_data['Close'].iloc[-1]
                            if price and price > 0:
                                logger.info(f"Got price for {ticker} using minute data: ${price}")
                                return price
                    except Exception as e:
                        logger.debug(f"Minute data not available for {ticker}: {e}")
                    
                    # Method 4: Try daily data as last resort
                    daily_data = stock.history(period="1d")
                    if not daily_data.empty:
                        price = daily_data['Close'].iloc[0]
                        logger.info(f"Got price for {ticker} using daily data: ${price}")
                        return price
                        
                    logger.warning(f"No price data available for {ticker} after trying all methods")
                    return None
                        
                except (requests.exceptions.RequestException, json.decoder.JSONDecodeError, 
                        ValueError, KeyError, IndexError) as e:
                    logger.warning(f"Error fetching data for {ticker}: {str(e)}")
                
                return None
            
            # Run the function in a thread pool with a timeout
            try:
                price_task = asyncio.create_task(loop.run_in_executor(None, fetch_price))
                # Wait for task with a timeout
                price = await asyncio.wait_for(price_task, timeout=10.0)
            except asyncio.TimeoutError:
                logger.error(f"Timeout fetching price for {ticker}")
                return None
            
            if price:
                return price
            else:
                logger.error(f"Could not get price for {ticker}")
                return None
                
        except Exception as e:
            logger.error(f"Error getting stock price for {ticker}: {e}")
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
    
    async def get_market_summary(self):
        """
        Get a summary of the current market state.
        
        Returns:
            dict: Market summary data including major indices and news
        """
        try:
            import yfinance as yf
            import requests.exceptions
            import json.decoder
            
            # Define function to get index data with improved error handling
            async def get_index_data(symbol):
                loop = asyncio.get_event_loop()
                
                def fetch_index():
                    try:
                        # Set a timeout for the request
                        index = yf.Ticker(symbol)
                        
                        # Method 1: Try fast_info for current data
                        try:
                            fast_info = index.fast_info
                            current = fast_info.last_price
                            previous = fast_info.previous_close
                            if current and previous and current > 0 and previous > 0:
                                change = current - previous
                                change_percent = (change / previous) * 100
                                logger.info(f"Successfully fetched {symbol} data using fast_info")
                                return {
                                    'price': current,
                                    'change': change,
                                    'change_percent': change_percent
                                }
                        except (AttributeError, KeyError) as e:
                            logger.debug(f"fast_info not available for {symbol}: {e}")
                        
                        # Method 2: Try info dictionary
                        try:
                            info = index.info
                            current = info.get('regularMarketPrice') or info.get('currentPrice') or info.get('price')
                            previous = info.get('regularMarketPreviousClose') or info.get('previousClose')
                            if current and previous and current > 0 and previous > 0:
                                change = current - previous
                                change_percent = (change / previous) * 100
                                logger.info(f"Successfully fetched {symbol} data using info dict")
                                return {
                                    'price': current,
                                    'change': change,
                                    'change_percent': change_percent
                                }
                        except (AttributeError, KeyError, ValueError) as e:
                            logger.debug(f"Info dict not available for {symbol}: {e}")
                            
                        # Method 3: Try 1-minute data for most recent price
                        try:
                            minute_data = index.history(period="2d", interval="1m")
                            if not minute_data.empty and len(minute_data) > 60:  # At least one hour of data
                                current = minute_data['Close'].iloc[-1]
                                # Use yesterday's close for previous
                                yesterday_data = index.history(period="2d")
                                if len(yesterday_data) >= 2:
                                    previous = yesterday_data['Close'].iloc[-2]
                                    change = current - previous
                                    change_percent = (change / previous) * 100
                                    logger.info(f"Successfully fetched {symbol} data using minute data")
                                    return {
                                        'price': current,
                                        'change': change,
                                        'change_percent': change_percent
                                    }
                        except Exception as e:
                            logger.debug(f"Minute data not available for {symbol}: {e}")
                            
                        # Method 4: Fall back to original method with daily data
                        data = index.history(period="2d")
                        if not data.empty and len(data) >= 2:
                            current = data['Close'].iloc[-1]
                            previous = data['Close'].iloc[-2]
                            change = current - previous
                            change_percent = (change / previous) * 100
                            logger.info(f"Successfully fetched {symbol} data using daily data")
                            return {
                                'price': current,
                                'change': change,
                                'change_percent': change_percent
                            }
                        elif not data.empty and len(data) == 1:
                            # Only one day available, use small change
                            current = data['Close'].iloc[-1]
                            # Assume zero change
                            change = 0
                            change_percent = 0
                            logger.warning(f"Only 1 day of data available for {symbol}")
                            return {
                                'price': current,
                                'change': change,
                                'change_percent': change_percent
                            }
                            
                        logger.warning(f"No data available for {symbol} after trying all methods")
                        return None
                        
                    except (requests.exceptions.RequestException, json.decoder.JSONDecodeError, 
                            ValueError, KeyError, IndexError) as e:
                        logger.error(f"Error fetching data for {symbol}: {str(e)}")
                    
                    # If any exception or empty data, return None
                    return None
                
                try:
                    return await loop.run_in_executor(None, fetch_index)
                except Exception as e:
                    logger.error(f"Thread pool error for {symbol}: {str(e)}")
                    return None
            
            # Try to get market indices with a timeout
            try:
                # Use asyncio.wait_for to add timeout
                sp500_task = asyncio.create_task(get_index_data("^GSPC"))  # S&P 500
                dow_task = asyncio.create_task(get_index_data("^DJI"))     # Dow Jones
                nasdaq_task = asyncio.create_task(get_index_data("^IXIC")) # NASDAQ
                
                # Wait for all tasks with a timeout
                done, pending = await asyncio.wait(
                    [sp500_task, dow_task, nasdaq_task], 
                    timeout=15.0  # Increased timeout for production
                )
                
                # Cancel any pending tasks
                for task in pending:
                    task.cancel()
                
                # Get results, handling timeouts
                sp500 = sp500_task.result() if sp500_task in done and not sp500_task.exception() else None
                dow = dow_task.result() if dow_task in done and not dow_task.exception() else None
                nasdaq = nasdaq_task.result() if nasdaq_task in done and not nasdaq_task.exception() else None
                
                # Log success or failure for each index
                logger.info(f"Market data fetch results - S&P 500: {'Success' if sp500 else 'Failed'}, "
                          f"Dow: {'Success' if dow else 'Failed'}, "
                          f"Nasdaq: {'Success' if nasdaq else 'Failed'}")
            
            except asyncio.TimeoutError:
                logger.error("Timeout fetching market indices")
                sp500, dow, nasdaq = None, None, None
            except Exception as e:
                logger.error(f"Error fetching market indices: {str(e)}")
                sp500, dow, nasdaq = None, None, None
            
            # Get market news
            news = [
                {"headline": "Fed Announces Interest Rate Decision", "summary": "The Federal Reserve announced it will maintain current interest rates."},
                {"headline": "Tech Stocks Rally on Earnings", "summary": "Major tech companies reported better-than-expected earnings, driving market gains."},
                {"headline": "Oil Prices Drop Amid Supply Concerns", "summary": "Crude oil prices fell 2% as OPEC+ considers increasing production."}
            ]
            
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
            
            return {
                'sp500': format_index(sp500),
                'dow': format_index(dow),
                'nasdaq': format_index(nasdaq),
                'top_news': "\n".join([f"{item['headline']}: {item['summary']}" for item in news])
            }
            
        except Exception as e:
            logger.error(f"Error getting market summary: {e}")
            return {
                'sp500': 'Unknown',
                'dow': 'Unknown',
                'nasdaq': 'Unknown',
                'top_news': 'No major news available at this time.'
            }
    
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
                return {"name": "buddy", "portfolio_value": 0, "recent_trades": "No recent trades."}
            
            user = user_info.data[0]
            
            # Get portfolio
            portfolio = self.supabase.table('portfolios').select('*').eq('user_id', user_id).execute()
            
            # Get recent trades
            recent_trades = self.supabase.table('trades').select('*').eq('user_id', user_id).order('timestamp', desc=True).limit(3).execute()
            
            # Calculate total portfolio value
            portfolio_value = user['cash_balance']
            positions = []
            
            for position in portfolio.data:
                # Get current price
                current_price = await self.get_stock_price(position['ticker'])
                
                if current_price:
                    position_value = current_price * position['quantity']
                    portfolio_value += position_value
                    
                    positions.append({
                        'ticker': position['ticker'],
                        'quantity': position['quantity'],
                        'avg_price': position['avg_price'],
                        'current_price': current_price,
                        'value': position_value,
                        'profit_loss': ((current_price - position['avg_price']) / position['avg_price']) * 100
                    })
            
            # Format recent trades
            formatted_trades = []
            for trade in recent_trades.data:
                formatted_trades.append(
                    f"{trade['action'].capitalize()} {trade['quantity']} {trade['ticker']} @ ${trade['price']}"
                )
            
            return {
                'name': user['name'],
                'portfolio_value': round(portfolio_value, 2),
                'cash_balance': round(user['cash_balance'], 2),
                'positions': positions,
                'recent_trades': "; ".join(formatted_trades) if formatted_trades else "No recent trades."
            }
            
        except Exception as e:
            logger.error(f"Error getting user summary: {e}")
            return {"name": "buddy", "portfolio_value": 0, "recent_trades": "No recent trades."} 