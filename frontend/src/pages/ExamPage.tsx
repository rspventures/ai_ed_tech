import { useState, useEffect, useRef } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
    CheckCircle,
    XCircle,
    ChevronRight,
    ChevronLeft,
    AlertCircle,
    Clock,
    Target,
    Award,
    Loader2,
    Sparkles,
    BookOpen,
    BarChart3,
    Settings,
    Play
} from 'lucide-react'

import { examService } from '@/services/exam'
import { curriculumService } from '@/services/curriculum'
import { useStudentStore } from '@/stores/studentStore'
import type { Subject, Topic } from '@/types'

type ExamState = 'setup' | 'active' | 'submitting' | 'results'

interface ExamQuestion {
    question_id: string
    question: string
    options: string[]
    topic_id: string
    topic_name: string
}

interface TopicBreakdown {
    topic_id: string
    topic_name: string
    correct: number
    total: number
    percentage: number
}

interface ExamResult {
    id: string
    score: number
    total_questions: number
    correct_questions: number
    duration_seconds?: number
    subject_name: string
    topic_breakdown: TopicBreakdown[]
    feedback?: {
        overall_interpretation: string
        topic_analysis: string[]
        strengths: string[]
        areas_to_focus: string[]
        study_recommendations: string[]
        encouraging_message: string
    }
}

// Utility to shuffle array
function shuffleArray<T>(array: T[]): T[] {
    const shuffled = [...array]
    for (let i = shuffled.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1));
        [shuffled[i], shuffled[j]] = [shuffled[j], shuffled[i]]
    }
    return shuffled
}

export default function ExamPage() {
    const { subjectSlug } = useParams<{ subjectSlug: string }>()
    const navigate = useNavigate()
    const [showCelebration, setShowCelebration] = useState(false)
    const { student, fetchStudent } = useStudentStore()

    // State
    const [status, setStatus] = useState<ExamState>('setup')
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)

    // Setup data
    const [subject, setSubject] = useState<Subject | null>(null)
    const [topics, setTopics] = useState<Topic[]>([])
    const [selectedTopicIds, setSelectedTopicIds] = useState<string[]>([])
    const [numQuestions, setNumQuestions] = useState(10)
    const [timeLimitMinutes, setTimeLimitMinutes] = useState<number | null>(null)

    // Exam data
    const [examId, setExamId] = useState<string>('')
    const [questions, setQuestions] = useState<ExamQuestion[]>([])
    const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0)
    const [answers, setAnswers] = useState<Record<string, { answer: string; correctAnswer: string }>>({})
    const [shuffledOptionsMap, setShuffledOptionsMap] = useState<Record<string, string[]>>({})
    const [result, setResult] = useState<ExamResult | null>(null)

    // Timer
    const [secondsElapsed, setSecondsElapsed] = useState(0)
    const [timeLimit, setTimeLimit] = useState<number | null>(null)
    const timerRef = useRef<ReturnType<typeof setInterval> | null>(null)

    // Get student's grade level
    const studentGrade = student?.grade_level || 1

    useEffect(() => {
        if (!student) {
            fetchStudent()
        }
    }, [])

    useEffect(() => {
        loadSubjectAndTopics()
        return () => stopTimer()
    }, [subjectSlug, studentGrade])

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

    const loadSubjectAndTopics = async () => {
        if (!subjectSlug) return
        try {
            const subjectData = await curriculumService.getSubject(subjectSlug)
            setSubject(subjectData)

            // Filter topics by student's grade level
            const allTopics = (subjectData as any).topics || []
            const gradeFilteredTopics = allTopics.filter((t: Topic) => t.grade_level === studentGrade)
            setTopics(gradeFilteredTopics)

            // Start with NO topics selected
            setSelectedTopicIds([])
        } catch {
            setError('Subject not found')
        } finally {
            setLoading(false)
        }
    }

    const toggleTopicSelection = (topicId: string) => {
        setSelectedTopicIds((prev: string[]) =>
            prev.includes(topicId)
                ? prev.filter((id: string) => id !== topicId)
                : [...prev, topicId]
        )
    }

    const selectAllTopics = () => {
        setSelectedTopicIds(topics.map((t: Topic) => t.id))
    }

    const deselectAllTopics = () => {
        setSelectedTopicIds([])
    }

    const startExam = async () => {
        if (!subject || selectedTopicIds.length === 0) return

        setLoading(true)
        setError(null)
        setAnswers({})
        setCurrentQuestionIndex(0)
        setSecondsElapsed(0)

        try {
            const data = await examService.startExam({
                subject_id: subject.id,
                topic_ids: selectedTopicIds,
                num_questions: numQuestions,
                time_limit_minutes: timeLimitMinutes || undefined
            })

            setExamId(data.exam_id)
            setQuestions(data.questions)
            setTimeLimit(data.time_limit_seconds || null)

            // Shuffle options for each question
            const optionsMap: Record<string, string[]> = {}
            data.questions.forEach((q: ExamQuestion) => {
                optionsMap[q.question_id] = shuffleArray([...q.options])
            })
            setShuffledOptionsMap(optionsMap)

            setStatus('active')
            startTimer()
        } catch {
            setError('Failed to start exam. Please try again.')
        } finally {
            setLoading(false)
        }
    }

    const selectAnswer = (questionId: string, answer: string, correctAnswer: string) => {
        setAnswers(prev => ({
            ...prev,
            [questionId]: { answer, correctAnswer }
        }))
    }

    const goToQuestion = (index: number) => {
        if (index >= 0 && index < questions.length) {
            setCurrentQuestionIndex(index)
        }
    }

    const submitExam = async () => {
        if (!subject) return

        stopTimer()
        setStatus('submitting')

        const submissionItems = questions.map(q => {
            const ans = answers[q.question_id]
            return {
                question_id: q.question_id,
                question: q.question,
                options: q.options,
                answer: ans?.answer || '',
                correct_answer: ans?.correctAnswer || q.options[0],
                topic_id: q.topic_id
            }
        })

        try {
            const resultData = await examService.submitExam({
                exam_id: examId,
                subject_id: subject.id,
                subject_name: subject.name,
                topic_ids: selectedTopicIds,
                answers: submissionItems,
                duration_seconds: secondsElapsed
            })

            setResult(resultData)
            setStatus('results')

            if (resultData.score >= 70) {
                setShowCelebration(true)
                setTimeout(() => setShowCelebration(false), 4000)
            }
        } catch {
            setError('Failed to submit exam.')
            setStatus('active')
        }
    }

    const formatTime = (seconds: number) => {
        const mins = Math.floor(seconds / 60)
        const secs = seconds % 60
        return `${mins}:${secs.toString().padStart(2, '0')}`
    }

    const getAnsweredCount = () => Object.keys(answers).length

    if (loading && !questions.length && status === 'setup') {
        return (
            <div className="min-h-screen flex items-center justify-center">
                <Loader2 className="w-8 h-8 text-primary-500 animate-spin" />
            </div>
        )
    }

    if (error && status === 'setup') {
        return (
            <div className="min-h-screen flex items-center justify-center p-4">
                <div className="max-w-md w-full glass-card text-center p-8">
                    <AlertCircle className="w-12 h-12 text-red-500 mx-auto mb-4" />
                    <h2 className="text-xl font-bold text-white mb-2">Error</h2>
                    <p className="text-gray-400 mb-6">{error}</p>
                    <button onClick={() => navigate('/dashboard')} className="btn-secondary w-full">
                        Back to Dashboard
                    </button>
                </div>
            </div>
        )
    }

    // 1. SETUP SCREEN
    if (status === 'setup' && subject) {
        return (
            <div className="min-h-screen py-12 px-4 sm:px-6 lg:px-8">
                <div className="max-w-4xl mx-auto">
                    <div className="glass-card p-8 mb-6">
                        <div className="flex items-center gap-4 mb-6">
                            <div className="w-16 h-16 bg-primary-500/20 rounded-full flex items-center justify-center">
                                <BookOpen className="w-8 h-8 text-primary-400" />
                            </div>
                            <div>
                                <h1 className="text-3xl font-bold text-white">{subject.name} Exam</h1>
                                <p className="text-gray-400">Configure your exam settings</p>
                            </div>
                        </div>

                        {/* Topic Selection */}
                        <div className="mb-8">
                            <div className="flex items-center justify-between mb-4">
                                <h3 className="text-lg font-semibold text-white flex items-center gap-2">
                                    <Target className="w-5 h-5 text-primary-400" />
                                    Select Topics ({selectedTopicIds.length}/{topics.length} selected)
                                    <span className="text-sm font-normal text-gray-400">• Grade {studentGrade}</span>
                                </h3>
                                <div className="flex gap-2">
                                    <button
                                        onClick={selectAllTopics}
                                        className="text-sm px-3 py-1 bg-primary-500/20 text-primary-400 rounded-lg hover:bg-primary-500/30 transition-colors"
                                    >
                                        Select All
                                    </button>
                                    <button
                                        onClick={deselectAllTopics}
                                        className="text-sm px-3 py-1 bg-white/10 text-gray-400 rounded-lg hover:bg-white/20 transition-colors"
                                    >
                                        Deselect All
                                    </button>
                                </div>
                            </div>
                            <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-3">
                                {topics.map(topic => (
                                    <button
                                        key={topic.id}
                                        onClick={() => toggleTopicSelection(topic.id)}
                                        className={`p-4 rounded-xl text-left transition-all border-2 ${selectedTopicIds.includes(topic.id)
                                            ? 'bg-primary-500/20 border-primary-500 text-white'
                                            : 'bg-white/5 border-transparent text-gray-300 hover:bg-white/10'
                                            }`}
                                    >
                                        <div className="flex items-center gap-3">
                                            <div className={`w-5 h-5 rounded border flex items-center justify-center ${selectedTopicIds.includes(topic.id)
                                                ? 'border-primary-500 bg-primary-500'
                                                : 'border-gray-500'
                                                }`}>
                                                {selectedTopicIds.includes(topic.id) && (
                                                    <CheckCircle className="w-4 h-4 text-white" />
                                                )}
                                            </div>
                                            <span>{topic.name}</span>
                                        </div>
                                    </button>
                                ))}
                            </div>
                        </div>

                        {/* Exam Settings */}
                        <div className="mb-8">
                            <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                                <Settings className="w-5 h-5 text-primary-400" />
                                Exam Settings
                            </h3>
                            <div className="grid grid-cols-1 sm:grid-cols-2 gap-6">
                                <div>
                                    <label className="block text-sm text-gray-400 mb-2">Number of Questions</label>
                                    <select
                                        value={numQuestions}
                                        onChange={(e) => setNumQuestions(Number(e.target.value))}
                                        className="w-full bg-white/10 border border-white/20 rounded-lg px-4 py-3 text-white focus:outline-none focus:border-primary-500"
                                    >
                                        <option value={5}>5 Questions (Quick)</option>
                                        <option value={10}>10 Questions (Standard)</option>
                                        <option value={20}>20 Questions (Comprehensive)</option>
                                        <option value={30}>30 Questions (Full Exam)</option>
                                    </select>
                                </div>
                                <div>
                                    <label className="block text-sm text-gray-400 mb-2">Time Limit (Optional)</label>
                                    <select
                                        value={timeLimitMinutes || ''}
                                        onChange={(e) => setTimeLimitMinutes(e.target.value ? Number(e.target.value) : null)}
                                        className="w-full bg-white/10 border border-white/20 rounded-lg px-4 py-3 text-white focus:outline-none focus:border-primary-500"
                                    >
                                        <option value="">No Time Limit</option>
                                        <option value={10}>10 Minutes</option>
                                        <option value={15}>15 Minutes</option>
                                        <option value={20}>20 Minutes</option>
                                        <option value={30}>30 Minutes</option>
                                        <option value={45}>45 Minutes</option>
                                        <option value={60}>60 Minutes</option>
                                    </select>
                                </div>
                            </div>
                        </div>

                        {/* Start Button */}
                        <div className="flex flex-col sm:flex-row gap-4 justify-center">
                            <button onClick={() => navigate(-1)} className="btn-secondary">
                                Cancel
                            </button>
                            <button
                                onClick={startExam}
                                disabled={loading || selectedTopicIds.length === 0}
                                className="btn-primary px-8 py-3 text-lg flex items-center gap-2"
                            >
                                {loading ? (
                                    <Loader2 className="w-5 h-5 animate-spin" />
                                ) : (
                                    <>
                                        <Play className="w-5 h-5" />
                                        Start Exam
                                    </>
                                )}
                            </button>
                        </div>
                    </div>
                </div>
            </div>
        )
    }

    // 2. RESULTS SCREEN
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
                            {feedback?.overall_interpretation || (passed ? 'Excellent Work!' : 'Keep Practicing!')}
                        </h2>

                        <p className="text-2xl text-gray-300 mb-4">
                            <span className={`font-bold ${passed ? 'text-green-400' : 'text-amber-400'}`}>
                                {percentage}%
                            </span>
                            <span className="text-lg ml-2">
                                ({result.correct_questions}/{result.total_questions} correct)
                            </span>
                        </p>

                        <p className="text-gray-400">Time: {formatTime(result.duration_seconds || secondsElapsed)}</p>
                    </div>

                    {/* Topic Breakdown */}
                    <div className="glass-card p-6 mb-6">
                        <h3 className="text-xl font-semibold text-white mb-4 flex items-center gap-2">
                            <BarChart3 className="w-5 h-5 text-primary-400" />
                            Topic Breakdown
                        </h3>
                        <div className="space-y-4">
                            {result.topic_breakdown.map((tb, i) => (
                                <div key={i} className="flex items-center gap-4">
                                    <div className="flex-1">
                                        <div className="flex justify-between mb-1">
                                            <span className="text-white">{tb.topic_name}</span>
                                            <span className={`font-medium ${tb.percentage >= 70 ? 'text-green-400' : 'text-amber-400'}`}>
                                                {tb.correct}/{tb.total} ({tb.percentage}%)
                                            </span>
                                        </div>
                                        <div className="h-2 bg-white/10 rounded-full overflow-hidden">
                                            <div
                                                className={`h-full transition-all ${tb.percentage >= 70 ? 'bg-green-500' : 'bg-amber-500'}`}
                                                style={{ width: `${tb.percentage}%` }}
                                            />
                                        </div>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>

                    {/* AI Feedback */}
                    {feedback && (
                        <div className="grid gap-6 md:grid-cols-2 mb-6">
                            {feedback.strengths.length > 0 && (
                                <div className="glass-card p-6">
                                    <h3 className="text-lg font-semibold text-white mb-3 flex items-center gap-2">
                                        <CheckCircle className="w-5 h-5 text-green-400" />
                                        Strengths
                                    </h3>
                                    <ul className="space-y-2">
                                        {feedback.strengths.map((item, i) => (
                                            <li key={i} className="text-gray-300 flex items-start gap-2">
                                                <span className="text-green-400">✓</span>
                                                {item}
                                            </li>
                                        ))}
                                    </ul>
                                </div>
                            )}

                            {feedback.areas_to_focus.length > 0 && (
                                <div className="glass-card p-6">
                                    <h3 className="text-lg font-semibold text-white mb-3 flex items-center gap-2">
                                        <Target className="w-5 h-5 text-amber-400" />
                                        Focus Areas
                                    </h3>
                                    <ul className="space-y-2">
                                        {feedback.areas_to_focus.map((item, i) => (
                                            <li key={i} className="text-gray-300 flex items-start gap-2">
                                                <span className="text-amber-400">→</span>
                                                {item}
                                            </li>
                                        ))}
                                    </ul>
                                </div>
                            )}
                        </div>
                    )}

                    {/* Encouraging Message */}
                    {feedback?.encouraging_message && (
                        <div className="glass-card p-6 text-center mb-6">
                            <Sparkles className="w-8 h-8 text-yellow-400 mx-auto mb-3" />
                            <p className="text-xl text-gray-200 italic">"{feedback.encouraging_message}"</p>
                        </div>
                    )}

                    {/* Actions */}
                    <div className="flex gap-4 justify-center">
                        <button onClick={() => navigate('/dashboard')} className="btn-secondary">
                            Dashboard
                        </button>
                        <button
                            onClick={() => {
                                setResult(null)
                                setStatus('setup')
                                setAnswers({})
                            }}
                            className="btn-primary"
                        >
                            Take Another Exam
                        </button>
                    </div>
                </div>
            </div>
        )
    }

    // 3. ACTIVE EXAM
    if (!questions.length) return null

    const question = questions[currentQuestionIndex]
    const currentAnswer = answers[question.question_id]?.answer || null
    const isLast = currentQuestionIndex === questions.length - 1
    const isFirst = currentQuestionIndex === 0
    const progress = ((currentQuestionIndex + 1) / questions.length) * 100

    return (
        <div className="min-h-screen py-8 px-4 sm:px-6 lg:px-8">
            <div className="max-w-3xl mx-auto">
                {/* Header */}
                <div className="flex items-center justify-between mb-4">
                    <div className="flex items-center gap-4">
                        <button
                            onClick={() => {
                                if (window.confirm("Quit exam? Progress will be lost.")) {
                                    navigate('/dashboard')
                                }
                            }}
                            className="text-gray-400 hover:text-white"
                        >
                            Exit
                        </button>
                        <span className="text-gray-400">
                            {subject?.name} Exam
                        </span>
                    </div>
                    <div className="flex items-center gap-4">
                        <span className="text-gray-400 text-sm">
                            {getAnsweredCount()}/{questions.length} answered
                        </span>
                        <div className="flex items-center gap-2 text-primary-400 font-mono">
                            <Clock className="w-4 h-4" />
                            {formatTime(secondsElapsed)}
                        </div>
                    </div>
                </div>

                {/* Progress Bar */}
                <div className="h-2 bg-white/10 rounded-full mb-6 overflow-hidden">
                    <div
                        className="h-full bg-primary-500 transition-all duration-300"
                        style={{ width: `${progress}%` }}
                    />
                </div>

                {/* Question Card */}
                <div className="glass-card p-6 sm:p-10 mb-6 min-h-[400px] flex flex-col">
                    <div className="mb-6">
                        <div className="flex items-center gap-2 mb-2">
                            <span className="text-sm font-medium text-gray-400 uppercase tracking-wider">
                                Question {currentQuestionIndex + 1} of {questions.length}
                            </span>
                            <span className="text-xs bg-primary-500/20 text-primary-400 px-2 py-1 rounded">
                                {question.topic_name}
                            </span>
                        </div>
                        <h2 className="text-2xl sm:text-3xl font-bold text-white leading-tight">
                            {question.question}
                        </h2>
                    </div>

                    <div className="space-y-3 flex-grow">
                        {(shuffledOptionsMap[question.question_id] || question.options).map((option: string, idx: number) => {
                            const isSelected = currentAnswer === option
                            return (
                                <button
                                    key={idx}
                                    onClick={() => selectAnswer(question.question_id, option, question.options[0])}
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

                {/* Question Navigator */}
                <div className="glass-card p-4 mb-6">
                    <div className="flex flex-wrap gap-2 justify-center">
                        {questions.map((_, idx) => {
                            const isAnswered = !!answers[questions[idx].question_id]
                            const isCurrent = idx === currentQuestionIndex
                            return (
                                <button
                                    key={idx}
                                    onClick={() => goToQuestion(idx)}
                                    className={`w-10 h-10 rounded-lg text-sm font-medium transition-all ${isCurrent
                                        ? 'bg-primary-500 text-white'
                                        : isAnswered
                                            ? 'bg-green-500/20 text-green-400 border border-green-500'
                                            : 'bg-white/10 text-gray-400 hover:bg-white/20'
                                        }`}
                                >
                                    {idx + 1}
                                </button>
                            )
                        })}
                    </div>
                </div>

                {/* Navigation */}
                <div className="flex justify-between">
                    <button
                        onClick={() => goToQuestion(currentQuestionIndex - 1)}
                        disabled={isFirst}
                        className="btn-secondary flex items-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                        <ChevronLeft className="w-5 h-5" />
                        Previous
                    </button>

                    {isLast ? (
                        <button
                            onClick={submitExam}
                            disabled={status === 'submitting'}
                            className="btn-primary px-8 flex items-center gap-2"
                        >
                            {status === 'submitting' ? (
                                <>
                                    <Loader2 className="w-5 h-5 animate-spin" />
                                    Submitting...
                                </>
                            ) : (
                                <>
                                    Finish Exam
                                    <CheckCircle className="w-5 h-5" />
                                </>
                            )}
                        </button>
                    ) : (
                        <button
                            onClick={() => goToQuestion(currentQuestionIndex + 1)}
                            className="btn-primary px-8 flex items-center gap-2"
                        >
                            Next Question
                            <ChevronRight className="w-5 h-5" />
                        </button>
                    )}
                </div>
            </div>
        </div>
    )
}
