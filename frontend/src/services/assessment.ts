import api from './api';
import type {
    AssessmentStartResponse,
    AssessmentResult,
    AssessmentSubmitRequest
} from '@/types';

export const assessmentService = {
    /**
     * Start a new assessment for a topic or subtopic
     */
    async startAssessment(topicId: string, subtopicId?: string): Promise<AssessmentStartResponse> {
        const url = subtopicId
            ? `/assessments/start/${topicId}?subtopic_id=${subtopicId}`
            : `/assessments/start/${topicId}`;
        const response = await api.post<AssessmentStartResponse>(url);
        return response.data;
    },

    /**
     * Submit an assessment
     */
    async submitAssessment(data: AssessmentSubmitRequest): Promise<AssessmentResult> {
        const response = await api.post<AssessmentResult>('/assessments/submit', data);
        return response.data;
    },

    /**
     * Get assessment history
     */
    async getHistory(): Promise<AssessmentResult[]> {
        const response = await api.get<AssessmentResult[]>('/assessments/history');
        return response.data;
    }
};

export default assessmentService;
