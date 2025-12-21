/**
 * Visuals Service - API client for AI image generation
 */
import api from './api'

export interface VisualRequest {
    concept: string
    grade: number
    size?: string  // "1024x1024" | "1792x1024" | "1024x1792"
    quality?: string  // "standard" | "hd"
    additional_context?: string
    student_id?: string
}

export interface Visual {
    id: string
    concept: string
    grade_level: number
    image_url: string | null
    image_path: string | null
    enhanced_prompt: string
    provider: string
    status: string
    created_at: string
}

export interface VisualListResponse {
    visuals: Visual[]
    total: number
}

export const visualsService = {
    /**
     * Generate a visual explanation for a concept
     */
    async explain(request: VisualRequest): Promise<Visual> {
        const response = await api.post('/visuals/explain', request)
        return response.data
    },

    /**
     * Get a specific visual by ID
     */
    async get(visualId: string): Promise<Visual> {
        const response = await api.get(`/visuals/${visualId}`)
        return response.data
    },

    /**
     * List all generated visuals
     */
    async list(studentId?: string, limit = 20, offset = 0): Promise<VisualListResponse> {
        const params = new URLSearchParams()
        if (studentId) params.append('student_id', studentId)
        params.append('limit', limit.toString())
        params.append('offset', offset.toString())

        const response = await api.get(`/visuals/?${params.toString()}`)
        return response.data
    },

    /**
     * Delete a visual
     */
    async delete(visualId: string): Promise<void> {
        await api.delete(`/visuals/${visualId}`)
    },
}

export default visualsService
