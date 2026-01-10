import api from '../api/client';
import { Subject, EnrichedProgress, SubjectWithTopics } from '../types';

export const curriculumService = {
    /**
     * Get all subjects
     */
    async getSubjects(): Promise<Subject[]> {
        const response = await api.get<Subject[]>('/curriculum/subjects');
        return response.data;
    },

    /**
     * Get a subject with its topics
     */
    async getSubject(slug: string): Promise<SubjectWithTopics> {
        const response = await api.get<SubjectWithTopics>(`/curriculum/subjects/${slug}`);
        return response.data;
    },

    /**
     * Get student progress across all topics
     */
    async getProgress(): Promise<EnrichedProgress[]> {
        const response = await api.get<EnrichedProgress[]>('/curriculum/progress');
        return response.data;
    },

    /**
     * Get a single topic by slug
     */
    async getTopic(slug: string): Promise<{ id: string; name: string }> {
        const response = await api.get<{ id: string; name: string }>(`/curriculum/topics/${slug}`);
        return response.data;
    },
};

export default curriculumService;
