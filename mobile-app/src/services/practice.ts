import api from '../api/client';
import { Question, QuestionFeedback } from '../types';

export const practiceService = {
    /**
     * Start a practice session for a subtopic or topic
     * Uses extended timeout since questions may be AI-generated
     */
    async startPractice(params: { subtopic_id?: string; topic_slug?: string }): Promise<Question> {
        const response = await api.post<Question>('/practice/start', params, {
            timeout: 60000, // 60 seconds for AI-generated questions
        });
        return response.data;
    },

    /**
     * Submit an answer for a question
     */
    async submitAnswer(questionId: string, answer: string | string[]): Promise<QuestionFeedback> {
        const response = await api.post<QuestionFeedback>('/practice/answer', {
            question_id: questionId,
            answer: answer
        });
        return response.data;
    }
};

export default practiceService;
