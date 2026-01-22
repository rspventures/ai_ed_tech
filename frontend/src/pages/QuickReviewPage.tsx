import { useState, useEffect } from 'react'
import { useNavigate, useSearchParams } from 'react-router-dom'
import {
    Loader2, Star, ChevronLeft, BookOpen, Lightbulb, Sparkles,
    Target, HelpCircle, Filter, ListOrdered, ClipboardCheck, CheckCircle
} from 'lucide-react'
import { studyService } from '@/services/study'
import { curriculumService } from '@/services/curriculum'
import type { FavoriteModule, Subject, Topic, Subtopic } from '@/types'

/**
 * QuickReviewPage - View starred/favorite modules
 * 
 * Supports hierarchical filtering:
 * - Global: Subject → Topic → Subtopic cascading filters
 * - Subject: Topic → Subtopic filters  
 * - Topic: Subtopic filter
 * - Subtopic: Only that subtopic's stars
 */
export default function QuickReviewPage() {
    const navigate = useNavigate()
    const [searchParams] = useSearchParams()

    // URL params for pre-filtering
    const urlSubjectId = searchParams.get('subject')
    const urlTopicId = searchParams.get('topic')
    const urlSubtopicId = searchParams.get('subtopic')

    const [loading, setLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)
    const [favorites, setFavorites] = useState<FavoriteModule[]>([])

    // Hierarchical data
    const [subjects, setSubjects] = useState<Subject[]>([])
    const [topics, setTopics] = useState<Topic[]>([])
    const [subtopics, setSubtopics] = useState<Subtopic[]>([])

    // Filter selections
    const [selectedSubject, setSelectedSubject] = useState<string>(urlSubjectId || '')
    const [selectedTopic, setSelectedTopic] = useState<string>(urlTopicId || '')
    const [selectedSubtopic, setSelectedSubtopic] = useState<string>(urlSubtopicId || '')

    // Determine the filter level based on URL params
    const filterLevel = urlSubtopicId ? 'subtopic' : urlTopicId ? 'topic' : urlSubjectId ? 'subject' : 'global'

    useEffect(() => {
        loadData()
    }, [])

    // Load topics when subject changes
    useEffect(() => {
        if (selectedSubject) {
            loadTopicsForSubject(selectedSubject)
        } else {
            setTopics([])
            setSelectedTopic('')
            setSubtopics([])
            setSelectedSubtopic('')
        }
    }, [selectedSubject])

    // Load subtopics when topic changes
    useEffect(() => {
        if (selectedTopic) {
            loadSubtopicsForTopic(selectedTopic)
        } else {
            setSubtopics([])
            setSelectedSubtopic('')
        }
    }, [selectedTopic])

    const loadData = async () => {
        setLoading(true)
        try {
            // Load all subjects first
            const subjectsData = await curriculumService.getSubjects()
            setSubjects(subjectsData)

            // Load favorites based on URL filter level
            let favData
            if (urlSubtopicId) {
                favData = await studyService.getFavoritesBySubtopic(urlSubtopicId)
            } else if (urlTopicId) {
                favData = await studyService.getFavoritesByTopic(urlTopicId)
            } else if (urlSubjectId) {
                favData = await studyService.getFavoritesBySubject(urlSubjectId)
            } else {
                favData = await studyService.getAllFavorites()
            }
            setFavorites(favData.favorites)

            // Auto-populate hierarchy based on URL level using favorites data
            if (favData.favorites.length > 0) {
                const firstFav = favData.favorites[0]

                // Subject level: auto-select subject, load topics
                if (urlSubjectId) {
                    setSelectedSubject(urlSubjectId)
                    const subject = subjectsData.find((s: Subject) => s.id === urlSubjectId)
                    if (subject) {
                        const details = await curriculumService.getSubject(subject.slug)
                        setTopics(details.topics || [])
                    }
                }

                // Topic level: auto-select subject and topic, load subtopics
                if (urlTopicId) {
                    // Get subject from favorites data
                    if (firstFav.subject_id) {
                        setSelectedSubject(firstFav.subject_id)
                        const subject = subjectsData.find((s: Subject) => s.id === firstFav.subject_id)
                        if (subject) {
                            const subjectDetails = await curriculumService.getSubject(subject.slug)
                            setTopics(subjectDetails.topics || [])

                            // Now load subtopics for this topic
                            const topic = subjectDetails.topics?.find((t: Topic) => t.id === urlTopicId)
                            if (topic) {
                                setSelectedTopic(urlTopicId)
                                const topicDetails = await curriculumService.getTopic(topic.slug)
                                setSubtopics(topicDetails.subtopics || [])
                            }
                        }
                    }
                }

                // Subtopic level: auto-select all three
                if (urlSubtopicId) {
                    if (firstFav.subject_id) {
                        setSelectedSubject(firstFav.subject_id)
                        const subject = subjectsData.find((s: Subject) => s.id === firstFav.subject_id)
                        if (subject) {
                            const subjectDetails = await curriculumService.getSubject(subject.slug)
                            setTopics(subjectDetails.topics || [])

                            if (firstFav.topic_id) {
                                setSelectedTopic(firstFav.topic_id)
                                const topic = subjectDetails.topics?.find((t: Topic) => t.id === firstFav.topic_id)
                                if (topic) {
                                    const topicDetails = await curriculumService.getTopic(topic.slug)
                                    setSubtopics(topicDetails.subtopics || [])
                                    setSelectedSubtopic(urlSubtopicId)
                                }
                            }
                        }
                    }
                }
            }
        } catch (err) {
            console.error('Failed to load favorites:', err)
            setError('Failed to load your favorites')
        } finally {
            setLoading(false)
        }
    }

    const loadTopicsForSubject = async (subjectId: string) => {
        try {
            const subject = subjects.find(s => s.id === subjectId)
            if (subject) {
                const details = await curriculumService.getSubject(subject.slug)
                setTopics(details.topics || [])
            }
        } catch (err) {
            console.error('Failed to load topics:', err)
        }
    }

    const loadSubtopicsForTopic = async (topicId: string) => {
        try {
            const topic = topics.find(t => t.id === topicId)
            if (topic) {
                const details = await curriculumService.getTopic(topic.slug)
                setSubtopics(details.subtopics || [])
            }
        } catch (err) {
            console.error('Failed to load subtopics:', err)
        }
    }

    const handleRemoveFavorite = async (favoriteId: string) => {
        try {
            await studyService.removeFavorite(favoriteId)
            setFavorites(prev => prev.filter(f => f.id !== favoriteId))
        } catch (err) {
            console.error('Failed to remove favorite:', err)
        }
    }

    // Get title based on filter level
    const getTitle = () => {
        if (urlSubtopicId) {
            const st = favorites[0]?.subtopic_name || 'Subtopic'
            return `Stars: ${st}`
        }
        if (urlTopicId) {
            const t = favorites[0]?.topic_name || 'Topic'
            return `Stars: ${t}`
        }
        if (urlSubjectId) {
            const s = favorites[0]?.subject_name || 'Subject'
            return `Stars: ${s}`
        }
        return 'Quick Review'
    }

    // Render module tile (same as before)
    const renderModuleTile = (fav: FavoriteModule) => {
        const content = fav.module_content
        const type = fav.module_type

        switch (type) {
            case 'hook':
                return (
                    <div className="bg-gradient-to-r from-yellow-500/20 to-orange-500/20 p-5 rounded-xl border border-yellow-500/30">
                        <div className="flex items-start gap-3">
                            <Sparkles className="w-6 h-6 text-yellow-400 flex-shrink-0" />
                            <div>
                                <span className="text-xs text-yellow-400 uppercase font-medium">Hook</span>
                                <p className="text-white mt-1">{content.emoji || '🤔'} {content.content}</p>
                            </div>
                        </div>
                    </div>
                )

            case 'text':
                return (
                    <div className="bg-white/5 p-5 rounded-xl border border-white/10">
                        <div className="flex items-start gap-3">
                            <BookOpen className="w-6 h-6 text-primary-400 flex-shrink-0" />
                            <div>
                                <span className="text-xs text-primary-400 uppercase font-medium">Text</span>
                                <p className="text-gray-200 mt-1">{content.content}</p>
                            </div>
                        </div>
                    </div>
                )

            case 'flashcard':
                return (
                    <div className="bg-gradient-to-br from-primary-500/20 to-purple-500/20 p-5 rounded-xl border border-primary-500/30">
                        <div className="flex items-start gap-3">
                            <Lightbulb className="w-6 h-6 text-purple-400 flex-shrink-0" />
                            <div className="flex-1">
                                <span className="text-xs text-purple-400 uppercase font-medium">Flashcard</span>
                                <div className="mt-2 space-y-2">
                                    <div className="bg-white/10 p-3 rounded-lg">
                                        <p className="text-xs text-gray-400 mb-1">Front:</p>
                                        <p className="text-white font-medium">{content.front}</p>
                                    </div>
                                    <div className="bg-purple-500/10 p-3 rounded-lg">
                                        <p className="text-xs text-gray-400 mb-1">Back:</p>
                                        <p className="text-purple-300">{content.back}</p>
                                    </div>
                                </div>
                            </div>
                        </div>
                    </div>
                )

            case 'fun_fact':
                return (
                    <div className="bg-gradient-to-r from-pink-500/20 to-purple-500/20 p-5 rounded-xl border border-pink-500/30">
                        <div className="flex items-start gap-3">
                            <Star className="w-6 h-6 text-pink-400 flex-shrink-0" />
                            <div>
                                <span className="text-xs text-pink-400 uppercase font-medium">Fun Fact</span>
                                <p className="text-white mt-1">🌟 {content.content}</p>
                            </div>
                        </div>
                    </div>
                )

            case 'quiz_single':
                return (
                    <div className="bg-white/5 p-5 rounded-xl border border-blue-500/30">
                        <div className="flex items-start gap-3">
                            <HelpCircle className="w-6 h-6 text-blue-400 flex-shrink-0" />
                            <div className="flex-1">
                                <span className="text-xs text-blue-400 uppercase font-medium">Quiz</span>
                                <p className="text-white font-medium mt-1">{content.question}</p>
                                <div className="mt-3 space-y-2">
                                    {content.options?.map((opt: string, idx: number) => (
                                        <div
                                            key={idx}
                                            className={`px-3 py-2 rounded-lg text-sm ${opt === content.correct_answer
                                                ? 'bg-green-500/20 text-green-400 border border-green-500/30'
                                                : 'bg-white/5 text-gray-300'
                                                }`}
                                        >
                                            {opt === content.correct_answer && <CheckCircle className="w-4 h-4 inline mr-2" />}
                                            {opt}
                                        </div>
                                    ))}
                                </div>
                            </div>
                        </div>
                    </div>
                )

            case 'activity':
                return (
                    <div className="bg-gradient-to-r from-blue-500/20 to-cyan-500/20 p-5 rounded-xl border border-blue-500/30">
                        <div className="flex items-start gap-3">
                            <Target className="w-6 h-6 text-cyan-400 flex-shrink-0" />
                            <div>
                                <span className="text-xs text-cyan-400 uppercase font-medium">Activity</span>
                                <p className="text-white mt-1">🎯 {content.content}</p>
                            </div>
                        </div>
                    </div>
                )

            case 'example':
                return (
                    <div className="bg-gradient-to-r from-green-500/20 to-emerald-500/20 p-5 rounded-xl border border-green-500/30">
                        <div className="flex items-start gap-3">
                            <ListOrdered className="w-6 h-6 text-green-400 flex-shrink-0" />
                            <div className="flex-1">
                                <span className="text-xs text-green-400 uppercase font-medium">Worked Example</span>
                                <p className="text-white font-medium mt-1">📝 {content.title || 'Example'}</p>
                                <div className="bg-white/5 p-3 rounded-lg mt-2 mb-2">
                                    <p className="text-gray-200">{content.problem}</p>
                                </div>
                                <div className="space-y-1">
                                    {content.steps?.map((step: string, idx: number) => (
                                        <div key={idx} className="flex items-start gap-2 text-sm">
                                            <span className="bg-green-500/30 text-green-400 px-2 py-0.5 rounded text-xs">
                                                {idx + 1}
                                            </span>
                                            <span className="text-gray-300">{step}</span>
                                        </div>
                                    ))}
                                </div>
                                <div className="bg-green-500/20 p-2 rounded-lg mt-2 border border-green-500/30">
                                    <span className="text-green-400 text-sm font-medium">Answer: </span>
                                    <span className="text-white text-sm">{content.answer}</span>
                                </div>
                            </div>
                        </div>
                    </div>
                )

            case 'summary':
                return (
                    <div className="bg-gradient-to-r from-indigo-500/20 to-violet-500/20 p-5 rounded-xl border border-indigo-500/30">
                        <div className="flex items-start gap-3">
                            <ClipboardCheck className="w-6 h-6 text-indigo-400 flex-shrink-0" />
                            <div className="flex-1">
                                <span className="text-xs text-indigo-400 uppercase font-medium">Summary</span>
                                <p className="text-white font-medium mt-1">✅ {content.title || 'Key Takeaways'}</p>
                                <ul className="mt-2 space-y-2">
                                    {content.points?.map((point: string, idx: number) => (
                                        <li key={idx} className="flex items-start gap-2">
                                            <CheckCircle className="w-4 h-4 text-indigo-400 flex-shrink-0 mt-0.5" />
                                            <span className="text-gray-200 text-sm">{point}</span>
                                        </li>
                                    ))}
                                </ul>
                            </div>
                        </div>
                    </div>
                )

            default:
                return (
                    <div className="bg-white/5 p-5 rounded-xl">
                        <p className="text-gray-400">{type}: {JSON.stringify(content).slice(0, 100)}...</p>
                    </div>
                )
        }
    }

    // Filter favorites based on selections (cascading)
    const filteredFavorites = favorites.filter(fav => {
        // Apply subject filter
        if (selectedSubject && fav.subject_id !== selectedSubject) return false
        // Apply topic filter
        if (selectedTopic && fav.topic_id !== selectedTopic) return false
        // Apply subtopic filter
        if (selectedSubtopic && fav.subtopic_id !== selectedSubtopic) return false
        return true
    })

    if (loading) {
        return (
            <div className="min-h-screen flex items-center justify-center">
                <div className="text-center">
                    <Loader2 className="w-12 h-12 text-primary-500 animate-spin mx-auto mb-4" />
                    <p className="text-gray-400">Loading your favorites...</p>
                </div>
            </div>
        )
    }

    if (error) {
        return (
            <div className="min-h-screen flex items-center justify-center">
                <div className="text-center">
                    <p className="text-red-400 mb-4">{error}</p>
                    <button onClick={() => navigate('/dashboard')} className="btn-primary">
                        Back to Dashboard
                    </button>
                </div>
            </div>
        )
    }

    return (
        <div className="min-h-screen py-8 px-4 sm:px-6 lg:px-8">
            <div className="max-w-4xl mx-auto">
                {/* Header */}
                <div className="mb-8">
                    <button
                        onClick={() => navigate(-1)}
                        className="text-gray-400 hover:text-white mb-4 flex items-center gap-2"
                    >
                        <ChevronLeft className="w-5 h-5" />
                        Back
                    </button>
                    <h1 className="text-3xl font-bold text-white flex items-center gap-3">
                        <Star className="w-8 h-8 text-yellow-400 fill-current" />
                        {getTitle()}
                    </h1>
                    <p className="text-gray-400 mt-2">
                        {filteredFavorites.length} starred items
                        {filterLevel !== 'global' && ` (${filterLevel} level)`}
                    </p>
                </div>

                {/* Cascading Filters */}
                <div className="glass-card p-4 mb-6">
                    <div className="flex items-center gap-2 mb-3">
                        <Filter className="w-5 h-5 text-gray-400" />
                        <span className="text-gray-400 text-sm font-medium">Filters:</span>
                    </div>

                    <div className="flex flex-wrap gap-3">
                        {/* Subject filter - always show, disabled at non-global levels */}
                        <select
                            value={selectedSubject}
                            onChange={(e) => {
                                setSelectedSubject(e.target.value)
                                setSelectedTopic('')
                                setSelectedSubtopic('')
                            }}
                            disabled={filterLevel !== 'global'}
                            className="bg-gray-800 text-white rounded-lg px-3 py-2 text-sm border border-white/20 disabled:opacity-50 [&>option]:bg-gray-800 [&>option]:text-white"
                        >
                            <option value="">All Subjects</option>
                            {subjects.map(subject => (
                                <option key={subject.id} value={subject.id}>{subject.name}</option>
                            ))}
                        </select>

                        {/* Topic filter - show at global/subject/topic levels */}
                        {filterLevel !== 'subtopic' && (
                            <select
                                value={selectedTopic}
                                onChange={(e) => {
                                    setSelectedTopic(e.target.value)
                                    setSelectedSubtopic('')
                                }}
                                disabled={filterLevel === 'topic' || (filterLevel === 'global' && !selectedSubject)}
                                className="bg-gray-800 text-white rounded-lg px-3 py-2 text-sm border border-white/20 disabled:opacity-50 [&>option]:bg-gray-800 [&>option]:text-white"
                            >
                                <option value="">
                                    {!selectedSubject && filterLevel === 'global' ? 'Select Subject First' : 'All Topics'}
                                </option>
                                {topics.map(topic => (
                                    <option key={topic.id} value={topic.id}>{topic.name}</option>
                                ))}
                            </select>
                        )}

                        {/* Subtopic filter - show at global/subject/topic levels */}
                        {filterLevel !== 'subtopic' && (
                            <select
                                value={selectedSubtopic}
                                onChange={(e) => setSelectedSubtopic(e.target.value)}
                                disabled={!selectedTopic}
                                className="bg-gray-800 text-white rounded-lg px-3 py-2 text-sm border border-white/20 disabled:opacity-50 [&>option]:bg-gray-800 [&>option]:text-white"
                            >
                                <option value="">
                                    {!selectedTopic ? 'Select Topic First' : 'All Subtopics'}
                                </option>
                                {subtopics.map(st => (
                                    <option key={st.id} value={st.id}>{st.name}</option>
                                ))}
                            </select>
                        )}
                    </div>
                </div>

                {/* Favorites Grid */}
                {filteredFavorites.length > 0 ? (
                    <div className="space-y-4">
                        {filteredFavorites.map((fav) => (
                            <div key={fav.id} className="relative group">
                                {/* Remove button */}
                                <button
                                    onClick={() => handleRemoveFavorite(fav.id)}
                                    className="absolute top-3 right-3 z-10 p-2 bg-yellow-500/20 text-yellow-400 
                                               hover:bg-yellow-500/30 rounded-full transition-colors"
                                    title="Remove from favorites"
                                >
                                    <Star className="w-5 h-5 fill-current" />
                                </button>

                                {/* Breadcrumb badge */}
                                <div className="absolute top-3 left-3 z-10 text-xs text-gray-400 bg-black/50 px-2 py-1 rounded flex gap-1">
                                    {fav.subject_name && <span>{fav.subject_name}</span>}
                                    {fav.topic_name && <span>› {fav.topic_name}</span>}
                                    {fav.subtopic_name && <span>› {fav.subtopic_name}</span>}
                                </div>

                                {/* Module tile */}
                                <div className="pt-10">
                                    {renderModuleTile(fav)}
                                </div>
                            </div>
                        ))}
                    </div>
                ) : (
                    <div className="text-center py-12">
                        <Star className="w-16 h-16 text-gray-600 mx-auto mb-4" />
                        <p className="text-gray-400 mb-2">No favorites found</p>
                        <p className="text-gray-500 text-sm">
                            {filterLevel === 'global'
                                ? 'Star modules while studying to add them here for quick review'
                                : 'No starred items at this level. Try removing some filters.'}
                        </p>
                    </div>
                )}
            </div>
        </div>
    )
}
