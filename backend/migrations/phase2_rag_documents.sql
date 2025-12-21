-- ============================================================================
-- AI Tutor Platform - Phase 2 Migration: RAG Document System
-- ============================================================================
-- This migration adds tables for document storage with pgvector support
-- Run this AFTER enabling the pgvector extension in PostgreSQL
-- ============================================================================

-- Enable pgvector extension (requires superuser or extension creation rights)
-- If this fails, you may need to run: CREATE EXTENSION vector; as superuser
CREATE EXTENSION IF NOT EXISTS vector;

-- ============================================================================
-- USER DOCUMENTS TABLE
-- Stores metadata for uploaded documents
-- ============================================================================
CREATE TABLE IF NOT EXISTS user_documents (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    student_id UUID REFERENCES students(id) ON DELETE SET NULL,
    
    -- File metadata
    filename VARCHAR(255) NOT NULL,
    original_filename VARCHAR(255) NOT NULL,
    file_type VARCHAR(50),
    file_size INTEGER,
    file_path VARCHAR(500),
    
    -- Educational context
    subject VARCHAR(100),
    grade_level INTEGER,
    description TEXT,
    
    -- Processing status
    status VARCHAR(50) DEFAULT 'pending',
    error_message TEXT,
    
    -- Stats
    chunk_count INTEGER DEFAULT 0,
    total_tokens INTEGER DEFAULT 0,
    
    -- Privacy
    is_private BOOLEAN DEFAULT TRUE,
    
    -- Timestamps
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    updated_at TIMESTAMP WITH TIME ZONE DEFAULT NOW(),
    processed_at TIMESTAMP WITH TIME ZONE
);

-- Indexes for user_documents
CREATE INDEX IF NOT EXISTS idx_user_documents_user_id ON user_documents(user_id);
CREATE INDEX IF NOT EXISTS idx_user_documents_student_id ON user_documents(student_id);
CREATE INDEX IF NOT EXISTS idx_user_documents_status ON user_documents(status);

-- ============================================================================
-- DOCUMENT CHUNKS TABLE
-- Stores text chunks with vector embeddings for similarity search
-- ============================================================================
CREATE TABLE IF NOT EXISTS document_chunks (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    document_id UUID NOT NULL REFERENCES user_documents(id) ON DELETE CASCADE,
    
    -- Chunk content
    content TEXT NOT NULL,
    chunk_index INTEGER NOT NULL,
    token_count INTEGER DEFAULT 0,
    
    -- Vector embedding (1536 dimensions for OpenAI text-embedding-3-small)
    embedding vector(1536),
    
    -- Metadata (JSON)
    metadata JSONB DEFAULT '{}',
    
    -- Timestamp
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for document_chunks
CREATE INDEX IF NOT EXISTS idx_document_chunks_document_id ON document_chunks(document_id);
CREATE INDEX IF NOT EXISTS idx_document_chunks_chunk_index ON document_chunks(document_id, chunk_index);

-- Vector similarity index (IVFFlat for approximate nearest neighbor search)
-- This dramatically speeds up similarity queries
CREATE INDEX IF NOT EXISTS idx_document_chunks_embedding 
ON document_chunks USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100);

-- ============================================================================
-- GENERATED IMAGES TABLE
-- Stores AI-generated images for visual concept explanations
-- ============================================================================
CREATE TABLE IF NOT EXISTS generated_images (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL REFERENCES users(id) ON DELETE CASCADE,
    student_id UUID REFERENCES students(id) ON DELETE SET NULL,
    
    -- Generation details
    prompt TEXT NOT NULL,
    enhanced_prompt TEXT,
    concept VARCHAR(255),
    grade_level INTEGER,
    
    -- Result
    image_url VARCHAR(500),
    image_path VARCHAR(500),
    provider VARCHAR(50),
    
    -- Status
    status VARCHAR(50) DEFAULT 'pending',
    error_message TEXT,
    
    -- Timestamp
    created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

-- Indexes for generated_images
CREATE INDEX IF NOT EXISTS idx_generated_images_user_id ON generated_images(user_id);
CREATE INDEX IF NOT EXISTS idx_generated_images_concept ON generated_images(concept);

-- ============================================================================
-- HELPFUL FUNCTIONS
-- ============================================================================

-- Function to search similar chunks
CREATE OR REPLACE FUNCTION search_similar_chunks(
    query_embedding vector(1536),
    p_user_id UUID,
    p_document_id UUID DEFAULT NULL,
    p_limit INTEGER DEFAULT 5
)
RETURNS TABLE (
    chunk_id UUID,
    content TEXT,
    chunk_index INTEGER,
    document_id UUID,
    filename VARCHAR(255),
    similarity FLOAT
) AS $$
BEGIN
    RETURN QUERY
    SELECT 
        dc.id as chunk_id,
        dc.content,
        dc.chunk_index,
        dc.document_id,
        ud.original_filename as filename,
        1 - (dc.embedding <=> query_embedding) as similarity
    FROM document_chunks dc
    JOIN user_documents ud ON dc.document_id = ud.id
    WHERE ud.user_id = p_user_id
    AND (p_document_id IS NULL OR dc.document_id = p_document_id)
    AND dc.embedding IS NOT NULL
    ORDER BY dc.embedding <=> query_embedding
    LIMIT p_limit;
END;
$$ LANGUAGE plpgsql;

-- ============================================================================
-- MIGRATION COMPLETE
-- ============================================================================
-- To verify:
-- SELECT * FROM user_documents LIMIT 1;
-- SELECT * FROM document_chunks LIMIT 1;
-- SELECT * FROM generated_images LIMIT 1;
