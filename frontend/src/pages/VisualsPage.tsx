import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import {
    ArrowLeft,
    Sparkles,
    ImageIcon,
    Loader2,
    Trash2,
    Download,
    RefreshCw,
    Wand2,
    GraduationCap,
} from 'lucide-react'
import visualsService, { Visual } from '../services/visuals'
import { useStudentStore } from '../stores/studentStore'

export default function VisualsPage() {
    const navigate = useNavigate()
    const { student } = useStudentStore()
    const [concept, setConcept] = useState('')
    const grade = student?.grade_level || 5  // Get grade from profile
    const [quality, setQuality] = useState<'standard' | 'hd'>('standard')
    const [isGenerating, setIsGenerating] = useState(false)
    const [generatedImage, setGeneratedImage] = useState<Visual | null>(null)
    const [history, setHistory] = useState<Visual[]>([])
    const [error, setError] = useState<string | null>(null)

    // Load history on mount
    useEffect(() => {
        loadHistory()
    }, [])

    const loadHistory = async () => {
        try {
            const response = await visualsService.list(undefined, 10)
            setHistory(response.visuals)
        } catch (err) {
            console.error('Failed to load history:', err)
        }
    }

    const handleGenerate = async () => {
        if (!concept.trim()) {
            setError('Please enter a concept to visualize')
            return
        }

        setIsGenerating(true)
        setError(null)
        setGeneratedImage(null)

        try {
            const visual = await visualsService.explain({
                concept: concept.trim(),
                grade,
                quality,
            })
            setGeneratedImage(visual)
            // Add to history
            setHistory(prev => [visual, ...prev.slice(0, 9)])
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to generate image')
        } finally {
            setIsGenerating(false)
        }
    }

    const handleDelete = async (visualId: string) => {
        try {
            await visualsService.delete(visualId)
            setHistory(prev => prev.filter(v => v.id !== visualId))
            if (generatedImage?.id === visualId) {
                setGeneratedImage(null)
            }
        } catch (err) {
            console.error('Failed to delete:', err)
        }
    }

    const handleDownload = (visual: Visual) => {
        if (visual.image_url) {
            window.open(visual.image_url, '_blank')
        }
    }

    return (
        <div className="min-h-screen bg-gradient-to-br from-gray-900 via-purple-900/20 to-gray-900">
            {/* Header */}
            <header className="bg-gray-900/80 backdrop-blur-xl border-b border-white/10 sticky top-0 z-50">
                <div className="max-w-7xl mx-auto px-6 py-4">
                    <div className="flex items-center justify-between">
                        <div className="flex items-center gap-4">
                            <button
                                onClick={() => navigate('/dashboard')}
                                className="p-2 hover:bg-white/10 rounded-lg transition-colors"
                            >
                                <ArrowLeft className="w-5 h-5 text-gray-400" />
                            </button>
                            <div className="flex items-center gap-3">
                                <div className="w-10 h-10 bg-gradient-to-br from-pink-500 to-purple-600 rounded-xl flex items-center justify-center">
                                    <Sparkles className="w-5 h-5 text-white" />
                                </div>
                                <div>
                                    <h1 className="text-xl font-bold text-white">Visual Explainer</h1>
                                    <p className="text-sm text-gray-400">AI-powered educational illustrations</p>
                                </div>
                            </div>
                        </div>
                    </div>
                </div>
            </header>

            {/* Main Content */}
            <main className="max-w-7xl mx-auto px-6 py-8">
                <div className="grid grid-cols-1 lg:grid-cols-3 gap-8">
                    {/* Generator Panel */}
                    <div className="lg:col-span-2 space-y-6">
                        {/* Input Card */}
                        <div className="bg-gray-800/50 backdrop-blur-xl rounded-2xl border border-white/10 p-6">
                            <h2 className="text-lg font-semibold text-white mb-4 flex items-center gap-2">
                                <Wand2 className="w-5 h-5 text-purple-400" />
                                Generate Visual Explanation
                            </h2>

                            <div className="space-y-4">
                                {/* Concept Input */}
                                <div>
                                    <label className="block text-sm font-medium text-gray-300 mb-2">
                                        What concept would you like to visualize?
                                    </label>
                                    <textarea
                                        value={concept}
                                        onChange={(e) => setConcept(e.target.value)}
                                        placeholder="e.g., Photosynthesis process, Water cycle, Solar system..."
                                        className="w-full px-4 py-3 bg-gray-900/50 border border-white/10 rounded-xl text-white placeholder-gray-500 focus:outline-none focus:ring-2 focus:ring-purple-500/50 focus:border-transparent resize-none"
                                        rows={3}
                                    />
                                </div>

                                {/* Options Row */}
                                <div className="flex flex-wrap gap-4">
                                    {/* Grade Display (from profile) */}
                                    <div className="flex-1 min-w-[150px]">
                                        <label className="block text-sm font-medium text-gray-300 mb-2">
                                            Grade Level
                                        </label>
                                        <div className="flex items-center gap-2 px-4 py-2 bg-gray-900/50 border border-white/10 rounded-xl text-white">
                                            <GraduationCap className="w-4 h-4 text-purple-400" />
                                            <span>Grade {grade}</span>
                                            <span className="text-xs text-gray-500">(from profile)</span>
                                        </div>
                                    </div>

                                    {/* Quality Selection */}
                                    <div className="flex-1 min-w-[150px]">
                                        <label className="block text-sm font-medium text-gray-300 mb-2">
                                            Image Quality
                                        </label>
                                        <select
                                            value={quality}
                                            onChange={(e) => setQuality(e.target.value as 'standard' | 'hd')}
                                            className="w-full px-4 py-2 bg-gray-900/50 border border-white/10 rounded-xl text-white focus:outline-none focus:ring-2 focus:ring-purple-500/50"
                                        >
                                            <option value="standard">Standard</option>
                                            <option value="hd">HD (Higher cost)</option>
                                        </select>
                                    </div>
                                </div>

                                {/* Generate Button */}
                                <button
                                    onClick={handleGenerate}
                                    disabled={isGenerating || !concept.trim()}
                                    className="w-full py-3 bg-gradient-to-r from-purple-600 to-pink-600 hover:from-purple-500 hover:to-pink-500 text-white font-medium rounded-xl transition-all disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
                                >
                                    {isGenerating ? (
                                        <>
                                            <Loader2 className="w-5 h-5 animate-spin" />
                                            Generating... (takes 10-20 seconds)
                                        </>
                                    ) : (
                                        <>
                                            <Sparkles className="w-5 h-5" />
                                            Generate Visual
                                        </>
                                    )}
                                </button>

                                {error && (
                                    <div className="p-4 bg-red-500/10 border border-red-500/30 rounded-xl text-red-400">
                                        {error}
                                    </div>
                                )}
                            </div>
                        </div>

                        {/* Generated Image Display */}
                        {generatedImage && (
                            <div className="bg-gray-800/50 backdrop-blur-xl rounded-2xl border border-white/10 p-6">
                                <div className="flex items-center justify-between mb-4">
                                    <h3 className="text-lg font-semibold text-white">
                                        Generated: {generatedImage.concept}
                                    </h3>
                                    <div className="flex items-center gap-2">
                                        <button
                                            onClick={() => handleDownload(generatedImage)}
                                            className="p-2 hover:bg-white/10 rounded-lg transition-colors text-gray-400 hover:text-white"
                                            title="Download"
                                        >
                                            <Download className="w-5 h-5" />
                                        </button>
                                        <button
                                            onClick={handleGenerate}
                                            className="p-2 hover:bg-white/10 rounded-lg transition-colors text-gray-400 hover:text-white"
                                            title="Regenerate"
                                        >
                                            <RefreshCw className="w-5 h-5" />
                                        </button>
                                    </div>
                                </div>

                                {generatedImage.image_url && (
                                    <img
                                        src={generatedImage.image_url}
                                        alt={generatedImage.concept}
                                        className="w-full rounded-xl shadow-2xl"
                                    />
                                )}

                                <div className="mt-4 p-4 bg-gray-900/50 rounded-xl">
                                    <p className="text-sm text-gray-400">
                                        <span className="text-gray-300 font-medium">Enhanced Prompt:</span>{' '}
                                        {generatedImage.enhanced_prompt}
                                    </p>
                                </div>
                            </div>
                        )}

                        {/* Empty State */}
                        {!generatedImage && !isGenerating && (
                            <div className="bg-gray-800/30 backdrop-blur-xl rounded-2xl border border-white/5 p-12 text-center">
                                <ImageIcon className="w-16 h-16 text-gray-600 mx-auto mb-4" />
                                <h3 className="text-lg font-medium text-gray-400">No image generated yet</h3>
                                <p className="text-sm text-gray-500 mt-2">
                                    Enter a concept above and click "Generate Visual" to create an educational illustration
                                </p>
                            </div>
                        )}
                    </div>

                    {/* History Sidebar */}
                    <div className="space-y-4">
                        <h2 className="text-lg font-semibold text-white">Recent Generations</h2>

                        {history.length === 0 ? (
                            <div className="bg-gray-800/30 rounded-xl p-6 text-center">
                                <p className="text-gray-500 text-sm">No history yet</p>
                            </div>
                        ) : (
                            <div className="space-y-3">
                                {history.map((visual) => (
                                    <div
                                        key={visual.id}
                                        className="bg-gray-800/50 rounded-xl border border-white/10 p-3 group cursor-pointer hover:border-purple-500/30 transition-all"
                                        onClick={() => setGeneratedImage(visual)}
                                    >
                                        <div className="flex items-start gap-3">
                                            {visual.image_url ? (
                                                <img
                                                    src={visual.image_url}
                                                    alt={visual.concept}
                                                    className="w-16 h-16 rounded-lg object-cover"
                                                />
                                            ) : (
                                                <div className="w-16 h-16 bg-gray-700 rounded-lg flex items-center justify-center">
                                                    <ImageIcon className="w-6 h-6 text-gray-500" />
                                                </div>
                                            )}
                                            <div className="flex-1 min-w-0">
                                                <p className="text-sm font-medium text-white truncate">
                                                    {visual.concept}
                                                </p>
                                                <p className="text-xs text-gray-400">
                                                    Grade {visual.grade_level}
                                                </p>
                                            </div>
                                            <button
                                                onClick={(e) => {
                                                    e.stopPropagation()
                                                    handleDelete(visual.id)
                                                }}
                                                className="p-1 opacity-0 group-hover:opacity-100 hover:bg-red-500/20 rounded transition-all"
                                            >
                                                <Trash2 className="w-4 h-4 text-red-400" />
                                            </button>
                                        </div>
                                    </div>
                                ))}
                            </div>
                        )}
                    </div>
                </div>
            </main>
        </div>
    )
}
