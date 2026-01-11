-- Sample Queries for Trading Bot Analysis
-- Run these in your Supabase SQL Editor

-- =====================================================
-- TRADING FLAGS - View Current Opportunities
-- =====================================================

-- Get all open trading flags ordered by confidence
SELECT 
    t.symbol,
    t.company_name,
    tf.confidence_score,
    tf.entry_price,
    tf.rationale,
    tf.created_at,
    tf.metadata->>'apewisdom_rank' as apewisdom_rank,
    tf.metadata->>'reddit_velocity_pct' as reddit_velocity
FROM trading_flags tf
JOIN tickers t ON tf.ticker_id = t.id
WHERE tf.status = 'OPEN'
ORDER BY tf.confidence_score DESC;


-- =====================================================
-- SENTIMENT ANALYSIS - Top Trending Tickers
-- =====================================================

-- Latest ApeWisdom rankings
SELECT 
    t.symbol,
    t.company_name,
    sl.rank,
    sl.mention_count,
    sl.upvotes,
    sl.timestamp
FROM sentiment_logs sl
JOIN tickers t ON sl.ticker_id = t.id
WHERE sl.source = 'APEWISDOM'
  AND sl.timestamp > NOW() - INTERVAL '24 hours'
ORDER BY sl.rank ASC
LIMIT 20;


-- Reddit mention velocity - highest growth
SELECT 
    t.symbol,
    t.company_name,
    rmv.mention_count_24h,
    rmv.velocity_change_pct,
    rmv.subreddit,
    rmv.timestamp
FROM reddit_mention_velocity rmv
JOIN tickers t ON rmv.ticker_id = t.id
WHERE rmv.timestamp > NOW() - INTERVAL '24 hours'
ORDER BY rmv.velocity_change_pct DESC
LIMIT 20;


-- =====================================================
-- FUNDAMENTAL ANALYSIS - Health Checks
-- =====================================================

-- Tickers with latest fundamental stats
SELECT 
    t.symbol,
    t.company_name,
    t.industry,
    fs.market_cap,
    fs.profit_margin,
    fs.pe_ratio,
    fs.debt_to_equity,
    fs.revenue_growth,
    fs.timestamp
FROM fundamental_stats fs
JOIN tickers t ON fs.ticker_id = t.id
WHERE fs.timestamp > NOW() - INTERVAL '7 days'
ORDER BY fs.market_cap DESC;


-- Tickers that pass health checks (Market Cap > $500M, Healthy margins)
SELECT 
    t.symbol,
    t.company_name,
    fs.market_cap,
    fs.profit_margin,
    fs.debt_to_equity
FROM fundamental_stats fs
JOIN tickers t ON fs.ticker_id = t.id
WHERE fs.timestamp > NOW() - INTERVAL '7 days'
  AND fs.market_cap > 500000000
  AND (fs.profit_margin > -50 OR fs.profit_margin IS NULL)
  AND (fs.debt_to_equity < 2.0 OR fs.debt_to_equity IS NULL)
ORDER BY fs.market_cap DESC;


-- =====================================================
-- COMBINED VIEW - Ready to Trade
-- =====================================================

-- Tickers in top 20 ApeWisdom + High velocity + Healthy fundamentals
WITH latest_apewisdom AS (
    SELECT DISTINCT ON (ticker_id)
        ticker_id,
        rank,
        mention_count
    FROM sentiment_logs
    WHERE source = 'APEWISDOM'
      AND timestamp > NOW() - INTERVAL '24 hours'
    ORDER BY ticker_id, timestamp DESC
),
latest_velocity AS (
    SELECT DISTINCT ON (ticker_id)
        ticker_id,
        velocity_change_pct,
        mention_count_24h
    FROM reddit_mention_velocity
    WHERE timestamp > NOW() - INTERVAL '24 hours'
    ORDER BY ticker_id, timestamp DESC
),
latest_fundamentals AS (
    SELECT DISTINCT ON (ticker_id)
        ticker_id,
        market_cap,
        profit_margin,
        pe_ratio
    FROM fundamental_stats
    WHERE timestamp > NOW() - INTERVAL '7 days'
    ORDER BY ticker_id, timestamp DESC
)
SELECT 
    t.symbol,
    t.company_name,
    la.rank as apewisdom_rank,
    la.mention_count as apewisdom_mentions,
    lv.velocity_change_pct as reddit_velocity,
    lv.mention_count_24h as reddit_mentions,
    lf.market_cap,
    lf.profit_margin,
    lf.pe_ratio
FROM tickers t
LEFT JOIN latest_apewisdom la ON t.id = la.ticker_id
LEFT JOIN latest_velocity lv ON t.id = lv.ticker_id
LEFT JOIN latest_fundamentals lf ON t.id = lf.ticker_id
WHERE la.rank <= 20
  AND lv.velocity_change_pct > 20
  AND lf.market_cap > 500000000
ORDER BY la.rank ASC;


-- =====================================================
-- HISTORICAL ANALYSIS - Performance Tracking
-- =====================================================

-- Sentiment trend for a specific ticker (replace 'GME' with your ticker)
SELECT 
    DATE(timestamp) as date,
    source,
    AVG(mention_count) as avg_mentions,
    AVG(upvotes) as avg_upvotes
FROM sentiment_logs sl
JOIN tickers t ON sl.ticker_id = t.id
WHERE t.symbol = 'GME'
  AND timestamp > NOW() - INTERVAL '30 days'
GROUP BY DATE(timestamp), source
ORDER BY date DESC, source;


-- Reddit velocity trend over time for a ticker
SELECT 
    DATE(timestamp) as date,
    subreddit,
    AVG(mention_count_24h) as avg_mentions,
    AVG(velocity_change_pct) as avg_velocity
FROM reddit_mention_velocity rmv
JOIN tickers t ON rmv.ticker_id = t.id
WHERE t.symbol = 'GME'
  AND timestamp > NOW() - INTERVAL '30 days'
GROUP BY DATE(timestamp), subreddit
ORDER BY date DESC;


-- Trading flags history
SELECT 
    t.symbol,
    tf.flag_type,
    tf.confidence_score,
    tf.status,
    tf.created_at,
    tf.closed_at,
    CASE 
        WHEN tf.closed_at IS NOT NULL 
        THEN EXTRACT(EPOCH FROM (tf.closed_at - tf.created_at))/86400 
        ELSE NULL 
    END as days_open
FROM trading_flags tf
JOIN tickers t ON tf.ticker_id = t.id
ORDER BY tf.created_at DESC;


-- =====================================================
-- MAINTENANCE - Data Quality Checks
-- =====================================================

-- Count records per table
SELECT 'tickers' as table_name, COUNT(*) as count FROM tickers
UNION ALL
SELECT 'sentiment_logs', COUNT(*) FROM sentiment_logs
UNION ALL
SELECT 'fundamental_stats', COUNT(*) FROM fundamental_stats
UNION ALL
SELECT 'trading_flags', COUNT(*) FROM trading_flags
UNION ALL
SELECT 'reddit_mention_velocity', COUNT(*) FROM reddit_mention_velocity;


-- Find tickers with missing fundamental data
SELECT 
    t.symbol,
    t.company_name,
    COUNT(fs.id) as fundamental_records
FROM tickers t
LEFT JOIN fundamental_stats fs ON t.id = fs.ticker_id
GROUP BY t.id, t.symbol, t.company_name
HAVING COUNT(fs.id) = 0;


-- Recent pipeline activity (last 7 days)
SELECT 
    DATE(timestamp) as date,
    COUNT(*) as records
FROM sentiment_logs
WHERE timestamp > NOW() - INTERVAL '7 days'
GROUP BY DATE(timestamp)
ORDER BY date DESC;


-- =====================================================
-- CLEANUP - Delete Old Data (Optional)
-- =====================================================

-- Delete sentiment logs older than 90 days
-- DELETE FROM sentiment_logs WHERE timestamp < NOW() - INTERVAL '90 days';

-- Delete fundamental stats older than 180 days
-- DELETE FROM fundamental_stats WHERE timestamp < NOW() - INTERVAL '180 days';

-- Close expired trading flags (open for more than 30 days)
-- UPDATE trading_flags 
-- SET status = 'EXPIRED', closed_at = NOW()
-- WHERE status = 'OPEN' 
--   AND created_at < NOW() - INTERVAL '30 days';

