import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import {
    ArrowLeft,
    BookOpen,
    Calculator,
    ChevronRight,
    Loader2,
    Sparkles,
    Target,
    Trophy,
    Rocket,
    Star,
    Zap,
    FlaskConical,
    ClipboardCheck
} from 'lucide-react'
import { curriculumService, type SubjectWithTopics } from '@/services/curriculum'
import { studyService } from '@/services/study'
import { useStudentStore } from '@/stores/studentStore'
import type { Topic, StudyAction } from '@/types'

const subjectIcons: Record<string, typeof Calculator> = {
    'calculator': Calculator,
    'book-open': BookOpen,
    'flask': FlaskConical,
}

const subjectColors: Record<string, string> = {
    '#6366f1': 'from-blue-500 to-indigo-500',
    '#10b981': 'from-emerald-500 to-teal-500',
}

// Status badge configurations
const statusConfig = {
    lesson: {
        label: 'Ready to Learn',
        icon: BookOpen,
        color: 'bg-blue-500/20 text-blue-400 border-blue-500/30',
        buttonText: 'Start Learning',
        buttonClass: 'bg-gradient-to-r from-blue-500 to-indigo-500 hover:from-blue-600 hover:to-indigo-600',
        emoji: '📚'
    },
    practice: {
        label: 'Practice Time',
        icon: Zap,
        color: 'bg-green-500/20 text-green-400 border-green-500/30',
        buttonText: 'Keep Practicing',
        buttonClass: 'bg-gradient-to-r from-green-500 to-emerald-500 hover:from-green-600 hover:to-emerald-600',
        emoji: '💪'
    },
    assessment: {
        label: 'Ready for Test',
        icon: Target,
        color: 'bg-purple-500/20 text-purple-400 border-purple-500/30',
        buttonText: 'Take the Challenge',
        buttonClass: 'bg-gradient-to-r from-purple-500 to-pink-500 hover:from-purple-600 hover:to-pink-600',
        emoji: '🎯'
    },
    complete: {
        label: 'Mastered!',
        icon: Trophy,
        color: 'bg-yellow-500/20 text-yellow-400 border-yellow-500/30',
        buttonText: 'Review',
        buttonClass: 'bg-gradient-to-r from-yellow-500 to-orange-500 hover:from-yellow-600 hover:to-orange-600',
        emoji: '🏆'
    }
}

interface TopicWithStatus extends Topic {
    studyAction?: StudyAction
    isLoading?: boolean
}

export default function SubjectPage() {
    const { slug } = useParams<{ slug: string }>()
    const navigate = useNavigate()
    const { student, fetchStudent } = useStudentStore()
    const [subject, setSubject] = useState<SubjectWithTopics | null>(null)
    const [topicsWithStatus, setTopicsWithStatus] = useState<TopicWithStatus[]>([])
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)

    // Get student's grade level (default to 1 if not set)
    const studentGrade = student?.grade_level || 1

    useEffect(() => {
        // Ensure we have student info
        if (!student) {
            fetchStudent()
        }
    }, [])

    useEffect(() => {
        if (slug) {
            loadSubject(slug)
        }
    }, [slug, studentGrade])

    const loadSubject = async (subjectSlug: string) => {
        try {
            setLoading(true)
            const data = await curriculumService.getSubject(subjectSlug)
            setSubject(data)

            // Filter topics by student's grade level
            if (data.topics) {
                const gradeFilteredTopics = data.topics.filter(
                    (topic) => topic.grade_level === studentGrade
                )

                const initialTopics = gradeFilteredTopics.map(t => ({ ...t, isLoading: true }))
                setTopicsWithStatus(initialTopics)

                // Fetch study status for each topic
                await loadTopicStatuses(gradeFilteredTopics)
            }
        } catch (err) {
            setError('Failed to load subject')
            console.error(err)
        } finally {
            setLoading(false)
        }
    }

    const loadTopicStatuses = async (topics: Topic[]) => {
        // Fetch status for each topic in parallel
        const statusPromises = topics.map(async (topic) => {
            try {
                const action = await studyService.getNextStep(topic.id)
                return { ...topic, studyAction: action, isLoading: false }
            } catch {
                // If we can't get status, default to "lesson" (new topic)
                return {
                    ...topic,
                    studyAction: {
                        action_type: 'lesson' as const,
                        resource_id: topic.id,
                        resource_name: topic.name,
                        reason: "Let's start learning!",
                        mastery_level: 0
                    },
                    isLoading: false
                }
            }
        })

        const results = await Promise.all(statusPromises)
        setTopicsWithStatus(results)
    }

    const handleTopicAction = (topic: TopicWithStatus) => {
        // Always navigate to study page - let the AI decide what to show
        navigate(`/study/${topic.slug}`)
    }

    const getIcon = () => {
        if (subject?.icon && subjectIcons[subject.icon]) {
            return subjectIcons[subject.icon]
        }
        return BookOpen
    }

    const getColor = () => {
        if (subject?.color && subjectColors[subject.color]) {
            return subjectColors[subject.color]
        }
        return 'from-gray-500 to-gray-600'
    }

    if (loading) {
        return (
            <div className="min-h-screen flex items-center justify-center">
                <div className="text-center">
                    <Loader2 className="w-10 h-10 text-primary-500 animate-spin mx-auto mb-4" />
                    <p className="text-gray-400">Loading your learning journey...</p>
                </div>
            </div>
        )
    }

    if (error || !subject) {
        return (
            <div className="min-h-screen flex items-center justify-center">
                <div className="glass-card text-center">
                    <p className="text-red-400 mb-4">{error || 'Subject not found'}</p>
                    <button onClick={() => navigate('/dashboard')} className="btn-primary">
                        Back to Dashboard
                    </button>
                </div>
            </div>
        )
    }

    const IconComponent = getIcon()
    const colorClass = getColor()

    return (
        <div className="min-h-screen">
            {/* Header */}
            <header className="glass border-b border-white/10">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                    <div className="flex items-center h-16">
                        <button
                            onClick={() => navigate('/dashboard')}
                            className="mr-4 p-2 text-gray-400 hover:text-white hover:bg-white/10 rounded-lg transition-colors"
                        >
                            <ArrowLeft className="w-5 h-5" />
                        </button>
                        <div className="flex items-center gap-3">
                            <div className="w-10 h-10 bg-gradient-to-br from-primary-500 to-accent-500 rounded-xl flex items-center justify-center">
                                <Sparkles className="w-5 h-5 text-white" />
                            </div>
                            <span className="text-xl font-bold gradient-text">AI Tutor</span>
                        </div>
                    </div>
                </div>
            </header>

            {/* Main content */}
            <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
                {/* Subject header */}
                <div className="glass-card mb-8">
                    <div className="flex items-center gap-6">
                        <div className={`w-20 h-20 bg-gradient-to-br ${colorClass} rounded-2xl flex items-center justify-center shadow-lg`}>
                            <IconComponent className="w-10 h-10 text-white" />
                        </div>
                        <div className="flex-1">
                            <h1 className="text-3xl font-bold text-white mb-2">{subject.name}</h1>
                            <p className="text-gray-400">{subject.description}</p>
                            <div className="mt-2 inline-flex items-center gap-2 px-3 py-1 bg-primary-500/20 rounded-full border border-primary-500/30">
                                <span className="text-sm font-medium text-primary-400">📚 Grade {studentGrade} Topics</span>
                            </div>
                        </div>
                        <div className="hidden sm:flex items-center gap-4">
                            <div className="flex items-center gap-2 text-gray-400">
                                <Rocket className="w-5 h-5" />
                                <span>{topicsWithStatus.length} Adventures</span>
                            </div>
                            <button
                                onClick={() => navigate(`/quick-review?subject=${subject.id}`)}
                                className="px-4 py-2 bg-yellow-500/20 border border-yellow-500/30 rounded-lg
                                           text-yellow-300 hover:bg-yellow-500/30 transition-colors flex items-center gap-2 text-sm font-medium"
                            >
                                <Star className="w-5 h-5" />
                                My Stars
                            </button>
                            <button
                                onClick={() => navigate(`/exams/${slug}`)}
                                className="btn-primary flex items-center gap-2"
                            >
                                <ClipboardCheck className="w-5 h-5" />
                                Take Exam
                            </button>
                        </div>
                    </div>
                </div>

                {/* Topics list - Smart Cards */}
                <div className="mb-8">
                    <h2 className="text-xl font-semibold text-white mb-4 flex items-center gap-2">
                        <Star className="w-5 h-5 text-yellow-400" />
                        Your Grade {studentGrade} Learning Path
                    </h2>

                    {topicsWithStatus.length > 0 ? (
                        <div className="grid gap-4">
                            {topicsWithStatus.map((topic) => {
                                const status = topic.studyAction?.action_type || 'lesson'
                                const config = statusConfig[status]
                                const StatusIcon = config.icon
                                const mastery = topic.studyAction?.mastery_level || 0
                                const masteryPercent = Math.round(mastery * 100)

                                return (
                                    <div
                                        key={topic.id}
                                        className="glass-card group hover:bg-white/5 transition-all duration-300"
                                    >
                                        <div className="flex flex-col sm:flex-row sm:items-center gap-4">
                                            {/* Topic info */}
                                            <div className="flex items-center gap-4 flex-1">
                                                <div className="w-14 h-14 bg-white/10 rounded-xl flex items-center justify-center text-2xl">
                                                    {config.emoji}
                                                </div>
                                                <div className="flex-1">
                                                    <div className="flex items-center gap-2 mb-1">
                                                        <h3 className="text-lg font-semibold text-white">{topic.name}</h3>
                                                        <span className={`text-xs px-2 py-0.5 rounded-full border ${config.color}`}>
                                                            {config.label}
                                                        </span>
                                                    </div>
                                                    <p className="text-sm text-gray-400 mb-2">
                                                        {topic.studyAction?.reason || topic.description || `Grade ${topic.grade_level}`}
                                                    </p>

                                                    {/* Progress bar */}
                                                    <div className="flex items-center gap-3">
                                                        <div className="flex-1 h-2 bg-white/10 rounded-full overflow-hidden max-w-[200px]">
                                                            <div
                                                                className={`h-full transition-all duration-500 ${masteryPercent >= 70
                                                                    ? 'bg-gradient-to-r from-green-500 to-emerald-400'
                                                                    : masteryPercent >= 40
                                                                        ? 'bg-gradient-to-r from-yellow-500 to-orange-400'
                                                                        : 'bg-gradient-to-r from-blue-500 to-indigo-400'
                                                                    }`}
                                                                style={{ width: `${masteryPercent}%` }}
                                                            />
                                                        </div>
                                                        <span className="text-sm text-gray-400 min-w-[3rem]">
                                                            {masteryPercent}%
                                                        </span>
                                                    </div>
                                                </div>
                                            </div>

                                            {/* Action buttons */}
                                            <div className="flex-shrink-0 flex gap-2">
                                                {topic.isLoading ? (
                                                    <div className="px-6 py-3">
                                                        <Loader2 className="w-5 h-5 animate-spin text-gray-400" />
                                                    </div>
                                                ) : (
                                                    <>
                                                        <button
                                                            onClick={() => navigate(`/tests/${topic.slug}`)}
                                                            className="px-4 py-3 rounded-xl text-purple-400 font-medium flex items-center gap-2 transition-all duration-300 bg-purple-500/10 border border-purple-500/30 hover:bg-purple-500/20"
                                                            title="Take a 10-question test"
                                                        >
                                                            <Target className="w-5 h-5" />
                                                            Test
                                                        </button>
                                                        <button
                                                            onClick={() => handleTopicAction(topic)}
                                                            className={`px-6 py-3 rounded-xl text-white font-semibold flex items-center gap-2 transition-all duration-300 shadow-lg hover:shadow-xl hover:scale-105 ${config.buttonClass}`}
                                                        >
                                                            <StatusIcon className="w-5 h-5" />
                                                            {config.buttonText}
                                                            <ChevronRight className="w-4 h-4" />
                                                        </button>
                                                    </>
                                                )}
                                            </div>
                                        </div>
                                    </div>
                                )
                            })}
                        </div>
                    ) : (
                        <div className="glass-card text-center py-12">
                            <BookOpen className="w-12 h-12 text-gray-500 mx-auto mb-4" />
                            <p className="text-gray-400">No topics available yet.</p>
                        </div>
                    )}
                </div>
            </main>
        </div>
    )
}
