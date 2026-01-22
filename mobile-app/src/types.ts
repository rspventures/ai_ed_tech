/**
 * Minimal type definitions for login-only mobile app
 */

// User type (from /auth/me endpoint)
export interface User {
    id: string;
    email: string;
    first_name: string;
    last_name: string;
    role: 'student' | 'parent' | 'teacher' | 'admin';
    is_active: boolean;
    is_verified: boolean;
    created_at: string;
}

// Register data
export interface RegisterData {
    first_name: string;
    last_name: string;
    email: string;
    password: string;
    role?: 'student'; // Default to student
}

// Login credentials
export interface LoginCredentials {
    email: string;
    password: string;
}

// Token response from /auth/login
export interface TokenResponse {
    access_token: string;
    refresh_token: string;
    token_type: string;
    expires_in: number;
}

// API error response
export interface ApiError {
    detail: string;
}

// Subject (from /curriculum/subjects)
export interface Subject {
    id: string;
    name: string;
    slug: string;
    description: string | null;
    icon: string | null;
    color: string;
    is_active: boolean;
    display_order: number;
}

// Progress data (from /curriculum/progress)
export interface EnrichedProgress {
    topic_id: string;
    topic_name: string;
    subject_name: string;
    mastery_level: number;
    questions_attempted: number;
    questions_correct: number;
    current_streak: number;
    last_activity: string | null;
}

// Topic (from /curriculum/subjects/{slug})
export interface Topic {
    id: string;
    subject_id: string;
    name: string;
    slug: string;
    description: string | null;
    grade_level: number;
    difficulty: number;
    display_order: number;
    is_active: boolean;
}

// Subject with topics
export interface SubjectWithTopics extends Subject {
    topics: Topic[];
}

// Subtopic (from /curriculum/topics/{slug})
export interface Subtopic {
    id: string;
    topic_id: string;
    name: string;
    slug: string;
    description: string | null;
    difficulty: 'easy' | 'medium' | 'hard';
    display_order: number;
    is_active: boolean;
}

// Topic with subtopics
export interface TopicWithSubtopics extends Topic {
    subtopics: Subtopic[];
}

// Study action (next recommended step)
export interface StudyAction {
    action_type: 'lesson' | 'practice' | 'assessment' | 'complete';
    resource_id: string;
    resource_name: string;
    reason: string;
    mastery_level: number;
}

// Learning path for a topic
export interface LearningPath {
    topic_id: string;
    current_mastery: number;
    total_lessons: number;
    completed_lessons: number;
    completed_practice: number;
    next_action: StudyAction;
}

// Lesson content
export interface Lesson {
    id: string;
    subtopic_id: string;
    title: string;
    content: string | LessonContent;
    summary: string;
    key_points: string[];
    examples: string[];
    is_completed: boolean;
    style: 'story' | 'facts' | 'visual';
}

export interface LessonContent {
    hook: string;
    introduction: string;
    sections: { title: string; content: string; image_prompt?: string }[];
    summary: string;
    fun_fact: string;
    analogy?: string; // Optional based on style
    interactive_element?: any;
}

// Question for practice
export interface Question {
    question_id: string;
    question: string;
    question_type: 'single_select' | 'multi_select' | 'boolean';
    options: string[];
    hint: string;
    subject: string;
    topic: string;
    subtopic: string;
    difficulty: 'easy' | 'medium' | 'hard';
}

// Answer feedback
export interface QuestionFeedback {
    is_correct: boolean;
    score: number;
    feedback: string;
    explanation: string;
    correct_answer: string | string[];
    hint_for_retry?: string;
}

// Assessment types
export interface AssessmentStartResponse {
    assessment_id: string;
    questions: Question[];
}

export interface AssessmentSubmissionItem {
    question_id: string;
    question: string;
    options: string[];
    answer: string;
    correct_answer: string; // Is this needed for submission? Frontend sends it... weird.
}

export interface AssessmentResult {
    score: number;
    total_questions: number;
    correct_questions: number;
    feedback: {
        overall_score_interpretation: string;
        strengths: string[];
        areas_of_improvement: string[];
        ways_to_improve: string[];
        encouraging_words: string;
        practical_assignments: string[];
    };
    details: {
        question: string;
        student_answer: string;
        correct_answer: string;
        is_correct: boolean;
    }[];
}

// ============================================================================
// Flashcard Types
// ============================================================================

export type FlashcardDifficulty = 'easy' | 'medium' | 'hard';

export interface FlashcardItem {
    front: string;
    back: string;
    difficulty?: FlashcardDifficulty;
}

export interface FlashcardDeck {
    id: string;
    subtopic_id: string;
    grade_level: number;
    title: string;
    description?: string;
    cards: FlashcardItem[];
    card_count: number;
    generated_by: string;
    cards_reviewed?: number;
    cards_mastered?: number;
    mastery_percentage?: number;
}

export interface FlashcardDeckListItem {
    id: string;
    subtopic_id: string;
    subtopic_name: string;
    title: string;
    card_count: number;
    mastery_percentage?: number;
}

