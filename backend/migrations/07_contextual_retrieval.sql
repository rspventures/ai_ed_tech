-- Phase 7: Contextual Retrieval - Add context enrichment columns
-- This migration adds columns for LLM-generated context per chunk

-- Add context column to document_chunks
-- This stores the LLM-generated context explaining what this chunk is about
ALTER TABLE document_chunks ADD COLUMN IF NOT EXISTS context TEXT;

-- Add summary column to user_documents  
-- This stores a document-level summary for hierarchical retrieval
ALTER TABLE user_documents ADD COLUMN IF NOT EXISTS summary TEXT;

-- Add index on context for potential full-text search
CREATE INDEX IF NOT EXISTS idx_document_chunks_context ON document_chunks USING gin(to_tsvector('english', context)) WHERE context IS NOT NULL;
