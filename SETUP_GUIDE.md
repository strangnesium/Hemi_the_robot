# 🚀 Quick Setup Guide

This guide will help you get your trading bot up and running in 15 minutes.

## Prerequisites

- Python 3.9 or higher
- Git
- A Supabase account (free tier is fine)
- A Reddit account

---

## Step-by-Step Setup

### 1️⃣ Supabase Database Setup (5 min)

1. **Create a Supabase Project**
   - Go to [supabase.com](https://supabase.com)
   - Click "New Project"
   - Choose a name and strong password
   - Select a region close to you
   - Wait for the project to be ready (~2 min)

2. **Get Your Credentials**
   - Click on "Settings" (gear icon) → "API"
   - Copy the **Project URL** (looks like: `https://xxxxx.supabase.co`)
   - Copy the **anon/public** key (the long string under "Project API keys")

3. **Create Database Tables**
   - Click on "SQL Editor" in the sidebar
   - Open `database/schema.sql` from this project
   - Copy the entire contents
   - Paste into the Supabase SQL Editor
   - Click "Run" (or press Ctrl/Cmd + Enter)
   - You should see "Success. No rows returned"

4. **Verify Tables Were Created**
   - Click on "Table Editor" in the sidebar
   - You should see 5 tables: `tickers`, `sentiment_logs`, `fundamental_stats`, `trading_flags`, `reddit_mention_velocity`

---

### 2️⃣ Reddit API Setup (3 min)

1. **Create a Reddit App**
   - Go to https://www.reddit.com/prefs/apps
   - Scroll to the bottom
   - Click "Create app" or "Create another app"

2. **Fill in the Form**
   - **Name**: `Trading Bot` (or anything you like)
   - **App type**: Select "script"
   - **Description**: (optional) `Sentiment analysis bot`
   - **About URL**: (leave blank)
   - **Redirect URI**: `http://localhost:8080` (required but not used)
   - Click "Create app"

3. **Get Your Credentials**
   - Under your app name, you'll see a string of characters (e.g., `PCz5A3g4wDn_N-U...`) - this is your **CLIENT_ID**
   - The line that says "secret" has your **CLIENT_SECRET**
   - Write these down!

---

### 3️⃣ Local Development Setup (5 min)

1. **Clone and Setup Virtual Environment**
   ```bash
   cd Hemi_the_robot
   python3 -m venv venv
   source venv/bin/activate  # On Windows: venv\Scripts\activate
   ```

2. **Install Dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Create Configuration File**
   ```bash
   cp env.example .env
   ```

4. **Edit .env File**
   ```bash
   # Open with your preferred editor
   nano .env
   # or
   code .env
   ```

   Fill in your credentials:
   ```
   SUPABASE_URL=https://xxxxx.supabase.co
   SUPABASE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
   
   REDDIT_CLIENT_ID=PCz5A3g4wDn_N-U...
   REDDIT_CLIENT_SECRET=qziRCLQW9BJ2N8...
   REDDIT_USER_AGENT=sentiment_bot_v2.0
   ```

5. **Test the Setup**
   ```bash
   python main.py
   ```

   You should see:
   ```
   ================================================================================
   TRADING BOT PIPELINE STARTED
   Timestamp: 2024-XX-XXTXX:XX:XX
   ================================================================================
   ```

---

### 4️⃣ GitHub Actions Setup (2 min)

1. **Push to GitHub**
   ```bash
   git add .
   git commit -m "Initial trading bot setup"
   git push origin main
   ```

2. **Add GitHub Secrets**
   - Go to your repository on GitHub
   - Click "Settings" → "Secrets and variables" → "Actions"
   - Click "New repository secret"
   - Add each of these secrets:

   | Name | Value |
   |------|-------|
   | `SUPABASE_URL` | Your Supabase project URL |
   | `SUPABASE_KEY` | Your Supabase anon key |
   | `REDDIT_CLIENT_ID` | Your Reddit client ID |
   | `REDDIT_CLIENT_SECRET` | Your Reddit client secret |
   | `REDDIT_USER_AGENT` | `sentiment_bot_v2.0` |

3. **Test GitHub Action**
   - Go to "Actions" tab in your repository
   - Click on "Daily Trading Bot"
   - Click "Run workflow" → "Run workflow"
   - Wait for it to complete (~2-5 minutes)
   - Check logs for any errors

---

## ✅ Verification Checklist

- [ ] Supabase project created with 5 tables
- [ ] Reddit app created with client ID and secret
- [ ] Local `.env` file configured
- [ ] `python main.py` runs without errors
- [ ] GitHub secrets configured
- [ ] GitHub Action runs successfully

---

## 🐛 Troubleshooting

### "Missing required environment variables"
- Check that your `.env` file exists and is in the project root
- Verify all variables are set (no empty values)
- Make sure there are no spaces around the `=` sign

### "Failed to scrape ApeWisdom"
- ApeWisdom might be down or HTML structure changed
- The bot will continue with Reddit data only
- Check if you can access https://apewisdom.io/ in your browser

### "Reddit API rate limit exceeded"
- Wait 5-10 minutes before trying again
- The bot has built-in retry logic with backoff
- Consider reducing the number of subreddits in `discovery.py`

### "Ticker not found in database"
- Make sure the schema was properly created
- Run the discovery phase first: `python src/discovery.py`
- Check Supabase Table Editor to see if tickers exist

### GitHub Action fails
- Check that all 5 secrets are properly set
- Look at the workflow logs for specific error messages
- Verify your Supabase project is not paused (free tier)

---

## 📞 Need Help?

- Check the main [README.md](README.md) for detailed documentation
- Review the logs in `trading_bot.log`
- Open an issue on GitHub

---

## 🎉 You're Done!

Your trading bot is now set up and will run automatically every day at 8:00 AM EST.

To view your results:
1. Log into Supabase
2. Go to "Table Editor"
3. Click on `trading_flags` to see flagged stocks
4. Or use the SQL Editor with the example queries in README.md

**Happy Trading!** 🚀📈

