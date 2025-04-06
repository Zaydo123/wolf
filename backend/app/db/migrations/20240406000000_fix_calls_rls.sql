-- Drop existing RLS policies
DROP POLICY IF EXISTS "Enable insert for service role" ON calls;
DROP POLICY IF EXISTS "Enable read for authenticated users" ON calls;

-- Create new RLS policies
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

-- Enable RLS
ALTER TABLE calls ENABLE ROW LEVEL SECURITY; 