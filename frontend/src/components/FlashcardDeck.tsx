import { useState, useRef } from 'react'
import {
    ChevronLeft,
    ChevronRight,
    RotateCcw,
    Shuffle,
    CheckCircle,
    Lightbulb
} from 'lucide-react'
import type { FlashcardDeck as FlashcardDeckType, FlashcardItem } from '@/types'

interface FlashcardDeckProps {
    deck: FlashcardDeckType
    onComplete?: () => void
}

/**
 * FlashcardDeck - Interactive Flashcard Viewer with Flip Animation
 * 
 * Features:
 * - Tap to flip cards
 * - Navigate through deck
 * - Shuffle option
 * - Progress tracking
 */
export default function FlashcardDeck({ deck, onComplete }: FlashcardDeckProps) {
    const [currentIndex, setCurrentIndex] = useState(0)
    const [isFlipped, setIsFlipped] = useState(false)
    const [reviewedCards, setReviewedCards] = useState<Set<number>>(new Set())
    const [shuffledCards, setShuffledCards] = useState<FlashcardItem[]>(deck.cards)

    const currentCard = shuffledCards[currentIndex]
    const isLast = currentIndex >= shuffledCards.length - 1
    const isFirst = currentIndex === 0
    const progress = (reviewedCards.size / shuffledCards.length) * 100

    const handleFlip = () => {
        setIsFlipped(!isFlipped)
        // Mark as reviewed when flipped
        if (!isFlipped) {
            setReviewedCards(prev => new Set(prev).add(currentIndex))
        }
    }

    const handleNext = () => {
        if (!isLast) {
            setCurrentIndex(currentIndex + 1)
            setIsFlipped(false)
        }
    }

    const handlePrev = () => {
        if (!isFirst) {
            setCurrentIndex(currentIndex - 1)
            setIsFlipped(false)
        }
    }

    const handleShuffle = () => {
        const shuffled = [...deck.cards].sort(() => Math.random() - 0.5)
        setShuffledCards(shuffled)
        setCurrentIndex(0)
        setIsFlipped(false)
        setReviewedCards(new Set())
    }

    const handleReset = () => {
        setShuffledCards([...deck.cards])
        setCurrentIndex(0)
        setIsFlipped(false)
        setReviewedCards(new Set())
    }

    const getDifficultyColor = (difficulty?: string) => {
        switch (difficulty) {
            case 'easy': return 'text-green-400 bg-green-500/20'
            case 'medium': return 'text-yellow-400 bg-yellow-500/20'
            case 'hard': return 'text-red-400 bg-red-500/20'
            default: return 'text-gray-400 bg-gray-500/20'
        }
    }

    return (
        <div className="max-w-2xl mx-auto">
            {/* Header */}
            <div className="mb-6">
                <h2 className="text-2xl font-bold text-white mb-2">{deck.title}</h2>
                {deck.description && (
                    <p className="text-gray-400">{deck.description}</p>
                )}
            </div>

            {/* Progress Bar */}
            <div className="mb-6">
                <div className="flex justify-between text-sm text-gray-400 mb-2">
                    <span>{reviewedCards.size} of {shuffledCards.length} reviewed</span>
                    <span>{Math.round(progress)}%</span>
                </div>
                <div className="w-full h-2 bg-white/10 rounded-full overflow-hidden">
                    <div
                        className="h-full bg-gradient-to-r from-primary-500 to-purple-500 transition-all duration-300"
                        style={{ width: `${progress}%` }}
                    />
                </div>
            </div>

            {/* Flashcard */}
            <div
                className="relative h-[300px] cursor-pointer perspective-1000 mb-6"
                onClick={handleFlip}
            >
                <div className={`
                    absolute inset-0 transition-transform duration-500 transform-style-3d
                    ${isFlipped ? 'rotate-y-180' : ''}
                `}>
                    {/* Front */}
                    <div className={`
                        absolute inset-0 backface-hidden
                        bg-gradient-to-br from-primary-500/30 to-purple-500/30 
                        p-8 rounded-2xl border-2 border-primary-500/50
                        flex flex-col items-center justify-center text-center
                        ${isFlipped ? 'invisible' : ''}
                    `}>
                        {currentCard?.difficulty && (
                            <span className={`absolute top-4 right-4 px-2 py-1 rounded-full text-xs ${getDifficultyColor(currentCard.difficulty)}`}>
                                {currentCard.difficulty}
                            </span>
                        )}
                        <Lightbulb className="w-10 h-10 text-primary-400 mb-4" />
                        <p className="text-2xl font-bold text-white">{currentCard?.front}</p>
                        <p className="text-sm text-gray-400 mt-6">Tap to reveal answer</p>
                    </div>

                    {/* Back */}
                    <div className={`
                        absolute inset-0 backface-hidden rotate-y-180
                        bg-gradient-to-br from-green-500/30 to-teal-500/30 
                        p-8 rounded-2xl border-2 border-green-500/50
                        flex flex-col items-center justify-center text-center
                        ${!isFlipped ? 'invisible' : ''}
                    `}>
                        <CheckCircle className="w-10 h-10 text-green-400 mb-4" />
                        <p className="text-xl text-white">{currentCard?.back}</p>
                        <p className="text-sm text-gray-400 mt-6">Tap to flip back</p>
                    </div>
                </div>
            </div>

            {/* Navigation */}
            <div className="flex justify-between items-center mb-6">
                <button
                    onClick={handlePrev}
                    disabled={isFirst}
                    className="btn-secondary flex items-center gap-2 disabled:opacity-50"
                >
                    <ChevronLeft className="w-5 h-5" />
                    Prev
                </button>

                <span className="text-gray-400">
                    {currentIndex + 1} / {shuffledCards.length}
                </span>

                <button
                    onClick={handleNext}
                    disabled={isLast}
                    className="btn-primary flex items-center gap-2 disabled:opacity-50"
                >
                    Next
                    <ChevronRight className="w-5 h-5" />
                </button>
            </div>

            {/* Actions */}
            <div className="flex justify-center gap-4">
                <button
                    onClick={handleShuffle}
                    className="btn-secondary flex items-center gap-2"
                >
                    <Shuffle className="w-4 h-4" />
                    Shuffle
                </button>
                <button
                    onClick={handleReset}
                    className="btn-secondary flex items-center gap-2"
                >
                    <RotateCcw className="w-4 h-4" />
                    Reset
                </button>
            </div>

            {/* Completion Button */}
            {progress === 100 && onComplete && (
                <div className="mt-8 text-center">
                    <button
                        onClick={onComplete}
                        className="btn-primary px-8 py-3"
                    >
                        <CheckCircle className="w-5 h-5 mr-2 inline" />
                        Complete Review
                    </button>
                </div>
            )}
        </div>
    )
}
