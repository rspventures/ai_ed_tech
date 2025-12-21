-- ============================================================================
-- AI Tutor Platform - Document Validation Columns Migration
-- ============================================================================
-- Adds validation columns to user_documents table for grade-appropriateness checks
-- ============================================================================

-- Add validation_status column
ALTER TABLE user_documents 
ADD COLUMN IF NOT EXISTS validation_status VARCHAR(50) DEFAULT 'pending';

-- Add validation_result column (JSONB for structured data)
ALTER TABLE user_documents 
ADD COLUMN IF NOT EXISTS validation_result JSONB;

-- Update document_chunks metadata column name if needed (from metadata to chunk_metadata)
-- First check if the column exists with old name and rename it
DO $$
BEGIN
    IF EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'document_chunks' AND column_name = 'metadata'
    ) AND NOT EXISTS (
        SELECT 1 FROM information_schema.columns 
        WHERE table_name = 'document_chunks' AND column_name = 'chunk_metadata'
    ) THEN
        ALTER TABLE document_chunks RENAME COLUMN metadata TO chunk_metadata;
    END IF;
END $$;

-- If chunk_metadata doesn't exist at all, create it
ALTER TABLE document_chunks 
ADD COLUMN IF NOT EXISTS chunk_metadata JSONB DEFAULT '{}';

-- ============================================================================
-- MIGRATION COMPLETE
-- ============================================================================
