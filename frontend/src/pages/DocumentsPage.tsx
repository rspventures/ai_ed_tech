import { useState, useEffect, useRef } from 'react'
import { useNavigate } from 'react-router-dom'
import {
    FileUp,
    FileText,
    MessageSquare,
    Trash2,
    Loader2,
    Send,
    ChevronLeft,
    Sparkles,
    BookOpen,
    Clock,
    Check,
    XCircle,
    FileQuestion,
    HelpCircle,
    X,
} from 'lucide-react'
import { useAuthStore } from '@/stores/authStore'
import { documentService, Document, ChatResponse, SearchResult, QuizQuestion } from '@/services/document'

interface ChatMessage {
    role: 'user' | 'assistant'
    content: string
    sources?: SearchResult[]
}

export default function DocumentsPage() {
    const navigate = useNavigate()
    const { user } = useAuthStore()
    const [documents, setDocuments] = useState<Document[]>([])
    const [loading, setLoading] = useState(true)
    const [uploading, setUploading] = useState(false)
    const [selectedDoc, setSelectedDoc] = useState<Document | null>(null)
    const [chatMessages, setChatMessages] = useState<ChatMessage[]>([])
    const [chatInput, setChatInput] = useState('')
    const [chatLoading, setChatLoading] = useState(false)
    const [uploadProgress, setUploadProgress] = useState(0)
    const [sessionId, setSessionId] = useState<string | null>(null)
    const [loadingHistory, setLoadingHistory] = useState(false)
    const fileInputRef = useRef<HTMLInputElement>(null)
    const chatEndRef = useRef<HTMLDivElement>(null)

    // Quiz state
    const [quizLoading, setQuizLoading] = useState(false)
    const [quizQuestions, setQuizQuestions] = useState<QuizQuestion[]>([])
    const [showQuizModal, setShowQuizModal] = useState(false)
    const [selectedAnswers, setSelectedAnswers] = useState<Record<number, string>>({})
    const [showResults, setShowResults] = useState(false)
    const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0)

    useEffect(() => {
        loadDocuments()
    }, [])

    useEffect(() => {
        // Scroll to bottom when new messages arrive
        chatEndRef.current?.scrollIntoView({ behavior: 'smooth' })
    }, [chatMessages])

    // Save session ID to localStorage when it changes
    useEffect(() => {
        if (sessionId && selectedDoc) {
            localStorage.setItem(`doc_chat_session_${selectedDoc.id}`, sessionId)
        }
    }, [sessionId, selectedDoc])

    const loadDocuments = async () => {
        try {
            setLoading(true)
            const response = await documentService.listDocuments()
            setDocuments(response.documents)
        } catch (error) {
            console.error('Failed to load documents:', error)
        } finally {
            setLoading(false)
        }
    }

    const handleFileUpload = async (e: React.ChangeEvent<HTMLInputElement>) => {
        const file = e.target.files?.[0]
        if (!file) return

        try {
            setUploading(true)
            setUploadProgress(0)

            // Simulate progress
            const progressInterval = setInterval(() => {
                setUploadProgress(prev => Math.min(prev + 10, 90))
            }, 200)

            const doc = await documentService.uploadDocument(file)

            clearInterval(progressInterval)
            setUploadProgress(100)

            // Add to list
            setDocuments(prev => [doc, ...prev])

            // Reset
            setTimeout(() => {
                setUploading(false)
                setUploadProgress(0)
            }, 1000)

        } catch (error) {
            console.error('Upload failed:', error)
            setUploading(false)
            setUploadProgress(0)
        }

        // Reset file input
        if (fileInputRef.current) {
            fileInputRef.current.value = ''
        }
    }

    const handleDeleteDocument = async (docId: string) => {
        if (!confirm('Are you sure you want to delete this document?')) return

        try {
            await documentService.deleteDocument(docId)
            setDocuments(prev => prev.filter(d => d.id !== docId))
            if (selectedDoc?.id === docId) {
                setSelectedDoc(null)
                setChatMessages([])
            }
        } catch (error) {
            console.error('Delete failed:', error)
        }
    }

    const handleSelectDocument = async (doc: Document) => {
        setSelectedDoc(doc)
        setChatMessages([])
        setChatInput('')
        setLoadingHistory(true)

        // Load stored session ID for this document
        const storedSessionId = localStorage.getItem(`doc_chat_session_${doc.id}`)
        setSessionId(storedSessionId)

        // If we have a stored session, try to load history
        if (storedSessionId) {
            try {
                const history = await documentService.getChatHistory(doc.id, storedSessionId)
                if (history.messages && history.messages.length > 0) {
                    setChatMessages(
                        history.messages.map(msg => ({
                            role: msg.role as 'user' | 'assistant',
                            content: msg.content,
                        }))
                    )
                }
            } catch (error) {
                console.error('Failed to load chat history:', error)
                // Clear invalid session
                localStorage.removeItem(`doc_chat_session_${doc.id}`)
                setSessionId(null)
            }
        }
        setLoadingHistory(false)
    }

    const handleSendMessage = async () => {
        if (!chatInput.trim() || !selectedDoc || chatLoading) return

        const userMessage = chatInput.trim()
        setChatInput('')
        setChatMessages(prev => [...prev, { role: 'user', content: userMessage }])
        setChatLoading(true)

        try {
            const response = await documentService.chatWithDocument(
                selectedDoc.id,
                userMessage,
                5, // default grade
                sessionId || undefined
            )

            // Save session ID for continuity
            if (response.session_id) {
                setSessionId(response.session_id)
            }

            setChatMessages(prev => [
                ...prev,
                {
                    role: 'assistant',
                    content: response.answer,
                    sources: response.sources,
                },
            ])
        } catch (error) {
            console.error('Chat failed:', error)
            setChatMessages(prev => [
                ...prev,
                {
                    role: 'assistant',
                    content: 'Sorry, I encountered an error processing your question. Please try again.',
                },
            ])
        } finally {
            setChatLoading(false)
        }
    }

    const handleGenerateQuiz = async () => {
        if (!selectedDoc || quizLoading) return

        setQuizLoading(true)
        setQuizQuestions([])
        setSelectedAnswers({})
        setShowResults(false)
        setCurrentQuestionIndex(0)

        try {
            const response = await documentService.generateQuiz(
                selectedDoc.id,
                5, // number of questions
                5  // grade level
            )
            setQuizQuestions(response.questions || [])
            setShowQuizModal(true)
        } catch (error) {
            console.error('Quiz generation failed:', error)
            alert('Failed to generate quiz. Please try again.')
        } finally {
            setQuizLoading(false)
        }
    }

    const handleAnswerSelect = (questionIndex: number, answer: string) => {
        if (showResults) return  // Don't allow changes after submitting
        setSelectedAnswers(prev => ({
            ...prev,
            [questionIndex]: answer
        }))
    }

    const handleSubmitQuiz = () => {
        setShowResults(true)
    }

    const calculateScore = () => {
        let correct = 0
        quizQuestions.forEach((q, idx) => {
            if (selectedAnswers[idx] === q.correct_answer) {
                correct++
            }
        })
        return correct
    }

    const getStatusIcon = (status: string) => {
        switch (status) {
            case 'completed':
                return <Check className="w-4 h-4 text-green-400" />
            case 'processing':
            case 'validating':
                return <Loader2 className="w-4 h-4 text-yellow-400 animate-spin" />
            case 'failed':
                return <XCircle className="w-4 h-4 text-red-400" />
            case 'rejected':
                return <XCircle className="w-4 h-4 text-red-500" />
            default:
                return <Clock className="w-4 h-4 text-gray-400" />
        }
    }

    // Get validation badge for document
    const getValidationBadge = (doc: Document) => {
        if (!doc.validation_status) return null

        switch (doc.validation_status) {
            case 'approved':
                return (
                    <span className="px-2 py-0.5 bg-green-500/20 text-green-400 text-xs rounded-full">
                        ✓ Approved
                    </span>
                )
            case 'needs_review':
                return (
                    <span className="px-2 py-0.5 bg-yellow-500/20 text-yellow-400 text-xs rounded-full">
                        ⚠️ Review
                    </span>
                )
            case 'rejected':
                return (
                    <span className="px-2 py-0.5 bg-red-500/20 text-red-400 text-xs rounded-full">
                        ✗ Rejected
                    </span>
                )
            default:
                return null
        }
    }

    const formatDate = (dateString: string) => {
        return new Date(dateString).toLocaleDateString('en-US', {
            month: 'short',
            day: 'numeric',
            hour: '2-digit',
            minute: '2-digit',
        })
    }

    return (
        <div className="min-h-screen">
            {/* Header */}
            <header className="glass border-b border-white/10">
                <div className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8">
                    <div className="flex items-center justify-between h-16">
                        <div className="flex items-center gap-4">
                            <button
                                onClick={() => navigate('/dashboard')}
                                className="p-2 text-gray-400 hover:text-white hover:bg-white/10 rounded-lg transition-colors"
                            >
                                <ChevronLeft className="w-5 h-5" />
                            </button>
                            <div className="flex items-center gap-3">
                                <div className="w-10 h-10 bg-gradient-to-br from-primary-500 to-accent-500 rounded-xl flex items-center justify-center">
                                    <FileText className="w-5 h-5 text-white" />
                                </div>
                                <span className="text-xl font-bold gradient-text">Study Materials</span>
                            </div>
                        </div>

                        <div className="flex items-center gap-4">
                            <span className="text-sm text-gray-400">{user?.email}</span>
                        </div>
                    </div>
                </div>
            </header>

            {/* Main Content */}
            <main className="max-w-7xl mx-auto px-4 sm:px-6 lg:px-8 py-8">
                <div className="grid lg:grid-cols-3 gap-6">
                    {/* Left Panel - Document List */}
                    <div className="lg:col-span-1">
                        <div className="glass-card">
                            <div className="flex items-center justify-between mb-6">
                                <h2 className="text-lg font-semibold text-white flex items-center gap-2">
                                    <BookOpen className="w-5 h-5 text-primary-400" />
                                    My Documents
                                </h2>
                                <span className="text-sm text-gray-400">{documents.length} files</span>
                            </div>

                            {/* Upload Area */}
                            <div className="mb-6">
                                <input
                                    type="file"
                                    ref={fileInputRef}
                                    onChange={handleFileUpload}
                                    accept=".pdf,.txt,.docx,.md"
                                    className="hidden"
                                />
                                <button
                                    onClick={() => fileInputRef.current?.click()}
                                    disabled={uploading}
                                    className={`w-full border-2 border-dashed border-white/20 rounded-xl p-6 text-center
                                              hover:border-primary-500/50 hover:bg-primary-500/5 transition-all cursor-pointer
                                              ${uploading ? 'opacity-50 cursor-not-allowed' : ''}`}
                                >
                                    {uploading ? (
                                        <div className="space-y-3">
                                            <Loader2 className="w-8 h-8 text-primary-400 mx-auto animate-spin" />
                                            <p className="text-gray-400">Uploading... {uploadProgress}%</p>
                                            <div className="h-2 bg-white/10 rounded-full overflow-hidden">
                                                <div
                                                    className="h-full bg-primary-500 transition-all duration-300"
                                                    style={{ width: `${uploadProgress}%` }}
                                                />
                                            </div>
                                        </div>
                                    ) : (
                                        <>
                                            <FileUp className="w-8 h-8 text-gray-400 mx-auto mb-3" />
                                            <p className="text-gray-300 font-medium">Upload Document</p>
                                            <p className="text-sm text-gray-500 mt-1">PDF, DOCX, TXT, MD</p>
                                        </>
                                    )}
                                </button>
                            </div>

                            {/* Document List */}
                            <div className="space-y-3 max-h-[500px] overflow-y-auto">
                                {loading ? (
                                    <div className="flex items-center justify-center py-8">
                                        <Loader2 className="w-6 h-6 text-primary-500 animate-spin" />
                                    </div>
                                ) : documents.length === 0 ? (
                                    <div className="text-center py-8">
                                        <FileText className="w-12 h-12 text-gray-600 mx-auto mb-3" />
                                        <p className="text-gray-400">No documents yet</p>
                                        <p className="text-sm text-gray-500">Upload your first study material</p>
                                    </div>
                                ) : (
                                    documents.map(doc => (
                                        <div
                                            key={doc.id}
                                            className={`p-4 rounded-xl border transition-all cursor-pointer group
                                                      ${selectedDoc?.id === doc.id
                                                    ? 'bg-primary-500/20 border-primary-500/50'
                                                    : 'bg-white/5 border-white/10 hover:bg-white/10'
                                                }`}
                                            onClick={() => handleSelectDocument(doc)}
                                        >
                                            <div className="flex items-start justify-between">
                                                <div className="flex items-start gap-3 flex-1 min-w-0">
                                                    <div className="w-10 h-10 bg-white/10 rounded-lg flex items-center justify-center flex-shrink-0">
                                                        <FileText className="w-5 h-5 text-primary-400" />
                                                    </div>
                                                    <div className="min-w-0 flex-1">
                                                        <div className="flex items-center gap-2">
                                                            <p className="text-white font-medium truncate">
                                                                {doc.original_filename}
                                                            </p>
                                                            {getValidationBadge(doc)}
                                                        </div>
                                                        {doc.status === 'rejected' && doc.error_message && (
                                                            <p className="text-xs text-red-400 mt-1 truncate">
                                                                {doc.error_message}
                                                            </p>
                                                        )}
                                                        <div className="flex items-center gap-2 text-xs text-gray-400 mt-1">
                                                            {getStatusIcon(doc.status)}
                                                            <span>{documentService.formatFileSize(doc.file_size)}</span>
                                                            <span>•</span>
                                                            <span>{doc.chunk_count} chunks</span>
                                                        </div>
                                                    </div>
                                                </div>
                                                <button
                                                    onClick={(e) => {
                                                        e.stopPropagation()
                                                        handleDeleteDocument(doc.id)
                                                    }}
                                                    className="p-2 text-gray-500 hover:text-red-400 opacity-0 group-hover:opacity-100 transition-all"
                                                >
                                                    <Trash2 className="w-4 h-4" />
                                                </button>
                                            </div>
                                        </div>
                                    ))
                                )}
                            </div>
                        </div>
                    </div>

                    {/* Right Panel - Chat Interface */}
                    <div className="lg:col-span-2">
                        <div className="glass-card h-[700px] flex flex-col">
                            {selectedDoc ? (
                                <>
                                    {/* Chat Header */}
                                    <div className="flex items-center justify-between pb-4 border-b border-white/10">
                                        <div className="flex items-center gap-3">
                                            <div className="w-10 h-10 bg-gradient-to-br from-primary-500 to-accent-500 rounded-lg flex items-center justify-center">
                                                <MessageSquare className="w-5 h-5 text-white" />
                                            </div>
                                            <div>
                                                <p className="text-white font-medium">
                                                    Chat with {selectedDoc.original_filename}
                                                </p>
                                                <p className="text-xs text-gray-400">
                                                    Ask questions about your document
                                                </p>
                                            </div>
                                        </div>
                                        <div className="flex items-center gap-2">
                                            <button
                                                onClick={handleGenerateQuiz}
                                                disabled={selectedDoc.status !== 'completed' || quizLoading}
                                                className="flex items-center gap-2 px-3 py-1.5 bg-gradient-to-r from-purple-500/20 to-pink-500/20
                                                         border border-purple-500/30 rounded-lg text-purple-300 hover:text-white
                                                         disabled:opacity-50 disabled:cursor-not-allowed transition-all text-sm"
                                            >
                                                {quizLoading ? (
                                                    <Loader2 className="w-4 h-4 animate-spin" />
                                                ) : (
                                                    <HelpCircle className="w-4 h-4" />
                                                )}
                                                <span>Generate Quiz</span>
                                            </button>
                                            {getStatusIcon(selectedDoc.status)}
                                            <span className={`text-sm ${documentService.getStatusColor(selectedDoc.status)}`}>
                                                {selectedDoc.status}
                                            </span>
                                        </div>
                                    </div>

                                    {/* Chat Messages */}
                                    <div className="flex-1 overflow-y-auto py-4 space-y-4">
                                        {chatMessages.length === 0 ? (
                                            <div className="flex flex-col items-center justify-center h-full text-center">
                                                <Sparkles className="w-16 h-16 text-primary-500/30 mb-4" />
                                                <p className="text-gray-400 mb-2">Ready to chat!</p>
                                                <p className="text-sm text-gray-500 max-w-md">
                                                    Ask me anything about this document. I'll find the relevant
                                                    information and answer your questions.
                                                </p>
                                                <div className="flex flex-wrap gap-2 mt-6 justify-center">
                                                    {['What is this document about?', 'Summarize the key points', 'Explain the main concepts'].map(
                                                        suggestion => (
                                                            <button
                                                                key={suggestion}
                                                                onClick={() => {
                                                                    setChatInput(suggestion)
                                                                }}
                                                                className="px-3 py-2 bg-white/5 hover:bg-white/10 rounded-lg text-sm text-gray-300 transition-colors"
                                                            >
                                                                {suggestion}
                                                            </button>
                                                        )
                                                    )}
                                                </div>
                                            </div>
                                        ) : (
                                            chatMessages.map((msg, idx) => (
                                                <div
                                                    key={idx}
                                                    className={`flex ${msg.role === 'user' ? 'justify-end' : 'justify-start'}`}
                                                >
                                                    <div
                                                        className={`max-w-[80%] p-4 rounded-2xl ${msg.role === 'user'
                                                            ? 'bg-primary-500 text-white rounded-br-none'
                                                            : 'bg-white/10 text-gray-200 rounded-bl-none'
                                                            }`}
                                                    >
                                                        <p className="whitespace-pre-wrap">{msg.content}</p>

                                                        {/* Show sources if available */}
                                                        {msg.sources && msg.sources.length > 0 && (
                                                            <div className="mt-3 pt-3 border-t border-white/20">
                                                                <p className="text-xs text-gray-400 mb-2">
                                                                    Sources:
                                                                </p>
                                                                <div className="space-y-2">
                                                                    {msg.sources.slice(0, 2).map((source, i) => (
                                                                        <div
                                                                            key={i}
                                                                            className="p-2 bg-white/5 rounded-lg text-xs text-gray-300"
                                                                        >
                                                                            <p className="truncate">{source.content.slice(0, 100)}...</p>
                                                                            <p className="text-gray-500 mt-1">
                                                                                Match: {(source.similarity * 100).toFixed(0)}%
                                                                            </p>
                                                                        </div>
                                                                    ))}
                                                                </div>
                                                            </div>
                                                        )}
                                                    </div>
                                                </div>
                                            ))
                                        )}

                                        {chatLoading && (
                                            <div className="flex justify-start">
                                                <div className="bg-white/10 p-4 rounded-2xl rounded-bl-none">
                                                    <div className="flex items-center gap-2">
                                                        <Loader2 className="w-4 h-4 animate-spin text-primary-400" />
                                                        <span className="text-gray-400">Thinking...</span>
                                                    </div>
                                                </div>
                                            </div>
                                        )}

                                        <div ref={chatEndRef} />
                                    </div>

                                    {/* Chat Input */}
                                    <div className="pt-4 border-t border-white/10">
                                        <div className="flex gap-3">
                                            <input
                                                type="text"
                                                value={chatInput}
                                                onChange={e => setChatInput(e.target.value)}
                                                onKeyDown={e => e.key === 'Enter' && handleSendMessage()}
                                                placeholder="Ask a question about this document..."
                                                disabled={selectedDoc.status !== 'completed' || chatLoading}
                                                className="flex-1 bg-white/5 border border-white/10 rounded-xl px-4 py-3
                                                         text-white placeholder-gray-500 focus:outline-none focus:border-primary-500
                                                         disabled:opacity-50 disabled:cursor-not-allowed"
                                            />
                                            <button
                                                onClick={handleSendMessage}
                                                disabled={!chatInput.trim() || selectedDoc.status !== 'completed' || chatLoading}
                                                className="btn-primary px-6 disabled:opacity-50 disabled:cursor-not-allowed"
                                            >
                                                <Send className="w-5 h-5" />
                                            </button>
                                        </div>
                                        {selectedDoc.status !== 'completed' && (
                                            <p className="text-xs text-amber-400 mt-2">
                                                Document is still processing. Please wait...
                                            </p>
                                        )}
                                    </div>
                                </>
                            ) : (
                                <div className="flex-1 flex flex-col items-center justify-center text-center">
                                    <FileQuestion className="w-20 h-20 text-gray-600 mb-4" />
                                    <h3 className="text-xl font-semibold text-white mb-2">
                                        Select a Document
                                    </h3>
                                    <p className="text-gray-400 max-w-md">
                                        Choose a document from the list to start chatting with it.
                                        You can ask questions and get answers based on the document content.
                                    </p>
                                </div>
                            )}
                        </div>
                    </div>
                </div>
            </main>

            {/* Quiz Modal */}
            {showQuizModal && (
                <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50 p-4">
                    <div className="bg-gray-900/95 border border-white/10 rounded-2xl max-w-3xl w-full max-h-[85vh] overflow-hidden flex flex-col shadow-2xl">
                        {/* Modal Header */}
                        <div className="flex items-center justify-between p-5 border-b border-white/10 flex-shrink-0">
                            <div className="flex items-center gap-3 min-w-0 flex-1">
                                <div className="w-10 h-10 bg-gradient-to-br from-purple-500 to-pink-500 rounded-xl flex items-center justify-center flex-shrink-0">
                                    <HelpCircle className="w-5 h-5 text-white" />
                                </div>
                                <div className="min-w-0">
                                    <h3 className="text-lg font-bold text-white">Document Quiz</h3>
                                    <p className="text-sm text-gray-400 truncate max-w-md">
                                        {selectedDoc?.original_filename}
                                    </p>
                                </div>
                            </div>
                            <button
                                onClick={() => {
                                    setShowQuizModal(false)
                                    setShowResults(false)
                                    setSelectedAnswers({})
                                }}
                                className="p-2 text-gray-400 hover:text-white hover:bg-white/10 rounded-lg transition-colors flex-shrink-0"
                            >
                                <X className="w-5 h-5" />
                            </button>
                        </div>

                        {/* Modal Content */}
                        <div className="flex-1 overflow-y-auto p-5">
                            {quizQuestions.length === 0 ? (
                                <div className="flex flex-col items-center justify-center py-12">
                                    <Loader2 className="w-10 h-10 text-purple-500 animate-spin mb-4" />
                                    <p className="text-gray-400">Generating questions from your document...</p>
                                    <p className="text-sm text-gray-500 mt-2">Reading entire document for coverage...</p>
                                </div>
                            ) : !showResults ? (
                                // Active Quiz Mode - Single Question
                                <div className="max-w-2xl mx-auto">
                                    {/* Progress Bar */}
                                    <div className="mb-6">
                                        <div className="flex justify-between text-sm text-gray-400 mb-2">
                                            <span>Question {currentQuestionIndex + 1} of {quizQuestions.length}</span>
                                            <span>{Math.round(((currentQuestionIndex + 1) / quizQuestions.length) * 100)}%</span>
                                        </div>
                                        <div className="h-2 bg-white/10 rounded-full overflow-hidden">
                                            <div
                                                className="h-full bg-purple-500 transition-all duration-300"
                                                style={{ width: `${((currentQuestionIndex + 1) / quizQuestions.length) * 100}%` }}
                                            />
                                        </div>
                                    </div>

                                    {/* Current Question */}
                                    <div className="bg-white/5 rounded-xl p-6 border border-white/5 animate-in fade-in slide-in-from-right-4 duration-300">
                                        <p className="text-white font-medium mb-6 text-lg leading-relaxed">
                                            {quizQuestions[currentQuestionIndex].question}
                                        </p>

                                        <div className="grid gap-3">
                                            {quizQuestions[currentQuestionIndex].options.map((option, optIdx) => {
                                                const isSelected = selectedAnswers[currentQuestionIndex] === option
                                                const isCorrect = option === quizQuestions[currentQuestionIndex].correct_answer
                                                const hasAnswered = !!selectedAnswers[currentQuestionIndex]
                                                const optionLetter = String.fromCharCode(65 + optIdx)

                                                let optionClass = 'bg-white/5 border-white/10 hover:bg-white/10 text-gray-300'
                                                let letterClass = 'bg-white/10 text-gray-400'

                                                if (hasAnswered) {
                                                    if (isCorrect) {
                                                        optionClass = 'bg-green-500/20 border-green-500/50 text-white'
                                                        letterClass = 'bg-green-500/30 text-green-300'
                                                    } else if (isSelected && !isCorrect) {
                                                        optionClass = 'bg-red-500/20 border-red-500/50 text-white'
                                                        letterClass = 'bg-red-500/30 text-red-300'
                                                    } else if (isSelected) {
                                                        // Fallback for selected
                                                        optionClass = 'bg-purple-500/20 border-purple-500/50 text-white'
                                                    }
                                                } else if (isSelected) {
                                                    optionClass = 'bg-purple-500/20 border-purple-500/50 text-white'
                                                    letterClass = 'bg-purple-500/30 text-purple-300'
                                                }

                                                return (
                                                    <button
                                                        key={optIdx}
                                                        onClick={() => handleAnswerSelect(currentQuestionIndex, option)}
                                                        className={`flex items-center gap-4 w-full p-4 text-left rounded-xl border transition-all ${optionClass} ${hasAnswered ? 'cursor-default' : 'cursor-pointer'}`}
                                                        disabled={hasAnswered}
                                                    >
                                                        <span className={`w-8 h-8 flex items-center justify-center rounded-lg text-sm font-bold flex-shrink-0 ${letterClass}`}>
                                                            {optionLetter}
                                                        </span>
                                                        <span className="text-base leading-relaxed">{option}</span>

                                                        {hasAnswered && isCorrect && (
                                                            <Check className="w-5 h-5 text-green-400 ml-auto" />
                                                        )}
                                                        {hasAnswered && isSelected && !isCorrect && (
                                                            <X className="w-5 h-5 text-red-400 ml-auto" />
                                                        )}
                                                    </button>
                                                )
                                            })}
                                        </div>

                                        {/* Immediate Feedback */}
                                        {selectedAnswers[currentQuestionIndex] && (
                                            <div className="mt-6 pt-6 border-t border-white/10 animate-in fade-in zoom-in-95">
                                                <div className={`p-4 rounded-xl border ${selectedAnswers[currentQuestionIndex] === quizQuestions[currentQuestionIndex].correct_answer
                                                    ? 'bg-green-500/10 border-green-500/20'
                                                    : 'bg-red-500/10 border-red-500/20'
                                                    }`}>
                                                    <p className={`font-semibold mb-2 ${selectedAnswers[currentQuestionIndex] === quizQuestions[currentQuestionIndex].correct_answer
                                                        ? 'text-green-400'
                                                        : 'text-red-400'
                                                        }`}>
                                                        {selectedAnswers[currentQuestionIndex] === quizQuestions[currentQuestionIndex].correct_answer
                                                            ? 'Correct! 🎉'
                                                            : 'Not quite right 😅'}
                                                    </p>
                                                    <p className="text-gray-300 text-sm leading-relaxed">
                                                        <span className="text-purple-400 font-semibold">Explanation: </span>
                                                        {quizQuestions[currentQuestionIndex].explanation}
                                                    </p>
                                                </div>
                                            </div>
                                        )}
                                    </div>
                                </div>
                            ) : (
                                /* Result Summary View */
                                <div className="max-w-2xl mx-auto text-center py-8">
                                    <div className="w-24 h-24 bg-gradient-to-br from-purple-500 to-pink-500 rounded-3xl mx-auto flex items-center justify-center mb-6 shadow-xl shadow-purple-500/20">
                                        <Sparkles className="w-12 h-12 text-white" />
                                    </div>

                                    <h2 className="text-3xl font-bold text-white mb-2">Quiz Complete!</h2>
                                    <p className="text-gray-400 mb-8">Here's how you performed on this document</p>

                                    <div className="grid grid-cols-3 gap-4 mb-8">
                                        <div className="bg-white/5 rounded-2xl p-4 border border-white/10">
                                            <p className="text-gray-400 text-sm mb-1">Score</p>
                                            <p className="text-2xl font-bold text-white">{Math.round((calculateScore() / quizQuestions.length) * 100)}%</p>
                                        </div>
                                        <div className="bg-white/5 rounded-2xl p-4 border border-white/10">
                                            <p className="text-gray-400 text-sm mb-1">Correct</p>
                                            <p className="text-2xl font-bold text-green-400">{calculateScore()}</p>
                                        </div>
                                        <div className="bg-white/5 rounded-2xl p-4 border border-white/10">
                                            <p className="text-gray-400 text-sm mb-1">Total</p>
                                            <p className="text-2xl font-bold text-white">{quizQuestions.length}</p>
                                        </div>
                                    </div>

                                    {/* Detailed Review List */}
                                    <div className="text-left space-y-4 mb-8 max-h-[300px] overflow-y-auto pr-2 custom-scrollbar">
                                        <h3 className="text-white font-semibold sticky top-0 bg-[#111827] py-2">Question Review</h3>
                                        {quizQuestions.map((q, idx) => (
                                            <div key={idx} className="bg-white/5 p-4 rounded-xl border border-white/5 flex gap-4">
                                                <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${selectedAnswers[idx] === q.correct_answer
                                                    ? 'bg-green-500/20 text-green-400'
                                                    : 'bg-red-500/20 text-red-400'
                                                    }`}>
                                                    {selectedAnswers[idx] === q.correct_answer ? <Check className="w-4 h-4" /> : <X className="w-4 h-4" />}
                                                </div>
                                                <div>
                                                    <p className="text-gray-200 text-sm font-medium mb-1 line-clamp-2">{q.question}</p>
                                                    <p className="text-xs text-gray-500">Correct answer: {q.correct_answer}</p>
                                                </div>
                                            </div>
                                        ))}
                                    </div>
                                </div>
                            )}
                        </div>

                        {/* Modal Footer */}
                        {quizQuestions.length > 0 && (
                            <div className="p-5 border-t border-white/10 flex-shrink-0 bg-gray-900/50 backdrop-blur-sm">
                                <div className="flex gap-3 max-w-2xl mx-auto w-full">
                                    {!showResults ? (
                                        <>
                                            <button
                                                onClick={() => setCurrentQuestionIndex(prev => Math.max(0, prev - 1))}
                                                disabled={currentQuestionIndex === 0}
                                                className="px-6 py-3 rounded-xl border border-white/10 text-white font-medium hover:bg-white/5 disabled:opacity-30 disabled:cursor-not-allowed transition-all"
                                            >
                                                Previous
                                            </button>
                                            <div className="flex-1"></div>
                                            {currentQuestionIndex < quizQuestions.length - 1 ? (
                                                <button
                                                    onClick={() => setCurrentQuestionIndex(prev => Math.min(quizQuestions.length - 1, prev + 1))}
                                                    disabled={!selectedAnswers[currentQuestionIndex]}
                                                    className="px-6 py-3 bg-white text-gray-900 font-bold rounded-xl hover:bg-gray-100 disabled:opacity-50 disabled:cursor-not-allowed transition-all flex items-center gap-2"
                                                >
                                                    Next Question
                                                    <ChevronLeft className="w-4 h-4 rotate-180" />
                                                </button>
                                            ) : (
                                                <button
                                                    onClick={() => setShowResults(true)}
                                                    disabled={!selectedAnswers[currentQuestionIndex]}
                                                    className="px-6 py-3 bg-gradient-to-r from-purple-500 to-pink-500 text-white font-bold rounded-xl hover:shadow-lg hover:shadow-purple-500/25 disabled:opacity-50 disabled:cursor-not-allowed transition-all"
                                                >
                                                    Finish Quiz
                                                </button>
                                            )}
                                        </>
                                    ) : (
                                        <>
                                            <button
                                                onClick={() => {
                                                    setShowQuizModal(false)
                                                    setShowResults(false)
                                                    setSelectedAnswers({})
                                                    setCurrentQuestionIndex(0)
                                                }}
                                                className="flex-1 py-3 px-6 border border-white/10 text-white font-medium rounded-xl hover:bg-white/5 transition-all"
                                            >
                                                Close
                                            </button>
                                            <button
                                                onClick={handleGenerateQuiz}
                                                className="flex-1 py-3 px-6 bg-gradient-to-r from-purple-500 to-pink-500 text-white font-bold rounded-xl hover:shadow-lg hover:shadow-purple-500/25 transition-all"
                                            >
                                                Try Another Quiz
                                            </button>
                                        </>
                                    )}
                                </div>
                            </div>
                        )}
                    </div>
                </div>
            )}
        </div>
    )
}
