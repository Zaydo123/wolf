-- Drop existing RLS policies for the users table
DROP POLICY IF EXISTS "Users can read their own data" ON users;
DROP POLICY IF EXISTS "Users can update their own data" ON users;
DROP POLICY IF EXISTS "Service can insert users" ON users;
DROP POLICY IF EXISTS "Service can access all users" ON users;

-- Create new RLS policies for the users table
-- Allow authenticated users to read their own data
CREATE POLICY "Users can read their own data" ON users
  FOR SELECT USING (auth.uid() = id);

-- Allow authenticated users to update their own data
CREATE POLICY "Users can update their own data" ON users
  FOR UPDATE USING (auth.uid() = id);

-- Allow service role to insert users (with a stronger policy)
CREATE POLICY "Service role can insert users" ON users
  FOR INSERT TO users
  WITH CHECK (true);

-- Allow service role to access all users
CREATE POLICY "Service role can access all users" ON users
  USING (auth.role() IN ('service_role', 'supabase_admin')); 