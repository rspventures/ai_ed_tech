/**
 * AI Tutor Platform - Test Service
 * API client for Topic-level tests (10 questions from subtopics)
 */
import api from '../api/client';

export interface TestQuestion {
    question_id: string;
    question: string;
    options: string[];
    subtopic_id?: string;
    subtopic_name?: string;
    question_type?: 'multiple_choice' | 'multi_select';
}

export interface TestStartResponse {
    test_id: string;
    topic_name: string;
    topic_id: string;
    questions: TestQuestion[];
    time_limit_seconds: number | null;
    total_questions: number;
}

export interface TestAnswerItem {
    question_id: string;
    question: string;
    answer: string | string[];
    correct_answer: string | string[];
    subtopic_id?: string;
}

export interface QuestionExplanation {
    question: string;
    student_answer: string;
    correct_answer: string;
    is_correct: boolean;
    explanation: string;
}

export interface TestFeedback {
    summary: string;
    strengths: string[];
    weaknesses: string[];
    recommendations: string[];
    encouragement: string;
}

export interface TestResult {
    id: string;
    score: number;
    total_questions: number;
    correct_questions: number;
    duration_seconds: number | null;
    completed_at: string;
    topic_name: string;
    question_results: QuestionExplanation[];
    feedback: TestFeedback | null;
}

export interface TestHistoryItem {
    id: string;
    score: number;
    total_questions: number;
    correct_questions: number;
    topic_name: string;
    completed_at: string;
}

export const testService = {
    /**
     * Start a topic-level test
     * Uses extended timeout for AI-generated questions
     */
    async startTest(topicId: string, timeLimitMinutes: number = 10): Promise<TestStartResponse> {
        const response = await api.post<TestStartResponse>('/tests/start', {
            topic_id: topicId,
            time_limit_minutes: timeLimitMinutes
        }, {
            timeout: 60000, // 60 seconds for AI generation
        });
        return response.data;
    },

    /**
     * Submit test answers and get results
     */
    async submitTest(
        testId: string,
        topicId: string,
        topicName: string,
        answers: TestAnswerItem[],
        durationSeconds: number
    ): Promise<TestResult> {
        const response = await api.post<TestResult>('/tests/submit', {
            test_id: testId,
            topic_id: topicId,
            topic_name: topicName,
            answers,
            duration_seconds: durationSeconds
        }, {
            timeout: 60000, // 60 seconds for AI feedback generation
        });
        return response.data;
    },

    /**
     * Get test history
     */
    async getHistory(): Promise<TestHistoryItem[]> {
        const response = await api.get<TestHistoryItem[]>('/tests/history');
        return response.data;
    }
};

export default testService;
