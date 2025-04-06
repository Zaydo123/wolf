import asyncio
import logging
import time
import yfinance as yf
from datetime import datetime

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Rate limiting settings
LAST_REQUEST_TIME = time.time()
MIN_REQUEST_INTERVAL = 3.0  # Increased to 3 seconds between requests

async def rate_limit_request():
    """Implement rate limiting"""
    global LAST_REQUEST_TIME
    
    current_time = time.time()
    time_since_last_request = current_time - LAST_REQUEST_TIME
    
    if time_since_last_request < MIN_REQUEST_INTERVAL:
        wait_time = MIN_REQUEST_INTERVAL - time_since_last_request
        logger.debug(f"Rate limiting: waiting {wait_time:.2f} seconds")
        await asyncio.sleep(wait_time)
    
    LAST_REQUEST_TIME = time.time()

async def test_stock_price(ticker):
    """Test getting stock price with rate limiting"""
    await rate_limit_request()
    
    try:
        stock = yf.Ticker(ticker)
        
        # Try multiple methods to get the price
        try:
            # Method 1: fast_info
            price = stock.fast_info.last_price
            if price and price > 0:
                logger.info(f"Got price for {ticker} using fast_info: ${price}")
                return price
        except Exception as e:
            logger.debug(f"fast_info failed: {e}")
        
        try:
            # Method 2: info dictionary
            info = stock.info
            price = info.get('regularMarketPrice') or info.get('currentPrice') or info.get('price')
            if price and price > 0:
                logger.info(f"Got price for {ticker} using info dict: ${price}")
                return price
        except Exception as e:
            logger.debug(f"info dict failed: {e}")
        
        try:
            # Method 3: 1-minute data
            data = stock.history(period="1d", interval="1m")
            if not data.empty:
                price = data['Close'].iloc[-1]
                if price and price > 0:
                    logger.info(f"Got price for {ticker} using minute data: ${price}")
                    return price
        except Exception as e:
            logger.debug(f"minute data failed: {e}")
        
        logger.warning(f"Could not get price for {ticker} using any method")
        return None
        
    except Exception as e:
        logger.error(f"Error getting price for {ticker}: {e}")
        return None

async def test_market_indices():
    """Test getting market indices with rate limiting"""
    indices = {
        "S&P 500": ["SPY", "^GSPC"],
        "Dow Jones": ["DIA", "^DJI"],
        "NASDAQ": ["QQQ", "^IXIC"]
    }
    
    results = {}
    for index_name, symbols in indices.items():
        for symbol in symbols:
            await rate_limit_request()
            
            try:
                index = yf.Ticker(symbol)
                
                # Try multiple methods
                try:
                    # Method 1: fast_info
                    fast_info = index.fast_info
                    current = fast_info.last_price
                    previous = fast_info.previous_close
                    if current and previous and current > 0 and previous > 0:
                        change = current - previous
                        change_percent = (change / previous) * 100
                        results[index_name] = {
                            'symbol': symbol,
                            'price': current,
                            'change': change,
                            'change_percent': change_percent
                        }
                        logger.info(f"Successfully fetched {index_name} using {symbol}")
                        break
                except Exception as e:
                    logger.debug(f"fast_info failed for {symbol}: {e}")
                
                try:
                    # Method 2: info dictionary
                    info = index.info
                    current = info.get('regularMarketPrice') or info.get('currentPrice')
                    previous = info.get('regularMarketPreviousClose') or info.get('previousClose')
                    if current and previous and current > 0 and previous > 0:
                        change = current - previous
                        change_percent = (change / previous) * 100
                        results[index_name] = {
                            'symbol': symbol,
                            'price': current,
                            'change': change,
                            'change_percent': change_percent
                        }
                        logger.info(f"Successfully fetched {index_name} using {symbol}")
                        break
                except Exception as e:
                    logger.debug(f"info dict failed for {symbol}: {e}")
                
                try:
                    # Method 3: 1-minute data
                    data = index.history(period="1d", interval="1m")
                    if not data.empty:
                        current = data['Close'].iloc[-1]
                        yesterday = index.history(period="2d")
                        if not yesterday.empty and len(yesterday) >= 2:
                            previous = yesterday['Close'].iloc[-2]
                            change = current - previous
                            change_percent = (change / previous) * 100
                            results[index_name] = {
                                'symbol': symbol,
                                'price': current,
                                'change': change,
                                'change_percent': change_percent
                            }
                            logger.info(f"Successfully fetched {index_name} using {symbol}")
                            break
                except Exception as e:
                    logger.debug(f"minute data failed for {symbol}: {e}")
                
            except Exception as e:
                logger.error(f"Error fetching {index_name} using {symbol}: {e}")
        
        if index_name not in results:
            logger.warning(f"Could not fetch data for {index_name}")
    
    return results

async def main():
    """Run the tests"""
    logger.info("Starting yfinance test...")
    
    # Test individual stock
    logger.info("\nTesting individual stock price...")
    stock_price = await test_stock_price("AAPL")
    logger.info(f"AAPL price: {stock_price}")
    
    # Test market indices
    logger.info("\nTesting market indices...")
    indices = await test_market_indices()
    for index_name, data in indices.items():
        logger.info(f"{index_name} ({data['symbol']}): ${data['price']} ({data['change_percent']:.2f}%)")

if __name__ == "__main__":
    asyncio.run(main()) 