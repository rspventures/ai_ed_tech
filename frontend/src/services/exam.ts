import api from './api';

export interface ExamStartRequest {
    subject_id: string;
    topic_ids: string[];
    num_questions: number;
    time_limit_minutes?: number;
}

export interface ExamQuestion {
    question_id: string;
    question: string;
    options: string[];
    topic_id: string;
    topic_name: string;
}

export interface ExamStartResponse {
    exam_id: string;
    subject_name: string;
    topics: { topic_id: string; topic_name: string }[];
    questions: ExamQuestion[];
    time_limit_seconds: number | null;
    total_questions: number;
}

export interface ExamSubmissionItem {
    question_id: string;
    question: string;
    options: string[];
    answer: string;
    correct_answer: string;
    topic_id: string;
}

export interface ExamSubmitRequest {
    exam_id: string;
    subject_id: string;
    subject_name: string;
    topic_ids: string[];
    answers: ExamSubmissionItem[];
    duration_seconds?: number;
}

export interface TopicBreakdown {
    topic_id: string;
    topic_name: string;
    correct: number;
    total: number;
    percentage: number;
}

export interface ExamFeedback {
    overall_interpretation: string;
    topic_analysis: string[];
    strengths: string[];
    areas_to_focus: string[];
    study_recommendations: string[];
    encouraging_message: string;
}

export interface ExamResult {
    id: string;
    score: number;
    total_questions: number;
    correct_questions: number;
    duration_seconds?: number;
    completed_at: string;
    subject_name: string;
    topic_breakdown: TopicBreakdown[];
    feedback?: ExamFeedback;
}

export interface ExamHistoryItem {
    id: string;
    score: number;
    total_questions: number;
    correct_questions: number;
    subject_name: string;
    topics_count: number;
    completed_at: string;
}

export const examService = {
    /**
     * Start a new exam
     */
    async startExam(data: ExamStartRequest): Promise<ExamStartResponse> {
        const response = await api.post<ExamStartResponse>('/exams/start', data);
        return response.data;
    },

    /**
     * Submit an exam
     */
    async submitExam(data: ExamSubmitRequest): Promise<ExamResult> {
        const response = await api.post<ExamResult>('/exams/submit', data);
        return response.data;
    },

    /**
     * Get exam history
     */
    async getHistory(): Promise<ExamHistoryItem[]> {
        const response = await api.get<ExamHistoryItem[]>('/exams/history');
        return response.data;
    }
};

export default examService;
