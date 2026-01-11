# Ticker-Subreddit Configuration

## Overview

This configuration allows the bot to track **subreddit subscriber growth** over time, which is a key signal for stock performance prediction.

## How It Works

The bot will:
1. Track subscriber counts for configured ticker-subreddit pairs
2. Calculate 7-day growth percentages
3. Store historical data in Supabase
4. Use subscriber growth as a signal in trading decisions

## Configuration

Edit `config/ticker_subreddits.py` and add your mappings:

```python
TICKER_SUBREDDITS = {
    'GME': 'GME',                    # GameStop subreddit
    'AMC': 'amcstock',               # AMC Entertainment subreddit
    'TSLA': 'teslainvestorsclub',   # Tesla investor subreddit
    'PLTR': 'PLTR',                  # Palantir subreddit
}
```

## Finding Subreddit Names

1. Go to Reddit and find the ticker's community
2. The subreddit name is in the URL: `reddit.com/r/SUBREDDIT_NAME`
3. Use the exact case-sensitive name from the URL

Examples:
- `reddit.com/r/GME` → Use `'GME'`
- `reddit.com/r/wallstreetbets` → Use `'wallstreetbets'`
- `reddit.com/r/Superstonk` → Use `'Superstonk'` (capital S!)

## What Gets Tracked

For each configured ticker-subreddit pair:
- **Current subscriber count**
- **7-day subscriber count** (historical)
- **Growth percentage** (7-day change)

Example output:
```
GME (r/GME): 429,834 subscribers (+12.5% 7d growth)
AMC (r/amcstock): 556,201 subscribers (+8.3% 7d growth)
```

## Integration with Trading Engine

Strong subscriber growth (e.g., >10% in 7 days) can be used as an additional signal in your trading logic. You can modify `src/engine.py` to factor in subscriber growth when calculating confidence scores.

## Important Notes

⚠️ **Only works for tickers that:**
- Have dedicated subreddits
- Are in the top 20 of ApeWisdom (for efficiency)

💡 **Pro tip:** Focus on meme stocks and stocks with active Reddit communities for best results.

## Example Configurations

### Meme Stocks
```python
TICKER_SUBREDDITS = {
    'GME': 'GME',
    'AMC': 'amcstock',
    'BB': 'BB_Stock',
    'NOK': 'Nokia_stock',
    'BBBY': 'BBBY',
}
```

### Tech Stocks
```python
TICKER_SUBREDDITS = {
    'TSLA': 'teslainvestorsclub',
    'PLTR': 'PLTR',
    'NVDA': 'nvda_stock',
}
```

### Penny Stocks
```python
TICKER_SUBREDDITS = {
    'CLOV': 'CLOV',
    'WISH': 'Wishstock',
    'SDC': 'SmileDirectClub',
}
```

## After Making Changes

1. Commit your changes to Git
2. Push to GitHub
3. The next scheduled run will use your new mappings
4. Check the logs to verify subscriber tracking is working

## Viewing Results

Query your Supabase database:

```sql
SELECT 
    t.symbol,
    rmv.top_posts->'subscriber_data'->>'subscriber_count' as subscribers,
    rmv.top_posts->'subscriber_data'->>'growth_7d_pct' as growth_7d,
    rmv.timestamp
FROM reddit_mention_velocity rmv
JOIN tickers t ON rmv.ticker_id = t.id
WHERE rmv.top_posts->'subscriber_data' IS NOT NULL
ORDER BY rmv.timestamp DESC;
```

