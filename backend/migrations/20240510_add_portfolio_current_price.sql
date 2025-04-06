-- Add current price and value columns to portfolios table
ALTER TABLE portfolios 
ADD COLUMN IF NOT EXISTS current_price DECIMAL(15, 2),
ADD COLUMN IF NOT EXISTS current_value DECIMAL(15, 2),
ADD COLUMN IF NOT EXISTS profit_loss DECIMAL(15, 2);

-- Create an index on ticker for faster lookup
CREATE INDEX IF NOT EXISTS idx_portfolios_ticker ON portfolios(ticker);

-- Initialize current_price with avg_price for existing records
UPDATE portfolios 
SET current_price = avg_price,
    current_value = quantity * avg_price,
    profit_loss = 0
WHERE current_price IS NULL;

-- Add comment explaining the purpose of these columns
COMMENT ON COLUMN portfolios.current_price IS 'The most recent stock price, updated when user visits portfolio';
COMMENT ON COLUMN portfolios.current_value IS 'The current value of the position (quantity * current_price)';
COMMENT ON COLUMN portfolios.profit_loss IS 'The profit/loss percentage based on average purchase price'; 