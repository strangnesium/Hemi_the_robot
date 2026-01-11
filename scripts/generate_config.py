#!/usr/bin/env python3
"""
Script to generate ticker_subreddits.py from CSV file
"""
import csv
import os
from pathlib import Path

def parse_subreddit_from_url(url):
    """Extract subreddit name from Reddit URL"""
    # URL format: https://reddit.com/r/SUBREDDIT_NAME
    if '/r/' in url:
        subreddit = url.split('/r/')[-1].strip()
        # Remove trailing slashes
        subreddit = subreddit.rstrip('/')
        return subreddit
    return None

def generate_ticker_subreddits_config(csv_path, output_path):
    """Parse CSV and generate Python config file"""
    
    ticker_mappings = {}
    skipped = []
    
    print(f"Reading {csv_path}...")
    
    with open(csv_path, 'r', encoding='utf-8') as f:
        reader = csv.DictReader(f)
        
        for row in reader:
            ticker = row.get('Ticker', '').strip()
            subreddit_url = row.get('Subreddit URL', '').strip()
            
            if not ticker or not subreddit_url:
                continue
            
            subreddit = parse_subreddit_from_url(subreddit_url)
            
            if subreddit:
                ticker_mappings[ticker] = subreddit
            else:
                skipped.append(f"{ticker} - Invalid URL: {subreddit_url}")
    
    print(f"✓ Parsed {len(ticker_mappings)} ticker-subreddit mappings")
    if skipped:
        print(f"⚠ Skipped {len(skipped)} entries with invalid URLs")
    
    # Generate the Python config file
    print(f"\nGenerating {output_path}...")
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write('"""\n')
        f.write('Ticker-to-Subreddit Mapping Configuration\n')
        f.write('Auto-generated from subreddits & stock tickers.csv\n')
        f.write('\n')
        f.write(f'Total mappings: {len(ticker_mappings)}\n')
        f.write('"""\n\n')
        
        f.write('# Main ticker-subreddit dictionary\n')
        f.write('TICKER_SUBREDDITS = {\n')
        
        # Sort by ticker for easier reading
        for ticker in sorted(ticker_mappings.keys()):
            subreddit = ticker_mappings[ticker]
            f.write(f"    '{ticker}': '{subreddit}',\n")
        
        f.write('}\n')
        
        # Add some useful subsets
        f.write('\n')
        f.write('# Popular meme stocks (examples - add more as needed)\n')
        f.write('MEME_STOCKS = {\n')
        meme_tickers = ['GME', 'AMC', 'BB', 'NOK', 'BBBY', 'PLTR', 'WISH', 'CLOV', 'SDC']
        for ticker in meme_tickers:
            if ticker in ticker_mappings:
                f.write(f"    '{ticker}': '{ticker_mappings[ticker]}',\n")
        f.write('}\n')
        
        f.write('\n')
        f.write('# Tech stocks (examples - add more as needed)\n')
        f.write('TECH_STOCKS = {\n')
        tech_tickers = ['TSLA', 'NVDA', 'AMD', 'AAPL', 'MSFT', 'GOOGL', 'META']
        for ticker in tech_tickers:
            if ticker in ticker_mappings:
                f.write(f"    '{ticker}': '{ticker_mappings[ticker]}',\n")
        f.write('}\n')
        
        f.write('\n')
        f.write('# Note: The bot will only track subreddits for tickers in the top 20 of ApeWisdom\n')
        f.write('# This ensures efficiency and focuses on currently trending stocks\n')
    
    print(f"✓ Generated config with {len(ticker_mappings)} mappings")
    print(f"\n📁 Config file: {output_path}")
    
    return len(ticker_mappings), len(skipped)

if __name__ == '__main__':
    # Get paths
    project_root = Path(__file__).parent.parent
    csv_path = project_root / 'subreddits & stock tickers.csv'
    output_path = project_root / 'config' / 'ticker_subreddits.py'
    
    if not csv_path.exists():
        print(f"❌ CSV file not found: {csv_path}")
        exit(1)
    
    # Generate config
    total, skipped = generate_ticker_subreddits_config(csv_path, output_path)
    
    print("\n" + "=" * 60)
    print("✅ Configuration generated successfully!")
    print("=" * 60)
    print(f"Total mappings: {total}")
    print(f"Skipped: {skipped}")
    print("\nNext steps:")
    print("1. Review the generated config/ticker_subreddits.py")
    print("2. Commit and push to GitHub")
    print("3. Run the bot to start tracking subscriber growth!")

