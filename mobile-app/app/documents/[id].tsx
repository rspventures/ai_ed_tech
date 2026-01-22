import React, { useState, useRef } from 'react';
import {
    View,
    Text,
    StyleSheet,
    SafeAreaView,
    TextInput,
    TouchableOpacity,
    FlatList,
    KeyboardAvoidingView,
    Platform,
    ActivityIndicator,
    Modal,
    ScrollView,
    Alert,
} from 'react-native';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { documentService, QuizQuestion } from '../../src/services/documents';

interface Message {
    id: string;
    text: string;
    isUser: boolean;
    sources?: any[];
}

export default function DocumentChatScreen() {
    const { id } = useLocalSearchParams();
    const router = useRouter();

    // Chat State
    const [messages, setMessages] = useState<Message[]>([
        { id: '1', text: 'Hello! Ask me anything about this document.', isUser: false }
    ]);
    const [inputText, setInputText] = useState('');
    const [loading, setLoading] = useState(false);
    const flatListRef = useRef<FlatList>(null);

    // Quiz State
    const [showQuiz, setShowQuiz] = useState(false);
    const [quizLoading, setQuizLoading] = useState(false);
    const [quizQuestions, setQuizQuestions] = useState<QuizQuestion[]>([]);
    const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0);
    const [selectedAnswers, setSelectedAnswers] = useState<Record<number, string>>({});
    const [showResults, setShowResults] = useState(false);

    const handleSend = async () => {
        if (!inputText.trim()) return;

        const userMsg: Message = {
            id: Date.now().toString(),
            text: inputText,
            isUser: true,
        };

        setMessages(prev => [...prev, userMsg]);
        setInputText('');
        setLoading(true);

        try {
            const response = await documentService.chatWithDocument(id as string, userMsg.text);

            const aiMsg: Message = {
                id: (Date.now() + 1).toString(),
                text: response.answer,
                isUser: false,
                sources: response.sources
            };

            setMessages(prev => [...prev, aiMsg]);
        } catch (error) {
            const errorMsg: Message = {
                id: (Date.now() + 1).toString(),
                text: "Sorry, I couldn't process that request.",
                isUser: false
            };
            setMessages(prev => [...prev, errorMsg]);
        } finally {
            setLoading(false);
        }
    };

    const handleGenerateQuiz = async () => {
        setQuizLoading(true);
        setShowQuiz(true);
        setQuizQuestions([]);
        setSelectedAnswers({});
        setShowResults(false);
        setCurrentQuestionIndex(0);

        try {
            const response = await documentService.generateQuiz(id as string, 5, 5);
            setQuizQuestions(response.questions || []);
        } catch (error) {
            console.error('Quiz generation failed:', error);
            Alert.alert('Error', 'Failed to generate quiz. Please try again.');
            setShowQuiz(false);
        } finally {
            setQuizLoading(false);
        }
    };

    const handleAnswerSelect = (answer: string) => {
        if (showResults) return;
        setSelectedAnswers(prev => ({
            ...prev,
            [currentQuestionIndex]: answer
        }));
    };

    const calculateScore = () => {
        let correct = 0;
        quizQuestions.forEach((q, idx) => {
            if (selectedAnswers[idx] === q.correct_answer) {
                correct++;
            }
        });
        return correct;
    };

    const renderQuizContent = () => {
        if (quizLoading) {
            return (
                <View style={styles.loadingContainer}>
                    <ActivityIndicator size="large" color="#007AFF" />
                    <Text style={styles.loadingText}>Generating your quiz...</Text>
                    <Text style={styles.loadingSubText}>Reading document for full coverage</Text>
                </View>
            );
        }

        if (quizQuestions.length === 0) {
            return (
                <View style={styles.emptyContainer}>
                    <Text style={styles.emptyText}>No questions generated.</Text>
                    <TouchableOpacity onPress={() => setShowQuiz(false)} style={styles.closeButton}>
                        <Text style={styles.closeButtonText}>Close</Text>
                    </TouchableOpacity>
                </View>
            );
        }

        if (showResults) {
            const score = calculateScore();
            const percentage = Math.round((score / quizQuestions.length) * 100);

            return (
                <ScrollView contentContainerStyle={styles.resultsContainer}>
                    <View style={styles.scoreCard}>
                        <Text style={styles.scoreTitle}>Quiz Complete!</Text>
                        <Text style={styles.scoreValue}>{percentage}%</Text>
                        <Text style={styles.scoreSubtitle}>{score} out of {quizQuestions.length} correct</Text>
                    </View>

                    <Text style={styles.sectionTitle}>Review</Text>
                    {quizQuestions.map((q, idx) => (
                        <View key={idx} style={styles.reviewItem}>
                            <View style={styles.reviewHeader}>
                                <View style={[styles.statusBadge, selectedAnswers[idx] === q.correct_answer ? styles.successBadge : styles.errorBadge]}>
                                    <Text style={styles.statusText}>{selectedAnswers[idx] === q.correct_answer ? '✓' : '✗'}</Text>
                                </View>
                                <Text style={styles.reviewQuestion}>{q.question}</Text>
                            </View>
                            <Text style={styles.correctAnswerText}>Correct: {q.correct_answer}</Text>
                        </View>
                    ))}

                    <View style={styles.resultActions}>
                        <TouchableOpacity
                            style={styles.actionButtonOutline}
                            onPress={() => {
                                setShowQuiz(false);
                                setShowResults(false);
                            }}
                        >
                            <Text style={styles.actionButtonTextOutline}>Close</Text>
                        </TouchableOpacity>
                        <TouchableOpacity
                            style={styles.actionButton}
                            onPress={handleGenerateQuiz}
                        >
                            <Text style={styles.actionButtonText}>New Quiz</Text>
                        </TouchableOpacity>
                    </View>
                </ScrollView>
            );
        }

        const currentQuestion = quizQuestions[currentQuestionIndex];
        const hasAnswered = !!selectedAnswers[currentQuestionIndex];
        const isCorrect = selectedAnswers[currentQuestionIndex] === currentQuestion.correct_answer;

        return (
            <View style={styles.quizContent}>
                {/* Progress */}
                <View style={styles.progressContainer}>
                    <Text style={styles.progressText}>Question {currentQuestionIndex + 1} of {quizQuestions.length}</Text>
                    <View style={styles.progressBarBg}>
                        <View style={[styles.progressBarFill, { width: `${((currentQuestionIndex + 1) / quizQuestions.length) * 100}%` }]} />
                    </View>
                </View>

                <ScrollView style={styles.questionContainer}>
                    <Text style={styles.questionText}>{currentQuestion.question}</Text>

                    <View style={styles.optionsContainer}>
                        {currentQuestion.options.map((option, idx) => {
                            const isSelected = selectedAnswers[currentQuestionIndex] === option;
                            let optionStyle = styles.optionButton;
                            let textStyle = styles.optionText;

                            if (hasAnswered) {
                                if (option === currentQuestion.correct_answer) {
                                    optionStyle = styles.optionCorrect;
                                    textStyle = styles.optionTextSelected;
                                } else if (isSelected) {
                                    optionStyle = styles.optionWrong;
                                    textStyle = styles.optionTextSelected;
                                }
                            } else if (isSelected) {
                                optionStyle = styles.optionSelected;
                                textStyle = styles.optionTextSelected;
                            }

                            return (
                                <TouchableOpacity
                                    key={idx}
                                    style={optionStyle}
                                    onPress={() => handleAnswerSelect(option)}
                                    disabled={hasAnswered}
                                >
                                    <Text style={styles.optionLetter}>{String.fromCharCode(65 + idx)}</Text>
                                    <Text style={textStyle}>{option}</Text>
                                    {hasAnswered && option === currentQuestion.correct_answer && <Text style={styles.checkMark}>✓</Text>}
                                    {hasAnswered && isSelected && option !== currentQuestion.correct_answer && <Text style={styles.crossMark}>✗</Text>}
                                </TouchableOpacity>
                            );
                        })}
                    </View>

                    {hasAnswered && (
                        <View style={[styles.feedbackContainer, isCorrect ? styles.feedbackSuccess : styles.feedbackError]}>
                            <Text style={[styles.feedbackTitle, isCorrect ? styles.textSuccess : styles.textError]}>
                                {isCorrect ? 'Correct!' : 'Incorrect'}
                            </Text>
                            <Text style={styles.explanationText}>
                                <Text style={{ fontWeight: 'bold' }}>Explanation: </Text>
                                {currentQuestion.explanation}
                            </Text>
                        </View>
                    )}
                </ScrollView>

                <View style={styles.quizFooter}>
                    {currentQuestionIndex > 0 ? (
                        <TouchableOpacity
                            style={styles.navButtonOutline}
                            onPress={() => setCurrentQuestionIndex(prev => prev - 1)}
                        >
                            <Text style={styles.navButtonTextOutline}>Previous</Text>
                        </TouchableOpacity>
                    ) : <View style={{ flex: 1 }} />}

                    <View style={{ width: 16 }} />

                    {currentQuestionIndex < quizQuestions.length - 1 ? (
                        <TouchableOpacity
                            style={[styles.navButton, !hasAnswered && styles.navButtonDisabled]}
                            onPress={() => setCurrentQuestionIndex(prev => prev + 1)}
                            disabled={!hasAnswered}
                        >
                            <Text style={styles.navButtonText}>Next</Text>
                        </TouchableOpacity>
                    ) : (
                        <TouchableOpacity
                            style={[styles.navButton, !hasAnswered && styles.navButtonDisabled]}
                            onPress={() => setShowResults(true)}
                            disabled={!hasAnswered}
                        >
                            <Text style={styles.navButtonText}>Finish</Text>
                        </TouchableOpacity>
                    )}
                </View>
            </View>
        );
    };

    return (
        <SafeAreaView style={styles.safeArea}>
            <View style={styles.header}>
                <TouchableOpacity onPress={() => router.back()} style={styles.backBtn}>
                    <Text style={styles.backIcon}>←</Text>
                </TouchableOpacity>
                <Text style={styles.headerTitle}>Document Chat</Text>
                <TouchableOpacity
                    style={styles.quizBtn}
                    onPress={handleGenerateQuiz}
                >
                    <Text style={styles.quizBtnText}>Quiz</Text>
                </TouchableOpacity>
            </View>

            <FlatList
                ref={flatListRef}
                data={messages}
                keyExtractor={item => item.id}
                contentContainerStyle={styles.messageList}
                onContentSizeChange={() => flatListRef.current?.scrollToEnd({ animated: true })}
                renderItem={({ item }) => (
                    <View style={[
                        styles.messageBubble,
                        item.isUser ? styles.userBubble : styles.aiBubble
                    ]}>
                        <Text style={[
                            styles.messageText,
                            item.isUser ? styles.userText : styles.aiText
                        ]}>{item.text}</Text>

                        {item.sources && item.sources.length > 0 && (
                            <View style={styles.sourceContainer}>
                                <Text style={styles.sourceLabel}>Sources found</Text>
                            </View>
                        )}
                    </View>
                )}
            />

            <KeyboardAvoidingView
                behavior={Platform.OS === 'ios' ? 'padding' : undefined}
                keyboardVerticalOffset={Platform.OS === 'ios' ? 90 : 0}
            >
                <View style={styles.inputContainer}>
                    <TextInput
                        style={styles.input}
                        value={inputText}
                        onChangeText={setInputText}
                        placeholder="Ask a question..."
                        placeholderTextColor="#999"
                        multiline
                    />
                    <TouchableOpacity
                        style={[styles.sendBtn, !inputText.trim() && styles.sendBtnDisabled]}
                        onPress={handleSend}
                        disabled={!inputText.trim() || loading}
                    >
                        {loading ? (
                            <ActivityIndicator color="#fff" size="small" />
                        ) : (
                            <Text style={styles.sendIcon}>↑</Text>
                        )}
                    </TouchableOpacity>
                </View>
            </KeyboardAvoidingView>

            <Modal
                visible={showQuiz}
                animationType="slide"
                presentationStyle="pageSheet"
            >
                <SafeAreaView style={styles.quizContainer}>
                    <View style={styles.quizHeader}>
                        <Text style={styles.quizTitle}>Quiz Mode</Text>
                        <TouchableOpacity onPress={() => setShowQuiz(false)} style={styles.closeIconBtn}>
                            <Text style={styles.closeIcon}>✕</Text>
                        </TouchableOpacity>
                    </View>
                    {renderQuizContent()}
                </SafeAreaView>
            </Modal>
        </SafeAreaView>
    );
}

const styles = StyleSheet.create({
    safeArea: {
        flex: 1,
        backgroundColor: '#fff',
    },
    header: {
        flexDirection: 'row',
        alignItems: 'center',
        justifyContent: 'space-between',
        padding: 16,
        borderBottomWidth: 1,
        borderBottomColor: '#f0f0f0',
    },
    backBtn: {
        padding: 8,
    },
    backIcon: {
        fontSize: 24,
        color: '#007AFF',
    },
    headerTitle: {
        fontSize: 18,
        fontWeight: 'bold',
        color: '#1a1a2e',
    },
    quizBtn: {
        backgroundColor: '#f0f0f0',
        paddingHorizontal: 12,
        paddingVertical: 6,
        borderRadius: 16,
    },
    quizBtnText: {
        color: '#007AFF',
        fontWeight: '600',
    },
    messageList: {
        padding: 16,
        paddingBottom: 24,
    },
    messageBubble: {
        maxWidth: '80%',
        padding: 12,
        borderRadius: 16,
        marginBottom: 12,
    },
    userBubble: {
        backgroundColor: '#007AFF',
        alignSelf: 'flex-end',
        borderBottomRightRadius: 4,
    },
    aiBubble: {
        backgroundColor: '#f0f2f5',
        alignSelf: 'flex-start',
        borderBottomLeftRadius: 4,
    },
    messageText: {
        fontSize: 16,
        lineHeight: 22,
    },
    userText: {
        color: '#fff',
    },
    aiText: {
        color: '#333',
    },
    sourceContainer: {
        marginTop: 8,
        paddingTop: 8,
        borderTopWidth: 1,
        borderTopColor: 'rgba(0,0,0,0.05)',
    },
    sourceLabel: {
        fontSize: 12,
        color: '#666',
        fontStyle: 'italic',
    },
    inputContainer: {
        flexDirection: 'row',
        padding: 16,
        borderTopWidth: 1,
        borderTopColor: '#f0f0f0',
        alignItems: 'flex-end',
        backgroundColor: '#fff',
    },
    input: {
        flex: 1,
        backgroundColor: '#f5f7fa',
        borderRadius: 20,
        paddingHorizontal: 16,
        paddingVertical: 10,
        minHeight: 40,
        maxHeight: 100,
        fontSize: 16,
        marginRight: 12,
    },
    sendBtn: {
        width: 40,
        height: 40,
        borderRadius: 20,
        backgroundColor: '#007AFF',
        justifyContent: 'center',
        alignItems: 'center',
    },
    sendBtnDisabled: {
        backgroundColor: '#ccc',
    },
    sendIcon: {
        color: '#fff',
        fontSize: 20,
        fontWeight: 'bold',
    },
    // Quiz Styles
    quizContainer: {
        flex: 1,
        backgroundColor: '#fff',
    },
    quizHeader: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
        padding: 16,
        borderBottomWidth: 1,
        borderBottomColor: '#f0f0f0',
    },
    quizTitle: {
        fontSize: 18,
        fontWeight: 'bold',
        color: '#1a1a2e',
    },
    closeIconBtn: {
        padding: 4,
    },
    closeIcon: {
        fontSize: 20,
        color: '#999',
    },
    loadingContainer: {
        flex: 1,
        justifyContent: 'center',
        alignItems: 'center',
    },
    loadingText: {
        marginTop: 16,
        fontSize: 16,
        color: '#666',
        fontWeight: '500',
    },
    loadingSubText: {
        marginTop: 8,
        fontSize: 14,
        color: '#999',
    },
    emptyContainer: {
        flex: 1,
        justifyContent: 'center',
        alignItems: 'center',
        padding: 24,
    },
    emptyText: {
        fontSize: 16,
        color: '#666',
        marginBottom: 16,
    },
    closeButton: {
        paddingVertical: 10,
        paddingHorizontal: 20,
        backgroundColor: '#f0f0f0',
        borderRadius: 8,
    },
    closeButtonText: {
        color: '#333',
        fontWeight: '500',
    },
    quizContent: {
        flex: 1,
        padding: 16,
    },
    progressContainer: {
        marginBottom: 20,
    },
    progressText: {
        fontSize: 14,
        color: '#666',
        marginBottom: 8,
    },
    progressBarBg: {
        height: 6,
        backgroundColor: '#f0f0f0',
        borderRadius: 3,
    },
    progressBarFill: {
        height: 6,
        backgroundColor: '#007AFF',
        borderRadius: 3,
    },
    questionContainer: {
        flex: 1,
    },
    questionText: {
        fontSize: 18,
        fontWeight: '600',
        color: '#1a1a2e',
        marginBottom: 24,
        lineHeight: 26,
    },
    optionsContainer: {
        gap: 12,
    },
    optionButton: {
        flexDirection: 'row',
        alignItems: 'center',
        padding: 16,
        backgroundColor: '#fff',
        borderWidth: 1,
        borderColor: '#e1e1e1',
        borderRadius: 12,
        marginBottom: 12,
    },
    optionSelected: {
        backgroundColor: '#f0f7ff',
        borderColor: '#007AFF',
        borderWidth: 2,
    },
    optionCorrect: {
        backgroundColor: '#f0fdf4',
        borderColor: '#22c55e',
        borderWidth: 2,
    },
    optionWrong: {
        backgroundColor: '#fef2f2',
        borderColor: '#ef4444',
        borderWidth: 2,
    },
    optionLetter: {
        width: 24,
        height: 24,
        borderRadius: 12,
        backgroundColor: '#f0f0f0',
        textAlign: 'center',
        lineHeight: 24,
        fontSize: 14,
        fontWeight: '600',
        marginRight: 12,
        color: '#666',
        overflow: 'hidden',
    },
    optionText: {
        fontSize: 16,
        color: '#333',
        flex: 1,
    },
    optionTextSelected: {
        fontWeight: '500',
        color: '#000',
    },
    checkMark: {
        marginLeft: 8,
        color: '#22c55e',
        fontSize: 16,
        fontWeight: 'bold',
    },
    crossMark: {
        marginLeft: 8,
        color: '#ef4444',
        fontSize: 16,
        fontWeight: 'bold',
    },
    feedbackContainer: {
        marginTop: 24,
        padding: 16,
        borderRadius: 12,
        borderWidth: 1,
    },
    feedbackSuccess: {
        backgroundColor: '#f0fdf4',
        borderColor: '#bbf7d0',
    },
    feedbackError: {
        backgroundColor: '#fef2f2',
        borderColor: '#fecaca',
    },
    feedbackTitle: {
        fontSize: 16,
        fontWeight: 'bold',
        marginBottom: 8,
    },
    textSuccess: { color: '#16a34a' },
    textError: { color: '#dc2626' },
    explanationText: {
        fontSize: 14,
        color: '#4b5563',
        lineHeight: 20,
    },
    quizFooter: {
        flexDirection: 'row',
        paddingTop: 16,
        paddingBottom: Platform.OS === 'ios' ? 0 : 16,
    },
    navButton: {
        flex: 1,
        backgroundColor: '#007AFF',
        padding: 16,
        borderRadius: 12,
        alignItems: 'center',
    },
    navButtonDisabled: {
        backgroundColor: '#ccc',
        opacity: 0.7,
    },
    navButtonText: {
        color: '#fff',
        fontWeight: '600',
        fontSize: 16,
    },
    navButtonOutline: {
        flex: 1,
        backgroundColor: 'transparent',
        padding: 16,
        borderRadius: 12,
        alignItems: 'center',
        borderWidth: 1,
        borderColor: '#e1e1e1',
    },
    navButtonTextOutline: {
        color: '#666',
        fontWeight: '600',
        fontSize: 16,
    },
    // Results
    resultsContainer: {
        padding: 20,
    },
    scoreCard: {
        alignItems: 'center',
        padding: 24,
        backgroundColor: '#007AFF',
        borderRadius: 20,
        marginBottom: 24,
    },
    scoreTitle: {
        color: 'rgba(255,255,255,0.8)',
        fontSize: 16,
        marginBottom: 8,
    },
    scoreValue: {
        color: '#fff',
        fontSize: 48,
        fontWeight: 'bold',
        marginBottom: 8,
    },
    scoreSubtitle: {
        color: 'rgba(255,255,255,0.9)',
        fontSize: 14,
    },
    sectionTitle: {
        fontSize: 18,
        fontWeight: 'bold',
        marginBottom: 16,
        color: '#1a1a2e',
    },
    reviewItem: {
        padding: 16,
        backgroundColor: '#f9fafb',
        borderRadius: 12,
        marginBottom: 12,
        borderWidth: 1,
        borderColor: '#e5e7eb',
    },
    reviewHeader: {
        flexDirection: 'row',
        gap: 12,
    },
    statusBadge: {
        width: 24,
        height: 24,
        borderRadius: 12,
        justifyContent: 'center',
        alignItems: 'center',
    },
    successBadge: { backgroundColor: '#dcfce7' },
    errorBadge: { backgroundColor: '#fee2e2' },
    statusText: { fontSize: 14, fontWeight: 'bold' },
    reviewQuestion: {
        flex: 1,
        fontSize: 14,
        color: '#374151',
        lineHeight: 20,
    },
    correctAnswerText: {
        marginTop: 8,
        fontSize: 12,
        color: '#6b7280',
        marginLeft: 36,
    },
    resultActions: {
        flexDirection: 'row',
        gap: 16,
        marginTop: 24,
        marginBottom: 40,
    },
    actionButton: {
        flex: 1,
        backgroundColor: '#007AFF',
        padding: 16,
        borderRadius: 12,
        alignItems: 'center',
    },
    actionButtonOutline: {
        flex: 1,
        backgroundColor: '#fff',
        padding: 16,
        borderRadius: 12,
        alignItems: 'center',
        borderWidth: 1,
        borderColor: '#e1e1e1',
    },
    actionButtonText: {
        color: '#fff',
        fontWeight: '600',
        fontSize: 16,
    },
    actionButtonTextOutline: {
        color: '#333',
        fontWeight: '600',
        fontSize: 16,
    },
});
