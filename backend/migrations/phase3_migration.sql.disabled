-- Phase 3 Database Migration
-- Adds new columns for Settings and Smart Review features

-- Add preferences column to students table
ALTER TABLE students ADD COLUMN IF NOT EXISTS preferences JSONB DEFAULT '{}';

-- Add SRS columns to progress table  
ALTER TABLE progress ADD COLUMN IF NOT EXISTS next_review_at TIMESTAMP WITH TIME ZONE;
ALTER TABLE progress ADD COLUMN IF NOT EXISTS review_interval_days INTEGER DEFAULT 1;

-- Verify the changes
SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'students' AND column_name = 'preferences';

SELECT column_name, data_type 
FROM information_schema.columns 
WHERE table_name = 'progress' AND column_name IN ('next_review_at', 'review_interval_days');
