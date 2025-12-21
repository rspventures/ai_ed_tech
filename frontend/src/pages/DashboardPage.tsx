import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import {
    BookOpen,
    Calculator,
    Trophy,
    TrendingUp,
    LogOut,
    Users,
    Sparkles,
    Target,
    Zap,
    Loader2,
    BarChart2,
    Calendar,
    ChevronRight,
    Award,
    Star,
    Rocket,
    Settings,
    FlaskConical
} from 'lucide-react'
import { useAuthStore } from '@/stores/authStore'
import { useStudentStore } from '@/stores/studentStore'
import { curriculumService } from '@/services/curriculum'
import { assessmentService } from '@/services/assessment'
import { studyService } from '@/services/study'
import SmartReviewCard from '@/components/SmartReviewCard'
import GamificationBar from '@/components/GamificationBar'
import type { Subject, EnrichedProgress, AssessmentResult, StudyAction } from '@/types'

// Icon mapping for subjects
const subjectIcons: Record<string, typeof Calculator> = {
    'calculator': Calculator,
    'book-open': BookOpen,
    'flask': FlaskConical,
}

// Color mapping for subjects
const subjectColors: Record<string, string> = {
    '#6366f1': 'from-blue-500 to-indigo-500',
    '#10b981': 'from-emerald-500 to-teal-500',
}

type TabType = 'subjects' | 'assessments'

interface RecommendedAction {
    topicSlug: string
    topicName: string
    subjectName: string
    action: StudyAction
}

export default function DashboardPage() {
    const navigate = useNavigate()
    const { user, logout, checkAuth } = useAuthStore()
    const { student, fetchStudent, getAvatarEmoji, getThemeGradient } = useStudentStore()
    const [subjects, setSubjects] = useState<Subject[]>([])
    const [progress, setProgress] = useState<EnrichedProgress[]>([])
    const [assessmentHistory, setAssessmentHistory] = useState<AssessmentResult[]>([])
    const [loading, setLoading] = useState(true)
    const [activeTab, setActiveTab] = useState<TabType>('subjects')
    const [recommendedAction, setRecommendedAction] = useState<RecommendedAction | null>(null)
    const [loadingRecommendation, setLoadingRecommendation] = useState(true)

    useEffect(() => {
        checkAuth()
        fetchStudent() // Load student personalization data
        loadData()
    }, [checkAuth, fetchStudent])

    const loadData = async () => {
        try {
            const [subjectsData, progressData] = await Promise.all([
                curriculumService.getSubjects(),
                curriculumService.getProgress()
            ])
            setSubjects(subjectsData)
            setProgress(progressData)

            // Load assessment history
            try {
                const historyData = await assessmentService.getHistory()
                setAssessmentHistory(historyData)
            } catch (err) {
                console.error('Failed to load assessment history:', err)
            }

            // Load recommended action from first subject's first topic
            await loadRecommendation(subjectsData)
        } catch (error) {
            console.error('Failed to load data:', error)
        } finally {
            setLoading(false)
        }
    }

    const loadRecommendation = async (subjectsData: Subject[]) => {
        setLoadingRecommendation(true)
        try {
            // Get the first subject with topics
            for (const subject of subjectsData) {
                const subjectDetails = await curriculumService.getSubject(subject.slug)
                if (subjectDetails.topics && subjectDetails.topics.length > 0) {
                    const firstTopic = subjectDetails.topics[0]
                    try {
                        const action = await studyService.getNextStep(firstTopic.id)
                        setRecommendedAction({
                            topicSlug: firstTopic.slug,
                            topicName: firstTopic.name,
                            subjectName: subject.name,
                            action
                        })
                        break
                    } catch {
                        // Continue to next topic/subject
                    }
                }
            }
        } catch (err) {
            console.error('Failed to load recommendation:', err)
        } finally {
            setLoadingRecommendation(false)
        }
    }

    const handleLogout = async () => {
        await logout()
        navigate('/login')
    }

    const handleSubjectClick = (subject: Subject) => {
        navigate(`/subjects/${subject.slug}`)
    }

    const handleStartRecommended = () => {
        if (recommendedAction) {
            navigate(`/study/${recommendedAction.topicSlug}`)
        }
    }

    // Calculate aggregated stats
    const totalQuestions = progress.reduce((sum: number, p: EnrichedProgress) => sum + p.questions_attempted, 0)
    const maxStreak = progress.reduce((max: number, p: EnrichedProgress) => Math.max(max, p.current_streak), 0)
    const totalAssessments = assessmentHistory.length
    const avgAssessmentScore = totalAssessments > 0
        ? Math.round(assessmentHistory.reduce((sum: number, a: AssessmentResult) => sum + a.score, 0) / totalAssessments)
        : 0

    const stats = [
        { label: 'Questions Answered', value: totalQuestions.toString(), icon: Target, color: 'text-blue-400' },
        { label: 'Current Streak', value: `${maxStreak} 🔥`, icon: Zap, color: 'text-amber-400' },
        { label: 'Assessments', value: totalAssessments.toString(), icon: Award, color: 'text-purple-400' },
        { label: 'Avg. Score', value: `${avgAssessmentScore}%`, icon: BarChart2, color: 'text-emerald-400' },
    ]

    const getSubjectIcon = (iconName: string | undefined) => {
        if (iconName && subjectIcons[iconName]) {
            return subjectIcons[iconName]
        }
        return BookOpen
    }

    const getSubjectColor = (color: string | undefined) => {
        if (color && subjectColors[color]) {
            return subjectColors[color]
        }
        return 'from-gray-500 to-gray-600'
    }

    const formatDate = (dateString: string) => {
        const date = new Date(dateString)
        return date.toLocaleDateString('en-US', {
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit'
        })
    }

    const getScoreColor = (score: number) => {
        if (score >= 80) return 'text-green-400'
        if (score >= 60) return 'text-yellow-400'
        return 'text-red-400'
    }

    const getScoreBg = (score: number) => {
        if (score >= 80) return 'bg-green-500/20'
        if (score >= 60) return 'bg-yellow-500/20'
        return 'bg-red-500/20'
    }

    const getActionEmoji = (actionType: string) => {
        switch (actionType) {
            case 'lesson': return '📚'
            case 'practice': return '💪'
            case 'assessment': return '🎯'
            case 'complete': return '🏆'
            default: return '🚀'
        }
    }

    const getActionLabel = (actionType: string) => {
        switch (actionType) {
            case 'lesson': return 'Learn Something New'
            case 'practice': return 'Practice Makes Perfect'
            case 'assessment': return 'Ready for a Challenge'
            case 'complete': return 'You\'re a Star!'
            default: return 'Continue Learning'
        }
    }

    return (
        <div className="min-h-screen">
            {/* Header */}
            <header className="glass border-b border-white/10">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                    <div className="flex items-center justify-between h-16">
                        <div className="flex items-center gap-3">
                            <div className="w-10 h-10 bg-gradient-to-br from-primary-500 to-accent-500 rounded-xl flex items-center justify-center">
                                <Sparkles className="w-5 h-5 text-white" />
                            </div>
                            <span className="text-xl font-bold gradient-text">AI Tutor</span>
                        </div>

                        <div className="flex items-center gap-4">
                            {/* Gamification Stats - XP, Level, Streak */}
                            <div className="hidden lg:block">
                                <GamificationBar compact />
                            </div>

                            {/* Study Materials / Documents Link */}
                            <button
                                onClick={() => navigate('/documents')}
                                className="flex items-center gap-2 px-3 py-2 bg-gradient-to-r from-emerald-500/20 to-teal-500/20 
                                           border border-emerald-500/30 rounded-lg text-emerald-300 hover:text-white 
                                           hover:from-emerald-500/30 hover:to-teal-500/30 transition-all"
                                title="Study Materials"
                            >
                                <BookOpen className="w-4 h-4" />
                                <span className="hidden sm:inline text-sm font-medium">Documents</span>
                            </button>

                            {/* Visual Explainer Link */}
                            <button
                                onClick={() => navigate('/visuals')}
                                className="flex items-center gap-2 px-3 py-2 bg-gradient-to-r from-pink-500/20 to-purple-500/20 
                                           border border-pink-500/30 rounded-lg text-pink-300 hover:text-white 
                                           hover:from-pink-500/30 hover:to-purple-500/30 transition-all"
                                title="Visual Explainer"
                            >
                                <Sparkles className="w-4 h-4" />
                                <span className="hidden sm:inline text-sm font-medium">Visuals</span>
                            </button>

                            {/* Parent Dashboard Link */}
                            <button
                                onClick={() => navigate('/parent')}
                                className="flex items-center gap-2 px-3 py-2 bg-gradient-to-r from-purple-500/20 to-indigo-500/20 
                                           border border-purple-500/30 rounded-lg text-purple-300 hover:text-white 
                                           hover:from-purple-500/30 hover:to-indigo-500/30 transition-all"
                                title="Parent Dashboard"
                            >
                                <Users className="w-4 h-4" />
                                <span className="hidden sm:inline text-sm font-medium">Parent View</span>
                            </button>


                            <div className="flex items-center gap-3">
                                {/* Personalized Avatar - Using student's selected avatar and theme color */}
                                <div
                                    className="w-10 h-10 rounded-full flex items-center justify-center text-xl shadow-lg"
                                    style={{ background: getThemeGradient() }}
                                >
                                    {getAvatarEmoji()}
                                </div>
                                <div className="hidden sm:block">
                                    <p className="text-sm font-medium text-white">
                                        {student?.display_name || student?.first_name || user?.first_name}
                                    </p>
                                    <p className="text-xs text-gray-400">
                                        Grade {student?.grade_level || 1} • {user?.email}
                                    </p>
                                </div>
                            </div>
                            <button
                                onClick={() => navigate('/settings')}
                                className="p-2 text-gray-400 hover:text-white hover:bg-white/10 rounded-lg transition-colors"
                                title="Settings"
                            >
                                <Settings className="w-5 h-5" />
                            </button>
                            <button
                                onClick={handleLogout}
                                className="p-2 text-gray-400 hover:text-white hover:bg-white/10 rounded-lg transition-colors"
                                title="Logout"
                            >
                                <LogOut className="w-5 h-5" />
                            </button>
                        </div>
                    </div>
                </div>
            </header>

            {/* Main content */}
            <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
                {/* Welcome section with personalized avatar */}
                <div className="mb-8 flex items-center gap-4">
                    <div
                        className="w-16 h-16 rounded-2xl flex items-center justify-center text-3xl shadow-lg"
                        style={{ background: getThemeGradient() }}
                    >
                        {getAvatarEmoji()}
                    </div>
                    <div>
                        <h1 className="text-3xl font-bold text-white mb-1">
                            Welcome back, {student?.display_name || student?.first_name || user?.first_name}!
                        </h1>
                        <p className="text-gray-400">
                            Ready to continue your learning journey? Let's make today count!
                        </p>
                    </div>
                </div>

                {/* 🌟 RECOMMENDED MISSION CARD (NEW) */}
                <div className="mb-8">
                    <div className="glass-card relative overflow-hidden bg-gradient-to-r from-primary-500/10 to-accent-500/10 border border-primary-500/20">
                        {/* Background decoration */}
                        <div className="absolute top-0 right-0 w-40 h-40 bg-primary-500/10 rounded-full blur-3xl" />
                        <div className="absolute bottom-0 left-0 w-32 h-32 bg-accent-500/10 rounded-full blur-3xl" />

                        <div className="relative">
                            <div className="flex items-center gap-2 mb-4">
                                <Rocket className="w-5 h-5 text-primary-400" />
                                <span className="text-sm font-medium text-primary-400 uppercase tracking-wider">
                                    Up Next For You
                                </span>
                            </div>

                            {loadingRecommendation ? (
                                <div className="flex items-center gap-4 py-4">
                                    <Loader2 className="w-6 h-6 text-primary-400 animate-spin" />
                                    <span className="text-gray-400">Finding your next adventure...</span>
                                </div>
                            ) : recommendedAction ? (
                                <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                                    <div className="flex items-center gap-4">
                                        <div className="w-16 h-16 bg-white/10 rounded-2xl flex items-center justify-center text-3xl">
                                            {getActionEmoji(recommendedAction.action.action_type)}
                                        </div>
                                        <div>
                                            <p className="text-sm text-gray-400">{recommendedAction.subjectName}</p>
                                            <h3 className="text-xl font-bold text-white">
                                                {recommendedAction.topicName}
                                            </h3>
                                            <p className="text-gray-300 mt-1">
                                                {getActionLabel(recommendedAction.action.action_type)}
                                            </p>
                                        </div>
                                    </div>

                                    <button
                                        onClick={handleStartRecommended}
                                        className="btn-primary px-6 py-3 text-lg flex items-center gap-2 shadow-lg hover:shadow-xl hover:scale-105 transition-all"
                                    >
                                        <span>Let's Go!</span>
                                        <ChevronRight className="w-5 h-5" />
                                    </button>
                                </div>
                            ) : (
                                <div className="text-gray-400 py-4">
                                    <p>Explore a subject to start your learning journey!</p>
                                </div>
                            )}
                        </div>
                    </div>
                </div>

                {/* Stats grid */}
                <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
                    {stats.map((stat) => (
                        <div key={stat.label} className="glass-card card-hover">
                            <div className="flex items-center gap-3">
                                <div className={`p-2 rounded-lg bg-white/5 ${stat.color}`}>
                                    <stat.icon className="w-5 h-5" />
                                </div>
                                <div>
                                    <p className="text-2xl font-bold text-white">{stat.value}</p>
                                    <p className="text-sm text-gray-400">{stat.label}</p>
                                </div>
                            </div>
                        </div>
                    ))}
                </div>

                {/* 🧠 SMART REVIEW SECTION */}
                <div className="mb-8">
                    <SmartReviewCard />
                </div>

                {/* Tabs */}
                <div className="flex gap-2 mb-6">
                    <button
                        onClick={() => setActiveTab('subjects')}
                        className={`px-6 py-3 rounded-xl font-medium transition-all ${activeTab === 'subjects'
                            ? 'bg-primary-500 text-white'
                            : 'bg-white/5 text-gray-400 hover:bg-white/10 hover:text-white'
                            }`}
                    >
                        <div className="flex items-center gap-2">
                            <BookOpen className="w-5 h-5" />
                            Subjects
                        </div>
                    </button>
                    <button
                        onClick={() => setActiveTab('assessments')}
                        className={`px-6 py-3 rounded-xl font-medium transition-all ${activeTab === 'assessments'
                            ? 'bg-primary-500 text-white'
                            : 'bg-white/5 text-gray-400 hover:bg-white/10 hover:text-white'
                            }`}
                    >
                        <div className="flex items-center gap-2">
                            <BarChart2 className="w-5 h-5" />
                            Assessment History
                            {assessmentHistory.length > 0 && (
                                <span className="bg-white/20 px-2 py-0.5 rounded-full text-xs">
                                    {assessmentHistory.length}
                                </span>
                            )}
                        </div>
                    </button>
                </div>

                {/* Tab Content */}
                {activeTab === 'subjects' && (
                    <div className="mb-8">
                        <h2 className="text-xl font-semibold text-white mb-4">Your Subjects</h2>

                        {loading ? (
                            <div className="flex items-center justify-center py-12">
                                <Loader2 className="w-8 h-8 text-primary-500 animate-spin" />
                            </div>
                        ) : subjects.length === 0 ? (
                            <div className="glass-card text-center py-12">
                                <BookOpen className="w-12 h-12 text-gray-500 mx-auto mb-4" />
                                <p className="text-gray-400">No subjects available yet.</p>
                            </div>
                        ) : (
                            <div className="grid md:grid-cols-2 gap-6">
                                {subjects.map((subject) => {
                                    const IconComponent = getSubjectIcon(subject.icon)
                                    const colorClass = getSubjectColor(subject.color)

                                    // Calculate subject specific progress
                                    const subjectProgress = progress.filter((p: EnrichedProgress) => p.subject_name === subject.name)
                                    const subjectMasterySum = subjectProgress.reduce((sum: number, p: EnrichedProgress) => sum + p.mastery_level, 0)
                                    const displayPercentage = subjectProgress.length > 0
                                        ? Math.round((subjectMasterySum / subjectProgress.length) * 100)
                                        : 0

                                    return (
                                        <div
                                            key={subject.id}
                                            onClick={() => handleSubjectClick(subject)}
                                            className="glass-card card-hover cursor-pointer group"
                                        >
                                            <div className="flex items-start justify-between mb-4">
                                                <div className="flex items-center gap-4">
                                                    <div className={`w-14 h-14 bg-gradient-to-br ${colorClass} rounded-xl flex items-center justify-center shadow-lg group-hover:scale-110 transition-transform`}>
                                                        <IconComponent className="w-7 h-7 text-white" />
                                                    </div>
                                                    <div>
                                                        <h3 className="text-lg font-semibold text-white">{subject.name}</h3>
                                                        <p className="text-sm text-gray-400">
                                                            {subject.description || 'Start learning today!'}
                                                        </p>
                                                    </div>
                                                </div>
                                            </div>

                                            {/* Progress bar */}
                                            <div className="space-y-2">
                                                <div className="flex items-center justify-between text-sm">
                                                    <span className="text-gray-400">Mastery</span>
                                                    <span className="text-white font-medium">{displayPercentage}%</span>
                                                </div>
                                                <div className="h-2 bg-white/10 rounded-full overflow-hidden">
                                                    <div
                                                        className={`h-full bg-gradient-to-r ${colorClass} rounded-full transition-all duration-500`}
                                                        style={{ width: `${displayPercentage}%` }}
                                                    />
                                                </div>
                                            </div>

                                            {/* Single smart button */}
                                            <div className="mt-4">
                                                <button
                                                    className="w-full btn-primary text-sm flex items-center justify-center gap-2"
                                                    onClick={(e: React.MouseEvent) => {
                                                        e.stopPropagation()
                                                        navigate(`/subjects/${subject.slug}`)
                                                    }}
                                                >
                                                    <Star className="w-4 h-4" />
                                                    Start Learning
                                                    <ChevronRight className="w-4 h-4" />
                                                </button>
                                            </div>
                                        </div>
                                    )
                                })}
                            </div>
                        )}
                    </div>
                )}

                {activeTab === 'assessments' && (
                    <div className="mb-8">
                        <h2 className="text-xl font-semibold text-white mb-4">Assessment History</h2>

                        {loading ? (
                            <div className="flex items-center justify-center py-12">
                                <Loader2 className="w-8 h-8 text-primary-500 animate-spin" />
                            </div>
                        ) : assessmentHistory.length === 0 ? (
                            <div className="glass-card text-center py-12">
                                <BarChart2 className="w-12 h-12 text-gray-500 mx-auto mb-4" />
                                <p className="text-gray-400 mb-4">No assessments completed yet.</p>
                                <p className="text-gray-500 text-sm">
                                    Complete an assessment to track your progress over time!
                                </p>
                            </div>
                        ) : (
                            <div className="space-y-4">
                                {/* Score Trend Chart */}
                                <div className="glass-card p-6 mb-6">
                                    <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                                        <TrendingUp className="w-5 h-5 text-primary-400" />
                                        Your Score Trend
                                    </h3>
                                    <div className="flex items-end gap-2 h-32">
                                        {assessmentHistory.slice(-10).map((assessment: AssessmentResult, idx: number) => (
                                            <div key={assessment.id} className="flex-1 flex flex-col items-center gap-1">
                                                <div
                                                    className={`w-full rounded-t-lg transition-all ${getScoreBg(assessment.score)}`}
                                                    style={{ height: `${assessment.score}%` }}
                                                />
                                                <span className="text-xs text-gray-500">{idx + 1}</span>
                                            </div>
                                        ))}
                                    </div>
                                </div>

                                {/* Assessment cards */}
                                {assessmentHistory.map((assessment: AssessmentResult) => (
                                    <div key={assessment.id} className="glass-card">
                                        <div className="flex items-center justify-between">
                                            <div className="flex items-center gap-4">
                                                <div className={`w-12 h-12 rounded-xl flex items-center justify-center ${getScoreBg(assessment.score)}`}>
                                                    {assessment.score >= 80 ? (
                                                        <Trophy className={`w-6 h-6 ${getScoreColor(assessment.score)}`} />
                                                    ) : (
                                                        <Target className={`w-6 h-6 ${getScoreColor(assessment.score)}`} />
                                                    )}
                                                </div>
                                                <div>
                                                    <h4 className="font-semibold text-white">
                                                        {assessment.topic_name || 'Assessment'}
                                                    </h4>
                                                    <div className="flex items-center gap-2 text-sm text-gray-400">
                                                        <Calendar className="w-4 h-4" />
                                                        {formatDate(assessment.completed_at)}
                                                    </div>
                                                </div>
                                            </div>
                                            <div className="text-right">
                                                <p className={`text-2xl font-bold ${getScoreColor(assessment.score)}`}>
                                                    {assessment.score}%
                                                </p>
                                                <p className="text-sm text-gray-400">
                                                    {assessment.correct_questions}/{assessment.total_questions} correct
                                                </p>
                                            </div>
                                        </div>

                                        {assessment.feedback && (
                                            <div className="mt-4 pt-4 border-t border-white/10">
                                                <p className="text-sm text-gray-300">
                                                    <strong className="text-primary-400">Feedback:</strong>{' '}
                                                    {assessment.feedback.overall_assessment?.slice(0, 150)}...
                                                </p>
                                            </div>
                                        )}
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
                )}
            </main>
        </div>
    )
}
