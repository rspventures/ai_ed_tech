import { useState, useEffect, useRef } from 'react'
import {
    BookOpen,
    Lightbulb,
    Sparkles,
    CheckCircle,
    ChevronRight,
    Loader2,
    Star
} from 'lucide-react'
import type { Lesson, LessonSection } from '@/types'
import { TutorChat } from './TutorChat'

interface LessonViewProps {
    lesson: Lesson
    onComplete: (timeSpentSeconds: number) => void
    isCompleting?: boolean
}

export default function LessonView({ lesson, onComplete, isCompleting }: LessonViewProps) {
    const [currentSection, setCurrentSection] = useState(0)
    const [sectionsRead, setSectionsRead] = useState<Set<number>>(new Set([0]))
    const startTimeRef = useRef<number>(Date.now())

    const { content } = lesson
    const totalSections = content.sections.length + 3 // hook/intro, sections, summary, fun_fact
    const isLastSection = currentSection >= totalSections - 1
    const allRead = sectionsRead.size >= totalSections

    const handleNext = () => {
        const nextSection = currentSection + 1
        setCurrentSection(nextSection)
        setSectionsRead(prev => new Set([...prev, nextSection]))
    }

    const handlePrev = () => {
        setCurrentSection(Math.max(0, currentSection - 1))
    }

    const handleComplete = () => {
        const timeSpent = Math.floor((Date.now() - startTimeRef.current) / 1000)
        onComplete(timeSpent)
    }

    const renderSection = () => {
        // Section 0: Hook + Introduction
        if (currentSection === 0) {
            return (
                <div className="space-y-6">
                    <div className="bg-gradient-to-r from-yellow-500/20 to-orange-500/20 p-6 rounded-2xl border border-yellow-500/30">
                        <div className="flex items-start gap-3">
                            <Sparkles className="w-6 h-6 text-yellow-400 flex-shrink-0 mt-1" />
                            <div>
                                <h3 className="text-lg font-semibold text-yellow-400 mb-2">Did you know? 🤔</h3>
                                <p className="text-white text-lg leading-relaxed">{content.hook}</p>
                            </div>
                        </div>
                    </div>

                    <div className="bg-white/5 p-6 rounded-2xl">
                        <h3 className="text-lg font-semibold text-primary-400 mb-3">What we'll learn today 📚</h3>
                        <p className="text-gray-300 text-lg leading-relaxed">{content.introduction}</p>
                    </div>
                </div>
            )
        }

        // Middle sections: Teaching content
        const sectionIndex = currentSection - 1
        if (sectionIndex < content.sections.length) {
            const section: LessonSection = content.sections[sectionIndex]
            return (
                <div className="space-y-6">
                    <div className="bg-white/5 p-6 rounded-2xl">
                        <h3 className="text-xl font-semibold text-white mb-4 flex items-center gap-2">
                            <BookOpen className="w-5 h-5 text-primary-400" />
                            {section.title}
                        </h3>
                        <p className="text-gray-300 text-lg leading-relaxed whitespace-pre-wrap">
                            {section.content}
                        </p>
                    </div>

                    {section.example && (
                        <div className="bg-green-500/10 p-6 rounded-2xl border border-green-500/30">
                            <h4 className="text-lg font-semibold text-green-400 mb-3 flex items-center gap-2">
                                <Lightbulb className="w-5 h-5" />
                                Example
                            </h4>
                            <p className="text-gray-200 text-lg leading-relaxed whitespace-pre-wrap">
                                {section.example}
                            </p>
                        </div>
                    )}
                </div>
            )
        }

        // Second to last: Summary
        if (currentSection === content.sections.length + 1) {
            return (
                <div className="space-y-6">
                    <div className="bg-gradient-to-r from-primary-500/20 to-purple-500/20 p-6 rounded-2xl border border-primary-500/30">
                        <h3 className="text-xl font-semibold text-white mb-4 flex items-center gap-2">
                            <Star className="w-5 h-5 text-primary-400" />
                            What We Learned 🎯
                        </h3>
                        <p className="text-gray-200 text-lg leading-relaxed whitespace-pre-wrap">
                            {content.summary}
                        </p>
                    </div>
                </div>
            )
        }

        // Last section: Fun fact + Complete button
        return (
            <div className="space-y-6">
                {content.fun_fact && (
                    <div className="bg-gradient-to-r from-pink-500/20 to-purple-500/20 p-6 rounded-2xl border border-pink-500/30">
                        <h3 className="text-xl font-semibold text-pink-400 mb-4 flex items-center gap-2">
                            <Sparkles className="w-5 h-5" />
                            Fun Fact! 🌟
                        </h3>
                        <p className="text-gray-200 text-lg leading-relaxed">
                            {content.fun_fact}
                        </p>
                    </div>
                )}

                <div className="bg-green-500/10 p-8 rounded-2xl border border-green-500/30 text-center">
                    <CheckCircle className="w-12 h-12 text-green-400 mx-auto mb-4" />
                    <h3 className="text-2xl font-bold text-white mb-2">Great Job! 🎉</h3>
                    <p className="text-gray-300 mb-6">You've finished reading this lesson!</p>
                    <button
                        onClick={handleComplete}
                        disabled={isCompleting || lesson.is_completed}
                        className="btn-primary px-8 py-3 text-lg disabled:opacity-50"
                    >
                        {isCompleting ? (
                            <>
                                <Loader2 className="w-5 h-5 animate-spin mr-2" />
                                Saving...
                            </>
                        ) : lesson.is_completed ? (
                            <>
                                <CheckCircle className="w-5 h-5 mr-2" />
                                Already Completed
                            </>
                        ) : (
                            <>
                                <CheckCircle className="w-5 h-5 mr-2" />
                                Mark as Complete
                            </>
                        )}
                    </button>
                </div>
            </div>
        )
    }

    return (
        <div className="max-w-3xl mx-auto">
            {/* Header */}
            <div className="mb-8">
                <h1 className="text-3xl font-bold text-white mb-2">{lesson.title}</h1>
                <div className="flex items-center gap-4 text-sm text-gray-400">
                    <span>Grade {lesson.grade_level}</span>
                    <span>•</span>
                    <span>AI Generated</span>
                </div>
            </div>

            {/* Progress bar */}
            <div className="mb-6">
                <div className="flex justify-between text-sm text-gray-400 mb-2">
                    <span>Progress</span>
                    <span>{currentSection + 1} / {totalSections}</span>
                </div>
                <div className="h-2 bg-white/10 rounded-full overflow-hidden">
                    <div
                        className="h-full bg-primary-500 transition-all duration-300"
                        style={{ width: `${((currentSection + 1) / totalSections) * 100}%` }}
                    />
                </div>
            </div>

            {/* Content */}
            <div className="glass-card p-8 mb-6 min-h-[300px]">
                {renderSection()}
            </div>

            {/* Navigation */}
            <div className="flex justify-between">
                <button
                    onClick={handlePrev}
                    disabled={currentSection === 0}
                    className="btn-secondary disabled:opacity-50 disabled:cursor-not-allowed"
                >
                    Previous
                </button>

                {!isLastSection ? (
                    <button onClick={handleNext} className="btn-primary flex items-center gap-2">
                        Next
                        <ChevronRight className="w-5 h-5" />
                    </button>
                ) : (
                    <div />
                )}
            </div>

            {/* AI Tutor Chat Widget */}
            <TutorChat
                contextType="lesson"
                contextId={lesson.id}
            />
        </div>
    )
}
