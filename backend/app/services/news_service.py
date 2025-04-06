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
        
    async def get_financial_news(self, max_items: int = 10, cache_bypass: bool = False) -> List[Dict[str, Any]]:
        """
        Get financial news articles from configured RSS feeds
        
        Parameters:
            max_items (int): Maximum number of news items to return
            cache_bypass (bool): Whether to bypass the cache
            
        Returns:
            List[Dict]: List of news articles with title, link, published date and summary
        """
        current_time = time()
        
        # Check if we can use cached news
        if not cache_bypass and current_time - self.last_fetch_time < self.cache_expiry and self.news_cache:
            logger.info("Using cached financial news")
            return self.news_cache[:max_items]
        
        logger.info("Fetching fresh financial news")
        
        # Run RSS parsing in a thread pool to avoid blocking
        loop = asyncio.get_event_loop()
        parsed_feeds = await loop.run_in_executor(
            None,
            lambda: self.feed_library.parse_all_feeds(fields=['title', 'link', 'published', 'summary'])
        )
        
        # Extract entries from all feeds and flatten into a single list
        news_items = []
        for feed in parsed_feeds:
            if 'entries' in feed:
                for entry in feed['entries']:
                    # Add simple processing to clean up data
                    if 'title' in entry:
                        # Create a cleaned news item
                        news_item = {
                            'title': entry.get('title', '').strip(),
                            'link': entry.get('link', ''),
                            'published': entry.get('published', ''),
                            'summary': entry.get('summary', '').strip() if entry.get('summary') else ''
                        }
                        news_items.append(news_item)
        
        # Sort by published date (newest first) if available
        # This is a simple approach - in production you'd want more robust date parsing
        news_items.sort(key=lambda x: x.get('published', ''), reverse=True)
        
        # Remove duplicate titles (keeping the first/newest occurrence)
        unique_titles = set()
        unique_news = []
        for item in news_items:
            if item['title'] not in unique_titles:
                unique_titles.add(item['title'])
                unique_news.append(item)
        
        # Update cache
        self.news_cache = unique_news
        self.last_fetch_time = current_time
        
        return unique_news[:max_items]

    async def get_market_news_summary(self, max_items: int = 5) -> str:
        """
        Get a concatenated summary of the latest market news
        
        Parameters:
            max_items (int): Maximum number of news items to include
            
        Returns:
            str: Concatenated news summary or empty message if no news
        """
        news_items = await self.get_financial_news(max_items=max_items)
        
        if not news_items:
            return ""  # Return empty string instead of a message
        
        # Format the news items into a simple text summary
        summary_lines = []
        for i, item in enumerate(news_items, 1):
            title = item.get('title', 'Untitled')
            summary_lines.append(f"{i}. {title}")
        
        return "\n".join(summary_lines)


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