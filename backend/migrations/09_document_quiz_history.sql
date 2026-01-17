-- Quiz Question History for Deduplication
-- Tracks previously generated quiz questions per document to avoid repetitions

CREATE TABLE IF NOT EXISTS document_quiz_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES user_documents(id) ON DELETE CASCADE,
    question_text TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT now()
);

-- Index for efficient lookups by document
CREATE INDEX IF NOT EXISTS idx_quiz_history_document_id 
ON document_quiz_history(document_id);

-- Index for ordering by recency
CREATE INDEX IF NOT EXISTS idx_quiz_history_created_at 
ON document_quiz_history(created_at DESC);
