import api from '../api/client';
import { TopicWithSubtopics, LearningPath, Lesson } from '../types';

export const studyService = {
    /**
     * Get topic with its subtopics
     */
    async getTopic(slug: string): Promise<TopicWithSubtopics> {
        const response = await api.get<TopicWithSubtopics>(`/curriculum/topics/${slug}`);
        return response.data;
    },

    /**
     * Get the full learning path for a topic
     */
    async getLearningPath(topicId: string): Promise<LearningPath> {
        const response = await api.get<LearningPath>(`/study/path/${topicId}`);
        return response.data;
    },

    /**
     * Get a lesson for a subtopic (generates if doesn't exist)
     * Uses extended timeout since LLM generation can take 30-60 seconds
     */
    async getLesson(subtopicId: string): Promise<Lesson> {
        const response = await api.get<Lesson>(`/study/lesson/${subtopicId}`, {
            timeout: 60000, // 60 seconds for LLM-generated content
        });
        return response.data;
    },

    /**
     * Mark a lesson as completed
     */
    async completeLesson(lessonId: string, timeSpentSeconds: number): Promise<void> {
        await api.post(`/study/lesson/${lessonId}/complete`, {
            time_spent_seconds: timeSpentSeconds
        });
    },

    /**
     * Get progress for a specific subtopic
     */
    async getSubtopicProgress(subtopicId: string): Promise<{
        mastery_level: number;
        lesson_completed: boolean;
        practice_count: number;
    }> {
        const response = await api.get(`/study/subtopic/${subtopicId}/progress`);
        return response.data;
    }
};

export default studyService;
