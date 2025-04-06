-- Add updated_at column to calls table
ALTER TABLE calls ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP;

-- Create a trigger to automatically update updated_at
CREATE OR REPLACE FUNCTION update_updated_at_column()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = CURRENT_TIMESTAMP;
    RETURN NEW;
END;
$$ language 'plpgsql';

CREATE TRIGGER update_calls_updated_at
    BEFORE UPDATE ON calls
    FOR EACH ROW
    EXECUTE FUNCTION update_updated_at_column(); 