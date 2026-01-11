"""
Validator Module - Checks fundamental health of tickers using Yahoo Finance
"""
import os
import time
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

import yfinance as yf
from supabase import create_client, Client

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class FundamentalValidator:
    """Validates ticker fundamentals using Yahoo Finance data"""
    
    # Default health check thresholds
    MIN_MARKET_CAP = 500_000_000  # $500M minimum
    MAX_DEBT_TO_EQUITY = 2.0  # Maximum debt-to-equity ratio
    MIN_PROFIT_MARGIN = -0.50  # Allow some negative margins but not too extreme
    
    def __init__(self):
        """Initialize Supabase client"""
        supabase_url = os.environ.get('SUPABASE_URL')
        supabase_key = os.environ.get('SUPABASE_KEY')
        
        if not supabase_url or not supabase_key:
            raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set")
        
        self.supabase: Client = create_client(supabase_url, supabase_key)
    
    def fetch_fundamentals(self, symbol: str, max_retries: int = 2) -> Optional[Dict]:
        """
        Fetch fundamental statistics for a ticker from Yahoo Finance
        
        Args:
            symbol: Stock ticker symbol
            max_retries: Maximum number of retry attempts on rate limit
            
        Returns:
            Dictionary of fundamental data or None if failed
        """
        for attempt in range(max_retries):
            try:
                if attempt > 0:
                    wait_time = 20 * (attempt + 1)  # Conservative backoff: 20s, 40s
                    logger.info(f"Retry {attempt}/{max_retries} for {symbol} after {wait_time}s...")
                    time.sleep(wait_time)
                
                logger.info(f"Fetching fundamentals for {symbol}...")
                
                ticker = yf.Ticker(symbol)
                info = ticker.info
            
            # Extract key metrics
            fundamentals = {
                'symbol': symbol,
                'company_name': info.get('longName', info.get('shortName')),
                'industry': info.get('industry', info.get('sector')),
                'market_cap': info.get('marketCap'),
                'short_float_pct': info.get('shortPercentOfFloat', info.get('sharesShort')) or 0,
                'debt_to_equity': info.get('debtToEquity'),
                'revenue_growth': info.get('revenueGrowth'),
                'profit_margin': info.get('profitMargins'),
                'pe_ratio': info.get('trailingPE', info.get('forwardPE')),
                'beta': info.get('beta'),
                'current_price': info.get('currentPrice', info.get('regularMarketPrice')),
                'fifty_two_week_high': info.get('fiftyTwoWeekHigh'),
                'fifty_two_week_low': info.get('fiftyTwoWeekLow'),
                'volume': info.get('volume'),
                'avg_volume': info.get('averageVolume'),
                'raw_data': info  # Store complete response
            }
            
            # Convert percentage values
            if fundamentals['short_float_pct']:
                # Convert to percentage if it's a decimal
                if fundamentals['short_float_pct'] < 1:
                    fundamentals['short_float_pct'] *= 100
            
            if fundamentals['revenue_growth']:
                if fundamentals['revenue_growth'] < 1:
                    fundamentals['revenue_growth'] *= 100
            
            if fundamentals['profit_margin']:
                if fundamentals['profit_margin'] < 1 and fundamentals['profit_margin'] > -1:
                    fundamentals['profit_margin'] *= 100
            
                logger.info(f"✓ Successfully fetched fundamentals for {symbol}")
                logger.debug(f"  Market Cap: ${fundamentals['market_cap']:,}" if fundamentals['market_cap'] else "  Market Cap: N/A")
                logger.debug(f"  P/E Ratio: {fundamentals['pe_ratio']:.2f}" if fundamentals['pe_ratio'] else "  P/E Ratio: N/A")
                
                return fundamentals
                
            except Exception as e:
                error_msg = str(e)
                # Check if it's a rate limit error (429)
                if '429' in error_msg or 'Too Many Requests' in error_msg:
                    if attempt < max_retries - 1:
                        logger.warning(f"⚠ Rate limit hit for {symbol}, will retry...")
                        continue
                    else:
                        logger.error(f"✗ Rate limit exceeded for {symbol} after {max_retries} attempts")
                        return None
                else:
                    logger.error(f"✗ Failed to fetch fundamentals for {symbol}: {e}")
                    return None
        
        # If we exhausted all retries
        logger.error(f"✗ Failed to fetch fundamentals for {symbol} after {max_retries} attempts")
        return None
    
    def check_health(self, fundamentals: Dict) -> Tuple[bool, List[str], float]:
        """
        Check if a ticker passes fundamental health checks
        
        Args:
            fundamentals: Dictionary of fundamental data
            
        Returns:
            Tuple of (is_healthy, reasons, health_score)
        """
        symbol = fundamentals['symbol']
        reasons = []
        health_score = 100.0
        
        # Check 1: Market Cap
        market_cap = fundamentals.get('market_cap')
        if market_cap is None:
            reasons.append("Missing market cap data")
            health_score -= 30
        elif market_cap < self.MIN_MARKET_CAP:
            reasons.append(f"Market cap ${market_cap:,.0f} below minimum ${self.MIN_MARKET_CAP:,.0f}")
            health_score -= 30
        else:
            logger.debug(f"  ✓ Market cap check passed: ${market_cap:,.0f}")
        
        # Check 2: Debt-to-Equity
        debt_to_equity = fundamentals.get('debt_to_equity')
        if debt_to_equity is not None and debt_to_equity > self.MAX_DEBT_TO_EQUITY:
            reasons.append(f"Debt-to-equity {debt_to_equity:.2f} exceeds maximum {self.MAX_DEBT_TO_EQUITY}")
            health_score -= 20
        elif debt_to_equity is not None:
            logger.debug(f"  ✓ Debt-to-equity check passed: {debt_to_equity:.2f}")
        
        # Check 3: Profit Margin
        profit_margin = fundamentals.get('profit_margin')
        if profit_margin is not None and profit_margin < self.MIN_PROFIT_MARGIN:
            reasons.append(f"Profit margin {profit_margin:.2f}% below minimum {self.MIN_PROFIT_MARGIN}%")
            health_score -= 25
        elif profit_margin is not None:
            logger.debug(f"  ✓ Profit margin check passed: {profit_margin:.2f}%")
        
        # Check 4: Data completeness
        critical_fields = ['market_cap', 'current_price', 'company_name']
        missing_fields = [f for f in critical_fields if not fundamentals.get(f)]
        if missing_fields:
            reasons.append(f"Missing critical data: {', '.join(missing_fields)}")
            health_score -= 15 * len(missing_fields)
        
        # Bonus: Revenue growth
        revenue_growth = fundamentals.get('revenue_growth')
        if revenue_growth and revenue_growth > 20:
            health_score += 10
            logger.debug(f"  ✓ Strong revenue growth: {revenue_growth:.2f}%")
        
        # Ensure score is between 0 and 100
        health_score = max(0, min(100, health_score))
        
        is_healthy = health_score >= 60 and len(reasons) <= 1
        
        if is_healthy:
            logger.info(f"✓ {symbol} passed health check (score: {health_score:.1f}/100)")
        else:
            logger.warning(f"✗ {symbol} failed health check (score: {health_score:.1f}/100): {', '.join(reasons)}")
        
        return is_healthy, reasons, health_score
    
    def save_to_supabase(self, fundamentals: Dict) -> bool:
        """
        Save fundamental statistics to Supabase
        
        Args:
            fundamentals: Dictionary of fundamental data
            
        Returns:
            True if successful, False otherwise
        """
        symbol = fundamentals['symbol']
        
        try:
            # Get ticker_id
            ticker_response = self.supabase.table('tickers').select('id').eq('symbol', symbol).execute()
            
            if not ticker_response.data:
                logger.error(f"Ticker {symbol} not found in database")
                return False
            
            ticker_id = ticker_response.data[0]['id']
            
            # Update ticker with company name and industry if available
            if fundamentals.get('company_name') or fundamentals.get('industry'):
                self.supabase.table('tickers').update({
                    'company_name': fundamentals.get('company_name'),
                    'industry': fundamentals.get('industry')
                }).eq('id', ticker_id).execute()
            
            # Insert fundamental stats
            self.supabase.table('fundamental_stats').insert({
                'ticker_id': ticker_id,
                'market_cap': fundamentals.get('market_cap'),
                'short_float_pct': fundamentals.get('short_float_pct'),
                'debt_to_equity': fundamentals.get('debt_to_equity'),
                'revenue_growth': fundamentals.get('revenue_growth'),
                'profit_margin': fundamentals.get('profit_margin'),
                'pe_ratio': fundamentals.get('pe_ratio'),
                'beta': fundamentals.get('beta'),
                'raw_data': fundamentals.get('raw_data', {}),
                'timestamp': datetime.utcnow().isoformat()
            }).execute()
            
            logger.debug(f"Saved fundamentals for {symbol} to Supabase")
            return True
            
        except Exception as e:
            logger.error(f"Error saving fundamentals for {symbol}: {e}")
            return False
    
    def validate_tickers(self, symbols: List[str]) -> Dict[str, Dict]:
        """
        Validate a list of ticker symbols
        
        Args:
            symbols: List of ticker symbols to validate
            
        Returns:
            Dictionary mapping symbol -> validation results
        """
        logger.info("=" * 60)
        logger.info(f"Validating {len(symbols)} tickers...")
        logger.info("=" * 60)
        
        results = {}
        
        for idx, symbol in enumerate(symbols):
            # Conservative rate limiting for 20-minute runtime
            # 4 seconds between each ticker + 15 seconds every 5 tickers
            if idx > 0:
                logger.debug(f"Rate limit pause: 4 seconds... ({idx}/{len(symbols)} completed)")
                time.sleep(4)  # 4 seconds between each ticker
            
            if idx > 0 and idx % 5 == 0:
                logger.info(f"Extended rate limit pause: 15 seconds... ({idx}/{len(symbols)} completed)")
                time.sleep(15)  # 15 seconds every 5 tickers
            
            # Fetch fundamentals
            fundamentals = self.fetch_fundamentals(symbol)
            
            if fundamentals is None:
                results[symbol] = {
                    'valid': False,
                    'fundamentals': None,
                    'health_check': (False, ['Failed to fetch data'], 0)
                }
                continue
            
            # Check health
            is_healthy, reasons, health_score = self.check_health(fundamentals)
            
            # Save to database
            self.save_to_supabase(fundamentals)
            
            results[symbol] = {
                'valid': is_healthy,
                'fundamentals': fundamentals,
                'health_check': (is_healthy, reasons, health_score)
            }
        
        # Summary
        valid_count = sum(1 for r in results.values() if r['valid'])
        logger.info("=" * 60)
        logger.info(f"Validation Complete: {valid_count}/{len(symbols)} tickers passed")
        logger.info("=" * 60)
        
        return results
    
    def validate_from_supabase(self, hours_back: int = 24, max_tickers: int = 50) -> Dict[str, Dict]:
        """
        Validate tickers that have recent sentiment logs in Supabase
        
        Args:
            hours_back: How many hours back to look for tickers
            max_tickers: Maximum number of tickers to validate (most mentioned first)
            
        Returns:
            Dictionary of validation results
        """
        try:
            # Get tickers with recent sentiment logs
            cutoff_time = (datetime.utcnow() - timedelta(hours=hours_back)).isoformat()
            
            sentiment_response = self.supabase.table('sentiment_logs')\
                .select('ticker_id, tickers(symbol), mention_count')\
                .gte('timestamp', cutoff_time)\
                .execute()
            
            if not sentiment_response.data:
                logger.warning("No recent tickers found in sentiment logs")
                return {}
            
            # Count mentions per ticker
            ticker_mentions = {}
            for log in sentiment_response.data:
                if log.get('tickers'):
                    symbol = log['tickers']['symbol']
                    mentions = log.get('mention_count', 0)
                    ticker_mentions[symbol] = ticker_mentions.get(symbol, 0) + mentions
            
            # Sort by mention count and take top N
            sorted_tickers = sorted(
                ticker_mentions.items(),
                key=lambda x: x[1],
                reverse=True
            )[:max_tickers]
            
            symbols = [ticker for ticker, _ in sorted_tickers]
            
            logger.info(f"Found {len(ticker_mentions)} unique tickers, validating top {len(symbols)} by mention count")
            
            return self.validate_tickers(symbols)
            
        except Exception as e:
            logger.error(f"Error validating from Supabase: {e}")
            return {}


if __name__ == '__main__':
    # For testing
    from dotenv import load_dotenv
    load_dotenv()
    
    validator = FundamentalValidator()
    
    # Test with some example tickers
    test_symbols = ['GME', 'AAPL', 'TSLA']
    results = validator.validate_tickers(test_symbols)
    
    print("\n=== VALIDATION RESULTS ===")
    for symbol, data in results.items():
        is_healthy, reasons, score = data['health_check']
        print(f"\n{symbol}: {'✓ PASS' if is_healthy else '✗ FAIL'} (Score: {score:.1f}/100)")
        if not is_healthy and reasons:
            print(f"  Reasons: {', '.join(reasons)}")
        if data['fundamentals']:
            fund = data['fundamentals']
            if fund.get('market_cap'):
                print(f"  Market Cap: ${fund['market_cap']:,.0f}")
            if fund.get('profit_margin'):
                print(f"  Profit Margin: {fund['profit_margin']:.2f}%")

