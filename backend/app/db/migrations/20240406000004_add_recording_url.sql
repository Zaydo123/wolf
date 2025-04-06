-- Add recording_url column to calls table
ALTER TABLE calls ADD COLUMN IF NOT EXISTS recording_url TEXT;

-- Create an index for better performance
CREATE INDEX IF NOT EXISTS idx_calls_recording_url ON calls(recording_url); 