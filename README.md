# 🤖 Sentiment-to-Value Trading Bot

A robust, cloud-native trading bot that identifies trending stocks based on social media sentiment and validates them with fundamental analysis.

## 📊 Overview

This bot follows a "Sentiment-to-Value" strategy:
1. **Discovery**: Tracks trending stocks on ApeWisdom and Reddit
2. **Validation**: Verifies fundamental health using Yahoo Finance
3. **Engine**: Generates trading flags for high-confidence opportunities

### Key Features

- ✅ **Cloud-Native**: Built for GitHub Actions + Supabase (no local dependencies)
- ✅ **Reddit Mention Velocity**: Tracks mention frequency and growth rate
- ✅ **Fundamental Validation**: Filters by market cap, debt, and profitability
- ✅ **Automated Daily Runs**: Scheduled via GitHub Actions at 8:00 AM EST
- ✅ **Confidence Scoring**: Each trading flag includes a confidence score

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    GitHub Actions (Scheduler)               │
│                  Runs daily at 8:00 AM EST                 │
└────────────────────┬────────────────────────────────────────┘
                     │
                     ▼
┌─────────────────────────────────────────────────────────────┐
│                      main.py (Orchestrator)                 │
└────────────────────┬────────────────────────────────────────┘
                     │
        ┌────────────┼────────────┐
        │            │            │
        ▼            ▼            ▼
┌──────────┐  ┌──────────┐  ┌──────────┐
│Discovery │  │Validator │  │  Engine  │
│          │  │          │  │          │
│ ApeWisdom│  │ Yahoo    │  │ Trading  │
│ Reddit   │  │ Finance  │  │ Flags    │
└─────┬────┘  └─────┬────┘  └─────┬────┘
      │             │              │
      └─────────────┼──────────────┘
                    ▼
        ┌───────────────────────┐
        │  Supabase (Postgres)  │
        │  - tickers            │
        │  - sentiment_logs     │
        │  - fundamental_stats  │
        │  - trading_flags      │
        └───────────────────────┘
```

## 📦 Project Structure

```
Hemi_the_robot/
├── main.py                          # Main orchestrator
├── requirements.txt                 # Python dependencies
├── env.example                      # Environment variables template
├── README.md                        # This file
│
├── src/                             # Core modules
│   ├── __init__.py
│   ├── discovery.py                 # ApeWisdom scraper + Reddit tracker
│   ├── validator.py                 # Yahoo Finance fundamentals
│   └── engine.py                    # Trading flag logic
│
├── database/                        # Database schema
│   └── schema.sql                   # Supabase table definitions
│
└── .github/
    └── workflows/
        └── daily_bot.yml            # GitHub Actions workflow
```

## 🚀 Setup Instructions

### 1. Database Setup (Supabase)

1. Create a new project at [supabase.com](https://supabase.com)
2. Copy your project URL and anon key
3. Run the SQL schema:
   - Open your Supabase SQL Editor
   - Copy contents of `database/schema.sql`
   - Execute the query

### 2. Reddit API Setup

1. Go to https://www.reddit.com/prefs/apps
2. Create a new app (select "script" type)
3. Note your `client_id` and `client_secret`

### 3. Local Development Setup

```bash
# Clone the repository
git clone <your-repo-url>
cd Hemi_the_robot

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Create .env file
cp env.example .env

# Edit .env with your credentials
nano .env
```

### 4. GitHub Actions Setup

1. Go to your repository → Settings → Secrets and variables → Actions
2. Add the following secrets:
   - `SUPABASE_URL`: Your Supabase project URL
   - `SUPABASE_KEY`: Your Supabase anon key
   - `REDDIT_CLIENT_ID`: Your Reddit app client ID
   - `REDDIT_CLIENT_SECRET`: Your Reddit app client secret
   - `REDDIT_USER_AGENT`: Something like `sentiment_bot_v2.0`

### 5. Test Locally

```bash
# Run the complete pipeline
python main.py

# Or test individual modules
python src/discovery.py
python src/validator.py
python src/engine.py
```

## 📋 Database Schema

### Tables

- **tickers**: Master list of stock symbols
- **sentiment_logs**: Social media mentions (ApeWisdom, Reddit)
- **fundamental_stats**: Yahoo Finance data (market cap, P/E, margins)
- **trading_flags**: Trading signals with confidence scores
- **reddit_mention_velocity**: Reddit mention tracking over time

### Views

- **latest_ticker_data**: Aggregated view of latest data for each ticker

## 🎯 Trading Logic

A ticker is flagged for trading if:

1. ✅ **Top 20 on ApeWisdom** (trending)
2. ✅ **Reddit mention velocity > +20%** (growing interest)
3. ✅ **Fundamental health score ≥ 60/100**
   - Market cap > $500M
   - Debt-to-Equity < 2.0
   - Profit margin > -50%

### Confidence Score Calculation

- **ApeWisdom Rank** (30 points): Top 5 = 30pts, Top 10 = 25pts, Top 20 = 20pts
- **Reddit Velocity** (30 points): >100% = 30pts, >50% = 25pts, >20% = 20pts
- **Fundamental Health** (25 points): Based on health score
- **Mention Volume** (15 points): >1000 = 15pts, >500 = 12pts, >100 = 10pts

Minimum confidence threshold: **70/100**

## 📊 Usage

### Manual Run

```bash
python main.py
```

### Scheduled Run (GitHub Actions)

The bot runs automatically every day at 8:00 AM EST via GitHub Actions.

### View Results

Query your Supabase database:

```sql
-- Get all open trading flags
SELECT 
    t.symbol,
    t.company_name,
    tf.confidence_score,
    tf.entry_price,
    tf.rationale,
    tf.created_at
FROM trading_flags tf
JOIN tickers t ON tf.ticker_id = t.id
WHERE tf.status = 'OPEN'
ORDER BY tf.confidence_score DESC;

-- View latest ticker data
SELECT * FROM latest_ticker_data
ORDER BY apewisdom_rank ASC;
```

## 🔧 Configuration

### Environment Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `SUPABASE_URL` | Your Supabase project URL | ✅ |
| `SUPABASE_KEY` | Your Supabase anon key | ✅ |
| `REDDIT_CLIENT_ID` | Reddit app client ID | ✅ |
| `REDDIT_CLIENT_SECRET` | Reddit app client secret | ✅ |
| `REDDIT_USER_AGENT` | User agent string | ✅ |

### Thresholds (Configurable in `src/engine.py`)

```python
APEWISDOM_TOP_N = 20                  # Top N tickers to consider
REDDIT_VELOCITY_THRESHOLD = 20.0      # Minimum velocity increase (%)
MIN_HEALTH_SCORE = 60.0               # Minimum fundamental health
MIN_CONFIDENCE_SCORE = 70.0           # Minimum confidence to flag
```

## 📈 Monitoring

### Logs

- Local: `trading_bot.log`
- GitHub Actions: Uploaded as artifacts (retained 30 days)

### Alerts

Failed pipeline runs automatically create GitHub Issues with the label `bot-failure`.

## 🔄 Migration from Google Sheets

The original `Subreddit_checker_example_code.py` has been refactored:

- ❌ Google Sheets → ✅ Supabase (Postgres)
- ❌ Subreddit subscriber counts → ✅ Reddit mention velocity
- ❌ Manual tracking → ✅ Automated GitHub Actions
- ❌ Single script → ✅ Modular architecture

## 📝 TODO / Roadmap

- [ ] Add Twitter/X sentiment tracking
- [ ] Implement email/Discord notifications
- [ ] Add backtesting framework
- [ ] Build dashboard for visualization
- [ ] Add paper trading integration
- [ ] Implement automated position management

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch (`git checkout -b feature/amazing-feature`)
3. Commit your changes (`git commit -m 'Add amazing feature'`)
4. Push to the branch (`git push origin feature/amazing-feature`)
5. Open a Pull Request

## ⚠️ Disclaimer

This bot is for educational and informational purposes only. It does not constitute financial advice. Always do your own research before making investment decisions. Past performance does not guarantee future results.

## 📄 License

MIT License - See LICENSE file for details

## 🙏 Acknowledgments

- Data sources: ApeWisdom, Reddit, Yahoo Finance
- Infrastructure: GitHub Actions, Supabase
- Built with: Python, PRAW, yfinance, BeautifulSoup

---

**Made with ❤️ for the trading community**

