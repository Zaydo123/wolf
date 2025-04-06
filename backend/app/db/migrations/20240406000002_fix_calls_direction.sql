-- Add the missing direction column to calls table
ALTER TABLE calls ADD COLUMN IF NOT EXISTS direction TEXT NOT NULL DEFAULT 'outbound';

-- Create an index for better performance
CREATE INDEX IF NOT EXISTS idx_calls_direction ON calls(direction);