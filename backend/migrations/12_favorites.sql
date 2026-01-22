-- Migration: 12_favorites.sql
-- Student Favorites for lesson modules (Quick Review feature)

-- Create student_favorites table
CREATE TABLE IF NOT EXISTS student_favorites (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    
    -- Student reference
    student_id UUID NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    
    -- Lesson and module reference
    lesson_id UUID NOT NULL REFERENCES generated_lessons(id) ON DELETE CASCADE,
    module_index INTEGER NOT NULL,
    module_type VARCHAR(50) NOT NULL,
    module_content JSONB NOT NULL,
    
    -- Hierarchy for filtering
    subtopic_id UUID NOT NULL REFERENCES subtopics(id) ON DELETE CASCADE,
    topic_id UUID NOT NULL REFERENCES topics(id) ON DELETE CASCADE,
    subject_id UUID NOT NULL REFERENCES subjects(id) ON DELETE CASCADE,
    
    -- Metadata
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW() NOT NULL,
    
    -- Unique constraint: prevent duplicate favorites
    UNIQUE(student_id, lesson_id, module_index)
);

-- Indexes for efficient querying
CREATE INDEX IF NOT EXISTS ix_favorites_student_id ON student_favorites(student_id);
CREATE INDEX IF NOT EXISTS ix_favorites_subtopic_id ON student_favorites(subtopic_id);
CREATE INDEX IF NOT EXISTS ix_favorites_topic_id ON student_favorites(topic_id);
CREATE INDEX IF NOT EXISTS ix_favorites_subject_id ON student_favorites(subject_id);
CREATE INDEX IF NOT EXISTS ix_favorites_student_lesson ON student_favorites(student_id, lesson_id);
CREATE INDEX IF NOT EXISTS ix_favorites_module_type ON student_favorites(module_type);

-- Add foreign key to generated_lessons if not exists
ALTER TABLE generated_lessons 
ADD COLUMN IF NOT EXISTS subtopic_id UUID REFERENCES subtopics(id);

COMMENT ON TABLE student_favorites IS 'Stores lesson modules that students mark as favorites for quick review';
