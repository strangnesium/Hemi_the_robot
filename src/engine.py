"""
Engine Module - Trading flag decision logic
"""
import os
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple

from supabase import create_client, Client

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class TradingEngine:
    """
    Core trading logic engine - decides when to flag tickers for trading
    """
    
    # Trading thresholds
    APEWISDOM_TOP_N = 20  # Must be in top 20 on ApeWisdom
    REDDIT_VELOCITY_THRESHOLD = 20.0  # Must have >20% increase in mention velocity
    MIN_HEALTH_SCORE = 60.0  # Minimum fundamental health score
    MIN_CONFIDENCE_SCORE = 70.0  # Minimum confidence to create a flag
    
    def __init__(self):
        """Initialize Supabase client"""
        supabase_url = os.environ.get('SUPABASE_URL')
        supabase_key = os.environ.get('SUPABASE_KEY')
        
        if not supabase_url or not supabase_key:
            raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set")
        
        self.supabase: Client = create_client(supabase_url, supabase_key)
    
    def get_recent_data(self, hours_back: int = 24) -> Dict[str, Dict]:
        """
        Retrieve recent sentiment, velocity, and fundamental data from Supabase
        
        Args:
            hours_back: How many hours back to look
            
        Returns:
            Dictionary mapping ticker symbol -> aggregated data
        """
        logger.info(f"Retrieving data from the last {hours_back} hours...")
        
        cutoff_time = (datetime.utcnow() - timedelta(hours=hours_back)).isoformat()
        ticker_data = {}
        
        try:
            # Get all tickers
            tickers_response = self.supabase.table('tickers').select('id, symbol, company_name').execute()
            
            for ticker in tickers_response.data:
                symbol = ticker['symbol']
                ticker_id = ticker['id']
                
                ticker_data[symbol] = {
                    'ticker_id': ticker_id,
                    'company_name': ticker['company_name'],
                    'apewisdom_rank': None,
                    'apewisdom_mentions': 0,
                    'reddit_mentions_24h': 0,
                    'reddit_velocity_pct': 0,
                    'market_cap': None,
                    'health_score': 0,
                    'current_price': None
                }
                
                # Get latest ApeWisdom sentiment
                apewisdom_response = self.supabase.table('sentiment_logs')\
                    .select('rank, mention_count')\
                    .eq('ticker_id', ticker_id)\
                    .eq('source', 'APEWISDOM')\
                    .gte('timestamp', cutoff_time)\
                    .order('timestamp', desc=True)\
                    .limit(1)\
                    .execute()
                
                if apewisdom_response.data:
                    ape_data = apewisdom_response.data[0]
                    ticker_data[symbol]['apewisdom_rank'] = ape_data.get('rank')
                    ticker_data[symbol]['apewisdom_mentions'] = ape_data.get('mention_count', 0)
                
                # Get latest Reddit velocity
                velocity_response = self.supabase.table('reddit_mention_velocity')\
                    .select('mention_count_24h, velocity_change_pct')\
                    .eq('ticker_id', ticker_id)\
                    .gte('timestamp', cutoff_time)\
                    .order('timestamp', desc=True)\
                    .limit(1)\
                    .execute()
                
                if velocity_response.data:
                    # Sum mentions across subreddits
                    for record in velocity_response.data:
                        ticker_data[symbol]['reddit_mentions_24h'] += record.get('mention_count_24h', 0)
                        # Use the highest velocity
                        ticker_data[symbol]['reddit_velocity_pct'] = max(
                            ticker_data[symbol]['reddit_velocity_pct'],
                            record.get('velocity_change_pct', 0)
                        )
                
                # Get latest fundamentals
                fundamentals_response = self.supabase.table('fundamental_stats')\
                    .select('market_cap, profit_margin, debt_to_equity, raw_data')\
                    .eq('ticker_id', ticker_id)\
                    .order('timestamp', desc=True)\
                    .limit(1)\
                    .execute()
                
                if fundamentals_response.data:
                    fund_data = fundamentals_response.data[0]
                    ticker_data[symbol]['market_cap'] = fund_data.get('market_cap')
                    
                    # Calculate health score (simplified version)
                    health_score = 100
                    
                    # Market cap check
                    if not fund_data.get('market_cap') or fund_data['market_cap'] < 500_000_000:
                        health_score -= 30
                    
                    # Debt check
                    debt_to_equity = fund_data.get('debt_to_equity')
                    if debt_to_equity and debt_to_equity > 2.0:
                        health_score -= 20
                    
                    # Profit margin check
                    profit_margin = fund_data.get('profit_margin')
                    if profit_margin and profit_margin < -50:
                        health_score -= 25
                    
                    ticker_data[symbol]['health_score'] = max(0, health_score)
                    
                    # Extract current price from raw_data
                    raw_data = fund_data.get('raw_data', {})
                    ticker_data[symbol]['current_price'] = raw_data.get('currentPrice') or raw_data.get('regularMarketPrice')
            
            # Filter out tickers with no recent data
            ticker_data = {
                symbol: data 
                for symbol, data in ticker_data.items() 
                if data['apewisdom_rank'] is not None or data['reddit_mentions_24h'] > 0
            }
            
            logger.info(f"Retrieved data for {len(ticker_data)} tickers")
            return ticker_data
            
        except Exception as e:
            logger.error(f"Error retrieving recent data: {e}")
            return {}
    
    def calculate_confidence_score(self, ticker_data: Dict) -> Tuple[float, Dict]:
        """
        Calculate confidence score for a trading signal
        
        Args:
            ticker_data: Dictionary of ticker metrics
            
        Returns:
            Tuple of (confidence_score, scoring_breakdown)
        """
        score = 0.0
        breakdown = {}
        
        # Factor 1: ApeWisdom Rank (30 points)
        if ticker_data['apewisdom_rank']:
            if ticker_data['apewisdom_rank'] <= 5:
                rank_score = 30
            elif ticker_data['apewisdom_rank'] <= 10:
                rank_score = 25
            elif ticker_data['apewisdom_rank'] <= 20:
                rank_score = 20
            else:
                rank_score = 10
            score += rank_score
            breakdown['apewisdom_rank'] = rank_score
        
        # Factor 2: Reddit Velocity (30 points)
        velocity = ticker_data['reddit_velocity_pct']
        if velocity >= 100:
            velocity_score = 30
        elif velocity >= 50:
            velocity_score = 25
        elif velocity >= 20:
            velocity_score = 20
        else:
            velocity_score = 10 * (velocity / 20)
        score += velocity_score
        breakdown['reddit_velocity'] = velocity_score
        
        # Factor 3: Fundamental Health (25 points)
        health_score = ticker_data['health_score']
        health_contribution = (health_score / 100) * 25
        score += health_contribution
        breakdown['fundamental_health'] = health_contribution
        
        # Factor 4: Mention Volume (15 points)
        total_mentions = ticker_data['apewisdom_mentions'] + ticker_data['reddit_mentions_24h']
        if total_mentions >= 1000:
            mention_score = 15
        elif total_mentions >= 500:
            mention_score = 12
        elif total_mentions >= 100:
            mention_score = 10
        else:
            mention_score = 5
        score += mention_score
        breakdown['mention_volume'] = mention_score
        
        return round(score, 2), breakdown
    
    def evaluate_ticker(self, symbol: str, ticker_data: Dict) -> Optional[Dict]:
        """
        Evaluate if a ticker should be flagged for trading
        
        Args:
            symbol: Ticker symbol
            ticker_data: Dictionary of ticker metrics
            
        Returns:
            Flag data if ticker passes criteria, None otherwise
        """
        logger.info(f"\nEvaluating {symbol}...")
        
        # Rule 1: Must be in top 20 on ApeWisdom
        if not ticker_data['apewisdom_rank'] or ticker_data['apewisdom_rank'] > self.APEWISDOM_TOP_N:
            logger.debug(f"  ✗ Not in top {self.APEWISDOM_TOP_N} on ApeWisdom (rank: {ticker_data['apewisdom_rank']})")
            return None
        
        logger.debug(f"  ✓ ApeWisdom rank: {ticker_data['apewisdom_rank']}")
        
        # Rule 2: Reddit mention velocity must be increasing
        if ticker_data['reddit_velocity_pct'] < self.REDDIT_VELOCITY_THRESHOLD:
            logger.debug(f"  ✗ Reddit velocity {ticker_data['reddit_velocity_pct']:.1f}% below threshold {self.REDDIT_VELOCITY_THRESHOLD}%")
            return None
        
        logger.debug(f"  ✓ Reddit velocity: {ticker_data['reddit_velocity_pct']:+.1f}%")
        
        # Rule 3: Must pass fundamental health check
        if ticker_data['health_score'] < self.MIN_HEALTH_SCORE:
            logger.debug(f"  ✗ Health score {ticker_data['health_score']:.1f} below minimum {self.MIN_HEALTH_SCORE}")
            return None
        
        logger.debug(f"  ✓ Health score: {ticker_data['health_score']:.1f}/100")
        
        # Calculate confidence score
        confidence_score, breakdown = self.calculate_confidence_score(ticker_data)
        
        logger.debug(f"  Confidence score: {confidence_score:.1f}/100")
        logger.debug(f"    Breakdown: {breakdown}")
        
        # Only create flag if confidence is high enough
        if confidence_score < self.MIN_CONFIDENCE_SCORE:
            logger.info(f"  ✗ Confidence {confidence_score:.1f} below minimum {self.MIN_CONFIDENCE_SCORE}")
            return None
        
        # Build rationale
        rationale = (
            f"ApeWisdom Rank #{ticker_data['apewisdom_rank']} with {ticker_data['apewisdom_mentions']} mentions. "
            f"Reddit velocity: {ticker_data['reddit_velocity_pct']:+.1f}% ({ticker_data['reddit_mentions_24h']} mentions in 24h). "
            f"Fundamental health score: {ticker_data['health_score']:.1f}/100."
        )
        
        flag_data = {
            'ticker_id': ticker_data['ticker_id'],
            'flag_type': 'BUY',
            'entry_price': ticker_data['current_price'],
            'confidence_score': confidence_score,
            'status': 'OPEN',
            'rationale': rationale,
            'metadata': {
                'apewisdom_rank': ticker_data['apewisdom_rank'],
                'apewisdom_mentions': ticker_data['apewisdom_mentions'],
                'reddit_mentions_24h': ticker_data['reddit_mentions_24h'],
                'reddit_velocity_pct': ticker_data['reddit_velocity_pct'],
                'health_score': ticker_data['health_score'],
                'market_cap': ticker_data['market_cap'],
                'scoring_breakdown': breakdown
            }
        }
        
        logger.info(f"  ✓ {symbol} FLAGGED for trading (confidence: {confidence_score:.1f}/100)")
        
        return flag_data
    
    def create_trading_flags(self, flags: List[Dict]) -> int:
        """
        Save trading flags to Supabase
        
        Args:
            flags: List of flag dictionaries
            
        Returns:
            Number of flags successfully created
        """
        if not flags:
            logger.info("No flags to create")
            return 0
        
        logger.info(f"Creating {len(flags)} trading flags...")
        
        created_count = 0
        
        for flag in flags:
            try:
                # Check if an open flag already exists for this ticker
                existing = self.supabase.table('trading_flags')\
                    .select('id')\
                    .eq('ticker_id', flag['ticker_id'])\
                    .eq('status', 'OPEN')\
                    .execute()
                
                if existing.data:
                    logger.info(f"  Skipping - Open flag already exists for ticker_id {flag['ticker_id']}")
                    continue
                
                # Create new flag
                self.supabase.table('trading_flags').insert(flag).execute()
                created_count += 1
                logger.info(f"  ✓ Created flag for ticker_id {flag['ticker_id']}")
                
            except Exception as e:
                logger.error(f"  ✗ Error creating flag: {e}")
        
        logger.info(f"Successfully created {created_count}/{len(flags)} flags")
        return created_count
    
    def run(self, hours_back: int = 24) -> Dict:
        """
        Main execution method - runs the trading engine logic
        
        Args:
            hours_back: How many hours of data to consider
            
        Returns:
            Dictionary with results summary
        """
        logger.info("=" * 60)
        logger.info("Starting Trading Engine")
        logger.info("=" * 60)
        
        # Step 1: Get recent data
        ticker_data = self.get_recent_data(hours_back)
        
        if not ticker_data:
            logger.warning("No recent ticker data found")
            return {'evaluated': 0, 'flagged': 0, 'created': 0}
        
        # Step 2: Evaluate each ticker
        flags_to_create = []
        
        for symbol, data in ticker_data.items():
            flag_data = self.evaluate_ticker(symbol, data)
            if flag_data:
                flags_to_create.append(flag_data)
        
        # Step 3: Create trading flags
        created_count = self.create_trading_flags(flags_to_create)
        
        results = {
            'evaluated': len(ticker_data),
            'flagged': len(flags_to_create),
            'created': created_count,
            'flags': flags_to_create
        }
        
        logger.info("=" * 60)
        logger.info("Trading Engine Complete")
        logger.info(f"Tickers evaluated: {results['evaluated']}")
        logger.info(f"Tickers flagged: {results['flagged']}")
        logger.info(f"Flags created: {results['created']}")
        logger.info("=" * 60)
        
        return results


if __name__ == '__main__':
    # For testing
    from dotenv import load_dotenv
    load_dotenv()
    
    engine = TradingEngine()
    results = engine.run(hours_back=24)
    
    print("\n=== ENGINE RESULTS ===")
    print(f"Evaluated: {results['evaluated']} tickers")
    print(f"Flagged: {results['flagged']} tickers")
    print(f"Created: {results['created']} new flags")
    
    if results['flags']:
        print("\nFlagged Tickers:")
        for flag in results['flags']:
            metadata = flag['metadata']
            print(f"  • Ticker ID {flag['ticker_id']}: {flag['confidence_score']:.1f}% confidence")
            print(f"    ApeWisdom #{metadata['apewisdom_rank']}, Reddit velocity: {metadata['reddit_velocity_pct']:+.1f}%")

