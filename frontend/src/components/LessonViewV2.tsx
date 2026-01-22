import { useState, useRef, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import {
    Sparkles,
    BookOpen,
    Lightbulb,
    HelpCircle,
    CheckCircle,
    XCircle,
    ChevronLeft,
    ChevronRight,
    RotateCcw,
    Loader2,
    Star,
    Target,
    ListOrdered,
    ClipboardCheck
} from 'lucide-react'
import type { LessonV2, LessonModule, FavoriteModule } from '@/types'
import { studyService } from '@/services/study'

interface LessonViewV2Props {
    lesson: LessonV2
    onComplete: (timeSpentSeconds: number) => void
    isCompleting?: boolean
}

/**
 * LessonViewV2 - Interactive Module Playlist Viewer
 * 
 * Renders Lesson 2.0 format with:
 * - Swipeable/navigable modules
 * - Interactive Flashcards (tap to flip)
 * - Quiz questions with instant feedback
 * - Activity prompts
 * - Star/favorite modules for quick review
 */
export default function LessonViewV2({ lesson, onComplete, isCompleting }: LessonViewV2Props) {
    const navigate = useNavigate()
    const [currentIndex, setCurrentIndex] = useState(0)
    const [flippedCards, setFlippedCards] = useState<Set<number>>(new Set())
    const [quizAnswers, setQuizAnswers] = useState<Record<number, string>>({})
    const [quizResults, setQuizResults] = useState<Record<number, boolean>>({})
    const [favorites, setFavorites] = useState<Map<number, string>>(new Map()) // moduleIndex -> favoriteId
    const [togglingFavorite, setTogglingFavorite] = useState<number | null>(null)
    const startTimeRef = useRef<number>(Date.now())

    const modules = lesson.content.modules
    const currentModule = modules[currentIndex]
    const isLast = currentIndex >= modules.length - 1
    const isFirst = currentIndex === 0

    const handleNext = () => {
        if (!isLast) setCurrentIndex(currentIndex + 1)
    }

    const handlePrev = () => {
        if (!isFirst) setCurrentIndex(currentIndex - 1)
    }

    const handleFlipCard = () => {
        setFlippedCards(prev => {
            const next = new Set(prev)
            if (next.has(currentIndex)) {
                next.delete(currentIndex)
            } else {
                next.add(currentIndex)
            }
            return next
        })
    }

    const handleQuizAnswer = (option: string, correctAnswer: string) => {
        setQuizAnswers(prev => ({ ...prev, [currentIndex]: option }))
        setQuizResults(prev => ({ ...prev, [currentIndex]: option === correctAnswer }))
    }

    const handleComplete = () => {
        const timeSpent = Math.floor((Date.now() - startTimeRef.current) / 1000)
        onComplete(timeSpent)
    }

    const handleToggleFavorite = async (moduleIndex: number) => {
        setTogglingFavorite(moduleIndex)
        try {
            const existingFavoriteId = favorites.get(moduleIndex)
            if (existingFavoriteId) {
                // Remove from favorites
                await studyService.removeFavorite(existingFavoriteId)
                setFavorites(prev => {
                    const next = new Map(prev)
                    next.delete(moduleIndex)
                    return next
                })
            } else {
                // Add to favorites
                const result = await studyService.addFavorite(lesson.id, moduleIndex)
                setFavorites(prev => new Map(prev).set(moduleIndex, result.id))
            }
        } catch (error) {
            console.error('Failed to toggle favorite:', error)
        } finally {
            setTogglingFavorite(null)
        }
    }

    const renderStarButton = (index: number) => {
        const isFavorited = favorites.has(index)
        const isToggling = togglingFavorite === index
        return (
            <button
                onClick={(e) => {
                    e.stopPropagation()
                    handleToggleFavorite(index)
                }}
                disabled={isToggling}
                className={`absolute top-3 right-3 p-2 rounded-full transition-all ${isFavorited
                    ? 'bg-yellow-500/20 text-yellow-400'
                    : 'bg-white/10 text-gray-400 hover:text-yellow-400'
                    }`}
                title={isFavorited ? 'Remove from favorites' : 'Add to favorites'}
            >
                {isToggling ? (
                    <Loader2 className="w-5 h-5 animate-spin" />
                ) : (
                    <Star className={`w-5 h-5 ${isFavorited ? 'fill-current' : ''}`} />
                )}
            </button>
        )
    }


    const renderModule = (module: LessonModule, index: number) => {
        switch (module.type) {
            case 'hook':
                return (
                    <div className="relative bg-gradient-to-r from-yellow-500/20 to-orange-500/20 p-6 rounded-2xl border border-yellow-500/30">
                        {renderStarButton(index)}
                        <div className="flex items-start gap-3 pr-10">
                            <Sparkles className="w-8 h-8 text-yellow-400 flex-shrink-0" />
                            <div>
                                <h3 className="text-lg font-semibold text-yellow-400 mb-2">
                                    {module.emoji || '🤔'} Did you know?
                                </h3>
                                <p className="text-white text-xl leading-relaxed">{module.content}</p>
                            </div>
                        </div>
                    </div>
                )

            case 'text':
                return (
                    <div className="relative bg-white/5 p-6 rounded-2xl">
                        {renderStarButton(index)}
                        <div className="flex items-start gap-3 pr-10">
                            <BookOpen className="w-6 h-6 text-primary-400 flex-shrink-0 mt-1" />
                            <p className="text-gray-200 text-lg leading-relaxed">{module.content}</p>
                        </div>
                    </div>
                )

            case 'flashcard':
                const isFlipped = flippedCards.has(index)
                return (
                    <div
                        className="cursor-pointer perspective-1000"
                        onClick={handleFlipCard}
                    >
                        <div className={`
                            relative w-full min-h-[200px] transition-transform duration-500 transform-style-3d
                            ${isFlipped ? 'rotate-y-180' : ''}
                        `}>
                            {/* Front */}
                            <div className={`
                                absolute inset-0 bg-gradient-to-br from-primary-500/30 to-purple-500/30 
                                p-8 rounded-2xl border-2 border-primary-500/50 backface-hidden
                                flex flex-col items-center justify-center text-center
                                ${isFlipped ? 'invisible' : ''}
                            `}>
                                <Lightbulb className="w-8 h-8 text-primary-400 mb-4" />
                                <p className="text-2xl font-bold text-white">{module.front}</p>
                                <p className="text-sm text-gray-400 mt-4">Tap to flip</p>
                            </div>
                            {/* Back */}
                            <div className={`
                                absolute inset-0 bg-gradient-to-br from-green-500/30 to-teal-500/30 
                                p-8 rounded-2xl border-2 border-green-500/50 backface-hidden rotate-y-180
                                flex flex-col items-center justify-center text-center
                                ${!isFlipped ? 'invisible' : ''}
                            `}>
                                <CheckCircle className="w-8 h-8 text-green-400 mb-4" />
                                <p className="text-xl text-white">{module.back}</p>
                                <p className="text-sm text-gray-400 mt-4">Tap to flip back</p>
                            </div>
                        </div>
                    </div>
                )

            case 'fun_fact':
                return (
                    <div className="relative bg-gradient-to-r from-pink-500/20 to-purple-500/20 p-6 rounded-2xl border border-pink-500/30">
                        {renderStarButton(index)}
                        <div className="flex items-start gap-3 pr-10">
                            <Star className="w-8 h-8 text-pink-400 flex-shrink-0" />
                            <div>
                                <h3 className="text-lg font-semibold text-pink-400 mb-2">🌟 Fun Fact!</h3>
                                <p className="text-white text-lg leading-relaxed">{module.content}</p>
                            </div>
                        </div>
                    </div>
                )

            case 'quiz_single':
                const selectedAnswer = quizAnswers[index]
                const isCorrect = quizResults[index]
                const hasAnswered = selectedAnswer !== undefined

                return (
                    <div className="relative bg-white/5 p-6 rounded-2xl">
                        {renderStarButton(index)}
                        <div className="flex items-start gap-3 mb-4 pr-10">
                            <HelpCircle className="w-6 h-6 text-blue-400 flex-shrink-0 mt-1" />
                            <h3 className="text-xl font-semibold text-white">{module.question}</h3>
                        </div>
                        <div className="space-y-3">
                            {module.options.map((option, optIdx) => {
                                const isSelected = selectedAnswer === option
                                const isCorrectOption = option === module.correct_answer

                                let bgClass = 'bg-white/10 hover:bg-white/20'
                                if (hasAnswered) {
                                    if (isCorrectOption) bgClass = 'bg-green-500/30 border-green-500'
                                    else if (isSelected && !isCorrect) bgClass = 'bg-red-500/30 border-red-500'
                                }

                                return (
                                    <button
                                        key={optIdx}
                                        onClick={() => !hasAnswered && handleQuizAnswer(option, module.correct_answer)}
                                        disabled={hasAnswered}
                                        className={`w-full p-4 rounded-xl border-2 border-transparent text-left transition-all ${bgClass}`}
                                    >
                                        <span className="text-white">{option}</span>
                                        {hasAnswered && isCorrectOption && (
                                            <CheckCircle className="inline w-5 h-5 text-green-400 ml-2" />
                                        )}
                                        {hasAnswered && isSelected && !isCorrect && (
                                            <XCircle className="inline w-5 h-5 text-red-400 ml-2" />
                                        )}
                                    </button>
                                )
                            })}
                        </div>
                        {hasAnswered && (
                            <div className={`mt-4 p-3 rounded-lg ${isCorrect ? 'bg-green-500/20' : 'bg-red-500/20'}`}>
                                <p className={isCorrect ? 'text-green-400' : 'text-red-400'}>
                                    {isCorrect ? '🎉 Correct!' : `❌ The answer is: ${module.correct_answer}`}
                                </p>
                            </div>
                        )}
                    </div>
                )

            case 'activity':
                return (
                    <div className="relative bg-gradient-to-r from-blue-500/20 to-cyan-500/20 p-6 rounded-2xl border border-blue-500/30">
                        {renderStarButton(index)}
                        <div className="flex items-start gap-3 pr-10">
                            <Target className="w-8 h-8 text-blue-400 flex-shrink-0" />
                            <div>
                                <h3 className="text-lg font-semibold text-blue-400 mb-2">
                                    🎯 Activity: {
                                        (module.activity_type === 'social' || module.activity_type === 'group')
                                            ? '👥 Team Up!'
                                            : module.activity_type === 'creative'
                                                ? '🎨 Get Creative!'
                                                : '📝 Try This!'
                                    }
                                </h3>
                                <p className="text-white text-lg leading-relaxed">{module.content}</p>
                            </div>
                        </div>
                    </div>
                )

            case 'example':
                return (
                    <div className="relative bg-gradient-to-r from-green-500/20 to-emerald-500/20 p-6 rounded-2xl border border-green-500/30">
                        {renderStarButton(index)}
                        <div className="pr-10">
                            <div className="flex items-center gap-3 mb-4">
                                <ListOrdered className="w-8 h-8 text-green-400" />
                                <h3 className="text-xl font-semibold text-green-400">
                                    📝 {module.title || 'Worked Example'}
                                </h3>
                            </div>
                            <div className="bg-white/5 p-4 rounded-xl mb-4">
                                <p className="text-white font-medium">{module.problem}</p>
                            </div>
                            <div className="space-y-2 mb-4">
                                {module.steps?.map((step: string, stepIdx: number) => (
                                    <div key={stepIdx} className="flex items-start gap-3">
                                        <span className="bg-green-500/30 text-green-400 px-2 py-0.5 rounded text-sm font-medium">
                                            {stepIdx + 1}
                                        </span>
                                        <span className="text-gray-200">{step}</span>
                                    </div>
                                ))}
                            </div>
                            <div className="bg-green-500/20 p-3 rounded-xl border border-green-500/40">
                                <span className="text-green-400 font-medium">Answer: </span>
                                <span className="text-white">{module.answer}</span>
                            </div>
                        </div>
                    </div>
                )

            case 'summary':
                return (
                    <div className="relative bg-gradient-to-r from-indigo-500/20 to-violet-500/20 p-6 rounded-2xl border border-indigo-500/30">
                        {renderStarButton(index)}
                        <div className="pr-10">
                            <div className="flex items-center gap-3 mb-4">
                                <ClipboardCheck className="w-8 h-8 text-indigo-400" />
                                <h3 className="text-xl font-semibold text-indigo-400">
                                    ✅ {module.title || 'Key Takeaways'}
                                </h3>
                            </div>
                            <ul className="space-y-3">
                                {module.points?.map((point: string, pointIdx: number) => (
                                    <li key={pointIdx} className="flex items-start gap-3">
                                        <CheckCircle className="w-5 h-5 text-indigo-400 flex-shrink-0 mt-0.5" />
                                        <span className="text-white">{point}</span>
                                    </li>
                                ))}
                            </ul>
                        </div>
                    </div>
                )

            default:
                return <div className="text-gray-400">Unknown module type: {module.type}</div>
        }
    }

    return (
        <div className="max-w-3xl mx-auto">
            {/* Header */}
            <div className="mb-6">
                <div className="flex items-center justify-between mb-2">
                    <h1 className="text-2xl font-bold text-white">{lesson.content.title}</h1>
                    <button
                        onClick={() => navigate(`/quick-review?subtopic=${lesson.subtopic_id}`)}
                        className="px-3 py-1.5 bg-yellow-500/20 border border-yellow-500/30 rounded-lg
                                   text-yellow-300 hover:bg-yellow-500/30 transition-colors flex items-center gap-1 text-sm"
                    >
                        <Star className="w-4 h-4" />
                        My Stars
                    </button>
                </div>
                <div className="flex items-center gap-4 text-sm text-gray-400">
                    <span>Grade {lesson.grade_level}</span>
                    <span>•</span>
                    <span>Interactive Lesson</span>
                    <span>•</span>
                    <span>{lesson.content.estimated_duration_minutes || modules.length + 2} min</span>
                </div>
            </div>

            {/* Progress Dots */}
            <div className="flex justify-center gap-2 mb-6">
                {modules.map((m, idx) => (
                    <button
                        key={idx}
                        onClick={() => setCurrentIndex(idx)}
                        className={`w-3 h-3 rounded-full transition-all ${idx === currentIndex
                            ? 'bg-primary-500 scale-125'
                            : idx < currentIndex
                                ? 'bg-green-500'
                                : 'bg-white/20'
                            }`}
                    />
                ))}
            </div>

            {/* Module Content */}
            <div className="glass-card p-8 mb-6 min-h-[250px]">
                {renderModule(currentModule, currentIndex)}
            </div>

            {/* Navigation */}
            <div className="flex justify-between items-center">
                <button
                    onClick={handlePrev}
                    disabled={isFirst}
                    className="btn-secondary flex items-center gap-2 disabled:opacity-50"
                >
                    <ChevronLeft className="w-5 h-5" />
                    Back
                </button>

                <span className="text-gray-400 text-sm">
                    {currentIndex + 1} / {modules.length}
                </span>

                {isLast ? (
                    <button
                        onClick={handleComplete}
                        disabled={isCompleting || lesson.is_completed}
                        className="btn-primary flex items-center gap-2 disabled:opacity-50"
                    >
                        {isCompleting ? (
                            <>
                                <Loader2 className="w-5 h-5 animate-spin" />
                                Saving...
                            </>
                        ) : lesson.is_completed ? (
                            <>
                                <CheckCircle className="w-5 h-5" />
                                Completed
                            </>
                        ) : (
                            <>
                                <CheckCircle className="w-5 h-5" />
                                Finish
                            </>
                        )}
                    </button>
                ) : (
                    <button
                        onClick={handleNext}
                        className="btn-primary flex items-center gap-2"
                    >
                        Next
                        <ChevronRight className="w-5 h-5" />
                    </button>
                )}
            </div>
        </div>
    )
}
