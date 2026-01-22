import api from '../api/client';

export interface Document {
    id: string;
    original_filename: string;
    file_size: number;
    chunk_count: number;
    status: 'processing' | 'completed' | 'failed' | 'rejected';
    validation_status?: 'approved' | 'rejected' | 'needs_review';
    error_message?: string;
    created_at: string;
}

export interface ChatResponse {
    answer: string;
    sources: SearchResult[];
}

export interface SearchResult {
    content: string;
    similarity: number;
}

export const documentService = {
    /**
     * List user documents
     */
    async listDocuments(): Promise<{ documents: Document[] }> {
        const response = await api.get<{ documents: Document[] }>('/documents/list', {
            timeout: 30000, // 30 seconds
        });
        return response.data;
    },

    /**
     * Upload a document
     * Uses extended timeout for large file uploads and processing
     */
    async uploadDocument(file: any): Promise<Document> {
        const formData = new FormData();
        formData.append('file', {
            uri: file.uri,
            name: file.name,
            type: file.mimeType || 'application/pdf',
        } as any);

        const response = await api.post<Document>('/documents/upload', formData, {
            headers: {
                'Content-Type': 'multipart/form-data',
            },
            timeout: 120000, // 2 minutes for large file uploads + processing
        });
        return response.data;
    },

    /**
     * Delete a document
     */
    async deleteDocument(docId: string): Promise<void> {
        await api.delete(`/documents/${docId}`);
    },

    /**
     * Chat with a document
     * Uses extended timeout for AI-powered responses
     */
    async chatWithDocument(docId: string, message: string, gradeLevel: number = 5): Promise<ChatResponse> {
        const response = await api.post<ChatResponse>(`/documents/${docId}/chat`, {
            query: message,
            grade: gradeLevel,
        }, {
            timeout: 60000, // 60 seconds for AI chat responses
        });
        return response.data;
    },

    /**
     * Generate quiz from document
     */
    async generateQuiz(docId: string, numQuestions: number = 5, gradeLevel: number = 5): Promise<QuizResponse> {
        const response = await api.post<QuizResponse>(`/documents/${docId}/quiz`, {
            num_questions: numQuestions,
            grade: gradeLevel,
        }, {
            timeout: 90000, // 90 seconds for quiz generation
        });
        return response.data;
    }
};

export interface QuizQuestion {
    question: string;
    options: string[];
    correct_answer: string;
    explanation: string;
}

export interface QuizResponse {
    questions: QuizQuestion[];
    document_id: string;
    total_questions: number;
}
