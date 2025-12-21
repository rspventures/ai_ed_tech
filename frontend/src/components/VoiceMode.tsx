/**
 * VoiceMode Component - Real-time voice conversation with Professor Sage
 * 
 * Uses Web Audio API to capture microphone input and play AI responses.
 * Connects to backend WebSocket which relays to OpenAI Realtime API.
 */
import { useState, useRef, useCallback, useEffect } from 'react'
import { Mic, MicOff, Phone, PhoneOff, Volume2 } from 'lucide-react'

interface VoiceModeProps {
    onClose?: () => void
}

interface Transcript {
    role: 'user' | 'assistant'
    text: string
}

export function VoiceMode({ onClose }: VoiceModeProps) {
    const [isConnected, setIsConnected] = useState(false)
    const [isListening, setIsListening] = useState(false)
    const [isSpeaking, setIsSpeaking] = useState(false)
    const [transcripts, setTranscripts] = useState<Transcript[]>([])
    const [error, setError] = useState<string | null>(null)
    const [audioLevel, setAudioLevel] = useState(0)

    const wsRef = useRef<WebSocket | null>(null)
    const audioContextRef = useRef<AudioContext | null>(null)
    const mediaStreamRef = useRef<MediaStream | null>(null)
    const processorRef = useRef<ScriptProcessorNode | null>(null)
    const audioQueueRef = useRef<Float32Array[]>([])
    const isPlayingRef = useRef(false)

    // Connect to voice WebSocket
    const connect = useCallback(async () => {
        if (wsRef.current?.readyState === WebSocket.OPEN) return

        try {
            // Get token from localStorage
            const accessToken = localStorage.getItem('access_token')
            if (!accessToken) {
                setError('Not authenticated. Please log in again.')
                return
            }

            // Request microphone access
            const stream = await navigator.mediaDevices.getUserMedia({
                audio: {
                    sampleRate: 24000,
                    channelCount: 1,
                    echoCancellation: true,
                    noiseSuppression: true,
                }
            })
            mediaStreamRef.current = stream

            // Create audio context
            audioContextRef.current = new AudioContext({ sampleRate: 24000 })

            // Connect to WebSocket
            const wsUrl = `${window.location.protocol === 'https:' ? 'wss:' : 'ws:'}//${window.location.host}/api/v1/voice/ws?token=${accessToken}`
            const ws = new WebSocket(wsUrl)
            wsRef.current = ws

            ws.onopen = () => {
                setIsConnected(true)
                setError(null)
                startListening()
            }

            ws.onmessage = (event) => {
                const data = JSON.parse(event.data)
                handleServerMessage(data)
            }

            ws.onerror = () => {
                setError('Connection error. Please try again.')
            }

            ws.onclose = () => {
                setIsConnected(false)
                setIsListening(false)
                stopListening()
            }

        } catch (err) {
            console.error('Voice connection error:', err)
            setError('Could not access microphone. Please allow microphone access.')
        }
    }, [])

    // Handle messages from server
    const handleServerMessage = useCallback((data: any) => {
        switch (data.type) {
            case 'audio':
                // Queue audio for playback
                const audioData = base64ToFloat32(data.data)
                audioQueueRef.current.push(audioData)
                playQueuedAudio()
                setIsSpeaking(true)
                break

            case 'transcript':
                setTranscripts(prev => {
                    const last = prev[prev.length - 1]
                    if (last && last.role === data.role) {
                        // Append to existing transcript
                        return [
                            ...prev.slice(0, -1),
                            { ...last, text: last.text + data.text }
                        ]
                    }
                    // New transcript
                    return [...prev, { role: data.role, text: data.text }]
                })
                break

            case 'response_complete':
                setIsSpeaking(false)
                break

            case 'error':
                setError(data.message)
                break

            case 'status':
                // Status message, could show as toast
                console.log('Voice status:', data.message)
                break
        }
    }, [])

    // Start capturing audio
    const startListening = useCallback(() => {
        if (!audioContextRef.current || !mediaStreamRef.current) return

        const source = audioContextRef.current.createMediaStreamSource(mediaStreamRef.current)
        const processor = audioContextRef.current.createScriptProcessor(4096, 1, 1)
        processorRef.current = processor

        processor.onaudioprocess = (e) => {
            if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return

            const inputData = e.inputBuffer.getChannelData(0)

            // Calculate audio level for visualization
            let sum = 0
            for (let i = 0; i < inputData.length; i++) {
                sum += inputData[i] * inputData[i]
            }
            const rms = Math.sqrt(sum / inputData.length)
            setAudioLevel(Math.min(1, rms * 10))

            // Convert to PCM16 and send
            const pcm16 = float32ToPCM16(inputData)
            const base64 = arrayBufferToBase64(pcm16.buffer)

            wsRef.current.send(JSON.stringify({
                type: 'audio',
                data: base64
            }))
        }

        source.connect(processor)
        processor.connect(audioContextRef.current.destination)
        setIsListening(true)
    }, [])

    // Stop capturing audio
    const stopListening = useCallback(() => {
        if (processorRef.current) {
            processorRef.current.disconnect()
            processorRef.current = null
        }
        setIsListening(false)
        setAudioLevel(0)
    }, [])

    // Play queued audio responses
    const playQueuedAudio = useCallback(async () => {
        if (isPlayingRef.current || audioQueueRef.current.length === 0) return
        if (!audioContextRef.current) return

        isPlayingRef.current = true

        while (audioQueueRef.current.length > 0) {
            const audioData = audioQueueRef.current.shift()!
            const buffer = audioContextRef.current.createBuffer(1, audioData.length, 24000)
            buffer.getChannelData(0).set(audioData)

            const source = audioContextRef.current.createBufferSource()
            source.buffer = buffer
            source.connect(audioContextRef.current.destination)

            await new Promise<void>((resolve) => {
                source.onended = () => resolve()
                source.start()
            })
        }

        isPlayingRef.current = false
    }, [])

    // Disconnect
    const disconnect = useCallback(() => {
        stopListening()

        if (wsRef.current) {
            wsRef.current.close()
            wsRef.current = null
        }

        if (mediaStreamRef.current) {
            mediaStreamRef.current.getTracks().forEach(track => track.stop())
            mediaStreamRef.current = null
        }

        if (audioContextRef.current) {
            audioContextRef.current.close()
            audioContextRef.current = null
        }

        setIsConnected(false)
        audioQueueRef.current = []
    }, [stopListening])

    // Cleanup on unmount
    useEffect(() => {
        return () => {
            disconnect()
        }
    }, [disconnect])

    // Toggle mute
    const toggleMute = useCallback(() => {
        if (isListening) {
            stopListening()
        } else {
            startListening()
        }
    }, [isListening, startListening, stopListening])

    return (
        <div className="fixed inset-0 bg-black/80 backdrop-blur-sm flex items-center justify-center z-50">
            <div className="bg-gradient-to-br from-[#1a1a2e] to-[#16213e] rounded-3xl p-8 w-full max-w-md mx-4 shadow-2xl border border-purple-500/30">
                {/* Header */}
                <div className="text-center mb-8">
                    <div className="w-20 h-20 bg-gradient-to-r from-purple-500 to-indigo-600 rounded-full flex items-center justify-center mx-auto mb-4 relative">
                        <span className="text-4xl">🦉</span>
                        {isSpeaking && (
                            <div className="absolute inset-0 rounded-full border-4 border-purple-400 animate-ping opacity-30" />
                        )}
                    </div>
                    <h2 className="text-2xl font-bold text-white">Professor Sage</h2>
                    <p className="text-purple-300 text-sm">
                        {isConnected ? 'Listening...' : 'Voice Tutor'}
                    </p>
                </div>

                {/* Audio Visualizer */}
                {isConnected && (
                    <div className="flex items-center justify-center gap-1 h-16 mb-6">
                        {[...Array(12)].map((_, i) => (
                            <div
                                key={i}
                                className="w-2 bg-gradient-to-t from-purple-500 to-indigo-400 rounded-full transition-all duration-75"
                                style={{
                                    height: `${Math.max(8, audioLevel * 100 * Math.sin((i + Date.now() / 100) * 0.5) + audioLevel * 50)}px`,
                                    opacity: 0.5 + audioLevel * 0.5
                                }}
                            />
                        ))}
                    </div>
                )}

                {/* Transcripts */}
                {transcripts.length > 0 && (
                    <div className="bg-white/10 rounded-2xl p-4 mb-6 max-h-48 overflow-y-auto">
                        {transcripts.slice(-4).map((t, i) => (
                            <div key={i} className={`mb-2 ${t.role === 'user' ? 'text-right' : 'text-left'}`}>
                                <span className={`inline-block px-3 py-1.5 rounded-2xl text-sm ${t.role === 'user'
                                    ? 'bg-purple-600 text-white'
                                    : 'bg-white/20 text-white'
                                    }`}>
                                    {t.text}
                                </span>
                            </div>
                        ))}
                    </div>
                )}

                {/* Error */}
                {error && (
                    <div className="bg-red-500/20 border border-red-500/50 rounded-lg p-3 mb-6 text-center">
                        <p className="text-red-300 text-sm">{error}</p>
                    </div>
                )}

                {/* Controls */}
                <div className="flex justify-center gap-4">
                    {!isConnected ? (
                        <button
                            onClick={connect}
                            className="w-16 h-16 bg-gradient-to-r from-green-500 to-emerald-600 rounded-full 
                                       flex items-center justify-center text-white shadow-lg
                                       hover:scale-105 transition-transform active:scale-95"
                            title="Start Voice Call"
                        >
                            <Phone className="w-7 h-7" />
                        </button>
                    ) : (
                        <>
                            <button
                                onClick={toggleMute}
                                className={`w-14 h-14 rounded-full flex items-center justify-center 
                                           transition-all shadow-lg ${isListening
                                        ? 'bg-purple-600 text-white'
                                        : 'bg-gray-600 text-gray-300'
                                    }`}
                                title={isListening ? 'Mute' : 'Unmute'}
                            >
                                {isListening ? <Mic className="w-6 h-6" /> : <MicOff className="w-6 h-6" />}
                            </button>

                            <button
                                onClick={disconnect}
                                className="w-16 h-16 bg-gradient-to-r from-red-500 to-rose-600 rounded-full 
                                           flex items-center justify-center text-white shadow-lg
                                           hover:scale-105 transition-transform active:scale-95"
                                title="End Call"
                            >
                                <PhoneOff className="w-7 h-7" />
                            </button>

                            <button
                                className={`w-14 h-14 rounded-full flex items-center justify-center 
                                           transition-all shadow-lg ${isSpeaking
                                        ? 'bg-indigo-600 text-white animate-pulse'
                                        : 'bg-gray-700 text-gray-400'
                                    }`}
                                title="Speaker"
                            >
                                <Volume2 className="w-6 h-6" />
                            </button>
                        </>
                    )}
                </div>

                {/* Close button */}
                {onClose && (
                    <button
                        onClick={() => {
                            disconnect()
                            onClose()
                        }}
                        className="absolute top-4 right-4 text-white/50 hover:text-white transition-colors"
                    >
                        ✕
                    </button>
                )}

                {/* Instructions */}
                {!isConnected && (
                    <p className="text-center text-purple-300/70 text-xs mt-6">
                        Tap the green button to start a voice conversation.<br />
                        Make sure to allow microphone access.
                    </p>
                )}
            </div>
        </div>
    )
}

// Utility functions for audio conversion
function float32ToPCM16(float32Array: Float32Array): Int16Array {
    const pcm16 = new Int16Array(float32Array.length)
    for (let i = 0; i < float32Array.length; i++) {
        const s = Math.max(-1, Math.min(1, float32Array[i]))
        pcm16[i] = s < 0 ? s * 0x8000 : s * 0x7FFF
    }
    return pcm16
}

function base64ToFloat32(base64: string): Float32Array {
    const binary = atob(base64)
    const bytes = new Uint8Array(binary.length)
    for (let i = 0; i < binary.length; i++) {
        bytes[i] = binary.charCodeAt(i)
    }
    const pcm16 = new Int16Array(bytes.buffer)
    const float32 = new Float32Array(pcm16.length)
    for (let i = 0; i < pcm16.length; i++) {
        float32[i] = pcm16[i] / 0x7FFF
    }
    return float32
}

function arrayBufferToBase64(buffer: ArrayBuffer): string {
    let binary = ''
    const bytes = new Uint8Array(buffer)
    for (let i = 0; i < bytes.byteLength; i++) {
        binary += String.fromCharCode(bytes[i])
    }
    return btoa(binary)
}

export default VoiceMode
