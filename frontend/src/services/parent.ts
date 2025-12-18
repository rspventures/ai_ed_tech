/**
 * Parent Dashboard Service - API calls for parent/guardian analytics
 */
import api from './api'
import type {
    ChildListItem,
    ChildSummary,
    ChildDetail,
    ActivityItem,
    WeeklyProgress
} from '@/types'

export const parentService = {
    /**
     * Get list of all children for the current parent
     */
    async getChildren(): Promise<ChildListItem[]> {
        const response = await api.get('/parent/children')
        return response.data
    },

    /**
     * Get full detail analytics for a child
     */
    async getChildDetail(studentId: string): Promise<ChildDetail> {
        const response = await api.get(`/parent/child/${studentId}`)
        return response.data
    },

    /**
     * Get quick summary for a child
     */
    async getChildSummary(studentId: string): Promise<ChildSummary> {
        const response = await api.get(`/parent/child/${studentId}/summary`)
        return response.data
    },

    /**
     * Get activity feed for a child
     */
    async getChildActivity(studentId: string, limit = 20): Promise<ActivityItem[]> {
        const response = await api.get(`/parent/child/${studentId}/activity`, {
            params: { limit }
        })
        return response.data
    },

    /**
     * Get weekly progress data for charts
     */
    async getWeeklyProgress(studentId: string): Promise<WeeklyProgress[]> {
        const response = await api.get(`/parent/child/${studentId}/weekly`)
        return response.data
    }
}

export default parentService
