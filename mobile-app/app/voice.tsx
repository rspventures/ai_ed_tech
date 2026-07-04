import React, { useState, useEffect, useRef } from 'react';
import {
    View,
    Text,
    TouchableOpacity,
    StyleSheet,
    SafeAreaView,
    Animated,
    Platform,
    Alert,
    ScrollView,
} from 'react-native';
import { useRouter } from 'expo-router';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { Audio, type AVPlaybackStatus } from 'expo-av';
import * as FileSystem from 'expo-file-system';
import { Ionicons } from '@expo/vector-icons';
import { WS_BASE_URL } from '../src/api/client';

// Types for Sarvam Voice Protocol
interface VoiceMessage {
    role: 'user' | 'assistant';
    text: string;
    language?: string;
}

const LANGUAGES: Record<string, string> = {
    'hi-IN': 'Hindi',
    'en-IN': 'English',
    'bn-IN': 'Bengali',
    'te-IN': 'Telugu',
    'ta-IN': 'Tamil',
    'mr-IN': 'Marathi',
    'gu-IN': 'Gujarati',
    'kn-IN': 'Kannada',
    'ml-IN': 'Malayalam',
    'pa-IN': 'Punjabi',
};

export default function VoiceScreen() {
    const router = useRouter();

    const [isConnected, setIsConnected] = useState(false);
    const [isRecording, setIsRecording] = useState(false);
    const [isSpeaking, setIsSpeaking] = useState(false);
    const [transcript, setTranscript] = useState<VoiceMessage[]>([]);
    const [detectedLanguage, setDetectedLanguage] = useState<string>('en-IN');
    const [error, setError] = useState<string | null>(null);

    // Refs
    const ws = useRef<WebSocket | null>(null);
    const recording = useRef<Audio.Recording | null>(null);
    const audioQueue = useRef<string[]>([]); // Queue of base64 audio strings or URIs
    const isPlaying = useRef(false);
    const animation = useRef(new Animated.Value(1)).current;

    useEffect(() => {
        setupAudio();
        connectWebSocket();

        return () => {
            disconnect();
        };
    }, []);

    const setupAudio = async () => {
        try {
            await Audio.requestPermissionsAsync();
            await Audio.setAudioModeAsync({
                allowsRecordingIOS: true,
                playsInSilentModeIOS: true,
                staysActiveInBackground: false,
                shouldDuckAndroid: true,
                playThroughEarpieceAndroid: false,
            });
        } catch (err) {
            setError('Audio permission denied');
            Alert.alert('Permission Denied', 'Microphone access is required for voice mode.');
        }
    };

    const connectWebSocket = async () => {
        try {
            const token = await AsyncStorage.getItem('access_token');
            if (!token) {
                setError('Not authenticated');
                return;
            }

            const WS_URL = `${WS_BASE_URL}/api/v1/voice/ws`;
            ws.current = new WebSocket(`${WS_URL}?token=${token}`);

            ws.current.onopen = () => {
                setIsConnected(true);
                setError(null);
            };

            ws.current.onmessage = (e) => {
                const message = JSON.parse(e.data);
                handleServerMessage(message);
            };

            ws.current.onerror = () => {
                setError('Connection lost');
                setIsConnected(false);
            };

            ws.current.onclose = () => {
                setIsConnected(false);
                setIsRecording(false);
            };

        } catch (err) {
            setError('Connection failed');
        }
    };

    const handleServerMessage = async (message: any) => {
        switch (message.type) {
            case 'transcript':
                if (message.language) setDetectedLanguage(message.language);

                setTranscript(prev => {
                    const last = prev[prev.length - 1];
                    if (last && last.role === message.role) {
                        return [
                            ...prev.slice(0, -1),
                            { ...last, text: last.text + message.text, language: message.language }
                        ];
                    }
                    return [...prev, { role: message.role, text: message.text, language: message.language }];
                });
                break;

            case 'audio':
                // Queue audio for playback
                if (message.data) {
                    await queueAudioChunk(message.data);
                }
                break;

            case 'response_complete':
                setIsSpeaking(false);
                break;

            case 'error':
                Alert.alert('Error', message.message);
                break;
        }
    };

    const queueAudioChunk = async (base64Data: string) => {
        // Save base64 to a temporary file
        const filename = `${FileSystem.cacheDirectory}audio_${Date.now()}.wav`;
        await FileSystem.writeAsStringAsync(filename, base64Data, {
            encoding: FileSystem.EncodingType.Base64,
        });

        audioQueue.current.push(filename);
        playQueue();
    };

    const playQueue = async () => {
        if (isPlaying.current || audioQueue.current.length === 0) return;

        isPlaying.current = true;
        setIsSpeaking(true);

        try {
            const nextFile = audioQueue.current.shift();
            if (nextFile) {
                const { sound } = await Audio.Sound.createAsync({ uri: nextFile });
                await sound.playAsync();

                sound.setOnPlaybackStatusUpdate(async (status: AVPlaybackStatus) => {
                    if (status.isLoaded && status.didJustFinish) {
                        await sound.unloadAsync();
                        await FileSystem.deleteAsync(nextFile, { idempotent: true });
                        isPlaying.current = false;
                        playQueue(); // Play next
                    }
                });
            }
        } catch (err) {
            isPlaying.current = false;
            setIsSpeaking(false);
        }
    };

    const startRecording = async () => {
        if (!isConnected) return;

        try {
            await Audio.setAudioModeAsync({
                allowsRecordingIOS: true,
                playsInSilentModeIOS: true,
            });

            const { recording: newRecording } = await Audio.Recording.createAsync(
                Audio.RecordingOptionsPresets.HIGH_QUALITY
            );

            recording.current = newRecording;
            setIsRecording(true);
            startPulseAnimation();

        } catch {
        }
    };

    const stopRecording = async () => {
        if (!recording.current) return;

        try {
            setIsRecording(false);
            stopPulseAnimation();

            await recording.current.stopAndUnloadAsync();
            const uri = recording.current.getURI();

            if (uri) {
                // Read file and send to backend
                const base64Audio = await FileSystem.readAsStringAsync(uri, {
                    encoding: FileSystem.EncodingType.Base64,
                });

                if (ws.current?.readyState === WebSocket.OPEN) {
                    ws.current.send(JSON.stringify({
                        type: 'audio',
                        data: base64Audio
                    }));

                    ws.current.send(JSON.stringify({
                        type: 'commit'
                    }));
                }
            }

            recording.current = null;

        } catch {
        }
    };

    const startPulseAnimation = () => {
        Animated.loop(
            Animated.sequence([
                Animated.timing(animation, {
                    toValue: 1.2,
                    duration: 1000,
                    useNativeDriver: true,
                }),
                Animated.timing(animation, {
                    toValue: 1,
                    duration: 1000,
                    useNativeDriver: true,
                }),
            ])
        ).start();
    };

    const stopPulseAnimation = () => {
        animation.stopAnimation();
        animation.setValue(1);
    };

    const disconnect = async () => {
        if (ws.current) ws.current.close();
        if (recording.current) await recording.current.stopAndUnloadAsync();
    };

    return (
        <SafeAreaView style={styles.container}>
            {/* Header */}
            <View style={styles.header}>
                <TouchableOpacity onPress={() => router.back()} style={styles.backButton}>
                    <Text style={styles.backButtonText}>✕</Text>
                </TouchableOpacity>
                <View style={styles.headerTitleContainer}>
                    <Text style={styles.headerTitle}>Professor Sage</Text>
                    <View style={styles.statusContainer}>
                        <View style={[styles.statusDot, { backgroundColor: isConnected ? '#10b981' : '#ef4444' }]} />
                        <Text style={styles.statusText}>
                            {isConnected ? (isSpeaking ? 'Speaking...' : 'Listening') : 'Connecting...'}
                        </Text>
                    </View>
                </View>
            </View>

            {/* Content */}
            <View style={styles.content}>
                <View style={styles.avatarContainer}>
                    <Animated.View style={[styles.avatarCircle, { transform: [{ scale: animation }] }]}>
                        <Text style={styles.avatarEmoji}>🦉</Text>
                    </Animated.View>

                    {detectedLanguage !== 'en-IN' && (
                        <View style={styles.languageBadge}>
                            <Text style={styles.languageText}>
                                {LANGUAGES[detectedLanguage] || 'Detected'}
                            </Text>
                        </View>
                    )}
                </View>

                {/* Transcripts */}
                <ScrollView
                    style={styles.transcriptContainer}
                    contentContainerStyle={styles.transcriptContent}
                    showsVerticalScrollIndicator={false}
                >
                    {error && (
                        <Text style={styles.errorText}>{error}</Text>
                    )}
                    {transcript.length === 0 && !error && (
                        <Text style={styles.placeholderText}>
                            Tap and hold the mic to speak in any Indian language! 🇮🇳
                        </Text>
                    )}

                    {transcript.slice(-4).map((msg, idx) => (
                        <View key={idx} style={[
                            styles.messageBubble,
                            msg.role === 'user' ? styles.userBubble : styles.assistantBubble
                        ]}>
                            <Text style={[
                                styles.messageText,
                                msg.role === 'user' ? styles.userText : styles.assistantText
                            ]}>
                                {msg.text}
                            </Text>
                        </View>
                    ))}
                </ScrollView>
            </View>

            {/* Controls */}
            <View style={styles.controls}>
                <TouchableOpacity
                    style={[styles.micButton, isRecording && styles.micButtonActive]}
                    onPressIn={startRecording}
                    onPressOut={stopRecording}
                    disabled={!isConnected}
                >
                    <Ionicons
                        name={isRecording ? "mic" : "mic-outline"}
                        size={32}
                        color="white"
                    />
                </TouchableOpacity>
                <Text style={styles.hintText}>Hold to speak</Text>
            </View>
        </SafeAreaView>
    );
}

const styles = StyleSheet.create({
    container: {
        flex: 1,
        backgroundColor: '#1a1a2e',
    },
    header: {
        flexDirection: 'row',
        alignItems: 'center',
        padding: 16,
        paddingTop: Platform.OS === 'android' ? 40 : 16,
    },
    backButton: {
        width: 40,
        height: 40,
        justifyContent: 'center',
        alignItems: 'center',
        backgroundColor: 'rgba(255,255,255,0.1)',
        borderRadius: 20,
    },
    backButtonText: {
        color: 'white',
        fontSize: 20,
        fontWeight: 'bold',
    },
    headerTitleContainer: {
        marginLeft: 16,
    },
    headerTitle: {
        color: 'white',
        fontSize: 18,
        fontWeight: 'bold',
    },
    statusContainer: {
        flexDirection: 'row',
        alignItems: 'center',
        marginTop: 4,
    },
    statusDot: {
        width: 6,
        height: 6,
        borderRadius: 3,
        marginRight: 6,
    },
    statusText: {
        color: '#a0a0b0',
        fontSize: 12,
    },
    content: {
        flex: 1,
        alignItems: 'center',
        paddingTop: 40,
    },
    avatarContainer: {
        alignItems: 'center',
        marginBottom: 40,
    },
    avatarCircle: {
        width: 120,
        height: 120,
        borderRadius: 60,
        backgroundColor: 'rgba(124, 58, 237, 0.2)',
        justifyContent: 'center',
        alignItems: 'center',
        borderWidth: 2,
        borderColor: '#7c3aed',
    },
    avatarEmoji: {
        fontSize: 60,
    },
    languageBadge: {
        marginTop: 16,
        paddingHorizontal: 12,
        paddingVertical: 6,
        backgroundColor: 'rgba(124, 58, 237, 0.3)',
        borderRadius: 20,
    },
    languageText: {
        color: '#e9d5ff',
        fontSize: 12,
        fontWeight: '600',
    },
    transcriptContainer: {
        flex: 1,
        width: '100%',
        paddingHorizontal: 20,
    },
    transcriptContent: {
        paddingBottom: 20,
    },
    errorText: {
        color: '#ef4444',
        textAlign: 'center',
        marginTop: 40,
        fontSize: 14,
    },
    placeholderText: {
        color: 'rgba(255,255,255,0.3)',
        textAlign: 'center',
        marginTop: 40,
        fontSize: 16,
    },
    messageBubble: {
        padding: 12,
        borderRadius: 16,
        marginBottom: 12,
        maxWidth: '85%',
    },
    userBubble: {
        backgroundColor: '#7c3aed',
        alignSelf: 'flex-end',
        borderBottomRightRadius: 4,
    },
    assistantBubble: {
        backgroundColor: 'rgba(255,255,255,0.1)',
        alignSelf: 'flex-start',
        borderBottomLeftRadius: 4,
    },
    messageText: {
        fontSize: 16,
        lineHeight: 22,
    },
    userText: {
        color: 'white',
    },
    assistantText: {
        color: '#e9d5ff',
    },
    controls: {
        padding: 30,
        alignItems: 'center',
        paddingBottom: 50,
    },
    micButton: {
        width: 80,
        height: 80,
        borderRadius: 40,
        backgroundColor: '#7c3aed',
        justifyContent: 'center',
        alignItems: 'center',
        shadowColor: '#7c3aed',
        shadowOffset: { width: 0, height: 0 },
        shadowOpacity: 0.5,
        shadowRadius: 20,
        elevation: 10,
    },
    micButtonActive: {
        backgroundColor: '#ef4444',
        shadowColor: '#ef4444',
        transform: [{ scale: 1.1 }],
    },
    hintText: {
        color: '#a0a0b0',
        marginTop: 16,
        fontSize: 14,
    },
});
