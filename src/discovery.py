"""
Discovery Module - Scrapes ApeWisdom and tracks Reddit mentions
"""
import os
import re
import time
import logging
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from collections import defaultdict

import praw
import prawcore
from bs4 import BeautifulSoup
import requests
from supabase import create_client, Client

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class DiscoveryEngine:
    """Discovers trending tickers from ApeWisdom and Reddit"""
    
    def __init__(self):
        """Initialize Reddit API and Supabase clients"""
        # Reddit API setup
        self.reddit = praw.Reddit(
            client_id=os.environ.get('REDDIT_CLIENT_ID'),
            client_secret=os.environ.get('REDDIT_CLIENT_SECRET'),
            user_agent=os.environ.get('REDDIT_USER_AGENT', 'sentiment_bot_v2.0')
        )
        
        # Supabase setup
        supabase_url = os.environ.get('SUPABASE_URL')
        supabase_key = os.environ.get('SUPABASE_KEY')
        
        if not supabase_url or not supabase_key:
            raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set")
        
        self.supabase: Client = create_client(supabase_url, supabase_key)
        
        # Target subreddits for mention tracking
        self.target_subreddits = ['wallstreetbets', 'stocks', 'investing', 'RobinHoodPennyStocks']
    
    def scrape_apewisdom(self, top_n: int = 50) -> List[Dict]:
        """
        Scrape top trending tickers from ApeWisdom
        
        Args:
            top_n: Number of top tickers to retrieve
            
        Returns:
            List of ticker dictionaries with rank, symbol, mentions, and upvotes
        """
        logger.info(f"Scraping top {top_n} tickers from ApeWisdom...")
        
        url = "https://apewisdom.io/"
        headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'
        }
        
        try:
            response = requests.get(url, headers=headers, timeout=30)
            response.raise_for_status()
            
            soup = BeautifulSoup(response.content, 'html.parser')
            tickers = []
            
            # Parse the trending table (adjust selectors based on actual HTML structure)
            # This is a placeholder - you'll need to inspect ApeWisdom's actual HTML
            ticker_rows = soup.find_all('tr', class_='ticker-row')[:top_n]
            
            for idx, row in enumerate(ticker_rows, 1):
                try:
                    # Adjust these selectors based on actual HTML structure
                    symbol_elem = row.find('td', class_='ticker-symbol') or row.find('a', class_='ticker')
                    mentions_elem = row.find('td', class_='mentions')
                    upvotes_elem = row.find('td', class_='upvotes')
                    
                    if symbol_elem:
                        symbol = symbol_elem.text.strip().upper()
                        # Remove $ prefix if present
                        symbol = symbol.replace('$', '')
                        
                        ticker_data = {
                            'rank': idx,
                            'symbol': symbol,
                            'mention_count': int(mentions_elem.text.strip()) if mentions_elem else 0,
                            'upvotes': int(upvotes_elem.text.strip()) if upvotes_elem else 0,
                            'source': 'APEWISDOM'
                        }
                        tickers.append(ticker_data)
                        logger.info(f"Rank {idx}: {symbol} - {ticker_data['mention_count']} mentions")
                
                except Exception as e:
                    logger.warning(f"Error parsing ticker row {idx}: {e}")
                    continue
            
            logger.info(f"Successfully scraped {len(tickers)} tickers from ApeWisdom")
            return tickers
            
        except requests.RequestException as e:
            logger.error(f"Failed to scrape ApeWisdom: {e}")
            return []
    
    def extract_ticker_from_text(self, text: str) -> List[str]:
        """
        Extract ticker symbols from text (looks for $TICKER or uppercase words)
        
        Args:
            text: Text to search for tickers
            
        Returns:
            List of ticker symbols found
        """
        # Pattern 1: $TICKER format
        dollar_tickers = re.findall(r'\$([A-Z]{1,5})\b', text)
        
        # Pattern 2: Standalone uppercase words (2-5 chars, common ticker length)
        # Be conservative to avoid false positives
        standalone_tickers = re.findall(r'\b([A-Z]{2,5})\b', text)
        
        # Filter out common words that aren't tickers
        excluded_words = {
            'THE', 'AND', 'FOR', 'ARE', 'BUT', 'NOT', 'YOU', 'ALL', 'CAN', 
            'HER', 'WAS', 'ONE', 'OUR', 'OUT', 'DAY', 'GET', 'HAS', 'HIM',
            'HOW', 'ITS', 'MAY', 'NEW', 'NOW', 'OLD', 'SEE', 'TWO', 'WAY',
            'WHO', 'BOY', 'DID', 'HIS', 'SHE', 'USE', 'WIN', 'YET', 'YOLO'
        }
        
        all_tickers = set(dollar_tickers + standalone_tickers)
        valid_tickers = [t for t in all_tickers if t not in excluded_words]
        
        return valid_tickers
    
    def track_reddit_mentions(
        self, 
        target_tickers: Optional[List[str]] = None,
        hours_back: int = 24
    ) -> Dict[str, Dict]:
        """
        Track Reddit mentions for specific tickers across target subreddits
        
        Args:
            target_tickers: List of ticker symbols to track (if None, discovers from posts)
            hours_back: How many hours back to search
            
        Returns:
            Dictionary mapping ticker -> mention data
        """
        logger.info(f"Tracking Reddit mentions for the last {hours_back} hours...")
        
        cutoff_time = datetime.utcnow() - timedelta(hours=hours_back)
        mention_data = defaultdict(lambda: {
            'mention_count_24h': 0,
            'subreddit_distribution': defaultdict(int),
            'top_posts': [],
            'total_upvotes': 0
        })
        
        for subreddit_name in self.target_subreddits:
            try:
                logger.info(f"Scanning r/{subreddit_name}...")
                subreddit = self.reddit.subreddit(subreddit_name)
                
                # Search both hot and new posts
                posts = list(subreddit.hot(limit=100)) + list(subreddit.new(limit=100))
                
                for post in posts:
                    post_time = datetime.utcfromtimestamp(post.created_utc)
                    
                    # Skip old posts
                    if post_time < cutoff_time:
                        continue
                    
                    # Extract tickers from title and selftext
                    text = f"{post.title} {post.selftext}"
                    found_tickers = self.extract_ticker_from_text(text)
                    
                    # If we have target tickers, filter to those
                    if target_tickers:
                        found_tickers = [t for t in found_tickers if t in target_tickers]
                    
                    for ticker in found_tickers:
                        mention_data[ticker]['mention_count_24h'] += 1
                        mention_data[ticker]['subreddit_distribution'][subreddit_name] += 1
                        mention_data[ticker]['total_upvotes'] += post.score
                        
                        # Store top posts (max 5)
                        if len(mention_data[ticker]['top_posts']) < 5:
                            mention_data[ticker]['top_posts'].append({
                                'title': post.title,
                                'url': post.url,
                                'score': post.score,
                                'subreddit': subreddit_name,
                                'created': post_time.isoformat()
                            })
                
                time.sleep(2)  # Rate limiting
                
            except prawcore.exceptions.Forbidden:
                logger.warning(f"Access forbidden to r/{subreddit_name}")
            except prawcore.exceptions.NotFound:
                logger.warning(f"Subreddit r/{subreddit_name} not found")
            except Exception as e:
                logger.error(f"Error scanning r/{subreddit_name}: {e}")
        
        # Calculate mention velocity (compare to previous period)
        for ticker, data in mention_data.items():
            previous_count = self._get_previous_mention_count(ticker, hours_back)
            if previous_count > 0:
                velocity_change = ((data['mention_count_24h'] - previous_count) / previous_count) * 100
            else:
                velocity_change = 100.0 if data['mention_count_24h'] > 0 else 0.0
            
            mention_data[ticker]['velocity_change_pct'] = round(velocity_change, 2)
        
        logger.info(f"Found mentions for {len(mention_data)} tickers")
        return dict(mention_data)
    
    def _get_previous_mention_count(self, ticker: str, hours_back: int) -> int:
        """
        Get the previous mention count for velocity calculation
        
        Args:
            ticker: Ticker symbol
            hours_back: Hours to look back
            
        Returns:
            Previous mention count
        """
        try:
            # Get ticker_id
            ticker_response = self.supabase.table('tickers').select('id').eq('symbol', ticker).execute()
            
            if not ticker_response.data:
                return 0
            
            ticker_id = ticker_response.data[0]['id']
            
            # Get mention count from ~24-48 hours ago
            cutoff_time = (datetime.utcnow() - timedelta(hours=hours_back * 2)).isoformat()
            velocity_response = self.supabase.table('reddit_mention_velocity')\
                .select('mention_count_24h')\
                .eq('ticker_id', ticker_id)\
                .gte('timestamp', cutoff_time)\
                .order('timestamp', desc=True)\
                .limit(1)\
                .execute()
            
            if velocity_response.data:
                return velocity_response.data[0]['mention_count_24h']
            
            return 0
            
        except Exception as e:
            logger.warning(f"Error getting previous mention count for {ticker}: {e}")
            return 0
    
    def save_to_supabase(
        self, 
        apewisdom_data: List[Dict], 
        reddit_data: Dict[str, Dict]
    ) -> None:
        """
        Save discovered data to Supabase
        
        Args:
            apewisdom_data: List of ApeWisdom ticker data
            reddit_data: Dictionary of Reddit mention data
        """
        logger.info("Saving discovery data to Supabase...")
        
        # First, ensure all tickers exist in the tickers table
        all_symbols = set([t['symbol'] for t in apewisdom_data] + list(reddit_data.keys()))
        
        for symbol in all_symbols:
            try:
                # Check if ticker exists
                result = self.supabase.table('tickers').select('id').eq('symbol', symbol).execute()
                
                if not result.data:
                    # Insert new ticker
                    self.supabase.table('tickers').insert({
                        'symbol': symbol,
                        'company_name': None,  # Will be filled by validator
                        'industry': None
                    }).execute()
                    logger.info(f"Created new ticker: {symbol}")
                    
            except Exception as e:
                logger.error(f"Error ensuring ticker {symbol} exists: {e}")
        
        # Save ApeWisdom sentiment logs
        for ticker_data in apewisdom_data:
            try:
                # Get ticker_id
                ticker_response = self.supabase.table('tickers').select('id').eq('symbol', ticker_data['symbol']).execute()
                
                if not ticker_response.data:
                    continue
                
                ticker_id = ticker_response.data[0]['id']
                
                # Insert sentiment log
                self.supabase.table('sentiment_logs').insert({
                    'ticker_id': ticker_id,
                    'source': 'APEWISDOM',
                    'mention_count': ticker_data['mention_count'],
                    'upvotes': ticker_data['upvotes'],
                    'rank': ticker_data['rank'],
                    'timestamp': datetime.utcnow().isoformat()
                }).execute()
                
                logger.debug(f"Saved ApeWisdom data for {ticker_data['symbol']}")
                
            except Exception as e:
                logger.error(f"Error saving ApeWisdom data for {ticker_data['symbol']}: {e}")
        
        # Save Reddit mention velocity data
        for symbol, data in reddit_data.items():
            try:
                # Get ticker_id
                ticker_response = self.supabase.table('tickers').select('id').eq('symbol', symbol).execute()
                
                if not ticker_response.data:
                    continue
                
                ticker_id = ticker_response.data[0]['id']
                
                # Aggregate subreddit distribution
                for subreddit, count in data['subreddit_distribution'].items():
                    self.supabase.table('reddit_mention_velocity').insert({
                        'ticker_id': ticker_id,
                        'subreddit': subreddit,
                        'mention_count_24h': count,
                        'velocity_change_pct': data['velocity_change_pct'],
                        'top_posts': data['top_posts'],
                        'timestamp': datetime.utcnow().isoformat()
                    }).execute()
                
                # Also create a sentiment log entry for Reddit
                self.supabase.table('sentiment_logs').insert({
                    'ticker_id': ticker_id,
                    'source': 'REDDIT',
                    'mention_count': data['mention_count_24h'],
                    'upvotes': data['total_upvotes'],
                    'timestamp': datetime.utcnow().isoformat()
                }).execute()
                
                logger.debug(f"Saved Reddit data for {symbol}")
                
            except Exception as e:
                logger.error(f"Error saving Reddit data for {symbol}: {e}")
        
        logger.info("Discovery data saved successfully")
    
    def run(self) -> Dict:
        """
        Main execution method - runs the full discovery pipeline
        
        Returns:
            Dictionary with results summary
        """
        logger.info("=" * 60)
        logger.info("Starting Discovery Engine")
        logger.info("=" * 60)
        
        # Step 1: Scrape ApeWisdom
        apewisdom_tickers = self.scrape_apewisdom(top_n=50)
        
        # Step 2: Track Reddit mentions for top 20 ApeWisdom tickers
        top_symbols = [t['symbol'] for t in apewisdom_tickers[:20]]
        reddit_mentions = self.track_reddit_mentions(target_tickers=top_symbols, hours_back=24)
        
        # Step 3: Save to Supabase
        self.save_to_supabase(apewisdom_tickers, reddit_mentions)
        
        results = {
            'apewisdom_count': len(apewisdom_tickers),
            'reddit_tracked_count': len(reddit_mentions),
            'top_trending': apewisdom_tickers[:5] if apewisdom_tickers else [],
            'highest_velocity': sorted(
                reddit_mentions.items(), 
                key=lambda x: x[1].get('velocity_change_pct', 0), 
                reverse=True
            )[:5]
        }
        
        logger.info("=" * 60)
        logger.info("Discovery Engine Complete")
        logger.info(f"ApeWisdom tickers found: {results['apewisdom_count']}")
        logger.info(f"Reddit mentions tracked: {results['reddit_tracked_count']}")
        logger.info("=" * 60)
        
        return results


if __name__ == '__main__':
    # For testing
    from dotenv import load_dotenv
    load_dotenv()
    
    engine = DiscoveryEngine()
    results = engine.run()
    
    print("\n=== DISCOVERY RESULTS ===")
    print(f"Top Trending on ApeWisdom:")
    for ticker in results['top_trending']:
        print(f"  {ticker['rank']}. {ticker['symbol']} - {ticker['mention_count']} mentions")
    
    print(f"\nHighest Velocity on Reddit:")
    for symbol, data in results['highest_velocity']:
        print(f"  {symbol}: {data['mention_count_24h']} mentions ({data['velocity_change_pct']:+.1f}% velocity)")

