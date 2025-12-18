/**
 * Study Service - API client for adaptive learning and lesson endpoints
 */
import { api } from './api'
import type { Lesson, LearningPath, LessonProgress, StudyAction } from '@/types'

export const studyService = {
    /**
     * Get the recommended next study action for a topic
     */
    async getNextStep(topicId: string): Promise<StudyAction> {
        const response = await api.get(`/study/next-step/${topicId}`)
        return response.data
    },

    /**
     * Get the full learning path for a topic
     */
    async getLearningPath(topicId: string): Promise<LearningPath> {
        const response = await api.get(`/study/path/${topicId}`)
        return response.data
    },

    /**
     * Get a lesson for a subtopic (generates if doesn't exist)
     */
    async getLesson(subtopicId: string): Promise<Lesson> {
        const response = await api.get(`/study/lesson/${subtopicId}`)
        return response.data
    },

    /**
     * Mark a lesson as completed
     */
    async completeLesson(lessonId: string, timeSpentSeconds: number): Promise<LessonProgress> {
        const response = await api.post(`/study/lesson/${lessonId}/complete`, {
            time_spent_seconds: timeSpentSeconds
        })
        return response.data
    },

    /**
     * Force generate a new lesson with specific style
     */
    async generateLesson(
        subtopicId: string,
        gradeLevel: number = 1,
        style: 'story' | 'facts' | 'visual' = 'story'
    ): Promise<Lesson> {
        const response = await api.post('/study/lesson/generate', {
            subtopic_id: subtopicId,
            grade_level: gradeLevel,
            style
        })
        return response.data
    },

    /**
     * Get progress for a specific subtopic
     */
    async getSubtopicProgress(subtopicId: string): Promise<{
        mastery_level: number
        lesson_completed: boolean
        practice_count: number
    }> {
        const response = await api.get(`/study/subtopic/${subtopicId}/progress`)
        return response.data
    }
}
