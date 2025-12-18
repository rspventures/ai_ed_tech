import { useState, useEffect, useRef } from 'react'
import { useParams, useNavigate, useSearchParams } from 'react-router-dom'
import {
    CheckCircle,
    XCircle,
    ChevronRight,
    AlertCircle,
    Clock,
    Target,
    Award,
    Loader2,
    Sparkles,
    Star,
    TrendingUp,
    Lightbulb,
    BookOpen,
    Heart
} from 'lucide-react'

import { assessmentService } from '@/services/assessment'
import { curriculumService } from '@/services/curriculum'
import type {
    AssessmentStartResponse,
    AssessmentSubmissionItem,
    AssessmentResult,
    AssessmentQuestion,
    Topic,
    Subject
} from '@/types'

type AssessmentState = 'intro' | 'active' | 'submitting' | 'results'

// Utility to shuffle array
function shuffleArray<T>(array: T[]): T[] {
    const shuffled = [...array]
    for (let i = shuffled.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1));
        [shuffled[i], shuffled[j]] = [shuffled[j], shuffled[i]]
    }
    return shuffled
}

export default function AssessmentPage() {
    const { topicSlug } = useParams<{ topicSlug: string }>()
    const [searchParams] = useSearchParams()
    const navigate = useNavigate()
    const [showCelebration, setShowCelebration] = useState(false)

    // State
    const [status, setStatus] = useState<AssessmentState>('intro')
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)

    // Data
    const [topic, setTopic] = useState<Topic | null>(null)
    const [subject, setSubject] = useState<Subject | null>(null)
    const [assessmentData, setAssessmentData] = useState<AssessmentStartResponse | null>(null)
    const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0)
    // Store full question data for submission
    const [answeredQuestions, setAnsweredQuestions] = useState<{
        question: AssessmentQuestion,
        selectedAnswer: string,
        correctAnswer: string
    }[]>([])
    const [result, setResult] = useState<AssessmentResult | null>(null)
    // Store shuffled options per question so answers aren't always first
    const [shuffledOptionsMap, setShuffledOptionsMap] = useState<Record<string, string[]>>({})

    // Timer
    const [secondsElapsed, setSecondsElapsed] = useState(0)
    const timerRef = useRef<ReturnType<typeof setInterval> | null>(null)


    useEffect(() => {
        loadTopic()
        return () => stopTimer()
    }, [topicSlug])

    const startTimer = () => {
        timerRef.current = setInterval(() => {
            setSecondsElapsed((prev: number) => prev + 1)
        }, 1000)
    }

    const stopTimer = () => {
        if (timerRef.current) {
            clearInterval(timerRef.current)
        }
    }

    const loadTopic = async () => {
        if (!topicSlug) return
        try {
            const data = await curriculumService.getTopic(topicSlug)
            setTopic(data)
            // Also try to get subject info
            const subjectSlug = searchParams.get('subject')
            if (subjectSlug) {
                try {
                    const subjectData = await curriculumService.getSubject(subjectSlug)
                    setSubject(subjectData)
                } catch { }
            }
        } catch {
            setError('Topic not found')
        } finally {
            setLoading(false)
        }
    }

    const startAssessment = async () => {
        if (!topic) return
        setStatus('intro')
        setLoading(true)
        setError(null)
        setAnsweredQuestions([])
        setCurrentQuestionIndex(0)
        setSecondsElapsed(0)

        try {
            // Get optional subtopic_id from query params
            const subtopicId = searchParams.get('subtopic') || undefined
            const data = await assessmentService.startAssessment(topic.id, subtopicId)
            setAssessmentData(data)

            // Create shuffled options for each question
            // This ensures the correct answer isn't always in the same position
            const optionsMap: Record<string, string[]> = {}
            data.questions.forEach((q: AssessmentQuestion) => {
                optionsMap[q.question_id] = shuffleArray([...q.options])
            })
            setShuffledOptionsMap(optionsMap)

            setStatus('active')
            startTimer()
        } catch {
            setError('Failed to start assessment. Please try again.')
        } finally {
            setLoading(false)
        }
    }


    const selectAnswer = (answer: string) => {
        if (!assessmentData) return
        const question = assessmentData.questions[currentQuestionIndex]

        // Store the answer with full context (correct answer is first option by convention)
        const existingIndex = answeredQuestions.findIndex(
            aq => aq.question.question_id === question.question_id
        )

        const questionData = {
            question,
            selectedAnswer: answer,
            correctAnswer: question.options[0] // First option is always correct
        }

        if (existingIndex >= 0) {
            setAnsweredQuestions((prev: typeof answeredQuestions) => {
                const updated = [...prev]
                updated[existingIndex] = questionData
                return updated
            })
        } else {
            setAnsweredQuestions((prev: typeof answeredQuestions) => [...prev, questionData])
        }
    }

    const getCurrentAnswer = () => {
        if (!assessmentData) return null
        const question = assessmentData.questions[currentQuestionIndex]
        const answered = answeredQuestions.find(
            aq => aq.question.question_id === question.question_id
        )
        return answered?.selectedAnswer || null
    }

    const nextQuestion = () => {
        if (!assessmentData) return
        if (currentQuestionIndex < assessmentData.questions.length - 1) {
            setCurrentQuestionIndex((prev: number) => prev + 1)
        } else {
            submitAssessment()
        }
    }

    const submitAssessment = async () => {
        if (!assessmentData || !topic) return

        stopTimer()
        setStatus('submitting')

        // Format answers with full question context
        const submissionItems: AssessmentSubmissionItem[] = answeredQuestions.map(aq => ({
            question_id: aq.question.question_id,
            question: aq.question.question,
            options: aq.question.options,
            answer: aq.selectedAnswer,
            correct_answer: aq.correctAnswer
        }))

        try {
            const resultData = await assessmentService.submitAssessment({
                topic_id: topic.id,
                answers: submissionItems,
                assessment_session_id: assessmentData.assessment_id,
                subject_name: subject?.name,
                topic_name: topic.name
            })
            setResult(resultData)
            setStatus('results')
            if (Math.round(resultData.score) >= 70) {
                setShowCelebration(true)
                setTimeout(() => setShowCelebration(false), 4000)
            }
        } catch {
            setError('Failed to submit assessment.')
            setStatus('active')
        }
    }

    const formatTime = (seconds: number) => {
        const mins = Math.floor(seconds / 60)
        const secs = seconds % 60
        return `${mins}:${secs.toString().padStart(2, '0')}`
    }

    if (loading && !assessmentData) {
        return (
            <div className="min-h-screen flex items-center justify-center">
                <Loader2 className="w-8 h-8 text-primary-500 animate-spin" />
            </div>
        )
    }

    if (error || !topic) {
        return (
            <div className="min-h-screen flex items-center justify-center p-4">
                <div className="max-w-md w-full glass-card text-center p-8">
                    <AlertCircle className="w-12 h-12 text-red-500 mx-auto mb-4" />
                    <h2 className="text-xl font-bold text-white mb-2">Error</h2>
                    <p className="text-gray-400 mb-6">{error || 'Topic not found'}</p>
                    <button onClick={() => navigate('/dashboard')} className="btn-secondary w-full">
                        Back to Dashboard
                    </button>
                </div>
            </div>
        )
    }

    // 1. INTRO SCREEN
    if (status === 'intro') {
        return (
            <div className="min-h-screen py-12 px-4 sm:px-6 lg:px-8 flex items-center justify-center">
                <div className="max-w-2xl w-full glass-card p-8 text-center relative overflow-hidden">
                    <div className="absolute top-0 left-0 w-full h-2 bg-gradient-to-r from-primary-500 to-accent-500" />

                    <div className="w-20 h-20 bg-primary-500/20 rounded-full flex items-center justify-center mx-auto mb-6">
                        <Target className="w-10 h-10 text-primary-400" />
                    </div>

                    <h1 className="text-3xl font-bold text-white mb-4">
                        {topic.name} Assessment
                    </h1>

                    <p className="text-xl text-gray-300 mb-8 max-w-lg mx-auto">
                        Ready to test your knowledge? This assessment contains 5 questions.
                        Answer all questions, then receive detailed feedback!
                    </p>

                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-4 mb-8">
                        <div className="bg-white/5 p-4 rounded-xl">
                            <Clock className="w-6 h-6 text-blue-400 mx-auto mb-2" />
                            <p className="text-sm text-gray-400">Untimed</p>
                        </div>
                        <div className="bg-white/5 p-4 rounded-xl">
                            <BookOpen className="w-6 h-6 text-purple-400 mx-auto mb-2" />
                            <p className="text-sm text-gray-400">5 Questions</p>
                        </div>
                        <div className="bg-white/5 p-4 rounded-xl">
                            <Lightbulb className="w-6 h-6 text-yellow-400 mx-auto mb-2" />
                            <p className="text-sm text-gray-400">AI Feedback</p>
                        </div>
                    </div>

                    <div className="flex flex-col sm:flex-row gap-4 justify-center">
                        <button onClick={() => navigate(-1)} className="btn-secondary">
                            Cancel
                        </button>
                        <button
                            onClick={startAssessment}
                            disabled={loading}
                            className="btn-primary px-8 py-3 text-lg"
                        >
                            {loading ? <Loader2 className="w-5 h-5 animate-spin" /> : 'Start Assessment'}
                        </button>
                    </div>
                </div>
            </div>
        )
    }

    // 2. RESULTS SCREEN WITH AI FEEDBACK
    if (status === 'results' && result) {
        const percentage = Math.round(result.score)
        const passed = percentage >= 70
        const feedback = result.feedback

        return (
            <div className="min-h-screen py-8 px-4 sm:px-6 lg:px-8 relative overflow-hidden">
                {/* Celebration Animation */}
                {showCelebration && (
                    <div className="fixed inset-0 pointer-events-none z-50">
                        {[...Array(30)].map((_, i) => (
                            <div
                                key={i}
                                className="absolute animate-bounce"
                                style={{
                                    left: `${Math.random() * 100}%`,
                                    top: `${Math.random() * 100}%`,
                                    animationDelay: `${Math.random() * 0.5}s`,
                                    animationDuration: `${0.5 + Math.random() * 1}s`
                                }}
                            >
                                <Sparkles className={`w-6 h-6 ${['text-yellow-400', 'text-pink-400', 'text-blue-400', 'text-green-400', 'text-purple-400'][i % 5]}`} />
                            </div>
                        ))}
                    </div>
                )}

                <div className="max-w-4xl mx-auto">
                    {/* Score Header */}
                    <div className="glass-card p-8 text-center mb-6">
                        <div className={`w-24 h-24 rounded-full flex items-center justify-center mx-auto mb-4 ${passed ? 'bg-green-500/20' : 'bg-amber-500/20'}`}>
                            {passed ? (
                                <Award className="w-12 h-12 text-green-400" />
                            ) : (
                                <Target className="w-12 h-12 text-amber-400" />
                            )}
                        </div>

                        <h2 className="text-4xl font-bold text-white mb-2">
                            {feedback?.overall_score_interpretation || (passed ? 'Great Job!' : 'Keep Practicing!')}
                        </h2>

                        <p className="text-2xl text-gray-300 mb-4">
                            <span className={`font-bold ${passed ? 'text-green-400' : 'text-amber-400'}`}>
                                {percentage}%
                            </span>
                            <span className="text-lg ml-2">
                                ({result.correct_questions}/{result.total_questions} correct)
                            </span>
                        </p>

                        <p className="text-gray-400">Time: {formatTime(secondsElapsed)}</p>
                    </div>

                    {/* AI Feedback Sections */}
                    {feedback && (
                        <div className="grid gap-6 md:grid-cols-2">
                            {/* Strengths */}
                            <div className="glass-card p-6">
                                <div className="flex items-center gap-3 mb-4">
                                    <div className="w-10 h-10 bg-green-500/20 rounded-full flex items-center justify-center">
                                        <Star className="w-5 h-5 text-green-400" />
                                    </div>
                                    <h3 className="text-xl font-semibold text-white">Strengths</h3>
                                </div>
                                <ul className="space-y-2">
                                    {feedback.strengths.map((item, i) => (
                                        <li key={i} className="flex items-start gap-2 text-gray-300">
                                            <CheckCircle className="w-5 h-5 text-green-400 flex-shrink-0 mt-0.5" />
                                            <span>{item}</span>
                                        </li>
                                    ))}
                                </ul>
                            </div>

                            {/* Areas of Improvement */}
                            <div className="glass-card p-6">
                                <div className="flex items-center gap-3 mb-4">
                                    <div className="w-10 h-10 bg-amber-500/20 rounded-full flex items-center justify-center">
                                        <TrendingUp className="w-5 h-5 text-amber-400" />
                                    </div>
                                    <h3 className="text-xl font-semibold text-white">Areas to Improve</h3>
                                </div>
                                <ul className="space-y-2">
                                    {feedback.areas_of_improvement.map((item, i) => (
                                        <li key={i} className="flex items-start gap-2 text-gray-300">
                                            <Target className="w-5 h-5 text-amber-400 flex-shrink-0 mt-0.5" />
                                            <span>{item}</span>
                                        </li>
                                    ))}
                                </ul>
                            </div>

                            {/* Ways to Improve */}
                            <div className="glass-card p-6">
                                <div className="flex items-center gap-3 mb-4">
                                    <div className="w-10 h-10 bg-blue-500/20 rounded-full flex items-center justify-center">
                                        <Lightbulb className="w-5 h-5 text-blue-400" />
                                    </div>
                                    <h3 className="text-xl font-semibold text-white">Ways to Improve</h3>
                                </div>
                                <ul className="space-y-2">
                                    {feedback.ways_to_improve.map((item, i) => (
                                        <li key={i} className="flex items-start gap-2 text-gray-300">
                                            <ChevronRight className="w-5 h-5 text-blue-400 flex-shrink-0 mt-0.5" />
                                            <span>{item}</span>
                                        </li>
                                    ))}
                                </ul>
                            </div>

                            {/* Practical Assignments */}
                            <div className="glass-card p-6">
                                <div className="flex items-center gap-3 mb-4">
                                    <div className="w-10 h-10 bg-purple-500/20 rounded-full flex items-center justify-center">
                                        <BookOpen className="w-5 h-5 text-purple-400" />
                                    </div>
                                    <h3 className="text-xl font-semibold text-white">Practice Activities</h3>
                                </div>
                                <ul className="space-y-2">
                                    {feedback.practical_assignments.map((item, i) => (
                                        <li key={i} className="flex items-start gap-2 text-gray-300">
                                            <Sparkles className="w-5 h-5 text-purple-400 flex-shrink-0 mt-0.5" />
                                            <span>{item}</span>
                                        </li>
                                    ))}
                                </ul>
                            </div>
                        </div>
                    )}

                    {/* Encouraging Words */}
                    {feedback?.encouraging_words && (
                        <div className="glass-card p-6 mt-6 text-center">
                            <Heart className="w-8 h-8 text-pink-400 mx-auto mb-3" />
                            <p className="text-xl text-gray-200 italic">
                                "{feedback.encouraging_words}"
                            </p>
                        </div>
                    )}

                    {/* Question Results Accordion */}
                    {result.details && result.details.length > 0 && (
                        <div className="glass-card p-6 mt-6">
                            <h3 className="text-xl font-semibold text-white mb-4">Question Results</h3>
                            <div className="space-y-3">
                                {result.details.map((detail, i) => (
                                    <div
                                        key={i}
                                        className={`p-4 rounded-xl border-l-4 ${detail.is_correct
                                            ? 'bg-green-500/10 border-green-500'
                                            : 'bg-red-500/10 border-red-500'
                                            }`}
                                    >
                                        <div className="flex items-start gap-3">
                                            {detail.is_correct ? (
                                                <CheckCircle className="w-5 h-5 text-green-400 flex-shrink-0 mt-0.5" />
                                            ) : (
                                                <XCircle className="w-5 h-5 text-red-400 flex-shrink-0 mt-0.5" />
                                            )}
                                            <div className="flex-1">
                                                <p className="text-white font-medium mb-1">{detail.question}</p>
                                                <p className="text-sm text-gray-400">
                                                    Your answer: <span className={detail.is_correct ? 'text-green-400' : 'text-red-400'}>{detail.student_answer}</span>
                                                </p>
                                                {!detail.is_correct && (
                                                    <p className="text-sm text-gray-400">
                                                        Correct answer: <span className="text-green-400">{detail.correct_answer}</span>
                                                    </p>
                                                )}
                                            </div>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        </div>
                    )}

                    {/* Actions */}
                    <div className="flex gap-4 justify-center mt-8">
                        <button onClick={() => navigate('/dashboard')} className="btn-secondary">
                            Dashboard
                        </button>
                        <button
                            onClick={() => {
                                setResult(null)
                                setStatus('intro')
                            }}
                            className="btn-primary"
                        >
                            Try Again
                        </button>
                    </div>
                </div>
            </div>
        )
    }

    // 3. ACTIVE QUIZ (Continuous questions without feedback)
    if (!assessmentData) return null

    const question = assessmentData.questions[currentQuestionIndex]
    const currentAnswer = getCurrentAnswer()
    const isLast = currentQuestionIndex === assessmentData.questions.length - 1
    const progress = ((currentQuestionIndex) / assessmentData.questions.length) * 100

    return (
        <div className="min-h-screen py-8 px-4 sm:px-6 lg:px-8">
            <div className="max-w-3xl mx-auto">
                {/* Header */}
                <div className="flex items-center justify-between mb-8">
                    <div className="flex items-center gap-4">
                        <button
                            onClick={() => {
                                if (window.confirm("Quit assessment? Progress will be lost.")) {
                                    navigate('/dashboard')
                                }
                            }}
                            className="text-gray-400 hover:text-white"
                        >
                            Exit
                        </button>
                        <div className="h-2 w-32 sm:w-48 bg-white/10 rounded-full overflow-hidden">
                            <div
                                className="h-full bg-primary-500 transition-all duration-300"
                                style={{ width: `${progress}%` }}
                            />
                        </div>
                    </div>
                    <div className="flex items-center gap-2 text-primary-400 font-mono">
                        <Clock className="w-4 h-4" />
                        {formatTime(secondsElapsed)}
                    </div>
                </div>

                {/* Question Card */}
                <div className="glass-card p-6 sm:p-10 mb-8 min-h-[400px] flex flex-col">
                    <div className="mb-8">
                        <span className="text-sm font-medium text-gray-400 uppercase tracking-wider">
                            Question {currentQuestionIndex + 1} of {assessmentData.questions.length}
                        </span>
                        <h2 className="text-2xl sm:text-3xl font-bold text-white mt-2 leading-tight">
                            {question.question}
                        </h2>
                    </div>

                    <div className="space-y-3 flex-grow">
                        {(shuffledOptionsMap[question.question_id] || question.options).map((option: string, idx: number) => {
                            const isSelected = currentAnswer === option
                            return (
                                <button
                                    key={idx}
                                    onClick={() => selectAnswer(option)}
                                    className={`w-full p-4 rounded-xl text-left transition-all border-2 ${isSelected
                                        ? 'bg-primary-500/20 border-primary-500 text-white'
                                        : 'bg-white/5 border-transparent text-gray-300 hover:bg-white/10 hover:border-white/10'
                                        }`}
                                >
                                    <div className="flex items-center gap-3">
                                        <div className={`w-6 h-6 rounded-full border flex items-center justify-center ${isSelected ? 'border-primary-500 bg-primary-500' : 'border-gray-500'
                                            }`}>
                                            {isSelected && <div className="w-2 h-2 bg-white rounded-full" />}
                                        </div>
                                        <span className="text-lg">{option}</span>
                                    </div>
                                </button>
                            )
                        })}
                    </div>

                </div>

                {/* Navigation */}
                <div className="flex justify-end">
                    <button
                        onClick={nextQuestion}
                        disabled={!currentAnswer || status === 'submitting'}
                        className="btn-primary px-8 flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                        {status === 'submitting' ? (
                            <>
                                <Loader2 className="w-5 h-5 animate-spin" />
                                Submitting...
                            </>
                        ) : isLast ? (
                            <>
                                Finish Assessment
                                <CheckCircle className="w-5 h-5" />
                            </>
                        ) : (
                            <>
                                Next Question
                                <ChevronRight className="w-5 h-5" />
                            </>
                        )}
                    </button>
                </div>
            </div>
        </div>
    )
}
