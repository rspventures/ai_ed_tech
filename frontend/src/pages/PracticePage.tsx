import { useState, useEffect } from 'react'
import { useParams, useNavigate, useSearchParams } from 'react-router-dom'
import {
    ArrowLeft,
    CheckCircle,
    Loader2,
    Sparkles,
    XCircle,
    Lightbulb,
    LogOut,
    RefreshCw,
    CheckSquare,
    Square
} from 'lucide-react'
import api from '@/services/api'

interface Question {
    question_id: string
    question: string
    question_type: string
    options?: string[]
    hint: string
    subject: string
    topic: string
    subtopic: string
    difficulty: string
}

interface Feedback {
    is_correct: boolean
    score: number
    feedback: string
    explanation: string
    correct_answer: string
    hint_for_retry?: string
}

export default function PracticePage() {
    const { topicSlug } = useParams()
    const [searchParams] = useSearchParams()
    const navigate = useNavigate()

    const subtopicId = searchParams.get('subtopic')

    const [question, setQuestion] = useState<Question | null>(null)
    const [selectedOption, setSelectedOption] = useState<string | string[] | null>(null)
    const [feedback, setFeedback] = useState<Feedback | null>(null)
    const [loading, setLoading] = useState(false)
    const [showHint, setShowHint] = useState(false)
    const [error, setError] = useState<string | null>(null)
    const [initialized, setInitialized] = useState(false)

    const loadQuestion = async () => {
        setLoading(true)
        setError(null)
        setFeedback(null)
        setSelectedOption(null)
        setShowHint(false)

        try {
            const payload: Record<string, string> = {}

            // Prioritize subtopic_id if provided
            if (subtopicId) {
                payload.subtopic_id = subtopicId
            } else if (topicSlug) {
                payload.topic_slug = topicSlug
            }

            const response = await api.post<Question>('/practice/start', payload)
            setQuestion(response.data)
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to load question')
        } finally {
            setLoading(false)
        }
    }

    const handleOptionSelect = (option: string) => {
        if (feedback || loading || !question) return

        if (question.question_type === 'multi_select') {
            setSelectedOption(prev => {
                const current = Array.isArray(prev) ? prev : (prev ? [prev as string] : [])
                if (current.includes(option)) {
                    return current.filter(o => o !== option)
                } else {
                    return [...current, option]
                }
            })
        } else {
            setSelectedOption(option)
        }
    }

    const submitAnswer = async () => {
        if (!question || !selectedOption) return

        setLoading(true)
        try {
            const response = await api.post<Feedback>('/practice/answer', {
                question_id: question.question_id,
                answer: selectedOption
            })
            setFeedback(response.data)
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to submit answer')
        } finally {
            setLoading(false)
        }
    }

    // Auto-load first question on mount
    useEffect(() => {
        if (!initialized) {
            setInitialized(true)
            if (subtopicId || topicSlug) {
                loadQuestion()
            }
        }
    }, [initialized, subtopicId, topicSlug])

    return (
        <div className="min-h-screen">
            {/* Header */}
            <header className="glass border-b border-white/10">
                <div className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8">
                    <div className="flex items-center h-16">
                        <button
                            onClick={() => navigate(-1)}
                            className="mr-4 p-2 text-gray-400 hover:text-white hover:bg-white/10 rounded-lg transition-colors"
                        >
                            <ArrowLeft className="w-5 h-5" />
                        </button>
                        <div className="flex items-center gap-3">
                            <div className="w-10 h-10 bg-gradient-to-br from-primary-500 to-accent-500 rounded-xl flex items-center justify-center">
                                <Sparkles className="w-5 h-5 text-white" />
                            </div>
                            <div>
                                <span className="text-xl font-bold gradient-text">Practice Mode</span>
                                {question && (
                                    <p className="text-xs text-gray-400">
                                        {question.subject} • {question.topic}
                                    </p>
                                )}
                            </div>
                        </div>

                        {/* End Session Button */}
                        <div className="ml-auto">
                            <button
                                onClick={() => navigate(-1)}
                                className="flex items-center gap-2 px-4 py-2 bg-red-500/20 hover:bg-red-500/30 text-red-400 hover:text-red-300 rounded-lg transition-colors border border-red-500/30"
                            >
                                <LogOut className="w-4 h-4" />
                                <span className="hidden sm:inline">End Session</span>
                            </button>
                        </div>
                    </div>
                </div>
            </header>

            {/* Main content */}
            <main className="max-w-4xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
                {/* Loading state */}
                {loading && !question && (
                    <div className="flex flex-col items-center justify-center py-20">
                        <Loader2 className="w-12 h-12 text-primary-500 animate-spin mb-4" />
                        <p className="text-gray-400">Generating your question...</p>
                    </div>
                )}

                {/* Error state */}
                {error && !question && (
                    <div className="glass-card text-center py-12">
                        <XCircle className="w-12 h-12 text-red-400 mx-auto mb-4" />
                        <p className="text-red-400 mb-4">{error}</p>
                        <button onClick={loadQuestion} className="btn-primary">
                            Try Again
                        </button>
                    </div>
                )}

                {/* Question card */}
                {question && (
                    <div className="space-y-6">
                        {/* Question header */}
                        <div className="flex items-center justify-between">
                            <div className="flex items-center gap-2">
                                <span className={`px-3 py-1 rounded-full text-xs font-medium ${question.difficulty === 'easy' ? 'bg-emerald-500/20 text-emerald-400' :
                                    question.difficulty === 'medium' ? 'bg-amber-500/20 text-amber-400' :
                                        'bg-red-500/20 text-red-400'
                                    }`}>
                                    {question.difficulty}
                                </span>
                                <span className="text-gray-400 text-sm">{question.subtopic}</span>
                            </div>
                        </div>

                        {/* Question */}
                        <div className="glass-card">
                            <h2 className="text-2xl font-bold text-white mb-6">
                                {question.question}
                            </h2>

                            {/* Multiple Choice Options */}
                            {!feedback && question.options && question.options.length > 0 && (
                                <div className="space-y-4">
                                    <div className="space-y-3">
                                        {question.options?.map((option, idx) => {
                                            const isMultiSelect = question.question_type === 'multi_select'
                                            const isSelected = isMultiSelect
                                                ? Array.isArray(selectedOption) && selectedOption.includes(option)
                                                : selectedOption === option

                                            const isCorrect = feedback?.correct_answer === option ||
                                                (Array.isArray(feedback?.correct_answer) && feedback?.correct_answer.includes(option))

                                            return (
                                                <button
                                                    key={idx}
                                                    onClick={() => handleOptionSelect(option)}
                                                    disabled={!!feedback || loading}
                                                    className={`w-full p-4 rounded-xl text-left transition-all border-2 ${isSelected
                                                        ? feedback
                                                            ? feedback.is_correct
                                                                ? 'bg-green-500/20 border-green-500 text-white'
                                                                : 'bg-red-500/20 border-red-500 text-white'
                                                            : 'bg-primary-500/20 border-primary-500 text-white'
                                                        : feedback && isCorrect
                                                            ? 'bg-green-500/20 border-green-500 text-white'
                                                            : 'bg-white/5 border-transparent text-gray-300 hover:bg-white/10'
                                                        }`}
                                                >
                                                    <div className="flex items-center gap-3">
                                                        {isMultiSelect ? (
                                                            isSelected ? <CheckSquare className="w-6 h-6" /> : <Square className="w-6 h-6" />
                                                        ) : (
                                                            <span className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium ${isSelected ? 'bg-primary-500 text-white' : 'bg-white/10'
                                                                }`}>
                                                                {String.fromCharCode(65 + idx)}
                                                            </span>
                                                        )}
                                                        <span>{option}</span>
                                                        {feedback && isCorrect && (
                                                            <CheckCircle className="w-5 h-5 text-green-400 ml-auto" />
                                                        )}
                                                        {feedback && isSelected && !feedback.is_correct && (
                                                            <XCircle className="w-5 h-5 text-red-400 ml-auto" />
                                                        )}
                                                    </div>
                                                </button>
                                            )
                                        })}
                                    </div>
                                    <div className="flex items-center gap-4 pt-4">
                                        <button
                                            onClick={submitAnswer}
                                            disabled={loading || !selectedOption}
                                            className="btn-primary flex items-center gap-2"
                                        >
                                            {loading ? (
                                                <Loader2 className="w-4 h-4 animate-spin" />
                                            ) : (
                                                <CheckCircle className="w-4 h-4" />
                                            )}
                                            Submit Answer
                                        </button>

                                        <button
                                            onClick={() => setShowHint(!showHint)}
                                            className="btn-secondary flex items-center gap-2"
                                        >
                                            <Lightbulb className="w-4 h-4" />
                                            {showHint ? 'Hide Hint' : 'Show Hint'}
                                        </button>
                                    </div>

                                    {/* Hint */}
                                    {showHint && (
                                        <div className="p-4 bg-amber-500/10 border border-amber-500/20 rounded-xl">
                                            <p className="text-amber-400">
                                                <Lightbulb className="w-4 h-4 inline mr-2" />
                                                {question.hint}
                                            </p>
                                        </div>
                                    )}
                                </div>
                            )}

                            {/* Feedback */}
                            {feedback && (
                                <div className="space-y-4">
                                    <div className={`p-6 rounded-xl ${feedback.is_correct
                                        ? 'bg-emerald-500/10 border border-emerald-500/20'
                                        : 'bg-red-500/10 border border-red-500/20'
                                        }`}>
                                        <div className="flex items-start gap-4">
                                            {feedback.is_correct ? (
                                                <CheckCircle className="w-8 h-8 text-emerald-400 flex-shrink-0" />
                                            ) : (
                                                <XCircle className="w-8 h-8 text-red-400 flex-shrink-0" />
                                            )}
                                            <div>
                                                <p className={`text-lg font-semibold ${feedback.is_correct ? 'text-emerald-400' : 'text-red-400'
                                                    }`}>
                                                    {feedback.feedback}
                                                </p>
                                                <p className="text-gray-300 mt-2">
                                                    {feedback.explanation}
                                                </p>
                                                {!feedback.is_correct && (
                                                    <p className="text-gray-400 mt-2">
                                                        <strong>Correct answer:</strong> {feedback.correct_answer}
                                                    </p>
                                                )}
                                            </div>
                                        </div>
                                    </div>

                                    <button
                                        onClick={loadQuestion}
                                        className="btn-primary flex items-center gap-2 mx-auto"
                                    >
                                        <RefreshCw className="w-4 h-4" />
                                        Next Question
                                    </button>
                                </div>
                            )}
                        </div>
                    </div>
                )}

                {/* Start button if no question */}
                {!question && !loading && !error && (
                    <div className="glass-card text-center py-12">
                        <Sparkles className="w-16 h-16 text-primary-400 mx-auto mb-4" />
                        <h2 className="text-2xl font-bold text-white mb-2">Ready to Practice?</h2>
                        <p className="text-gray-400 mb-6">
                            AI-powered questions tailored to your learning level
                        </p>
                        <button onClick={loadQuestion} className="btn-primary">
                            Start Practice
                        </button>
                    </div>
                )}
            </main>
        </div>
    )
}
