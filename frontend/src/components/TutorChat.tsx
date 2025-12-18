/**
 * TutorChat Component - Interactive AI Tutor Chat Widget
 * 
 * A floating chat button that expands into a full conversation interface
 * with Professor Sage, the friendly AI tutor.
 */
import { useState, useRef, useEffect } from 'react'
import {
    MessageCircle,
    X,
    Send,
    Loader2,
    Sparkles,
    HelpCircle
} from 'lucide-react'
import { chatService } from '@/services/chat'
import type { ChatMessage, ChatContextType, ChatResponse } from '@/types'

interface TutorChatProps {
    /** Type of content being viewed */
    contextType: ChatContextType
    /** ID of the lesson or question being viewed */
    contextId?: string
    /** Whether to show the chat initially minimized */
    initiallyMinimized?: boolean
}

export function TutorChat({
    contextType,
    contextId,
    initiallyMinimized = true
}: TutorChatProps) {
    const [isOpen, setIsOpen] = useState(!initiallyMinimized)
    const [messages, setMessages] = useState<ChatMessage[]>([])
    const [inputValue, setInputValue] = useState('')
    const [isLoading, setIsLoading] = useState(false)
    const [sessionId, setSessionId] = useState<string | null>(null)
    const [suggestions, setSuggestions] = useState<string[]>([])
    const messagesEndRef = useRef<HTMLDivElement>(null)
    const inputRef = useRef<HTMLInputElement>(null)

    // Scroll to bottom when new messages arrive
    useEffect(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
    }, [messages])

    // Focus input when chat opens
    useEffect(() => {
        if (isOpen) {
            inputRef.current?.focus()
        }
    }, [isOpen])

    const handleSendMessage = async (message?: string) => {
        const text = message || inputValue.trim()
        if (!text || isLoading) return

        // Add user message immediately
        const userMessage: ChatMessage = {
            role: 'user',
            content: text,
            timestamp: new Date().toISOString()
        }
        setMessages(prev => [...prev, userMessage])
        setInputValue('')
        setIsLoading(true)
        setSuggestions([])

        try {
            const response: ChatResponse = await chatService.askTutor({
                message: text,
                context_type: contextType,
                context_id: contextId,
                session_id: sessionId || undefined
            })

            // Save session ID for conversation continuity
            setSessionId(response.session_id)

            // Add AI response
            const aiMessage: ChatMessage = {
                role: 'assistant',
                content: response.response,
                timestamp: new Date().toISOString()
            }
            setMessages(prev => [...prev, aiMessage])

            // Set follow-up suggestions
            if (response.suggestions && response.suggestions.length > 0) {
                setSuggestions(response.suggestions)
            }
        } catch (error) {
            console.error('Chat error:', error)
            const errorMessage: ChatMessage = {
                role: 'assistant',
                content: "Oops! I had a little hiccup 🙈. Could you try asking again?",
                timestamp: new Date().toISOString()
            }
            setMessages(prev => [...prev, errorMessage])
        } finally {
            setIsLoading(false)
        }
    }

    const handleKeyPress = (e: React.KeyboardEvent) => {
        if (e.key === 'Enter' && !e.shiftKey) {
            e.preventDefault()
            handleSendMessage()
        }
    }

    const handleSuggestionClick = (suggestion: string) => {
        handleSendMessage(suggestion)
    }

    if (!isOpen) {
        // Floating button (closed state)
        return (
            <button
                onClick={() => setIsOpen(true)}
                className="fixed bottom-6 right-6 w-16 h-16 bg-gradient-to-r from-purple-500 to-indigo-600 
                           rounded-full shadow-lg hover:shadow-xl transition-all duration-300 
                           flex items-center justify-center group z-50
                           hover:scale-110 active:scale-95"
                aria-label="Open AI Tutor Chat"
            >
                <div className="relative">
                    <MessageCircle className="w-7 h-7 text-white" />
                    <Sparkles className="w-4 h-4 text-yellow-300 absolute -top-2 -right-2 
                                         animate-pulse" />
                </div>

                {/* Tooltip */}
                <span className="absolute right-full mr-3 px-3 py-2 bg-gray-900 text-white 
                                 text-sm rounded-lg opacity-0 group-hover:opacity-100 
                                 transition-opacity whitespace-nowrap pointer-events-none">
                    Need help? Ask Professor Sage! 🦉
                </span>
            </button>
        )
    }

    // Expanded chat window
    return (
        <div className="fixed bottom-6 right-6 w-96 h-[500px] bg-white rounded-2xl shadow-2xl 
                        flex flex-col overflow-hidden z-50 border border-gray-200
                        animate-in slide-in-from-bottom-4 duration-300">

            {/* Header */}
            <div className="bg-gradient-to-r from-purple-500 to-indigo-600 px-4 py-3 
                            flex items-center justify-between">
                <div className="flex items-center gap-3">
                    <div className="w-10 h-10 bg-white/20 rounded-full flex items-center justify-center">
                        <span className="text-2xl">🦉</span>
                    </div>
                    <div>
                        <h3 className="text-white font-semibold">Professor Sage</h3>
                        <p className="text-white/80 text-xs">Your AI Learning Buddy</p>
                    </div>
                </div>
                <button
                    onClick={() => setIsOpen(false)}
                    className="text-white/80 hover:text-white transition-colors p-1"
                    aria-label="Close chat"
                >
                    <X className="w-5 h-5" />
                </button>
            </div>

            {/* Messages Area */}
            <div className="flex-1 overflow-y-auto p-4 space-y-4 bg-gray-50">
                {messages.length === 0 && (
                    <div className="text-center py-8">
                        <div className="w-16 h-16 bg-purple-100 rounded-full flex items-center 
                                        justify-center mx-auto mb-4">
                            <HelpCircle className="w-8 h-8 text-purple-500" />
                        </div>
                        <h4 className="text-gray-800 font-medium mb-2">Hi there! 👋</h4>
                        <p className="text-gray-500 text-sm">
                            I'm Professor Sage, your friendly tutor!<br />
                            Ask me anything about what you're learning.
                        </p>
                    </div>
                )}

                {messages.map((message, index) => (
                    <div
                        key={index}
                        className={`flex ${message.role === 'user' ? 'justify-end' : 'justify-start'}`}
                    >
                        <div
                            className={`max-w-[80%] rounded-2xl px-4 py-2 ${message.role === 'user'
                                    ? 'bg-purple-600 text-white rounded-br-sm'
                                    : 'bg-white text-gray-800 shadow-sm border border-gray-100 rounded-bl-sm'
                                }`}
                        >
                            <p className="text-sm whitespace-pre-wrap">{message.content}</p>
                        </div>
                    </div>
                ))}

                {isLoading && (
                    <div className="flex justify-start">
                        <div className="bg-white rounded-2xl px-4 py-3 shadow-sm border border-gray-100 
                                        rounded-bl-sm">
                            <div className="flex items-center gap-2">
                                <Loader2 className="w-4 h-4 animate-spin text-purple-500" />
                                <span className="text-sm text-gray-500">Thinking...</span>
                            </div>
                        </div>
                    </div>
                )}

                <div ref={messagesEndRef} />
            </div>

            {/* Suggestions */}
            {suggestions.length > 0 && !isLoading && (
                <div className="px-4 py-2 bg-purple-50 border-t border-purple-100">
                    <p className="text-xs text-purple-600 mb-2">Try asking:</p>
                    <div className="flex flex-wrap gap-2">
                        {suggestions.map((suggestion, index) => (
                            <button
                                key={index}
                                onClick={() => handleSuggestionClick(suggestion)}
                                className="text-xs px-3 py-1.5 bg-white border border-purple-200 
                                           rounded-full text-purple-700 hover:bg-purple-100 
                                           transition-colors"
                            >
                                {suggestion}
                            </button>
                        ))}
                    </div>
                </div>
            )}

            {/* Input Area */}
            <div className="p-3 border-t border-gray-200 bg-white">
                <div className="flex items-center gap-2">
                    <input
                        ref={inputRef}
                        type="text"
                        value={inputValue}
                        onChange={(e) => setInputValue(e.target.value)}
                        onKeyPress={handleKeyPress}
                        placeholder="Ask me anything..."
                        disabled={isLoading}
                        className="flex-1 px-4 py-2 bg-gray-100 rounded-full text-sm
                                   focus:outline-none focus:ring-2 focus:ring-purple-500 
                                   focus:bg-white transition-all disabled:opacity-50"
                    />
                    <button
                        onClick={() => handleSendMessage()}
                        disabled={!inputValue.trim() || isLoading}
                        className="w-10 h-10 bg-purple-600 rounded-full flex items-center 
                                   justify-center text-white hover:bg-purple-700 
                                   transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                        aria-label="Send message"
                    >
                        {isLoading ? (
                            <Loader2 className="w-5 h-5 animate-spin" />
                        ) : (
                            <Send className="w-5 h-5" />
                        )}
                    </button>
                </div>
            </div>
        </div>
    )
}

export default TutorChat
