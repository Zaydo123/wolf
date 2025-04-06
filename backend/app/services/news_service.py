import logging
import asyncio
from typing import List, Dict, Any
import json
from concurrent.futures import ThreadPoolExecutor
from typing import List, Set, Union
from time import time
import feedparser
import os
import httpx
import random
from bs4 import BeautifulSoup

# Set the log level to DEBUG if the environment is not production
log_level = logging.DEBUG if "prod" not in (os.getenv('ENVIRONMENT') or "").lower() else logging.INFO
logging.basicConfig(level=log_level)

MAX_WORKERS = 10  # Number of threads to use for parsing feeds

logger = logging.getLogger(__name__)

"""
    Wrapper function to measure the execution time of a function
"""
def measure_execution_time(func):
    def wrapper(*args, **kwargs):
        start = time()
        result = func(*args, **kwargs)
        end = time()
        logging.debug(f"Execution time for {func.__name__}: {round(end - start, 2)} seconds")
        return result
    return wrapper

"""
    RSS Feed class
"""
class RSSFeed:

    def __init__(self, url, **kwargs):
        self.url: str = url
        self.last_fetched: float = 0
        self.tags: List[str] = kwargs.get('tags', [])
        
    """
        Parse the feed and return a dictionary with the requested fields
    """
    def parse(self, select_fields: List[str] = None) -> Union[dict, None]:
        feed = feedparser.parse(self.url)
        
        if feed.bozo and not feed.entries:
            logging.error(f"Malformed feed: {getattr(feed, 'bozo_exception', 'Unknown error')} : {self.url}")
            return {}

        self.last_fetched = time()
        
        # BFS to select only the required fields
        if select_fields:
            def bfs(node, fields):
                result = {}
                for field in fields:
                    if field in node:
                        result[field] = node[field]
                if 'entries' in node:
                    result['entries'] = []
                    for entry in node['entries']:
                        result['entries'].append(bfs(entry, fields))
                return result
            return bfs(feed, select_fields)
        
        return feed
    
    def __str__(self):
        return f"RSSFeed({self.url}, {self.tags}, {self.last_fetched})"
    
    def __repr__(self):
        return self.__str__()
    
"""
    Class to store a library of RSS feeds
"""
class FeedLibrary:

    def __init__(self):
        self.feeds = []
    
    def add_feed(self, feed: RSSFeed) -> None:
        self.feeds.append(feed)
    
    def remove_feed(self, feed: Union[RSSFeed, str]) -> None:
        if isinstance(feed, str):
            self.feeds = [f for f in self.feeds if f.url != feed]  # More Pythonic
        else:
            try:
                self.feeds.remove(feed)
            except ValueError:
                logging.warning(f"Feed {feed} not found in the library.")

    def list_feeds(self) -> List[RSSFeed]:
        return self.feeds

    def get_all_tags(self) -> Set[str]:
        tags = set()
        for feed in self.feeds:
            tags.update(feed.tags)
        return tags

    @measure_execution_time
    def parse_all_feeds(self, fields=None):
        results = []
        with ThreadPoolExecutor(max_workers=MAX_WORKERS) as executor:
            results = list(executor.map(lambda feed: feed.parse(fields), self.feeds))
        # Filter out None values
        return [res for res in results if res]

class NewsService:
    """
    News service for fetching financial news feeds
    """
    def __init__(self):
        # Initialize the feed library
        self.feed_library = FeedLibrary()
        
        # Add financial news feeds
        self.feed_library.add_feed(RSSFeed(
            'https://feeds.content.dowjones.io/public/rss/mw_topstories',
            tags=['financial', 'top-stories']
        ))
        self.feed_library.add_feed(RSSFeed(
            'https://feeds.content.dowjones.io/public/rss/mw_realtimeheadlines',
            tags=['financial', 'realtime']
        ))
        self.feed_library.add_feed(RSSFeed(
            'http://feeds.marketwatch.com/marketwatch/bulletins',
            tags=['financial', 'bulletins']
        ))
        self.feed_library.add_feed(RSSFeed(
            'https://feeds.content.dowjones.io/public/rss/mw_marketpulse',
            tags=['financial', 'market-pulse']
        ))
        
        # Cache mechanism
        self.news_cache = {}
        self.last_fetch_time = 0
        self.cache_expiry = 600  # 10 minutes in seconds
        
        self.rss_feeds = [
            'https://feeds.content.dowjones.io/public/rss/mw_topstories',
            'https://feeds.content.dowjones.io/public/rss/mw_realtimeheadlines',
            'http://feeds.marketwatch.com/marketwatch/bulletins',
            'https://feeds.content.dowjones.io/public/rss/mw_marketpulse',
            'http://feeds.reuters.com/reuters/businessNews',
            'http://feeds.reuters.com/news/wealth',
            'https://www.investing.com/rss/news.rss',
            'https://www.fool.com/feeds/index.aspx',
            'http://feeds.feedburner.com/TheStreet-Stocks'
        ]
        self.cache = None
        self.cache_timestamp = None
        
    async def get_financial_news(self, max_items=10):
        """
        Get recent financial news from various RSS feeds.
        
        Parameters:
            max_items: Maximum number of news items to return
            
        Returns:
            list: List of news items with title and summary
        """
        try:
            # Gather all news items from feeds
            all_news = []
            
            # Fetch news from each feed asynchronously
            feed_tasks = []
            for feed_url in self.rss_feeds:
                feed_tasks.append(self._fetch_feed(feed_url))
                
            # Wait for all feeds to be fetched
            feed_results = await asyncio.gather(*feed_tasks, return_exceptions=True)
            
            # Process results, excluding exceptions
            for result in feed_results:
                if not isinstance(result, Exception) and result:
                    all_news.extend(result)
            
            # Randomize the news items
            random.shuffle(all_news)
            
            # Limit to requested number of items
            return all_news[:max_items]
        except Exception as e:
            logger.error(f"Error fetching financial news: {e}")
            return []
            
    async def _fetch_feed(self, feed_url):
        """
        Fetch news from a single RSS feed.
        
        Parameters:
            feed_url: URL of the RSS feed
            
        Returns:
            list: News items from this feed
        """
        try:
            # Use asyncio to fetch the feed
            loop = asyncio.get_event_loop()
            feed = await loop.run_in_executor(None, lambda: feedparser.parse(feed_url))
            
            results = []
            for entry in feed.entries:
                # Extract title and clean it
                title = entry.title.strip()
                
                # Extract and clean the summary if available
                summary = ""
                if hasattr(entry, 'summary'):
                    # Remove HTML tags from summary
                    soup = BeautifulSoup(entry.summary, 'html.parser')
                    summary = soup.get_text().strip()
                    
                    # Truncate summary to keep it concise
                    if len(summary) > 150:
                        summary = summary[:147] + "..."
                
                results.append({
                    "headline": title,
                    "summary": summary,
                    "source": feed.feed.title if hasattr(feed, 'feed') and hasattr(feed.feed, 'title') else "Financial News",
                    "published": entry.published if hasattr(entry, 'published') else None
                })
                
            return results
        except Exception as e:
            logger.error(f"Error fetching feed {feed_url}: {e}")
            return []
    
    async def get_market_news_summary(self, max_items=5):
        """
        Get a simple text summary of recent market news.
        
        Parameters:
            max_items: Maximum number of news items to include
            
        Returns:
            str: Newline-separated list of headlines
        """
        # Get extra items to ensure variety after shuffling
        news_items = await self.get_financial_news(max_items=max_items+10)
        
        # Randomize and take the requested number
        random.shuffle(news_items)
        selected_items = news_items[:max_items]
        
        # Format as newline-separated headlines
        headlines = [item["headline"] for item in selected_items]
        return "\n".join(headlines)


# For testing
if __name__ == '__main__':
    async def test_news_service():
        news_service = NewsService()
        news = await news_service.get_financial_news(max_items=5)
        print(json.dumps(news, indent=2))
        
        summary = await news_service.get_market_news_summary(max_items=3)
        print("\nSummary:")
        print(summary)
    
    asyncio.run(test_news_service())