-- Supabase Database Schema for Sentiment-to-Value Trading Bot
-- Run this in your Supabase SQL Editor to create the tables

-- Enable UUID extension
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- Table 1: Tickers - Master list of stock symbols
CREATE TABLE IF NOT EXISTS tickers (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    symbol VARCHAR(10) UNIQUE NOT NULL,
    company_name VARCHAR(255),
    industry VARCHAR(100),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Table 2: Sentiment Logs - Track social media mentions and sentiment
CREATE TABLE IF NOT EXISTS sentiment_logs (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    ticker_id UUID NOT NULL REFERENCES tickers(id) ON DELETE CASCADE,
    source VARCHAR(50) NOT NULL, -- 'APEWISDOM', 'REDDIT', 'TWITTER', etc.
    mention_count INTEGER DEFAULT 0,
    upvotes INTEGER DEFAULT 0,
    rank INTEGER,
    sentiment_score DECIMAL(5,2), -- Optional: -1.0 to 1.0 scale
    raw_data JSONB, -- Store additional metadata
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Table 3: Fundamental Stats - Yahoo Finance fundamental data
CREATE TABLE IF NOT EXISTS fundamental_stats (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    ticker_id UUID NOT NULL REFERENCES tickers(id) ON DELETE CASCADE,
    market_cap BIGINT,
    short_float_pct DECIMAL(5,2),
    debt_to_equity DECIMAL(10,2),
    revenue_growth DECIMAL(5,2),
    profit_margin DECIMAL(5,2),
    pe_ratio DECIMAL(10,2),
    beta DECIMAL(5,2),
    raw_data JSONB, -- Store complete yfinance response
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Table 4: Trading Flags - Action items for trades
CREATE TABLE IF NOT EXISTS trading_flags (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    ticker_id UUID NOT NULL REFERENCES tickers(id) ON DELETE CASCADE,
    flag_type VARCHAR(50) NOT NULL, -- 'BUY', 'SELL', 'WATCH', 'HOLD'
    entry_price DECIMAL(10,2),
    target_price DECIMAL(10,2),
    stop_loss DECIMAL(10,2),
    confidence_score DECIMAL(5,2) NOT NULL, -- 0.0 to 1.0 scale
    status VARCHAR(20) DEFAULT 'OPEN', -- 'OPEN', 'CLOSED', 'EXPIRED'
    rationale TEXT,
    metadata JSONB, -- Store calculation details
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    closed_at TIMESTAMP WITH TIME ZONE
);

-- Table 5: Reddit Mention Velocity - Track mention frequency over time
CREATE TABLE IF NOT EXISTS reddit_mention_velocity (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    ticker_id UUID NOT NULL REFERENCES tickers(id) ON DELETE CASCADE,
    subreddit VARCHAR(50) NOT NULL,
    mention_count_24h INTEGER DEFAULT 0,
    mention_count_7d INTEGER DEFAULT 0,
    velocity_change_pct DECIMAL(5,2), -- % change in 24h mentions
    top_posts JSONB, -- Store top 5 posts mentioning ticker
    timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create indexes for better query performance
CREATE INDEX idx_sentiment_ticker_timestamp ON sentiment_logs(ticker_id, timestamp DESC);
CREATE INDEX idx_sentiment_source ON sentiment_logs(source);
CREATE INDEX idx_fundamental_ticker_timestamp ON fundamental_stats(ticker_id, timestamp DESC);
CREATE INDEX idx_flags_status ON trading_flags(status);
CREATE INDEX idx_flags_ticker_status ON trading_flags(ticker_id, status);
CREATE INDEX idx_velocity_ticker_timestamp ON reddit_mention_velocity(ticker_id, timestamp DESC);
CREATE INDEX idx_tickers_symbol ON tickers(symbol);

-- Create a view for the latest data
CREATE OR REPLACE VIEW latest_ticker_data AS
SELECT 
    t.symbol,
    t.company_name,
    t.industry,
    (SELECT mention_count FROM sentiment_logs sl 
     WHERE sl.ticker_id = t.id AND sl.source = 'APEWISDOM'
     ORDER BY timestamp DESC LIMIT 1) as apewisdom_mentions,
    (SELECT rank FROM sentiment_logs sl 
     WHERE sl.ticker_id = t.id AND sl.source = 'APEWISDOM'
     ORDER BY timestamp DESC LIMIT 1) as apewisdom_rank,
    (SELECT mention_count_24h FROM reddit_mention_velocity rmv 
     WHERE rmv.ticker_id = t.id 
     ORDER BY timestamp DESC LIMIT 1) as reddit_mentions_24h,
    (SELECT velocity_change_pct FROM reddit_mention_velocity rmv 
     WHERE rmv.ticker_id = t.id 
     ORDER BY timestamp DESC LIMIT 1) as reddit_velocity,
    (SELECT market_cap FROM fundamental_stats fs 
     WHERE fs.ticker_id = t.id 
     ORDER BY timestamp DESC LIMIT 1) as market_cap,
    (SELECT profit_margin FROM fundamental_stats fs 
     WHERE fs.ticker_id = t.id 
     ORDER BY timestamp DESC LIMIT 1) as profit_margin,
    (SELECT COUNT(*) FROM trading_flags tf 
     WHERE tf.ticker_id = t.id AND tf.status = 'OPEN') as open_flags
FROM tickers t;

-- Function to update updated_at timestamp
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Create triggers for automatic updated_at updates
CREATE TRIGGER update_tickers_updated_at BEFORE UPDATE ON tickers
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

CREATE TRIGGER update_trading_flags_updated_at BEFORE UPDATE ON trading_flags
    FOR EACH ROW EXECUTE FUNCTION update_updated_at_column();

-- Insert some example data (optional - remove in production)
-- INSERT INTO tickers (symbol, company_name, industry) 
-- VALUES 
--     ('GME', 'GameStop Corp.', 'Retail'),
--     ('AMC', 'AMC Entertainment Holdings Inc.', 'Entertainment'),
--     ('TSLA', 'Tesla Inc.', 'Automotive');

COMMENT ON TABLE tickers IS 'Master list of stock ticker symbols';
COMMENT ON TABLE sentiment_logs IS 'Social media mentions and sentiment data';
COMMENT ON TABLE fundamental_stats IS 'Yahoo Finance fundamental statistics';
COMMENT ON TABLE trading_flags IS 'Trading signals and action items';
COMMENT ON TABLE reddit_mention_velocity IS 'Track Reddit mention frequency and velocity';

