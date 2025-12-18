/**
 * Chat Service - API calls for the interactive AI tutor
 */
import api from './api'
import type { ChatRequest, ChatResponse, ChatHistory } from '@/types'

export const chatService = {
    /**
     * Send a message to the AI tutor
     */
    async askTutor(request: ChatRequest): Promise<ChatResponse> {
        const response = await api.post('/chat/ask', request)
        return response.data
    },

    /**
     * Get chat history for a session
     */
    async getHistory(sessionId: string): Promise<ChatHistory> {
        const response = await api.get(`/chat/history/${sessionId}`)
        return response.data
    },

    /**
     * Clear a chat session
     */
    async clearSession(sessionId: string): Promise<void> {
        await api.delete(`/chat/session/${sessionId}`)
    }
}

export default chatService
