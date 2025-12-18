/**
 * AI Tutor Platform - Test Page
 * Topic-level test with 10 questions from subtopics
 */
import { useState, useEffect, useRef } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
    ArrowLeft,
    ArrowRight,
    BookOpen,
    CheckCircle,
    Clock,
    Loader2,
    Play,
    Target,
    Trophy,
    XCircle,
    RefreshCw,
    Home,
    Lightbulb,
    Award,
    TrendingUp,

    AlertCircle,
    CheckSquare,
    Square
} from 'lucide-react'

import { testService, TestQuestion, TestResult, TestAnswerItem } from '@/services/test'
import { curriculumService } from '@/services/curriculum'
import type { Topic } from '@/types'

type TestState = 'intro' | 'active' | 'submitting' | 'results'

// Fisher-Yates shuffle
function shuffleArray<T>(array: T[]): T[] {
    const shuffled = [...array]
    for (let i = shuffled.length - 1; i > 0; i--) {
        const j = Math.floor(Math.random() * (i + 1));
        [shuffled[i], shuffled[j]] = [shuffled[j], shuffled[i]]
    }
    return shuffled
}

export default function TestPage() {
    const { topicSlug } = useParams<{ topicSlug: string }>()
    const navigate = useNavigate()

    // State
    const [status, setStatus] = useState<TestState>('intro')
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)

    // Topic data
    const [topic, setTopic] = useState<Topic | null>(null)

    // Test data
    const [testId, setTestId] = useState<string>('')
    const [questions, setQuestions] = useState<TestQuestion[]>([])
    const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0)
    const [answers, setAnswers] = useState<Record<string, { answer: string | string[]; correctAnswer: string | string[] }>>({})
    const [shuffledOptionsMap, setShuffledOptionsMap] = useState<Record<string, string[]>>({})
    const [result, setResult] = useState<TestResult | null>(null)

    // Timer
    const [secondsElapsed, setSecondsElapsed] = useState(0)
    const [timeLimit, setTimeLimit] = useState<number | null>(null)
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
            // Get topic by slug - need to find it in subjects
            const subjects = await curriculumService.getSubjects()
            let foundTopic: Topic | null = null

            for (const subject of subjects) {
                const subjectData = await curriculumService.getSubject(subject.slug)
                const topicMatch = (subjectData as any).topics?.find((t: Topic) => t.slug === topicSlug)
                if (topicMatch) {
                    foundTopic = topicMatch
                    setTopic(topicMatch)
                    break
                }
            }

            if (!foundTopic) {
                setError('Topic not found')
            }
        } catch {
            setError('Failed to load topic')
        } finally {
            setLoading(false)
        }
    }

    const startTest = async () => {
        if (!topic) return

        setLoading(true)
        setError(null)

        try {
            const response = await testService.startTest(topic.id, 10)
            setTestId(response.test_id)
            setTimeLimit(response.time_limit_seconds)

            // Shuffle options for each question
            const optionsMap: Record<string, string[]> = {}
            response.questions.forEach((q: TestQuestion) => {
                optionsMap[q.question_id] = shuffleArray(q.options)
            })
            setShuffledOptionsMap(optionsMap)

            setQuestions(response.questions)
            setCurrentQuestionIndex(0)
            setAnswers({})
            setSecondsElapsed(0)
            setStatus('active')
            startTimer()
        } catch (err) {
            setError('Failed to start test. Please try again.')
            console.error(err)
        } finally {
            setLoading(false)
        }
    }

    const selectAnswer = (question: TestQuestion, option: string) => {
        const isMultiSelect = question.question_type === 'multi_select'
        const questionId = question.question_id

        setAnswers(prev => {
            const current = prev[questionId]?.answer
            let newAnswer: string | string[]

            if (isMultiSelect) {
                const currentList = Array.isArray(current) ? (current as string[]) : (current ? [current as string] : [])
                if (currentList.includes(option)) {
                    newAnswer = currentList.filter(a => a !== option)
                } else {
                    newAnswer = [...currentList, option]
                }
            } else {
                newAnswer = option
            }

            return {
                ...prev,
                [questionId]: {
                    answer: newAnswer,
                    correctAnswer: question.options[0] // Approximation, backend validates
                }
            }
        })
    }

    const goToNextQuestion = () => {
        if (currentQuestionIndex < questions.length - 1) {
            setCurrentQuestionIndex((prev: number) => prev + 1)
        }
    }

    const goToPrevQuestion = () => {
        if (currentQuestionIndex > 0) {
            setCurrentQuestionIndex((prev: number) => prev - 1)
        }
    }

    const submitTest = async () => {
        if (!topic) return

        stopTimer()
        setStatus('submitting')

        try {
            const answerItems: TestAnswerItem[] = questions.map((q: TestQuestion) => ({
                question_id: q.question_id,
                question: q.question,
                answer: answers[q.question_id]?.answer || '',
                correct_answer: answers[q.question_id]?.correctAnswer || q.options[0] || '',
                subtopic_id: q.subtopic_id
            }))

            const testResult = await testService.submitTest(
                testId,
                topic.id,
                topic.name,
                answerItems,
                secondsElapsed
            )

            setResult(testResult)
            setStatus('results')
        } catch (err) {
            setError('Failed to submit test')
            setStatus('active')
            startTimer()
        }
    }

    const retakeTest = () => {
        setStatus('intro')
        setResult(null)
        setQuestions([])
        setAnswers({})
    }

    const formatTime = (seconds: number) => {
        const mins = Math.floor(seconds / 60)
        const secs = seconds % 60
        return `${mins}:${secs.toString().padStart(2, '0')}`
    }

    // Loading
    if (loading && status === 'intro') {
        return (
            <div className="min-h-screen flex items-center justify-center">
                <div className="text-center">
                    <Loader2 className="w-10 h-10 text-primary-500 animate-spin mx-auto mb-4" />
                    <p className="text-gray-400">Loading test...</p>
                </div>
            </div>
        )
    }

    // Error
    if (error) {
        return (
            <div className="min-h-screen flex items-center justify-center">
                <div className="glass-card text-center">
                    <XCircle className="w-12 h-12 text-red-400 mx-auto mb-4" />
                    <p className="text-red-400 mb-4">{error}</p>
                    <button onClick={() => navigate(-1)} className="btn-primary">
                        Go Back
                    </button>
                </div>
            </div>
        )
    }

    // Intro screen
    if (status === 'intro' && topic) {
        return (
            <div className="min-h-screen flex items-center justify-center p-4">
                <div className="glass-card max-w-lg w-full text-center">
                    <div className="w-20 h-20 bg-gradient-to-br from-purple-500 to-pink-500 rounded-full flex items-center justify-center mx-auto mb-6">
                        <Target className="w-10 h-10 text-white" />
                    </div>
                    <h1 className="text-3xl font-bold text-white mb-2">{topic.name} Test</h1>
                    <p className="text-gray-400 mb-6">
                        Challenge yourself with 10 questions covering all subtopics
                    </p>

                    <div className="bg-white/5 rounded-xl p-4 mb-6 text-left">
                        <div className="flex items-center gap-3 mb-3">
                            <BookOpen className="w-5 h-5 text-primary-400" />
                            <span className="text-gray-300">10 Multiple Choice Questions</span>
                        </div>
                        <div className="flex items-center gap-3 mb-3">
                            <Clock className="w-5 h-5 text-primary-400" />
                            <span className="text-gray-300">10 Minutes Time Limit</span>
                        </div>
                        <div className="flex items-center gap-3">
                            <Lightbulb className="w-5 h-5 text-primary-400" />
                            <span className="text-gray-300">Get explanations for wrong answers</span>
                        </div>
                    </div>

                    <div className="flex gap-4">
                        <button
                            onClick={() => navigate(-1)}
                            className="flex-1 px-6 py-3 bg-white/10 text-white rounded-xl hover:bg-white/20 transition-colors"
                        >
                            <ArrowLeft className="w-5 h-5 inline mr-2" />
                            Back
                        </button>
                        <button
                            onClick={startTest}
                            disabled={loading}
                            className="flex-1 btn-primary flex items-center justify-center gap-2"
                        >
                            {loading ? (
                                <Loader2 className="w-5 h-5 animate-spin" />
                            ) : (
                                <>
                                    <Play className="w-5 h-5" />
                                    Start Test
                                </>
                            )}
                        </button>
                    </div>
                </div>
            </div>
        )
    }

    // Active test
    if (status === 'active' || status === 'submitting') {
        const currentQuestion = questions[currentQuestionIndex]
        const currentAnswer = answers[currentQuestion?.question_id]?.answer
        const shuffledOptions = shuffledOptionsMap[currentQuestion?.question_id] || currentQuestion?.options || []
        const answeredCount = Object.keys(answers).length
        const progress = (answeredCount / questions.length) * 100

        return (
            <div className="min-h-screen">
                {/* Header */}
                <header className="glass border-b border-white/10">
                    <div className="max-w-4xl mx-auto px-4 py-4">
                        <div className="flex items-center justify-between">
                            <div className="flex items-center gap-4">
                                <Target className="w-6 h-6 text-purple-400" />
                                <span className="font-semibold text-white">{topic?.name} Test</span>
                            </div>
                            <div className="flex items-center gap-4">
                                <div className="flex items-center gap-2 text-gray-400">
                                    <Clock className="w-5 h-5" />
                                    <span className="font-mono">{formatTime(secondsElapsed)}</span>
                                    {timeLimit && (
                                        <span className="text-gray-500">/ {formatTime(timeLimit)}</span>
                                    )}
                                </div>
                                <span className="text-gray-400">
                                    {currentQuestionIndex + 1} / {questions.length}
                                </span>
                            </div>
                        </div>
                        {/* Progress bar */}
                        <div className="mt-3 h-2 bg-white/10 rounded-full overflow-hidden">
                            <div
                                className="h-full bg-gradient-to-r from-purple-500 to-pink-500 transition-all duration-300"
                                style={{ width: `${progress}%` }}
                            />
                        </div>
                    </div>
                </header>

                {/* Question */}
                <main className="max-w-4xl mx-auto px-4 py-8">
                    {currentQuestion && (
                        <div className="glass-card">
                            {currentQuestion.subtopic_name && (
                                <div className="inline-block px-3 py-1 bg-purple-500/20 text-purple-400 text-sm rounded-full mb-4">
                                    {currentQuestion.subtopic_name}
                                </div>
                            )}
                            <h2 className="text-xl font-semibold text-white mb-6">
                                {currentQuestion.question}
                            </h2>

                            <div className="space-y-3">

                                {shuffledOptions.map((option: string, idx: number) => {
                                    const isMultiSelect = currentQuestion.question_type === 'multi_select'
                                    const isSelected = isMultiSelect
                                        ? Array.isArray(currentAnswer) && currentAnswer.includes(option)
                                        : currentAnswer === option

                                    return (
                                        <button
                                            key={idx}
                                            onClick={() => selectAnswer(currentQuestion, option)}
                                            className={`w-full p-4 rounded-xl text-left transition-all border-2 ${isSelected
                                                ? 'bg-primary-500/20 border-primary-500 text-white'
                                                : 'bg-white/5 border-transparent text-gray-300 hover:bg-white/10'
                                                }`}
                                        >
                                            <div className="flex items-center gap-3">
                                                {isMultiSelect ? (
                                                    isSelected ? (
                                                        <CheckSquare className="w-6 h-6 text-primary-400" />
                                                    ) : (
                                                        <Square className="w-6 h-6 text-gray-500" />
                                                    )
                                                ) : (
                                                    <span className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-medium ${isSelected ? 'bg-primary-500 text-white' : 'bg-white/10'
                                                        }`}>
                                                        {String.fromCharCode(65 + idx)}
                                                    </span>
                                                )}
                                                <span>{option}</span>
                                            </div>
                                        </button>
                                    )
                                })}
                            </div>

                            {/* Navigation */}
                            <div className="flex justify-between mt-8">
                                <button
                                    onClick={goToPrevQuestion}
                                    disabled={currentQuestionIndex === 0}
                                    className="px-6 py-3 bg-white/10 text-white rounded-xl hover:bg-white/20 disabled:opacity-50 disabled:cursor-not-allowed transition-colors"
                                >
                                    <ArrowLeft className="w-5 h-5 inline mr-2" />
                                    Previous
                                </button>

                                {currentQuestionIndex === questions.length - 1 ? (
                                    <button
                                        onClick={submitTest}
                                        disabled={status === 'submitting' || answeredCount < questions.length}
                                        className="btn-primary px-8 py-3 disabled:opacity-50"
                                    >
                                        {status === 'submitting' ? (
                                            <Loader2 className="w-5 h-5 animate-spin inline mr-2" />
                                        ) : (
                                            <CheckCircle className="w-5 h-5 inline mr-2" />
                                        )}
                                        Submit Test
                                    </button>
                                ) : (
                                    <button
                                        onClick={goToNextQuestion}
                                        className="btn-primary px-6 py-3"
                                    >
                                        Next
                                        <ArrowRight className="w-5 h-5 inline ml-2" />
                                    </button>
                                )}
                            </div>
                        </div>
                    )}

                    {/* Question Navigator */}
                    <div className="mt-6 flex flex-wrap gap-2 justify-center">
                        {questions.map((_: TestQuestion, idx: number) => (
                            <button
                                key={idx}
                                onClick={() => setCurrentQuestionIndex(idx)}
                                className={`w-10 h-10 rounded-lg flex items-center justify-center font-medium transition-colors ${idx === currentQuestionIndex
                                    ? 'bg-primary-500 text-white'
                                    : answers[questions[idx].question_id]
                                        ? 'bg-green-500/20 text-green-400 border border-green-500/50'
                                        : 'bg-white/10 text-gray-400 hover:bg-white/20'
                                    }`}
                            >
                                {idx + 1}
                            </button>
                        ))}
                    </div>
                </main>
            </div>
        )
    }

    // Results
    if (status === 'results' && result) {
        const isPassing = result.score >= 60
        const isExcellent = result.score >= 80

        return (
            <div className="min-h-screen py-8 px-4">
                <div className="max-w-4xl mx-auto">
                    {/* Score Card */}
                    <div className="glass-card text-center mb-8">
                        <div className={`w-24 h-24 mx-auto mb-4 rounded-full flex items-center justify-center ${isExcellent ? 'bg-gradient-to-br from-yellow-400 to-orange-500' :
                            isPassing ? 'bg-gradient-to-br from-green-400 to-emerald-500' :
                                'bg-gradient-to-br from-gray-400 to-gray-500'
                            }`}>
                            {isExcellent ? (
                                <Trophy className="w-12 h-12 text-white" />
                            ) : isPassing ? (
                                <Award className="w-12 h-12 text-white" />
                            ) : (
                                <TrendingUp className="w-12 h-12 text-white" />
                            )}
                        </div>

                        <h1 className="text-4xl font-bold text-white mb-2">
                            {Math.round(result.score)}%
                        </h1>
                        <p className="text-gray-400 mb-4">
                            {result.correct_questions} / {result.total_questions} correct
                        </p>
                        <p className="text-gray-400">
                            Time: {formatTime(result.duration_seconds || 0)}
                        </p>
                    </div>

                    {/* Feedback */}
                    {result.feedback && (
                        <div className="glass-card mb-8">
                            <h2 className="text-xl font-semibold text-white mb-4">Feedback</h2>
                            <p className="text-gray-300 mb-4">{result.feedback.summary}</p>

                            {result.feedback.strengths.length > 0 && (
                                <div className="mb-4">
                                    <h3 className="text-green-400 font-medium mb-2">✅ Strengths</h3>
                                    <ul className="text-gray-400 space-y-1">
                                        {result.feedback.strengths.map((s: string, i: number) => (
                                            <li key={i}>• {s}</li>
                                        ))}
                                    </ul>
                                </div>
                            )}

                            {result.feedback.weaknesses.length > 0 && (
                                <div className="mb-4">
                                    <h3 className="text-yellow-400 font-medium mb-2">📚 Areas to Improve</h3>
                                    <ul className="text-gray-400 space-y-1">
                                        {result.feedback.weaknesses.map((w: string, i: number) => (
                                            <li key={i}>• {w}</li>
                                        ))}
                                    </ul>
                                </div>
                            )}

                            <p className="text-primary-400 text-lg mt-4">
                                {result.feedback.encouragement}
                            </p>
                        </div>
                    )}

                    {/* Question Results */}
                    <div className="glass-card mb-8">
                        <h2 className="text-xl font-semibold text-white mb-4">Question Review</h2>
                        <div className="space-y-4">
                            {result.question_results.map((qr, idx) => (
                                <div
                                    key={idx}
                                    className={`p-4 rounded-xl border ${qr.is_correct
                                        ? 'bg-green-500/10 border-green-500/30'
                                        : 'bg-red-500/10 border-red-500/30'
                                        }`}
                                >
                                    <div className="flex items-start gap-3">
                                        {qr.is_correct ? (
                                            <CheckCircle className="w-6 h-6 text-green-400 flex-shrink-0 mt-1" />
                                        ) : (
                                            <XCircle className="w-6 h-6 text-red-400 flex-shrink-0 mt-1" />
                                        )}
                                        <div className="flex-1">
                                            <p className="text-white font-medium mb-2">
                                                Q{idx + 1}: {qr.question}
                                            </p>
                                            <div className="text-sm text-gray-400 space-y-1">
                                                <p>Your answer: <span className={qr.is_correct ? 'text-green-400' : 'text-red-400'}>{qr.student_answer || '(No answer)'}</span></p>
                                                {!qr.is_correct && (
                                                    <p>Correct answer: <span className="text-green-400">{qr.correct_answer}</span></p>
                                                )}
                                            </div>
                                            {!qr.is_correct && qr.explanation && (
                                                <div className="mt-3 p-3 bg-white/5 rounded-lg">
                                                    <div className="flex items-start gap-2">
                                                        <Lightbulb className="w-5 h-5 text-yellow-400 flex-shrink-0" />
                                                        <p className="text-gray-300 text-sm">{qr.explanation}</p>
                                                    </div>
                                                </div>
                                            )}
                                        </div>
                                    </div>
                                </div>
                            ))}
                        </div>
                    </div>

                    {/* Actions */}
                    <div className="flex gap-4 justify-center">
                        <button
                            onClick={() => navigate('/dashboard')}
                            className="px-6 py-3 bg-white/10 text-white rounded-xl hover:bg-white/20 transition-colors"
                        >
                            <Home className="w-5 h-5 inline mr-2" />
                            Dashboard
                        </button>
                        <button
                            onClick={retakeTest}
                            className="btn-primary px-6 py-3"
                        >
                            <RefreshCw className="w-5 h-5 inline mr-2" />
                            Retake Test
                        </button>
                    </div>
                </div>
            </div>
        )
    }

    return null
}
