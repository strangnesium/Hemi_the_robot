"""
Main Orchestrator - Runs the complete Sentiment-to-Value trading bot pipeline
"""
import os
import sys
import logging
from datetime import datetime
from typing import Dict
import traceback

from dotenv import load_dotenv

# Add src to path
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'src'))

from discovery import DiscoveryEngine
from validator import FundamentalValidator
from engine import TradingEngine

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler('trading_bot.log')
    ]
)
logger = logging.getLogger(__name__)


class TradingBotOrchestrator:
    """
    Orchestrates the complete trading bot pipeline
    """
    
    def __init__(self):
        """Initialize all pipeline components"""
        logger.info("Initializing Trading Bot Orchestrator...")
        
        # Verify environment variables
        self._verify_environment()
        
        # Initialize components
        self.discovery = DiscoveryEngine()
        self.validator = FundamentalValidator()
        self.engine = TradingEngine()
        
        logger.info("All components initialized successfully")
    
    def _verify_environment(self):
        """Verify all required environment variables are set"""
        required_vars = [
            'SUPABASE_URL',
            'SUPABASE_KEY',
            'REDDIT_CLIENT_ID',
            'REDDIT_CLIENT_SECRET',
            'REDDIT_USER_AGENT'
        ]
        
        missing_vars = [var for var in required_vars if not os.environ.get(var)]
        
        if missing_vars:
            error_msg = f"Missing required environment variables: {', '.join(missing_vars)}"
            logger.error(error_msg)
            raise ValueError(error_msg)
        
        logger.info("✓ All required environment variables are set")
    
    def run_pipeline(self) -> Dict:
        """
        Execute the complete trading bot pipeline
        
        Returns:
            Dictionary with pipeline execution results
        """
        start_time = datetime.now()
        logger.info("=" * 80)
        logger.info("TRADING BOT PIPELINE STARTED")
        logger.info(f"Timestamp: {start_time.isoformat()}")
        logger.info("=" * 80)
        
        results = {
            'start_time': start_time.isoformat(),
            'status': 'running',
            'discovery': None,
            'validation': None,
            'engine': None,
            'errors': []
        }
        
        try:
            # ═══════════════════════════════════════════════════════════
            # PHASE 1: DISCOVERY
            # ═══════════════════════════════════════════════════════════
            logger.info("\n" + "═" * 80)
            logger.info("PHASE 1: DISCOVERY - Finding Trending Tickers")
            logger.info("═" * 80)
            
            discovery_results = self.discovery.run()
            results['discovery'] = discovery_results
            
            logger.info(f"✓ Discovery complete: {discovery_results['apewisdom_count']} ApeWisdom tickers, "
                       f"{discovery_results['reddit_tracked_count']} Reddit mentions tracked")
            
            # ═══════════════════════════════════════════════════════════
            # PHASE 2: VALIDATION
            # ═══════════════════════════════════════════════════════════
            logger.info("\n" + "═" * 80)
            logger.info("PHASE 2: VALIDATION - Checking Fundamental Health")
            logger.info("═" * 80)
            
            # Validate tickers from the last 24 hours
            validation_results = self.validator.validate_from_supabase(hours_back=24)
            results['validation'] = {
                'total_validated': len(validation_results),
                'passed': sum(1 for r in validation_results.values() if r['valid']),
                'failed': sum(1 for r in validation_results.values() if not r['valid'])
            }
            
            logger.info(f"✓ Validation complete: {results['validation']['passed']}/{results['validation']['total_validated']} tickers passed health checks")
            
            # ═══════════════════════════════════════════════════════════
            # PHASE 3: ENGINE
            # ═══════════════════════════════════════════════════════════
            logger.info("\n" + "═" * 80)
            logger.info("PHASE 3: ENGINE - Generating Trading Flags")
            logger.info("═" * 80)
            
            engine_results = self.engine.run(hours_back=24)
            results['engine'] = engine_results
            
            logger.info(f"✓ Engine complete: {engine_results['created']} new trading flags created")
            
            # ═══════════════════════════════════════════════════════════
            # PIPELINE COMPLETE
            # ═══════════════════════════════════════════════════════════
            results['status'] = 'success'
            
        except Exception as e:
            logger.error(f"Pipeline failed with error: {e}")
            logger.error(traceback.format_exc())
            results['status'] = 'failed'
            results['errors'].append(str(e))
        
        finally:
            end_time = datetime.now()
            duration = (end_time - start_time).total_seconds()
            results['end_time'] = end_time.isoformat()
            results['duration_seconds'] = duration
            
            logger.info("\n" + "=" * 80)
            logger.info("TRADING BOT PIPELINE COMPLETED")
            logger.info(f"Status: {results['status'].upper()}")
            logger.info(f"Duration: {duration:.2f} seconds")
            logger.info("=" * 80)
            
            # Print summary
            self._print_summary(results)
        
        return results
    
    def _print_summary(self, results: Dict):
        """Print a formatted summary of pipeline results"""
        print("\n" + "=" * 80)
        print("PIPELINE SUMMARY")
        print("=" * 80)
        
        if results['status'] == 'success':
            print("✓ Status: SUCCESS")
        else:
            print("✗ Status: FAILED")
            if results['errors']:
                print(f"  Errors: {', '.join(results['errors'])}")
        
        print(f"\nDuration: {results.get('duration_seconds', 0):.2f} seconds")
        
        # Discovery summary
        if results.get('discovery'):
            disc = results['discovery']
            print("\n--- DISCOVERY ---")
            print(f"ApeWisdom Tickers: {disc['apewisdom_count']}")
            print(f"Reddit Mentions Tracked: {disc['reddit_tracked_count']}")
            
            if disc.get('top_trending'):
                print("\nTop 5 Trending:")
                for ticker in disc['top_trending'][:5]:
                    print(f"  {ticker['rank']}. ${ticker['symbol']} - {ticker['mention_count']} mentions")
        
        # Validation summary
        if results.get('validation'):
            val = results['validation']
            print("\n--- VALIDATION ---")
            print(f"Total Validated: {val['total_validated']}")
            print(f"Passed: {val['passed']} ✓")
            print(f"Failed: {val['failed']} ✗")
        
        # Engine summary
        if results.get('engine'):
            eng = results['engine']
            print("\n--- ENGINE ---")
            print(f"Tickers Evaluated: {eng['evaluated']}")
            print(f"Tickers Flagged: {eng['flagged']}")
            print(f"New Flags Created: {eng['created']}")
            
            if eng.get('flags'):
                print("\nTrading Flags:")
                for flag in eng['flags']:
                    confidence = flag['confidence_score']
                    metadata = flag.get('metadata', {})
                    rank = metadata.get('apewisdom_rank', 'N/A')
                    velocity = metadata.get('reddit_velocity_pct', 0)
                    print(f"  • Ticker ID {flag['ticker_id']}: {confidence:.1f}% confidence")
                    print(f"    (ApeWisdom #{rank}, Reddit velocity: {velocity:+.1f}%)")
        
        print("\n" + "=" * 80)


def main():
    """Main entry point"""
    # Load environment variables from .env file
    load_dotenv()
    
    try:
        # Create and run orchestrator
        orchestrator = TradingBotOrchestrator()
        results = orchestrator.run_pipeline()
        
        # Exit with appropriate code
        if results['status'] == 'success':
            sys.exit(0)
        else:
            sys.exit(1)
    
    except KeyboardInterrupt:
        logger.info("\nPipeline interrupted by user")
        sys.exit(130)
    
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        logger.error(traceback.format_exc())
        sys.exit(1)


if __name__ == '__main__':
    main()

