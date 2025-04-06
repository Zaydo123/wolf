-- Add duration column to calls table
ALTER TABLE calls ADD COLUMN IF NOT EXISTS duration INTEGER; 