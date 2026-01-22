import { useState, useEffect } from 'react'
import { useParams, useNavigate, useSearchParams } from 'react-router-dom'
import {
    BookOpen,
    Target,
    Award,
    Loader2,
    AlertCircle,
    CheckCircle,
    ChevronRight,
    Sparkles,
    TrendingUp,
    ChevronDown,
    Play,
    Lock,
    Star,
    Layers
} from 'lucide-react'

import { studyService } from '@/services/study'
import { curriculumService } from '@/services/curriculum'
import LessonView from '@/components/LessonView'
import LessonViewV2 from '@/components/LessonViewV2'
import type { Topic, Subtopic, Lesson, LessonV2, StudyAction, LearningPath } from '@/types'

type StudyState = 'loading' | 'overview' | 'lesson' | 'redirecting' | 'complete' | 'error'

interface SubtopicWithProgress extends Subtopic {
    mastery_level: number
    lesson_completed: boolean
    practice_count: number
}

export default function StudyPage() {
    const { topicSlug } = useParams<{ topicSlug: string }>()
    const [searchParams] = useSearchParams()
    const navigate = useNavigate()

    // State
    const [state, setState] = useState<StudyState>('loading')
    const [error, setError] = useState<string | null>(null)

    // Data
    const [topic, setTopic] = useState<Topic | null>(null)
    const [subtopics, setSubtopics] = useState<SubtopicWithProgress[]>([])
    const [learningPath, setLearningPath] = useState<LearningPath | null>(null)
    const [currentLesson, setCurrentLesson] = useState<Lesson | null>(null)
    const [currentLessonV2, setCurrentLessonV2] = useState<LessonV2 | null>(null)
    const [isCompleting, setIsCompleting] = useState(false)
    const [expandedSubtopic, setExpandedSubtopic] = useState<string | null>(null)
    // const [useV2, setUseV2] = useState(true) // Forced V2

    useEffect(() => {
        loadStudyData()
    }, [topicSlug])

    const loadStudyData = async () => {
        if (!topicSlug) return
        setState('loading')
        setError(null)

        try {
            // Get topic info with subtopics
            const topicData = await curriculumService.getTopic(topicSlug)
            setTopic(topicData)

            // Get learning path recommendation
            const path = await studyService.getLearningPath(topicData.id)
            setLearningPath(path)

            // Load subtopic progress
            if (topicData.subtopics && topicData.subtopics.length > 0) {
                const subtopicsWithProgress = await Promise.all(
                    topicData.subtopics.map(async (subtopic: Subtopic) => {
                        try {
                            const progress = await studyService.getSubtopicProgress(subtopic.id)
                            return {
                                ...subtopic,
                                mastery_level: progress.mastery_level,
                                lesson_completed: progress.lesson_completed,
                                practice_count: progress.practice_count
                            }
                        } catch {
                            return {
                                ...subtopic,
                                mastery_level: 0,
                                lesson_completed: false,
                                practice_count: 0
                            }
                        }
                    })
                )
                setSubtopics(subtopicsWithProgress)
            }

            // Check if URL has direct lesson request
            const subtopicId = searchParams.get('lesson')
            if (subtopicId) {
                await loadLesson(subtopicId)
            } else {
                setState('overview')
            }
        } catch (err) {
            console.error('Failed to load study data:', err)
            setError('Failed to load study materials. Please try again.')
            setState('error')
        }
    }

    const loadLesson = async (subtopicId: string) => {
        setState('loading')
        try {
            // STRICT V2 ONLY - No Fallback
            // Load interactive V2 lesson
            const lessonV2 = await studyService.getLessonV2(subtopicId)
            setCurrentLessonV2(lessonV2)
            setCurrentLesson(null)

            setState('lesson')
        } catch (err) {
            console.error('Failed to load lesson:', err)
            setError('Failed to load lesson. Please try again.')
            setState('error')
        }
    }

    const handleStartLesson = async (subtopicId: string) => {
        await loadLesson(subtopicId)
    }

    const handleStartPractice = (subtopicId: string) => {
        navigate(`/practice/${topicSlug}?subtopic=${subtopicId}`)
    }

    const handleStartAssessment = (subtopicId: string) => {
        navigate(`/assessments/${topicSlug}?subtopic=${subtopicId}`)
    }

    const handleStartRecommended = async () => {
        if (!learningPath) return

        const { next_action } = learningPath

        if (next_action.action_type === 'lesson') {
            await loadLesson(next_action.resource_id)
        } else if (next_action.action_type === 'practice') {
            navigate(`/practice/${topicSlug}?subtopic=${next_action.resource_id}`)
        } else if (next_action.action_type === 'assessment') {
            navigate(`/assessments/${topicSlug}`)
        } else {
            // Complete - stay on overview
            setState('complete')
        }
    }

    const handleLessonComplete = async (timeSpentSeconds: number) => {
        // Support both V1 and V2 lessons
        const lessonId = currentLessonV2?.id || currentLesson?.id
        if (!lessonId) return

        setIsCompleting(true)
        try {
            await studyService.completeLesson(lessonId, timeSpentSeconds)
            // Refresh the learning path and subtopic progress
            if (topic) {
                const path = await studyService.getLearningPath(topic.id)
                setLearningPath(path)
                await loadStudyData()
            }
            // Update lesson state
            if (currentLessonV2) {
                setCurrentLessonV2({ ...currentLessonV2, is_completed: true })
            } else if (currentLesson) {
                setCurrentLesson({ ...currentLesson, is_completed: true })
            }
        } catch (err) {
            console.error('Failed to complete lesson:', err)
        } finally {
            setIsCompleting(false)
        }
    }

    const handleBackToOverview = () => {
        setCurrentLesson(null)
        setCurrentLessonV2(null)
        setState('overview')
        // Remove lesson param from URL
        navigate(`/study/${topicSlug}`, { replace: true })
    }

    const getMasteryColor = (mastery: number) => {
        if (mastery >= 0.7) return 'text-green-400'
        if (mastery >= 0.4) return 'text-yellow-400'
        return 'text-gray-400'
    }

    const getMasteryBgColor = (mastery: number) => {
        if (mastery >= 0.7) return 'bg-green-500'
        if (mastery >= 0.4) return 'bg-yellow-500'
        return 'bg-gray-500'
    }

    const getProgressBarColor = (mastery: number) => {
        if (mastery >= 0.7) return 'from-green-500 to-emerald-500'
        if (mastery >= 0.4) return 'from-yellow-500 to-orange-500'
        return 'from-gray-500 to-gray-600'
    }

    const getStatusIcon = (subtopic: SubtopicWithProgress) => {
        if (subtopic.mastery_level >= 0.7) {
            return <CheckCircle className="w-5 h-5 text-green-400" />
        } else if (subtopic.lesson_completed) {
            return <Star className="w-5 h-5 text-yellow-400" />
        }
        return <Play className="w-5 h-5 text-gray-400" />
    }

    // Loading state
    if (state === 'loading') {
        return (
            <div className="min-h-screen flex items-center justify-center">
                <div className="text-center">
                    <Loader2 className="w-12 h-12 text-primary-500 animate-spin mx-auto mb-4" />
                    <p className="text-gray-400">Preparing your learning path...</p>
                </div>
            </div>
        )
    }

    // Error state
    if (state === 'error' || !topic) {
        return (
            <div className="min-h-screen flex items-center justify-center p-4">
                <div className="max-w-md w-full glass-card text-center p-8">
                    <AlertCircle className="w-12 h-12 text-red-500 mx-auto mb-4" />
                    <h2 className="text-xl font-bold text-white mb-2">Oops!</h2>
                    <p className="text-gray-400 mb-6">{error || 'Something went wrong'}</p>
                    <button onClick={() => navigate('/dashboard')} className="btn-secondary w-full">
                        Back to Dashboard
                    </button>
                </div>
            </div>
        )
    }

    // Lesson view (V2 interactive or V1 classic)
    if (state === 'lesson' && (currentLessonV2 || currentLesson)) {
        return (
            <div className="min-h-screen py-8 px-4 sm:px-6 lg:px-8">
                <button
                    onClick={handleBackToOverview}
                    className="text-gray-400 hover:text-white mb-6 flex items-center gap-2"
                >
                    ← Back to Overview
                </button>

                {currentLessonV2 && (
                    <LessonViewV2
                        lesson={currentLessonV2}
                        onComplete={handleLessonComplete}
                        isCompleting={isCompleting}
                    />
                )}
            </div>
        )
    }

    // Overview / Learning Path view with Subtopics
    return (
        <div className="min-h-screen py-8 px-4 sm:px-6 lg:px-8">
            <div className="max-w-4xl mx-auto">
                {/* Header */}
                <div className="mb-8">
                    <button
                        onClick={() => navigate('/dashboard')}
                        className="text-gray-400 hover:text-white mb-4 flex items-center gap-2"
                    >
                        ← Back to Dashboard
                    </button>
                    <div className="flex items-center justify-between">
                        <div>
                            <h1 className="text-3xl font-bold text-white mb-2">
                                {topic.name}
                            </h1>
                            <p className="text-gray-400">{topic.description}</p>
                        </div>
                        <button
                            onClick={() => navigate(`/flashcards/${topicSlug}`)}
                            className="btn-secondary flex items-center gap-2"
                        >
                            <Layers className="w-5 h-5" />
                            Flashcards
                        </button>
                        <button
                            onClick={() => navigate(`/quick-review?topic=${topic.id}`)}
                            className="px-4 py-2 bg-yellow-500/20 border border-yellow-500/30 rounded-lg
                                       text-yellow-300 hover:bg-yellow-500/30 transition-colors flex items-center gap-2 text-sm font-medium"
                        >
                            <Star className="w-5 h-5" />
                            My Stars
                        </button>
                    </div>
                </div>

                {/* Progress Overview */}
                {learningPath && (
                    <div className="glass-card p-6 mb-8">
                        <div className="flex items-center justify-between mb-4">
                            <h2 className="text-xl font-semibold text-white">Your Progress</h2>
                            <span className="text-2xl font-bold text-primary-400">
                                {Math.round(learningPath.current_mastery * 100)}%
                            </span>
                        </div>

                        {/* Progress bar */}
                        <div className="h-3 bg-white/10 rounded-full overflow-hidden mb-4">
                            <div
                                className="h-full bg-gradient-to-r from-primary-500 to-accent-500 transition-all duration-500"
                                style={{ width: `${learningPath.current_mastery * 100}%` }}
                            />
                        </div>

                        {/* Stats */}
                        <div className="grid grid-cols-3 gap-4 text-center">
                            <div className="bg-white/5 p-3 rounded-xl">
                                <BookOpen className="w-5 h-5 text-blue-400 mx-auto mb-1" />
                                <p className="text-lg font-semibold text-white">
                                    {learningPath.completed_lessons}/{learningPath.total_lessons}
                                </p>
                                <p className="text-xs text-gray-400">Lessons</p>
                            </div>
                            <div className="bg-white/5 p-3 rounded-xl">
                                <Target className="w-5 h-5 text-green-400 mx-auto mb-1" />
                                <p className="text-lg font-semibold text-white">
                                    {learningPath.completed_practice}
                                </p>
                                <p className="text-xs text-gray-400">Practiced</p>
                            </div>
                            <div className="bg-white/5 p-3 rounded-xl">
                                <TrendingUp className="w-5 h-5 text-purple-400 mx-auto mb-1" />
                                <p className="text-lg font-semibold text-white">
                                    {Math.round(learningPath.current_mastery * 100)}%
                                </p>
                                <p className="text-xs text-gray-400">Mastery</p>
                            </div>
                        </div>
                    </div>
                )}

                {/* Recommended Next Action */}
                {learningPath && learningPath.next_action.action_type !== 'complete' && (
                    <div className="glass-card p-6 mb-8 border-l-4 border-primary-500">
                        <div className="flex items-center gap-4">
                            <div className={`w-12 h-12 rounded-full flex items-center justify-center ${learningPath.next_action.action_type === 'lesson'
                                ? 'bg-blue-500/20'
                                : learningPath.next_action.action_type === 'practice'
                                    ? 'bg-green-500/20'
                                    : 'bg-purple-500/20'
                                }`}>
                                {learningPath.next_action.action_type === 'lesson' && (
                                    <BookOpen className="w-6 h-6 text-blue-400" />
                                )}
                                {learningPath.next_action.action_type === 'practice' && (
                                    <Target className="w-6 h-6 text-green-400" />
                                )}
                                {learningPath.next_action.action_type === 'assessment' && (
                                    <Award className="w-6 h-6 text-purple-400" />
                                )}
                            </div>
                            <div className="flex-1">
                                <p className="text-sm text-gray-400 uppercase tracking-wider">
                                    Recommended Next
                                </p>
                                <h3 className="text-lg font-bold text-white">
                                    {learningPath.next_action.resource_name}
                                </h3>
                                <p className="text-sm text-gray-300">
                                    {learningPath.next_action.reason}
                                </p>
                            </div>
                            <button
                                onClick={handleStartRecommended}
                                className="btn-primary px-6 py-2 flex items-center gap-2"
                            >
                                Start
                                <ChevronRight className="w-4 h-4" />
                            </button>
                        </div>
                    </div>
                )}

                {/* Subtopics List */}
                <div className="mb-8">
                    <h2 className="text-xl font-semibold text-white mb-4 flex items-center gap-2">
                        <BookOpen className="w-5 h-5 text-primary-400" />
                        All Subtopics ({subtopics.length})
                    </h2>

                    <div className="space-y-3">
                        {subtopics.map((subtopic, index) => (
                            <div
                                key={subtopic.id}
                                className="glass-card overflow-hidden transition-all duration-200"
                            >
                                {/* Subtopic Header */}
                                <div
                                    className="p-4 cursor-pointer hover:bg-white/5 transition-colors"
                                    onClick={() => setExpandedSubtopic(
                                        expandedSubtopic === subtopic.id ? null : subtopic.id
                                    )}
                                >
                                    <div className="flex items-center gap-4">
                                        {/* Number Badge */}
                                        <div className={`w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold ${subtopic.mastery_level >= 0.7
                                            ? 'bg-green-500/20 text-green-400'
                                            : subtopic.lesson_completed
                                                ? 'bg-yellow-500/20 text-yellow-400'
                                                : 'bg-white/10 text-gray-400'
                                            }`}>
                                            {subtopic.mastery_level >= 0.7 ? '✓' : index + 1}
                                        </div>

                                        {/* Content */}
                                        <div className="flex-1 min-w-0">
                                            <div className="flex items-center gap-2">
                                                <h3 className="font-semibold text-white truncate">
                                                    {subtopic.name}
                                                </h3>
                                                <span className={`text-xs px-2 py-0.5 rounded-full ${subtopic.difficulty === 'hard'
                                                    ? 'bg-red-500/20 text-red-400'
                                                    : subtopic.difficulty === 'medium'
                                                        ? 'bg-yellow-500/20 text-yellow-400'
                                                        : 'bg-green-500/20 text-green-400'
                                                    }`}>
                                                    {subtopic.difficulty}
                                                </span>
                                            </div>

                                            {/* Progress Bar */}
                                            <div className="mt-2 flex items-center gap-3">
                                                <div className="flex-1 h-2 bg-white/10 rounded-full overflow-hidden">
                                                    <div
                                                        className={`h-full bg-gradient-to-r ${getProgressBarColor(subtopic.mastery_level)} transition-all duration-300`}
                                                        style={{ width: `${subtopic.mastery_level * 100}%` }}
                                                    />
                                                </div>
                                                <span className={`text-sm font-medium ${getMasteryColor(subtopic.mastery_level)}`}>
                                                    {Math.round(subtopic.mastery_level * 100)}%
                                                </span>
                                            </div>
                                        </div>

                                        {/* Status Icon */}
                                        <div className="flex items-center gap-2">
                                            {getStatusIcon(subtopic)}
                                            <ChevronDown
                                                className={`w-5 h-5 text-gray-400 transition-transform ${expandedSubtopic === subtopic.id ? 'rotate-180' : ''
                                                    }`}
                                            />
                                        </div>
                                    </div>
                                </div>

                                {/* Expanded Actions */}
                                {expandedSubtopic === subtopic.id && (
                                    <div className="border-t border-white/10 p-4 bg-white/5">
                                        <div className="grid grid-cols-3 gap-3">
                                            {/* Lesson Button */}
                                            <button
                                                onClick={(e) => {
                                                    e.stopPropagation()
                                                    handleStartLesson(subtopic.id)
                                                }}
                                                className={`p-3 rounded-xl text-center transition-all ${subtopic.lesson_completed
                                                    ? 'bg-blue-500/20 hover:bg-blue-500/30'
                                                    : 'bg-blue-500/30 hover:bg-blue-500/40 ring-2 ring-blue-500/50'
                                                    }`}
                                            >
                                                <BookOpen className="w-5 h-5 text-blue-400 mx-auto mb-1" />
                                                <span className="text-sm text-blue-400 font-medium">
                                                    {subtopic.lesson_completed ? 'Review Lesson' : 'Start Lesson'}
                                                </span>
                                                {subtopic.lesson_completed && (
                                                    <p className="text-xs text-blue-300/60 mt-1">Completed ✓</p>
                                                )}
                                            </button>

                                            {/* Practice Button */}
                                            <button
                                                onClick={(e) => {
                                                    e.stopPropagation()
                                                    handleStartPractice(subtopic.id)
                                                }}
                                                className="p-3 rounded-xl text-center bg-green-500/20 hover:bg-green-500/30 transition-all"
                                            >
                                                <Target className="w-5 h-5 text-green-400 mx-auto mb-1" />
                                                <span className="text-sm text-green-400 font-medium">Practice</span>
                                                {subtopic.practice_count > 0 && (
                                                    <p className="text-xs text-green-300/60 mt-1">
                                                        {subtopic.practice_count} sessions
                                                    </p>
                                                )}
                                            </button>

                                            {/* Assessment Button */}
                                            <button
                                                onClick={(e) => {
                                                    e.stopPropagation()
                                                    handleStartAssessment(subtopic.id)
                                                }}
                                                className={`p-3 rounded-xl text-center transition-all ${subtopic.mastery_level >= 0.4
                                                    ? 'bg-purple-500/20 hover:bg-purple-500/30'
                                                    : 'bg-gray-500/20 cursor-not-allowed'
                                                    }`}
                                                disabled={subtopic.mastery_level < 0.4}
                                            >
                                                {subtopic.mastery_level >= 0.4 ? (
                                                    <Award className="w-5 h-5 text-purple-400 mx-auto mb-1" />
                                                ) : (
                                                    <Lock className="w-5 h-5 text-gray-500 mx-auto mb-1" />
                                                )}
                                                <span className={`text-sm font-medium ${subtopic.mastery_level >= 0.4 ? 'text-purple-400' : 'text-gray-500'
                                                    }`}>
                                                    Assessment
                                                </span>
                                                {subtopic.mastery_level < 0.4 && (
                                                    <p className="text-xs text-gray-500 mt-1">Complete lesson first</p>
                                                )}
                                            </button>
                                        </div>
                                    </div>
                                )}
                            </div>
                        ))}
                    </div>
                </div>

                {/* Topic Complete Banner */}
                {learningPath && learningPath.next_action.action_type === 'complete' && (
                    <div className="glass-card p-8 text-center border border-green-500/30">
                        <div className="w-16 h-16 bg-green-500/20 rounded-full flex items-center justify-center mx-auto mb-4">
                            <Sparkles className="w-8 h-8 text-green-400" />
                        </div>
                        <h3 className="text-2xl font-bold text-white mb-2">
                            Topic Mastered! 🎉
                        </h3>
                        <p className="text-gray-400 mb-6">
                            Congratulations! You've completed all subtopics and achieved mastery.
                        </p>
                        <button
                            onClick={() => navigate('/dashboard')}
                            className="btn-primary px-8 py-3"
                        >
                            Continue to Dashboard
                        </button>
                    </div>
                )}
            </div>
        </div>
    )
}
