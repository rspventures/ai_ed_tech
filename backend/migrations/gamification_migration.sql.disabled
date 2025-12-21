-- Phase 3.2 Migration: Add Gamification Fields to Students Table
-- Run this after the main schema is created

-- Add gamification columns to students table
ALTER TABLE students 
ADD COLUMN IF NOT EXISTS xp_total INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS level INTEGER DEFAULT 1,
ADD COLUMN IF NOT EXISTS current_streak INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS longest_streak INTEGER DEFAULT 0,
ADD COLUMN IF NOT EXISTS last_activity_date TIMESTAMP WITH TIME ZONE;

-- Create index for gamification stats queries
CREATE INDEX IF NOT EXISTS idx_students_gamification 
ON students (xp_total DESC, level DESC);

-- Create index for streak queries
CREATE INDEX IF NOT EXISTS idx_students_streak 
ON students (current_streak DESC);

-- Update existing students to have default values
UPDATE students 
SET xp_total = 0, 
    level = 1, 
    current_streak = 0, 
    longest_streak = 0 
WHERE xp_total IS NULL;
