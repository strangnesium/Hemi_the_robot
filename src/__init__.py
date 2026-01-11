"""
Sentiment-to-Value Trading Bot
A cloud-native pipeline for identifying trending stocks based on social sentiment and fundamentals
"""

__version__ = '2.0.0'
__author__ = 'Trading Bot Team'

from .discovery import DiscoveryEngine
from .validator import FundamentalValidator
from .engine import TradingEngine

__all__ = ['DiscoveryEngine', 'FundamentalValidator', 'TradingEngine']

