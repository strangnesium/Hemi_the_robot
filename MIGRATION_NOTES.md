# 📋 Migration Notes: Google Sheets → Supabase

This document explains how the original `Subreddit_checker_example_code.py` was refactored into the new cloud-native architecture.

## Original Implementation Summary

### What it did:
- Tracked **subreddit subscriber growth** over time
- Stored data in Google Sheets (2 tabs: main tracker + history)
- Calculated weekly, monthly, and 3-month growth rates
- Used PRAW (Reddit API) to fetch subscriber counts
- Ran manually or on a schedule (not automated)

### Limitations:
- ❌ Only tracked subscriber counts (not mentions or sentiment)
- ❌ Google Sheets had rate limits and manual setup
- ❌ No fundamental analysis of stocks
- ❌ No trading signals or flags
- ❌ Single monolithic script (hard to maintain)

---

## New Implementation

### Major Changes

| Feature | Old | New |
|---------|-----|-----|
| **Data Storage** | Google Sheets | Supabase (PostgreSQL) |
| **Tracking Method** | Subreddit subscribers | Reddit mentions + ApeWisdom |
| **Architecture** | Single script | Modular (discovery, validator, engine) |
| **Automation** | Manual/Cron | GitHub Actions |
| **Credentials** | Service account JSON | Environment variables |
| **Data Analysis** | Growth percentages | Velocity + Fundamentals + Confidence scores |
| **Output** | Spreadsheet cells | Trading flags in database |

### Code Mapping

#### 1. Reddit API Setup
**Old:**
```python
reddit = praw.Reddit(
    client_id="PCz5A3g4wDn_N-UWlPzuiA",
    client_secret="qziRCLQW9BJ2N8odnob7Wlk1N0BVjw",
    user_agent="sub_checker_1.0"
)
```

**New:**
```python
# In src/discovery.py
self.reddit = praw.Reddit(
    client_id=os.environ.get('REDDIT_CLIENT_ID'),
    client_secret=os.environ.get('REDDIT_CLIENT_SECRET'),
    user_agent=os.environ.get('REDDIT_USER_AGENT')
)
```
✅ **Improvement**: Credentials from environment variables (secure, no hardcoding)

---

#### 2. Data Fetching

**Old:**
```python
def safe_fetch_subscribers(subreddit_name, retries=0):
    subreddit = reddit.subreddit(subreddit_name)
    return subreddit.subscribers
```

**New:**
```python
# In src/discovery.py
def track_reddit_mentions(self, target_tickers, hours_back=24):
    # Searches for $TICKER mentions in posts and comments
    # Tracks mention frequency, velocity, and top posts
    # Much more comprehensive than just subscriber counts
```
✅ **Improvement**: Tracks actual mentions of tickers, not just subscriber growth

---

#### 3. Historical Data

**Old:**
```python
# Manually stored in "Subscriber History" sheet
history_data = history_sheet.get_all_values()
prev_week_count = get_historical_count(history_data, subreddit_name, one_week_ago)
```

**New:**
```python
# Automatically stored in Supabase with timestamps
# In src/discovery.py
def _get_previous_mention_count(self, ticker, hours_back):
    velocity_response = self.supabase.table('reddit_mention_velocity')\
        .select('mention_count_24h')\
        .gte('timestamp', cutoff_time)\
        .order('timestamp', desc=True)
```
✅ **Improvement**: Automatic time-series storage with SQL queries

---

#### 4. Growth Calculation

**Old:**
```python
def calculate_growth(current, previous):
    return ((current - previous) / previous * 100) if previous else 0

weekly_growth = calculate_growth(subscriber_count, prev_week_count)
```

**New:**
```python
# In src/discovery.py - Velocity calculation
previous_count = self._get_previous_mention_count(ticker, hours_back)
if previous_count > 0:
    velocity_change = ((data['mention_count_24h'] - previous_count) / previous_count) * 100
```
✅ **Improvement**: Same concept but applied to mentions, not subscribers

---

#### 5. Data Storage

**Old:**
```python
# Batch update to Google Sheets
batch_updates.append({
    "range": f"D{row_number}:K{row_number}",
    "values": [[current_date, subscriber_count, prev_week_count, ...]]
})
worksheet.batch_update(batch_updates)
```

**New:**
```python
# In src/discovery.py - Insert to Supabase
self.supabase.table('reddit_mention_velocity').insert({
    'ticker_id': ticker_id,
    'subreddit': subreddit,
    'mention_count_24h': count,
    'velocity_change_pct': data['velocity_change_pct'],
    'timestamp': datetime.utcnow().isoformat()
}).execute()
```
✅ **Improvement**: Proper database with relationships, indexes, and SQL capabilities

---

## New Features Added

### 1. ApeWisdom Integration
```python
# src/discovery.py - scrape_apewisdom()
# Scrapes top 50 trending tickers from ApeWisdom
```
**Purpose**: Discover which stocks are gaining traction across multiple platforms

### 2. Fundamental Validation
```python
# src/validator.py - FundamentalValidator
# Uses yfinance to check:
# - Market cap (must be > $500M)
# - Debt-to-equity (< 2.0)
# - Profit margins (> -50%)
```
**Purpose**: Filter out unhealthy companies before trading

### 3. Trading Engine
```python
# src/engine.py - TradingEngine
# Evaluates tickers based on:
# - ApeWisdom rank (top 20)
# - Reddit velocity (> 20% increase)
# - Fundamental health score (> 60/100)
# - Generates confidence scores (0-100)
```
**Purpose**: Automated trading signal generation

### 4. GitHub Actions Automation
```yaml
# .github/workflows/daily_bot.yml
# Runs every day at 8:00 AM EST
# No manual intervention needed
```
**Purpose**: Fully automated pipeline

---

## Database Schema Comparison

### Old (Google Sheets)

**Sheet 1 - Main Tracker:**
| Ticker | Company | Subreddit URL | Date | Subscribers | Prev Week | Weekly Growth | ... |
|--------|---------|---------------|------|-------------|-----------|---------------|-----|
| GME | GameStop | ... | 2024-01-15 | 15,234 | 14,987 | 1.65% | ... |

**Sheet 2 - Subscriber History:**
| Subreddit | Date | Subscriber Count |
|-----------|------|------------------|
| GME | 2024-01-15 | 15,234 |

### New (Supabase)

**5 Normalized Tables:**

1. **tickers** - Master ticker list
   - id (UUID, PK)
   - symbol (unique)
   - company_name
   - industry

2. **sentiment_logs** - Social media mentions
   - ticker_id (FK)
   - source (APEWISDOM, REDDIT)
   - mention_count
   - upvotes
   - rank
   - timestamp

3. **fundamental_stats** - Yahoo Finance data
   - ticker_id (FK)
   - market_cap
   - profit_margin
   - debt_to_equity
   - timestamp

4. **trading_flags** - Action items
   - ticker_id (FK)
   - confidence_score
   - status (OPEN/CLOSED)
   - rationale
   - metadata (JSONB)

5. **reddit_mention_velocity** - Mention tracking
   - ticker_id (FK)
   - subreddit
   - mention_count_24h
   - velocity_change_pct
   - top_posts (JSONB)
   - timestamp

---

## What Was Kept

✅ **PRAW (Reddit API)** - Still using the same library
✅ **Rate limiting logic** - Exponential backoff preserved
✅ **Time-based analysis** - Still comparing historical periods
✅ **Growth/velocity calculations** - Same math, different metric

## What Was Removed

❌ **Google Sheets API** - Replaced with Supabase
❌ **Service account JSON** - Replaced with env vars
❌ **Subscriber tracking** - Replaced with mention tracking
❌ **Manual execution** - Replaced with GitHub Actions

---

## Migration Checklist

If you're migrating from the old system:

- [ ] Export your ticker list from Google Sheets
- [ ] Insert tickers into Supabase `tickers` table
- [ ] Set up new environment variables (no more JSON files)
- [ ] Update Reddit API credentials (reuse same app)
- [ ] Run `test_setup.py` to verify new setup
- [ ] Run `python main.py` for first full pipeline execution
- [ ] Configure GitHub Actions for automation
- [ ] Archive old Google Sheets (keep for reference)

---

## Performance Comparison

| Metric | Old | New |
|--------|-----|-----|
| Data fetch time | ~2-3 min | ~3-5 min (more data) |
| Storage limits | 5M cells (Sheets) | 500MB free (Supabase) |
| Query speed | Slow (spreadsheet) | Fast (indexed SQL) |
| Scalability | Limited | High |
| Automation | Manual/Cron | GitHub Actions |
| Maintenance | High | Low (modular) |

---

## Key Improvements

1. **No More Rate Limits** - Supabase can handle millions of rows
2. **Better Analytics** - SQL queries vs spreadsheet formulas
3. **More Data Points** - Sentiment + Fundamentals + Velocity
4. **Automated Pipeline** - Set it and forget it
5. **Professional Stack** - Production-ready architecture
6. **Version Control** - Code in Git, not spreadsheets
7. **Secure Credentials** - Environment variables, not hardcoded

---

## Still Have Questions?

- See `README.md` for full documentation
- See `SETUP_GUIDE.md` for step-by-step setup
- Check `database/sample_queries.sql` for example queries
- Run `test_setup.py` to verify your configuration

**Your old data is safe!** Keep your Google Sheet as a backup while you test the new system.

