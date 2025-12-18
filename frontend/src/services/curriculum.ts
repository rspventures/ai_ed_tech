import api from './api';
import type { Subject, Topic, Subtopic, EnrichedProgress } from '@/types';

export interface SubjectWithTopics extends Subject {
    topics: Topic[];
}

export interface TopicWithSubtopics extends Topic {
    subtopics: Subtopic[];
}

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
     * Get a topic with its subtopics
     */
    async getTopic(slug: string): Promise<TopicWithSubtopics> {
        const response = await api.get<TopicWithSubtopics>(`/curriculum/topics/${slug}`);
        return response.data;
    },

    /**
     * Get topics by grade level
     */
    async getTopicsByGrade(gradeLevel: number): Promise<Topic[]> {
        const response = await api.get<Topic[]>(`/curriculum/grade/${gradeLevel}/topics`);
        return response.data;
    },

    /**
     * Get student progress
     */
    async getProgress(): Promise<EnrichedProgress[]> {
        const response = await api.get<EnrichedProgress[]>('/curriculum/progress');
        return response.data;
    },
};

export default curriculumService;
