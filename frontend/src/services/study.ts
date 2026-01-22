/**
 * Study Service - API client for adaptive learning and lesson endpoints
 */
import { api } from './api'
import type { Lesson, LessonV2, LearningPath, LessonProgress, StudyAction } from '@/types'

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
     * Get a Lesson 2.0 (Interactive Playlist) for a subtopic
     */
    async getLessonV2(subtopicId: string): Promise<LessonV2> {
        const response = await api.get(`/study/lesson/v2/${subtopicId}`)
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
    },

    // ========================================================================
    // Flashcard Methods
    // ========================================================================

    /**
     * Get or generate a flashcard deck for a subtopic
     */
    async getFlashcards(subtopicId: string): Promise<import('@/types').FlashcardDeck> {
        const response = await api.get(`/study/flashcards/${subtopicId}`)
        return response.data
    },

    /**
     * List all flashcard decks for a topic
     */
    async listFlashcardDecks(topicId: string): Promise<import('@/types').FlashcardDeckListItem[]> {
        const response = await api.get(`/study/flashcards/topic/${topicId}`)
        return response.data
    },

    // ========================================================================
    // Favorites Methods (Quick Review)
    // ========================================================================

    /**
     * Add a module to favorites
     */
    async addFavorite(lessonId: string, moduleIndex: number): Promise<import('@/types').FavoriteModule> {
        const response = await api.post('/study/favorites', {
            lesson_id: lessonId,
            module_index: moduleIndex
        })
        return response.data
    },

    /**
     * Remove a module from favorites
     */
    async removeFavorite(favoriteId: string): Promise<void> {
        await api.delete(`/study/favorites/${favoriteId}`)
    },

    /**
     * Get all favorites for the student
     */
    async getAllFavorites(): Promise<import('@/types').FavoriteListResponse> {
        const response = await api.get('/study/favorites')
        return response.data
    },

    /**
     * Get favorites by subtopic
     */
    async getFavoritesBySubtopic(subtopicId: string): Promise<import('@/types').FavoriteListResponse> {
        const response = await api.get(`/study/favorites/subtopic/${subtopicId}`)
        return response.data
    },

    /**
     * Get favorites by topic
     */
    async getFavoritesByTopic(topicId: string): Promise<import('@/types').FavoriteListResponse> {
        const response = await api.get(`/study/favorites/topic/${topicId}`)
        return response.data
    },

    /**
     * Get favorites by subject
     */
    async getFavoritesBySubject(subjectId: string): Promise<import('@/types').FavoriteListResponse> {
        const response = await api.get(`/study/favorites/subject/${subjectId}`)
        return response.data
    }
}


