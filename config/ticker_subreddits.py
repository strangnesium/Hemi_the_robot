"""
Ticker-to-Subreddit Mapping Configuration

Add your ticker symbols and their associated subreddits here.
The bot will track subscriber growth for these subreddits over time.

Format: 'TICKER_SYMBOL': 'subreddit_name'

Example:
    'GME': 'GME',
    'SUPERSTONK': 'Superstonk',
    'AMC': 'amcstock',
"""

TICKER_SUBREDDITS = {
    # Add your mappings below
    # 'GME': 'GME',
    # 'AMC': 'amcstock',
    # 'TSLA': 'teslainvestorsclub',
    # 'PLTR': 'PLTR',
    # 'BB': 'BB_Stock',
    # 'NOK': 'Nokia_stock',
    # 'CLOV': 'CLOV',
    # 'WISH': 'Wishstock',
    # 'SDC': 'SmileDirectClub',
    # 'BBIG': 'BBIG',
}

# You can also create different mapping groups for different strategies
MEME_STOCK_SUBREDDITS = {
    'GME': 'GME',
    'AMC': 'amcstock',
}

TECH_STOCK_SUBREDDITS = {
    'TSLA': 'teslainvestorsclub',
    'PLTR': 'PLTR',
}

# Default: Use the main mapping
# To use a different group, update the import in discovery.py

