-- Users Table
CREATE TABLE IF NOT EXISTS users (
  id UUID PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  email TEXT UNIQUE NOT NULL,
  name TEXT NOT NULL,
  phone_number TEXT,
  cash_balance DECIMAL(15, 2) DEFAULT 10000.00,
  call_preferences JSONB DEFAULT '{"market_open": true, "mid_day": false, "market_close": true}'::jsonb,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create RLS policies for users table
ALTER TABLE users ENABLE ROW LEVEL SECURITY;

-- Users can read their own data
CREATE POLICY "Users can read their own data" ON users
  FOR SELECT USING (auth.uid() = id);

-- Users can update their own data
CREATE POLICY "Users can update their own data" ON users
  FOR UPDATE USING (auth.uid() = id);

-- Allow service role to insert users (needed for registration)
CREATE POLICY "Service can insert users" ON users
  FOR INSERT WITH CHECK (true);

-- Allow service role to access all users (needed for calls)
CREATE POLICY "Service can access all users" ON users
  FOR ALL USING (auth.role() = 'service_role');

-- Portfolios Table (user's stock holdings)
CREATE TABLE IF NOT EXISTS portfolios (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID REFERENCES users(id) ON DELETE CASCADE,
  ticker TEXT NOT NULL,
  quantity INTEGER NOT NULL,
  avg_price DECIMAL(15, 2) NOT NULL,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  UNIQUE(user_id, ticker)
);

-- Create RLS policies for portfolios table
ALTER TABLE portfolios ENABLE ROW LEVEL SECURITY;

-- Users can read their own portfolios
CREATE POLICY "Users can read their own portfolios" ON portfolios
  FOR SELECT USING (auth.uid() = user_id);

-- Users can update their own portfolios
CREATE POLICY "Users can update their own portfolios" ON portfolios
  FOR ALL USING (auth.uid() = user_id);

-- Trades Table (history of trades)
CREATE TABLE IF NOT EXISTS trades (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID REFERENCES users(id) ON DELETE CASCADE,
  ticker TEXT NOT NULL,
  action TEXT NOT NULL, -- 'buy' or 'sell'
  quantity INTEGER NOT NULL,
  price DECIMAL(15, 2) NOT NULL,
  total_value DECIMAL(15, 2) NOT NULL,
  timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create RLS policies for trades table
ALTER TABLE trades ENABLE ROW LEVEL SECURITY;

-- Users can read their own trades
CREATE POLICY "Users can read their own trades" ON trades
  FOR SELECT USING (auth.uid() = user_id);

-- Users can create their own trades
CREATE POLICY "Users can create their own trades" ON trades
  FOR INSERT WITH CHECK (auth.uid() = user_id);

-- Watchlists Table
CREATE TABLE IF NOT EXISTS watchlists (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID REFERENCES users(id) ON DELETE CASCADE,
  ticker TEXT NOT NULL,
  added_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  UNIQUE(user_id, ticker)
);

-- Create RLS policies for watchlists table
ALTER TABLE watchlists ENABLE ROW LEVEL SECURITY;

-- Users can read their own watchlists
CREATE POLICY "Users can read their own watchlists" ON watchlists
  FOR SELECT USING (auth.uid() = user_id);

-- Users can manage their own watchlists
CREATE POLICY "Users can manage their own watchlists" ON watchlists
  FOR ALL USING (auth.uid() = user_id);

-- Call Schedules Table
CREATE TABLE IF NOT EXISTS call_schedules (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID REFERENCES users(id) ON DELETE CASCADE,
  phone_number TEXT NOT NULL,
  call_time TEXT NOT NULL,
  call_type TEXT NOT NULL, -- 'market_open', 'mid_day', 'market_close'
  status TEXT NOT NULL DEFAULT 'scheduled',
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create RLS policies for call_schedules table
ALTER TABLE call_schedules ENABLE ROW LEVEL SECURITY;

-- Users can read their own call schedules
CREATE POLICY "Users can read their own call schedules" ON call_schedules
  FOR SELECT USING (auth.uid() = user_id);

-- Users can manage their own call schedules
CREATE POLICY "Users can manage their own call schedules" ON call_schedules
  FOR ALL USING (auth.uid() = user_id);

-- Calls Table
CREATE TABLE IF NOT EXISTS calls (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID REFERENCES users(id) ON DELETE CASCADE,
  call_sid TEXT,
  status TEXT NOT NULL,
  direction TEXT NOT NULL DEFAULT 'outbound', -- 'inbound' or 'outbound'
  phone_number TEXT NOT NULL,
  started_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
  ended_at TIMESTAMP WITH TIME ZONE
);

-- Create RLS policies for calls table
ALTER TABLE calls ENABLE ROW LEVEL SECURITY;

-- Users can read their own calls
CREATE POLICY "Users can read their own calls" ON calls
  FOR SELECT USING (auth.uid() = user_id);

-- Call Logs Table
CREATE TABLE IF NOT EXISTS call_logs (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  user_id UUID REFERENCES users(id) ON DELETE CASCADE,
  call_sid TEXT,
  direction TEXT NOT NULL, -- 'inbound' or 'outbound'
  content TEXT NOT NULL,
  timestamp TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Create RLS policies for call_logs table
ALTER TABLE call_logs ENABLE ROW LEVEL SECURITY;

-- Users can read their own call logs
CREATE POLICY "Users can read their own call logs" ON call_logs
  FOR SELECT USING (auth.uid() = user_id); 