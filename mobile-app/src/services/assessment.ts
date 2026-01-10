import api from '../api/client';
import { AssessmentStartResponse, AssessmentSubmissionItem, AssessmentResult } from '../types';

export const assessmentService = {
    /**
     * Start an assessment - uses extended timeout for AI question generation
     */
    async startAssessment(topicId: string, subtopicId?: string): Promise<AssessmentStartResponse> {
        const payload: any = { topic_id: topicId };
        if (subtopicId) payload.subtopic_id = subtopicId;

        const response = await api.post<AssessmentStartResponse>('/assessment/start', payload, {
            timeout: 60000, // 60 seconds for AI-generated assessment
        });
        return response.data;
    },

    async submitAssessment(payload: {
        topic_id: string;
        answers: AssessmentSubmissionItem[];
        assessment_session_id: string;
        subject_name?: string;
        topic_name?: string;
    }): Promise<AssessmentResult> {
        const response = await api.post<AssessmentResult>('/assessment/submit', payload);
        return response.data;
    }
};

export default assessmentService;
