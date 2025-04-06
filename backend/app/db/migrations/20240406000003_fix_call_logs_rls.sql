-- Add service role access to call_logs table
DROP POLICY IF EXISTS "Enable all operations for service role" ON call_logs;

CREATE POLICY "Enable all operations for service role"
ON call_logs
FOR ALL
TO service_role
USING (true)
WITH CHECK (true);

-- Add the missing updated_at column to calls table if it doesn't exist
ALTER TABLE calls ADD COLUMN IF NOT EXISTS updated_at TIMESTAMP WITH TIME ZONE DEFAULT CURRENT_TIMESTAMP;