"""
Setup Verification Script
Run this to test that all your credentials and connections are working
"""
import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def test_environment_variables():
    """Test that all required environment variables are set"""
    print("=" * 60)
    print("Testing Environment Variables...")
    print("=" * 60)
    
    required_vars = {
        'SUPABASE_URL': 'Supabase project URL',
        'SUPABASE_KEY': 'Supabase anon key',
        'REDDIT_CLIENT_ID': 'Reddit client ID',
        'REDDIT_CLIENT_SECRET': 'Reddit client secret',
        'REDDIT_USER_AGENT': 'Reddit user agent'
    }
    
    all_set = True
    for var, description in required_vars.items():
        value = os.environ.get(var)
        if value:
            # Show partial value for security
            if len(value) > 20:
                display_value = f"{value[:10]}...{value[-5:]}"
            else:
                display_value = value[:3] + "..." if len(value) > 3 else "***"
            print(f"✓ {var}: {display_value}")
        else:
            print(f"✗ {var}: NOT SET")
            all_set = False
    
    print()
    return all_set


def test_supabase_connection():
    """Test Supabase connection and database schema"""
    print("=" * 60)
    print("Testing Supabase Connection...")
    print("=" * 60)
    
    try:
        from supabase import create_client
        
        supabase_url = os.environ.get('SUPABASE_URL')
        supabase_key = os.environ.get('SUPABASE_KEY')
        
        if not supabase_url or not supabase_key:
            print("✗ Supabase credentials not set")
            return False
        
        # Create client
        supabase = create_client(supabase_url, supabase_key)
        print("✓ Supabase client created")
        
        # Test each table
        tables = ['tickers', 'sentiment_logs', 'fundamental_stats', 'trading_flags', 'reddit_mention_velocity']
        
        for table in tables:
            try:
                result = supabase.table(table).select("*").limit(1).execute()
                count = len(result.data) if result.data else 0
                print(f"✓ Table '{table}' exists (has {count} sample records)")
            except Exception as e:
                print(f"✗ Table '{table}' error: {str(e)[:50]}...")
                return False
        
        print()
        return True
        
    except ImportError:
        print("✗ supabase library not installed. Run: pip install -r requirements.txt")
        return False
    except Exception as e:
        print(f"✗ Supabase connection failed: {e}")
        return False


def test_reddit_connection():
    """Test Reddit API connection"""
    print("=" * 60)
    print("Testing Reddit API Connection...")
    print("=" * 60)
    
    try:
        import praw
        
        reddit_client_id = os.environ.get('REDDIT_CLIENT_ID')
        reddit_client_secret = os.environ.get('REDDIT_CLIENT_SECRET')
        reddit_user_agent = os.environ.get('REDDIT_USER_AGENT')
        
        if not all([reddit_client_id, reddit_client_secret, reddit_user_agent]):
            print("✗ Reddit credentials not set")
            return False
        
        # Create Reddit instance
        reddit = praw.Reddit(
            client_id=reddit_client_id,
            client_secret=reddit_client_secret,
            user_agent=reddit_user_agent
        )
        print("✓ Reddit client created")
        
        # Test by fetching a subreddit
        subreddit = reddit.subreddit('wallstreetbets')
        print(f"✓ Connected to r/wallstreetbets ({subreddit.subscribers:,} subscribers)")
        
        # Test by fetching a post
        post = next(subreddit.hot(limit=1))
        print(f"✓ Successfully fetched posts (latest: '{post.title[:50]}...')")
        
        print()
        return True
        
    except ImportError:
        print("✗ praw library not installed. Run: pip install -r requirements.txt")
        return False
    except Exception as e:
        print(f"✗ Reddit connection failed: {e}")
        return False


def test_yahoo_finance():
    """Test Yahoo Finance connection"""
    print("=" * 60)
    print("Testing Yahoo Finance Connection...")
    print("=" * 60)
    
    try:
        import yfinance as yf
        
        # Test with a well-known ticker
        ticker = yf.Ticker('AAPL')
        info = ticker.info
        
        print(f"✓ Successfully fetched data for AAPL")
        print(f"  Company: {info.get('longName', 'N/A')}")
        print(f"  Market Cap: ${info.get('marketCap', 0):,}")
        print(f"  Current Price: ${info.get('currentPrice', info.get('regularMarketPrice', 0)):.2f}")
        
        print()
        return True
        
    except ImportError:
        print("✗ yfinance library not installed. Run: pip install -r requirements.txt")
        return False
    except Exception as e:
        print(f"✗ Yahoo Finance connection failed: {e}")
        return False


def test_web_scraping():
    """Test web scraping capabilities"""
    print("=" * 60)
    print("Testing Web Scraping (BeautifulSoup)...")
    print("=" * 60)
    
    try:
        import requests
        from bs4 import BeautifulSoup
        
        # Test with a simple request
        response = requests.get('https://httpbin.org/html', timeout=10)
        soup = BeautifulSoup(response.content, 'html.parser')
        
        print("✓ requests library working")
        print("✓ BeautifulSoup parsing working")
        
        # Test ApeWisdom accessibility (don't parse, just check if accessible)
        try:
            ape_response = requests.get('https://apewisdom.io/', timeout=10)
            if ape_response.status_code == 200:
                print("✓ ApeWisdom is accessible")
            else:
                print(f"⚠ ApeWisdom returned status code {ape_response.status_code}")
        except Exception as e:
            print(f"⚠ ApeWisdom not accessible: {e}")
        
        print()
        return True
        
    except ImportError:
        print("✗ requests or beautifulsoup4 not installed. Run: pip install -r requirements.txt")
        return False
    except Exception as e:
        print(f"✗ Web scraping test failed: {e}")
        return False


def main():
    """Run all tests"""
    print("\n" + "=" * 60)
    print("TRADING BOT SETUP VERIFICATION")
    print("=" * 60 + "\n")
    
    results = {
        'Environment Variables': test_environment_variables(),
        'Supabase Connection': test_supabase_connection(),
        'Reddit API': test_reddit_connection(),
        'Yahoo Finance': test_yahoo_finance(),
        'Web Scraping': test_web_scraping()
    }
    
    # Summary
    print("=" * 60)
    print("VERIFICATION SUMMARY")
    print("=" * 60)
    
    all_passed = True
    for test_name, passed in results.items():
        status = "✓ PASS" if passed else "✗ FAIL"
        print(f"{status} - {test_name}")
        if not passed:
            all_passed = False
    
    print("\n" + "=" * 60)
    
    if all_passed:
        print("🎉 ALL TESTS PASSED!")
        print("\nYour trading bot is ready to run!")
        print("Next steps:")
        print("  1. Run the bot: python main.py")
        print("  2. Check logs: cat trading_bot.log")
        print("  3. View data in Supabase Table Editor")
        print("=" * 60)
        sys.exit(0)
    else:
        print("⚠️  SOME TESTS FAILED")
        print("\nPlease fix the failed tests before running the bot.")
        print("Refer to SETUP_GUIDE.md for detailed instructions.")
        print("=" * 60)
        sys.exit(1)


if __name__ == '__main__':
    main()

