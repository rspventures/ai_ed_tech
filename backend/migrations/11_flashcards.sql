-- Migration: 11_flashcards.sql
-- Creates flashcard_decks and student_flashcard_progress tables

-- Flashcard Decks table
CREATE TABLE IF NOT EXISTS flashcard_decks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    subtopic_id UUID NOT NULL REFERENCES subtopics(id) ON DELETE CASCADE,
    grade_level INTEGER NOT NULL DEFAULT 1,
    
    -- Deck metadata
    title VARCHAR(300) NOT NULL,
    description VARCHAR(500),
    
    -- Flashcards content (JSONB array)
    -- Structure: [{"front": "Term", "back": "Definition", "difficulty": "easy|medium|hard"}]
    cards JSONB NOT NULL DEFAULT '[]'::jsonb,
    card_count INTEGER NOT NULL DEFAULT 0,
    
    -- Generation metadata
    generated_by VARCHAR(100) NOT NULL,
    
    -- Timestamps
    created_at TIMESTAMPTZ NOT NULL DEFAULT NOW(),
    updated_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

-- Index for fast lookups by subtopic
CREATE INDEX IF NOT EXISTS idx_flashcard_decks_subtopic ON flashcard_decks(subtopic_id);

-- Unique constraint: one deck per subtopic+grade
CREATE UNIQUE INDEX IF NOT EXISTS idx_flashcard_decks_unique 
ON flashcard_decks(subtopic_id, grade_level, generated_by);

-- Student Flashcard Progress table
CREATE TABLE IF NOT EXISTS student_flashcard_progress (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    student_id UUID NOT NULL REFERENCES students(id) ON DELETE CASCADE,
    deck_id UUID NOT NULL REFERENCES flashcard_decks(id) ON DELETE CASCADE,
    
    -- Progress tracking
    cards_reviewed INTEGER NOT NULL DEFAULT 0,
    cards_mastered INTEGER NOT NULL DEFAULT 0,
    last_reviewed_at TIMESTAMPTZ,
    
    -- Unique constraint: one progress record per student+deck
    UNIQUE(student_id, deck_id)
);

-- Indexes for progress lookups
CREATE INDEX IF NOT EXISTS idx_student_flashcard_progress_student ON student_flashcard_progress(student_id);
CREATE INDEX IF NOT EXISTS idx_student_flashcard_progress_deck ON student_flashcard_progress(deck_id);

-- Updated_at trigger for flashcard_decks
CREATE OR REPLACE FUNCTION update_flashcard_decks_updated_at()
RETURNS TRIGGER AS $$
BEGIN
    NEW.updated_at = NOW();
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

DROP TRIGGER IF EXISTS trigger_flashcard_decks_updated_at ON flashcard_decks;
CREATE TRIGGER trigger_flashcard_decks_updated_at
    BEFORE UPDATE ON flashcard_decks
    FOR EACH ROW
    EXECUTE FUNCTION update_flashcard_decks_updated_at();
