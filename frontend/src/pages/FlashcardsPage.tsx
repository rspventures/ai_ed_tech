import { useState, useEffect } from 'react'
import { useParams, useNavigate } from 'react-router-dom'
import { Loader2, BookOpen, ChevronLeft, Layers, Sparkles } from 'lucide-react'
import { studyService } from '@/services/study'
import { curriculumService } from '@/services/curriculum'
import FlashcardDeck from '@/components/FlashcardDeck'
import type { FlashcardDeck as FlashcardDeckType, FlashcardDeckListItem, Topic } from '@/types'

/**
 * FlashcardsPage - Browse and Study Flashcard Decks
 * 
 * Allows students to:
 * - View all flashcard decks for a topic
 * - Generate flashcards for subtopics that don't have them
 * - Study with interactive flip cards
 */
export default function FlashcardsPage() {
    const { topicSlug, subtopicId } = useParams<{ topicSlug?: string; subtopicId?: string }>()
    const navigate = useNavigate()

    // State
    const [loading, setLoading] = useState(true)
    const [error, setError] = useState<string | null>(null)
    const [topic, setTopic] = useState<Topic | null>(null)
    const [deckList, setDeckList] = useState<FlashcardDeckListItem[]>([])
    const [currentDeck, setCurrentDeck] = useState<FlashcardDeckType | null>(null)
    const [loadingDeck, setLoadingDeck] = useState(false)
    const [generatingDeckId, setGeneratingDeckId] = useState<string | null>(null)

    // Load topic and deck list
    useEffect(() => {
        if (topicSlug) {
            loadTopicData()
        }
    }, [topicSlug])

    // Load specific deck if subtopicId provided
    useEffect(() => {
        if (subtopicId) {
            loadDeck(subtopicId)
        }
    }, [subtopicId])

    const loadTopicData = async () => {
        if (!topicSlug) return
        setLoading(true)
        try {
            const topicData = await curriculumService.getTopic(topicSlug)
            setTopic(topicData)

            // Load deck list for this topic
            const decks = await studyService.listFlashcardDecks(topicData.id)
            setDeckList(decks)
        } catch (err) {
            console.error('Failed to load topic:', err)
            setError('Failed to load flashcard decks')
        } finally {
            setLoading(false)
        }
    }

    const loadDeck = async (subtopicId: string) => {
        setLoadingDeck(true)
        try {
            const deck = await studyService.getFlashcards(subtopicId)
            setCurrentDeck(deck)
        } catch (err) {
            console.error('Failed to load deck:', err)
            setError('Failed to load flashcard deck')
        } finally {
            setLoadingDeck(false)
        }
    }

    const handleSelectDeck = (subtopicId: string, hasCards: boolean) => {
        if (hasCards) {
            loadDeck(subtopicId)
        }
    }

    const handleGenerateDeck = async (e: React.MouseEvent, subtopicId: string) => {
        e.stopPropagation() // Prevent triggering deck selection
        setGeneratingDeckId(subtopicId)
        try {
            // This will trigger generation on the backend via FlashcardAgent
            const deck = await studyService.getFlashcards(subtopicId)
            setCurrentDeck(deck)

            // Refresh the deck list to show updated card count
            if (topic) {
                const decks = await studyService.listFlashcardDecks(topic.id)
                setDeckList(decks)
            }
        } catch (err) {
            console.error('Failed to generate flashcards:', err)
            setError('Failed to generate flashcard deck')
        } finally {
            setGeneratingDeckId(null)
        }
    }

    const handleBackToList = () => {
        setCurrentDeck(null)
    }

    // Loading state
    if (loading) {
        return (
            <div className="min-h-screen flex items-center justify-center">
                <div className="text-center">
                    <Loader2 className="w-12 h-12 text-primary-500 animate-spin mx-auto mb-4" />
                    <p className="text-gray-400">Loading flashcards...</p>
                </div>
            </div>
        )
    }

    // Error state
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

    // Studying a specific deck
    if (currentDeck) {
        return (
            <div className="min-h-screen py-8 px-4 sm:px-6 lg:px-8">
                <button
                    onClick={handleBackToList}
                    className="text-gray-400 hover:text-white mb-6 flex items-center gap-2"
                >
                    <ChevronLeft className="w-5 h-5" />
                    Back to Deck List
                </button>

                {loadingDeck ? (
                    <div className="flex items-center justify-center py-12">
                        <Loader2 className="w-8 h-8 text-primary-500 animate-spin" />
                    </div>
                ) : (
                    <FlashcardDeck deck={currentDeck} />
                )}
            </div>
        )
    }

    // Deck list view
    return (
        <div className="min-h-screen py-8 px-4 sm:px-6 lg:px-8">
            <div className="max-w-4xl mx-auto">
                {/* Header */}
                <div className="mb-8">
                    <button
                        onClick={() => navigate('/dashboard')}
                        className="text-gray-400 hover:text-white mb-4 flex items-center gap-2"
                    >
                        <ChevronLeft className="w-5 h-5" />
                        Back to Dashboard
                    </button>
                    <h1 className="text-3xl font-bold text-white flex items-center gap-3">
                        <Layers className="w-8 h-8 text-primary-400" />
                        {topic?.name || 'Flashcards'}
                    </h1>
                    <p className="text-gray-400 mt-2">
                        Choose a deck to start studying
                    </p>
                </div>

                {/* Deck Grid */}
                <div className="grid grid-cols-1 md:grid-cols-2 gap-4">
                    {deckList.map((deck) => {
                        const hasCards = deck.card_count > 0
                        const isGenerating = generatingDeckId === deck.subtopic_id

                        return (
                            <div
                                key={deck.subtopic_id}
                                onClick={() => handleSelectDeck(deck.subtopic_id, hasCards)}
                                className={`glass-card p-6 transition-all ${hasCards
                                        ? 'cursor-pointer hover:border-primary-500/50'
                                        : 'cursor-default'
                                    }`}
                            >
                                <div className="flex items-start justify-between">
                                    <div className="flex-1">
                                        <h3 className="text-lg font-semibold text-white mb-1">
                                            {deck.subtopic_name}
                                        </h3>
                                        <p className="text-sm text-gray-400">
                                            {hasCards
                                                ? `${deck.card_count} cards`
                                                : 'Not yet generated'
                                            }
                                        </p>
                                    </div>
                                    {hasCards ? (
                                        <BookOpen className="w-6 h-6 text-primary-400" />
                                    ) : (
                                        <button
                                            onClick={(e) => handleGenerateDeck(e, deck.subtopic_id)}
                                            disabled={isGenerating}
                                            className="btn-primary text-sm px-3 py-2 flex items-center gap-2"
                                        >
                                            {isGenerating ? (
                                                <>
                                                    <Loader2 className="w-4 h-4 animate-spin" />
                                                    Generating...
                                                </>
                                            ) : (
                                                <>
                                                    <Sparkles className="w-4 h-4" />
                                                    Generate
                                                </>
                                            )}
                                        </button>
                                    )}
                                </div>

                                {/* Progress bar - only show if has cards */}
                                {hasCards && deck.mastery_percentage !== null && deck.mastery_percentage !== undefined && (
                                    <div className="mt-4">
                                        <div className="flex justify-between text-xs text-gray-400 mb-1">
                                            <span>Mastery</span>
                                            <span>{Math.round(deck.mastery_percentage)}%</span>
                                        </div>
                                        <div className="w-full h-2 bg-white/10 rounded-full overflow-hidden">
                                            <div
                                                className="h-full bg-gradient-to-r from-primary-500 to-purple-500"
                                                style={{ width: `${deck.mastery_percentage}%` }}
                                            />
                                        </div>
                                    </div>
                                )}
                            </div>
                        )
                    })}
                </div>

                {deckList.length === 0 && (
                    <div className="text-center py-12">
                        <Layers className="w-16 h-16 text-gray-600 mx-auto mb-4" />
                        <p className="text-gray-400">No flashcard decks available yet.</p>
                    </div>
                )}
            </div>
        </div>
    )
}
