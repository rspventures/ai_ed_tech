/**
 * ParentDashboardPage - Analytics dashboard for parents/guardians
 * Shows child progress, activity feed, and insights
 */
import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import {
    Users,
    BookOpen,
    Award,
    Clock,
    TrendingUp,
    TrendingDown,
    AlertCircle,
    Star,
    Activity,
    ChevronRight,
    Loader2,
    BarChart3,
    Brain
} from 'lucide-react'
import { useAuthStore } from '@/stores/authStore'
import { parentService } from '@/services/parent'
import type { ChildListItem, ChildDetail, SubjectMastery, ActivityItem } from '@/types'

export default function ParentDashboardPage() {
    const navigate = useNavigate()
    const { user } = useAuthStore()

    const [children, setChildren] = useState<ChildListItem[]>([])
    const [selectedChild, setSelectedChild] = useState<string | null>(null)
    const [childDetail, setChildDetail] = useState<ChildDetail | null>(null)
    const [isLoading, setIsLoading] = useState(true)
    const [isLoadingDetail, setIsLoadingDetail] = useState(false)
    const [error, setError] = useState<string | null>(null)

    // Load children list
    useEffect(() => {
        async function loadChildren() {
            try {
                const data = await parentService.getChildren()
                setChildren(data)
                if (data.length > 0) {
                    setSelectedChild(data[0].student_id)
                }
            } catch (err) {
                setError('Failed to load children')
                console.error(err)
            } finally {
                setIsLoading(false)
            }
        }
        loadChildren()
    }, [])

    // Load selected child's detail
    useEffect(() => {
        async function loadChildDetail() {
            if (!selectedChild) return

            setIsLoadingDetail(true)
            try {
                const data = await parentService.getChildDetail(selectedChild)
                setChildDetail(data)
            } catch (err) {
                console.error(err)
            } finally {
                setIsLoadingDetail(false)
            }
        }
        loadChildDetail()
    }, [selectedChild])

    const getMasteryColor = (level: SubjectMastery['mastery_level']) => {
        switch (level) {
            case 'mastered': return 'text-green-400 bg-green-500/20'
            case 'proficient': return 'text-blue-400 bg-blue-500/20'
            case 'learning': return 'text-yellow-400 bg-yellow-500/20'
            case 'struggling': return 'text-red-400 bg-red-500/20'
            default: return 'text-gray-400 bg-gray-500/20'
        }
    }

    const getMasteryIcon = (level: SubjectMastery['mastery_level']) => {
        switch (level) {
            case 'mastered': return '🏆'
            case 'proficient': return '⭐'
            case 'learning': return '📚'
            case 'struggling': return '💪'
            default: return '📖'
        }
    }

    if (isLoading) {
        return (
            <div className="min-h-screen flex items-center justify-center">
                <Loader2 className="w-8 h-8 animate-spin text-primary-400" />
            </div>
        )
    }

    if (error) {
        return (
            <div className="min-h-screen flex items-center justify-center">
                <div className="text-center">
                    <AlertCircle className="w-12 h-12 text-red-400 mx-auto mb-4" />
                    <p className="text-red-400">{error}</p>
                </div>
            </div>
        )
    }

    if (children.length === 0) {
        return (
            <div className="min-h-screen flex items-center justify-center">
                <div className="text-center">
                    <Users className="w-16 h-16 text-gray-500 mx-auto mb-4" />
                    <h2 className="text-2xl font-bold text-white mb-2">No Students Found</h2>
                    <p className="text-gray-400">Add a student profile to start tracking their progress.</p>
                </div>
            </div>
        )
    }

    const summary = childDetail?.summary

    return (
        <div className="min-h-screen p-6 max-w-7xl mx-auto">
            {/* Header */}
            <div className="mb-8">
                <h1 className="text-3xl font-bold text-white mb-2">
                    👨‍👩‍👧 Parent Dashboard
                </h1>
                <p className="text-gray-400">
                    Track your child's learning progress and achievements
                </p>
            </div>

            {/* Child Selector */}
            {children.length > 1 && (
                <div className="mb-6">
                    <div className="flex gap-3">
                        {children.map(child => (
                            <button
                                key={child.student_id}
                                onClick={() => setSelectedChild(child.student_id)}
                                className={`px-4 py-2 rounded-lg transition-all ${selectedChild === child.student_id
                                        ? 'bg-primary-500 text-white'
                                        : 'bg-white/10 text-gray-300 hover:bg-white/20'
                                    }`}
                            >
                                {child.student_name}
                            </button>
                        ))}
                    </div>
                </div>
            )}

            {isLoadingDetail ? (
                <div className="flex items-center justify-center py-20">
                    <Loader2 className="w-8 h-8 animate-spin text-primary-400" />
                </div>
            ) : childDetail && summary ? (
                <>
                    {/* AI Insights Banner */}
                    {childDetail.ai_insights && (
                        <div className="glass-card p-6 mb-6 border-l-4 border-primary-500">
                            <div className="flex items-start gap-4">
                                <div className="w-12 h-12 bg-primary-500/20 rounded-full flex items-center justify-center flex-shrink-0">
                                    <Brain className="w-6 h-6 text-primary-400" />
                                </div>
                                <div>
                                    <h3 className="text-lg font-semibold text-white mb-1">AI Insights</h3>
                                    <p className="text-gray-300">{childDetail.ai_insights}</p>
                                </div>
                            </div>
                        </div>
                    )}

                    {/* Stats Cards */}
                    <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
                        <div className="glass-card p-6">
                            <div className="flex items-center gap-4">
                                <div className="w-12 h-12 bg-blue-500/20 rounded-xl flex items-center justify-center">
                                    <BookOpen className="w-6 h-6 text-blue-400" />
                                </div>
                                <div>
                                    <p className="text-gray-400 text-sm">Lessons Completed</p>
                                    <p className="text-2xl font-bold text-white">
                                        {summary.total_lessons_completed}
                                    </p>
                                </div>
                            </div>
                        </div>

                        <div className="glass-card p-6">
                            <div className="flex items-center gap-4">
                                <div className="w-12 h-12 bg-green-500/20 rounded-xl flex items-center justify-center">
                                    <Award className="w-6 h-6 text-green-400" />
                                </div>
                                <div>
                                    <p className="text-gray-400 text-sm">Average Score</p>
                                    <p className="text-2xl font-bold text-white">
                                        {summary.average_score}%
                                    </p>
                                </div>
                            </div>
                        </div>

                        <div className="glass-card p-6">
                            <div className="flex items-center gap-4">
                                <div className="w-12 h-12 bg-purple-500/20 rounded-xl flex items-center justify-center">
                                    <Clock className="w-6 h-6 text-purple-400" />
                                </div>
                                <div>
                                    <p className="text-gray-400 text-sm">Time Spent</p>
                                    <p className="text-2xl font-bold text-white">
                                        {summary.total_time_minutes} min
                                    </p>
                                </div>
                            </div>
                        </div>

                        <div className="glass-card p-6">
                            <div className="flex items-center gap-4">
                                <div className="w-12 h-12 bg-orange-500/20 rounded-xl flex items-center justify-center">
                                    <BarChart3 className="w-6 h-6 text-orange-400" />
                                </div>
                                <div>
                                    <p className="text-gray-400 text-sm">Assessments</p>
                                    <p className="text-2xl font-bold text-white">
                                        {summary.total_assessments_taken}
                                    </p>
                                </div>
                            </div>
                        </div>
                    </div>

                    {/* Main Content Grid */}
                    <div className="grid grid-cols-1 lg:grid-cols-3 gap-6">
                        {/* Subject Mastery */}
                        <div className="lg:col-span-2 glass-card p-6">
                            <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                                <Star className="w-5 h-5 text-yellow-400" />
                                Subject Mastery
                            </h3>

                            {summary.subject_mastery.length > 0 ? (
                                <div className="space-y-4">
                                    {summary.subject_mastery.map(subject => (
                                        <div key={subject.subject_id} className="bg-white/5 rounded-xl p-4">
                                            <div className="flex items-center justify-between mb-2">
                                                <div className="flex items-center gap-3">
                                                    <span className="text-2xl">{getMasteryIcon(subject.mastery_level)}</span>
                                                    <div>
                                                        <p className="text-white font-medium">{subject.subject_name}</p>
                                                        <p className="text-gray-400 text-sm">
                                                            {subject.topics_completed} / {subject.total_topics} topics
                                                        </p>
                                                    </div>
                                                </div>
                                                <span className={`px-3 py-1 rounded-full text-sm ${getMasteryColor(subject.mastery_level)}`}>
                                                    {subject.mastery_level}
                                                </span>
                                            </div>
                                            <div className="h-2 bg-white/10 rounded-full overflow-hidden">
                                                <div
                                                    className="h-full bg-gradient-to-r from-primary-500 to-purple-500 transition-all"
                                                    style={{ width: `${(subject.topics_completed / subject.total_topics) * 100}%` }}
                                                />
                                            </div>
                                        </div>
                                    ))}
                                </div>
                            ) : (
                                <p className="text-gray-400 text-center py-8">
                                    No subject data yet. Start learning to see progress!
                                </p>
                            )}
                        </div>

                        {/* Strengths & Alerts */}
                        <div className="space-y-6">
                            {/* Top Subjects */}
                            {summary.top_subjects.length > 0 && (
                                <div className="glass-card p-6">
                                    <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                                        <TrendingUp className="w-5 h-5 text-green-400" />
                                        Strengths
                                    </h3>
                                    <div className="space-y-2">
                                        {summary.top_subjects.map((subject, i) => (
                                            <div key={i} className="flex items-center gap-2">
                                                <span className="text-green-400">✓</span>
                                                <span className="text-gray-300">{subject}</span>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            )}

                            {/* Needs Attention */}
                            {summary.needs_attention.length > 0 && (
                                <div className="glass-card p-6 border border-yellow-500/30">
                                    <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                                        <TrendingDown className="w-5 h-5 text-yellow-400" />
                                        Needs Practice
                                    </h3>
                                    <div className="space-y-2">
                                        {summary.needs_attention.map((subject, i) => (
                                            <div key={i} className="flex items-center gap-2">
                                                <span className="text-yellow-400">!</span>
                                                <span className="text-gray-300">{subject}</span>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            )}
                        </div>
                    </div>

                    {/* Weekly Progress Chart */}
                    <div className="glass-card p-6 mt-6">
                        <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                            <Activity className="w-5 h-5 text-primary-400" />
                            This Week's Activity
                        </h3>
                        <div className="flex justify-between items-end h-40 gap-2">
                            {childDetail.weekly_progress.map((day, i) => (
                                <div key={i} className="flex-1 flex flex-col items-center gap-2">
                                    <div
                                        className="w-full bg-primary-500/50 rounded-t-lg transition-all hover:bg-primary-500"
                                        style={{
                                            height: `${Math.max(10, day.lessons * 30)}px`,
                                            maxHeight: '120px'
                                        }}
                                    />
                                    <span className="text-gray-400 text-xs">{day.day}</span>
                                </div>
                            ))}
                        </div>
                    </div>

                    {/* Recent Activity */}
                    <div className="glass-card p-6 mt-6">
                        <h3 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                            <Clock className="w-5 h-5 text-purple-400" />
                            Recent Activity
                        </h3>
                        {childDetail.recent_activity.length > 0 ? (
                            <div className="space-y-3">
                                {childDetail.recent_activity.slice(0, 5).map((activity, i) => (
                                    <div key={i} className="flex items-center gap-4 p-3 bg-white/5 rounded-lg">
                                        <span className="text-2xl">{activity.emoji}</span>
                                        <div className="flex-1">
                                            <p className="text-white">{activity.description}</p>
                                            <p className="text-gray-400 text-sm">
                                                {new Date(activity.timestamp).toLocaleDateString()}
                                            </p>
                                        </div>
                                        {activity.score !== undefined && (
                                            <span className={`font-bold ${activity.score >= 80 ? 'text-green-400' :
                                                    activity.score >= 60 ? 'text-yellow-400' : 'text-red-400'
                                                }`}>
                                                {activity.score}%
                                            </span>
                                        )}
                                    </div>
                                ))}
                            </div>
                        ) : (
                            <p className="text-gray-400 text-center py-8">
                                No recent activity. Encourage your child to start learning!
                            </p>
                        )}
                    </div>
                </>
            ) : null}
        </div>
    )
}
