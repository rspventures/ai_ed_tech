/**
 * Document Service - API client for document and RAG operations
 */
import api from './api'

export interface Document {
    id: string
    filename: string
    original_filename: string
    file_type: string
    file_size: number
    subject: string | null
    grade_level: number | null
    description: string | null
    status: string
    chunk_count: number
    total_tokens: number
    error_message: string | null
    validation_status: string | null
    validation_result: {
        is_appropriate: boolean
        grade_match: string
        estimated_grade_range: [number, number]
        reason: string
        educational_value: string | null
        content_warnings: string[]
    } | null
    created_at: string
}

export interface DocumentListResponse {
    documents: Document[]
    total: number
}

export interface SearchResult {
    chunk_id: string
    content: string
    chunk_index: number
    document_id: string
    filename: string
    similarity: number
}

export interface ChatResponse {
    answer: string
    grounded: boolean
    confidence: number
    sources: SearchResult[]
    session_id?: string  // For chat history persistence
}

export interface QuizQuestion {
    question: string
    options: string[]
    correct_answer: string
    explanation: string
}

export interface QuizResponse {
    questions: QuizQuestion[]
    document_id: string
    total_questions: number
}

export interface ProcessingStep {
    name: string
    status: 'pending' | 'running' | 'completed' | 'failed'
    message: string | null
}

export interface ProcessingStatus {
    document_id: string
    status: string
    progress_percent: number
    current_step: string
    steps: ProcessingStep[]
    error_message: string | null
    error_suggestion: string | null
    chunk_count: number
    entity_count: number
    estimated_time_remaining: number | null
}

class DocumentService {
    /**
     * Upload a document for RAG processing
     */
    async uploadDocument(
        file: File,
        subject?: string,
        gradeLevel?: number,
        description?: string
    ): Promise<Document> {
        const formData = new FormData()
        formData.append('file', file)
        if (subject) formData.append('subject', subject)
        if (gradeLevel) formData.append('grade_level', gradeLevel.toString())
        if (description) formData.append('description', description)

        const response = await api.post('/documents/upload', formData, {
            headers: {
                'Content-Type': 'multipart/form-data',
            },
        })
        return response.data
    }

    /**
     * List all documents for the current user
     */
    async listDocuments(
        studentId?: string,
        subject?: string,
        limit = 20,
        offset = 0
    ): Promise<DocumentListResponse> {
        const params: Record<string, string | number> = { limit, offset }
        if (studentId) params.student_id = studentId
        if (subject) params.subject = subject

        const response = await api.get('/documents/', { params })
        return response.data
    }

    /**
     * Get a specific document by ID
     */
    async getDocument(documentId: string): Promise<Document> {
        const response = await api.get(`/documents/${documentId}`)
        return response.data
    }

    /**
     * Get document processing status with detailed steps
     * Use this for polling during upload/processing
     */
    async getDocumentStatus(documentId: string): Promise<ProcessingStatus> {
        const response = await api.get(`/documents/${documentId}/status`)
        return response.data
    }

    /**
     * Poll document status until complete or failed
     * Returns final status or throws on timeout
     */
    async pollUntilComplete(
        documentId: string,
        onProgress?: (status: ProcessingStatus) => void,
        maxAttempts = 60,
        intervalMs = 2000
    ): Promise<ProcessingStatus> {
        for (let i = 0; i < maxAttempts; i++) {
            const status = await this.getDocumentStatus(documentId)
            onProgress?.(status)

            if (status.status === 'completed' || status.status === 'failed' || status.status === 'rejected') {
                return status
            }

            await new Promise(resolve => setTimeout(resolve, intervalMs))
        }
        throw new Error('Document processing timeout')
    }

    /**
     * Delete a document
     */
    async deleteDocument(documentId: string): Promise<void> {
        await api.delete(`/documents/${documentId}`)
    }

    /**
     * Chat with a document
     */
    async chatWithDocument(
        documentId: string,
        query: string,
        grade = 5,
        sessionId?: string
    ): Promise<ChatResponse> {
        const response = await api.post(`/documents/${documentId}/chat`, {
            query,
            grade,
            session_id: sessionId,
        })
        return response.data
    }

    /**
     * Get chat history for a document session
     */
    async getChatHistory(
        documentId: string,
        sessionId: string
    ): Promise<{ session_id: string; messages: Array<{ role: string; content: string; created_at: string }> }> {
        const response = await api.get(`/documents/${documentId}/chat/history/${sessionId}`)
        return response.data
    }

    /**
     * Generate quiz from a document
     */
    async generateQuiz(
        documentId: string,
        numQuestions = 5,
        grade = 5
    ): Promise<QuizResponse> {
        const response = await api.post(`/documents/${documentId}/quiz`, {
            num_questions: numQuestions,
            grade,
        })
        return response.data
    }

    /**
     * Search across documents
     */
    async searchDocuments(
        query: string,
        documentId?: string,
        limit = 5
    ): Promise<{ results: SearchResult[]; query: string }> {
        const response = await api.post('/documents/search', {
            query,
            document_id: documentId,
            limit,
        })
        return response.data
    }

    /**
     * Format file size for display
     */
    formatFileSize(bytes: number): string {
        if (bytes < 1024) return `${bytes} B`
        if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
        return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
    }

    /**
     * Get status color for display
     */
    getStatusColor(status: string): string {
        switch (status) {
            case 'completed':
                return 'text-green-400'
            case 'processing':
            case 'validating':
                return 'text-yellow-400'
            case 'failed':
            case 'rejected':
                return 'text-red-400'
            default:
                return 'text-gray-400'
        }
    }

    /**
     * Get validation status color and label
     */
    getValidationInfo(status: string | null): { color: string; label: string; icon: string } {
        switch (status) {
            case 'approved':
                return { color: 'text-green-400', label: 'Approved', icon: '✓' }
            case 'needs_review':
                return { color: 'text-yellow-400', label: 'Needs Review', icon: '⚠️' }
            case 'rejected':
                return { color: 'text-red-400', label: 'Rejected', icon: '✗' }
            default:
                return { color: 'text-gray-400', label: 'Pending', icon: '...' }
        }
    }
}

export const documentService = new DocumentService()
