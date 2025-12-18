/**
 * TypeScript type definitions for the AI Tutor Platform
 */

// User types
export interface User {
    id: string
    email: string
    first_name: string
    last_name: string
    role: UserRole
    avatar_url: string | null
    timezone: string
    is_active: boolean
    is_verified: boolean
    created_at: string
    last_login?: string | null
}

export type UserRole = 'student' | 'parent' | 'teacher' | 'admin'

export interface UserProfile extends User {
    students: Student[]
}

export interface Student {
    id: string
    parent_id: string
    first_name: string
    last_name: string
    display_name: string | null
    avatar_url: string | null
    theme_color: string
    grade_level: number
    birth_date: string | null
    is_active: boolean
    created_at: string
    // Gamification
    xp_total?: number
    level?: number
    current_streak?: number
    longest_streak?: number
    last_activity_date?: string | null
}

// Authentication types
export interface TokenResponse {
    access_token: string
    refresh_token: string
    token_type: string
    expires_in: number
}

export interface LoginCredentials {
    email: string
    password: string
}

export interface RegisterData {
    email: string
    password: string
    first_name: string
    last_name: string
}

// Curriculum types
export interface Subject {
    id: string
    name: string
    slug: string
    description: string | null
    icon: string | null
    color: string
    is_active: boolean
    display_order: number
}

export interface Topic {
    id: string
    subject_id: string
    name: string
    slug: string
    description: string | null
    grade_level: number
    learning_objectives: string[] | null
    estimated_duration_minutes: number
    is_active: boolean
}

export interface Subtopic {
    id: string
    topic_id: string
    name: string
    slug: string
    description: string | null
    difficulty: DifficultyLevel
    is_active: boolean
}

export type DifficultyLevel = 'easy' | 'medium' | 'hard'

// Progress types
export interface Progress {
    id: string
    student_id: string
    subtopic_id: string
    questions_attempted: number
    questions_correct: number
    current_streak: number
    best_streak: number
    mastery_level: number
    total_time_seconds: number
    last_practiced_at: string | null
}

export interface EnrichedProgress extends Progress {
    subject_name: string
    topic_name: string
    subtopic_name: string
}

// Assessment types
export interface AssessmentQuestion {
    question_id: string
    question: string
    options: string[]
    question_type?: 'multiple_choice' | 'multi_select'
}

export interface AssessmentStartResponse {
    assessment_id: string
    topic_name: string
    questions: AssessmentQuestion[]
}

export interface AssessmentSubmissionItem {
    question_id: string
    question: string
    options: string[]
    answer: string | string[]
    correct_answer: string | string[]
}

export interface AssessmentSubmitRequest {
    topic_id: string
    answers: AssessmentSubmissionItem[]
    assessment_session_id: string
    subject_name?: string
    topic_name?: string
}

export interface AssessmentResultDetail {
    question: string
    student_answer: string
    correct_answer: string
    is_correct: boolean
    explanation: string
}

export interface AssessmentFeedback {
    overall_score_interpretation: string
    strengths: string[]
    areas_of_improvement: string[]
    ways_to_improve: string[]
    practical_assignments: string[]
    encouraging_words: string
    pattern_analysis: string
}

export interface AssessmentResult {
    id: string
    topic_name?: string
    score: number
    total_questions: number
    correct_questions: number
    completed_at: string
    details?: AssessmentResultDetail[]
    feedback?: AssessmentFeedback
}

// API error type
export interface ApiError {
    detail: string
    status?: number
}

// ============================================================================
// Lesson & Study Types
// ============================================================================

export type StudyActionType = 'lesson' | 'practice' | 'assessment' | 'complete'

export interface LessonSection {
    title: string
    content: string
    example?: string
}

export interface LessonContent {
    hook: string
    introduction: string
    sections: LessonSection[]
    summary: string
    fun_fact?: string
}

export interface Lesson {
    id: string
    subtopic_id: string
    grade_level: number
    title: string
    content: LessonContent
    generated_by: string
    created_at: string
    is_completed?: boolean
    completed_at?: string
}

export interface StudyAction {
    action_type: StudyActionType
    resource_id: string
    resource_name: string
    reason: string
    mastery_level: number
    estimated_time_minutes?: number
    difficulty?: string
}

export interface LearningPath {
    topic_id: string
    topic_name: string
    current_mastery: number
    next_action: StudyAction
    completed_lessons: number
    total_lessons: number
    completed_practice: number
    recommended_path: StudyAction[]
}

export interface LessonProgress {
    lesson_id: string
    student_id: string
    completed_at: string
    time_spent_seconds: number
}

// ============================================================================
// Chat Types (Interactive AI Tutor)
// ============================================================================

export type ChatContextType = 'lesson' | 'question' | 'general'
export type ChatRole = 'user' | 'assistant' | 'system'

export interface ChatMessage {
    role: ChatRole
    content: string
    timestamp: string
}

export interface ChatRequest {
    message: string
    context_type: ChatContextType
    context_id?: string
    session_id?: string
}

export interface ChatResponse {
    response: string
    session_id: string
    suggestions: string[]
}

export interface ChatHistory {
    session_id: string
    messages: ChatMessage[]
    context_type: ChatContextType
    context_id?: string
}

// ============================================================================
// Parent Dashboard Types
// ============================================================================

export interface SubjectMastery {
    subject_id: string
    subject_name: string
    average_score: number
    topics_completed: number
    total_topics: number
    mastery_level: 'struggling' | 'learning' | 'proficient' | 'mastered'
}

export interface ActivityItem {
    timestamp: string
    action_type: string
    description: string
    subject?: string
    score?: number
    emoji: string
}

export interface ChildSummary {
    student_id: string
    student_name: string
    avatar_url?: string
    grade_level: number
    total_lessons_completed: number
    total_assessments_taken: number
    total_time_minutes: number
    average_score: number
    current_streak: number
    subject_mastery: SubjectMastery[]
    top_subjects: string[]
    needs_attention: string[]
}

export interface ChildListItem {
    student_id: string
    student_name: string
    avatar_url?: string
    grade_level: number
}

export interface WeeklyProgress {
    day: string
    lessons: number
    practice_time: number
    score?: number
}

export interface ChildDetail {
    summary: ChildSummary
    weekly_progress: WeeklyProgress[]
    recent_activity: ActivityItem[]
    ai_insights?: string
}
