-- Drop existing calls table if it exists
DROP TABLE IF EXISTS calls;

-- Create new calls table with correct structure
CREATE TABLE calls (
    id UUID DEFAULT gen_random_uuid() PRIMARY KEY,
    user_id UUID NOT NULL REFERENCES users(id),
    phone_number TEXT NOT NULL,
    call_sid TEXT,
    status TEXT NOT NULL,
    started_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    ended_at TIMESTAMP WITH TIME ZONE,
    created_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP,
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP
);

-- Create indexes
CREATE INDEX idx_calls_user_id ON calls(user_id);
CREATE INDEX idx_calls_call_sid ON calls(call_sid);

-- Enable RLS
ALTER TABLE calls ENABLE ROW LEVEL SECURITY;

-- Create RLS policies
CREATE POLICY "Enable all operations for service role"
ON calls
FOR ALL
TO service_role
USING (true)
WITH CHECK (true);

CREATE POLICY "Enable read for authenticated users"
ON calls
FOR SELECT
TO authenticated
USING (user_id = auth.uid()); 