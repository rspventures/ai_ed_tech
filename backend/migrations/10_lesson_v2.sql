-- ============================================================================
-- Lesson 2.0 Schema Additions
-- Adds content_version tracking for GeneratedLesson
-- ============================================================================

-- Add content_version column to track V1 vs V2 lessons
ALTER TABLE generated_lessons 
    ADD COLUMN IF NOT EXISTS content_version INTEGER DEFAULT 1;

-- Add index for efficient V2 lesson queries
CREATE INDEX IF NOT EXISTS idx_generated_lessons_version 
    ON generated_lessons(subtopic_id, grade_level, generated_by);

-- Update existing lessons to have version 1
UPDATE generated_lessons 
    SET content_version = 1 
    WHERE content_version IS NULL;

-- Comment for documentation
COMMENT ON COLUMN generated_lessons.content_version IS 
    'Lesson format version: 1=text sections, 2=module playlist';
