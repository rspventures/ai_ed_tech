/**
 * AI Tutor Platform - Test Service
 * API client for Topic-level tests
 */
import api from './api'

export interface TestQuestion {
    question_id: string
    question: string
    options: string[]
    subtopic_id?: string
    subtopic_name?: string
    question_type?: 'multiple_choice' | 'multi_select'
}

export interface TestStartResponse {
    test_id: string
    topic_name: string
    topic_id: string
    questions: TestQuestion[]
    time_limit_seconds: number | null
    total_questions: number
}

export interface TestAnswerItem {
    question_id: string
    question: string
    answer: string | string[]
    correct_answer: string | string[]
    subtopic_id?: string
}

export interface QuestionExplanation {
    question: string
    student_answer: string
    correct_answer: string
    is_correct: boolean
    explanation: string
}

export interface TestFeedback {
    summary: string
    strengths: string[]
    weaknesses: string[]
    recommendations: string[]
    encouragement: string
}

export interface TestResult {
    id: string
    score: number
    total_questions: number
    correct_questions: number
    duration_seconds: number | null
    completed_at: string
    topic_name: string
    question_results: QuestionExplanation[]
    feedback: TestFeedback | null
}

export interface TestHistoryItem {
    id: string
    score: number
    total_questions: number
    correct_questions: number
    topic_name: string
    completed_at: string
}

export const testService = {
    async startTest(topicId: string, timeLimitMinutes: number = 10): Promise<TestStartResponse> {
        const response = await api.post<TestStartResponse>('/tests/start', {
            topic_id: topicId,
            time_limit_minutes: timeLimitMinutes
        })
        return response.data
    },

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
        })
        return response.data
    },

    async getHistory(): Promise<TestHistoryItem[]> {
        const response = await api.get<TestHistoryItem[]>('/tests/history')
        return response.data
    }
}

export default testService
