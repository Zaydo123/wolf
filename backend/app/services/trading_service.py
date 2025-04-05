import logging
import asyncio
import datetime
import httpx

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
            
            # This is a synchronous call, so we'll run it in a thread pool
            loop = asyncio.get_event_loop()
            
            # Define the function to run in the thread pool
            def fetch_price():
                stock = yf.Ticker(ticker)
                # Get the latest price data
                data = stock.history(period="1d")
                if not data.empty:
                    # Return the most recent closing price
                    return data['Close'].iloc[-1]
                return None
            
            # Run the function in a thread pool
            price = await loop.run_in_executor(None, fetch_price)
            
            if price:
                logger.info(f"Got price for {ticker}: ${price}")
                return price
            else:
                logger.warning(f"Could not get price for {ticker}")
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
            
            # Define function to get index data
            async def get_index_data(symbol):
                loop = asyncio.get_event_loop()
                
                def fetch_index():
                    index = yf.Ticker(symbol)
                    data = index.history(period="2d")
                    if not data.empty:
                        current = data['Close'].iloc[-1]
                        previous = data['Close'].iloc[-2]
                        change = current - previous
                        change_percent = (change / previous) * 100
                        return {
                            'price': current,
                            'change': change,
                            'change_percent': change_percent
                        }
                    return None
                
                return await loop.run_in_executor(None, fetch_index)
            
            # Get market indices
            sp500 = await get_index_data("^GSPC")  # S&P 500
            dow = await get_index_data("^DJI")     # Dow Jones
            nasdaq = await get_index_data("^IXIC")  # NASDAQ
            
            indices = {
                'sp500': sp500 or {'price': 'Unknown', 'change_percent': 0},
                'dow': dow or {'price': 'Unknown', 'change_percent': 0},
                'nasdaq': nasdaq or {'price': 'Unknown', 'change_percent': 0},
            }
            
            # Get top news (in a real app, you'd use the RSS feed parser or news API)
            # For simplicity, we'll mock this
            news = [
                {"headline": "Fed Announces Interest Rate Decision", "summary": "The Federal Reserve announced it will maintain current interest rates."},
                {"headline": "Tech Stocks Rally on Earnings", "summary": "Major tech companies reported better-than-expected earnings, driving market gains."},
                {"headline": "Oil Prices Drop Amid Supply Concerns", "summary": "Crude oil prices fell 2% as OPEC+ considers increasing production."}
            ]
            
            return {
                'sp500': f"{indices['sp500']['price']:.2f} ({indices['sp500']['change_percent']:.2f}%)",
                'dow': f"{indices['dow']['price']:.2f} ({indices['dow']['change_percent']:.2f}%)",
                'nasdaq': f"{indices['nasdaq']['price']:.2f} ({indices['nasdaq']['change_percent']:.2f}%)",
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