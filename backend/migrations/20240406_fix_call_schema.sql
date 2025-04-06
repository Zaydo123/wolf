-- Drop existing columns if they exist
ALTER TABLE calls DROP COLUMN IF EXISTS duration;
ALTER TABLE calls DROP COLUMN IF EXISTS updated_at;

-- Add columns with proper constraints
ALTER TABLE calls ADD COLUMN duration INTEGER;
ALTER TABLE calls ADD COLUMN updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP;

-- Ensure required columns exist
ALTER TABLE calls ALTER COLUMN user_id SET NOT NULL;
ALTER TABLE calls ALTER COLUMN call_sid SET NOT NULL;
ALTER TABLE calls ALTER COLUMN status SET NOT NULL;
ALTER TABLE calls ALTER COLUMN direction SET NOT NULL;
ALTER TABLE calls ALTER COLUMN started_at SET NOT NULL;

-- Add indexes for better performance
CREATE INDEX IF NOT EXISTS idx_calls_user_id ON calls(user_id);
CREATE INDEX IF NOT EXISTS idx_calls_call_sid ON calls(call_sid);
CREATE INDEX IF NOT EXISTS idx_calls_status ON calls(status);
CREATE INDEX IF NOT EXISTS idx_calls_started_at ON calls(started_at);

-- Create a trigger to automatically update updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

-- Drop the trigger if it exists
DROP TRIGGER IF EXISTS update_calls_updated_at ON calls;

-- Create the trigger
CREATE TRIGGER update_calls_updated_at
    BEFORE UPDATE ON calls
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column(); 