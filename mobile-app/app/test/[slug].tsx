/**
 * AI Tutor Platform - Test Screen
 * Topic-level test with 10 questions from subtopics
 */
import React, { useEffect, useState, useRef } from 'react';
import {
    View,
    Text,
    TouchableOpacity,
    StyleSheet,
    SafeAreaView,
    ScrollView,
    ActivityIndicator,
    Alert,
    Dimensions,
} from 'react-native';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { testService, TestQuestion, TestAnswerItem, TestResult } from '../../src/services/test';
import { curriculumService } from '../../src/services/curriculum';

const { width } = Dimensions.get('window');

type TestState = 'loading' | 'ready' | 'in_progress' | 'submitting' | 'results';

export default function TestScreen() {
    const router = useRouter();
    const { slug } = useLocalSearchParams<{ slug: string }>();

    // Test state
    const [state, setState] = useState<TestState>('loading');
    const [topic, setTopic] = useState<{ id: string; name: string } | null>(null);
    const [testId, setTestId] = useState<string>('');
    const [questions, setQuestions] = useState<TestQuestion[]>([]);
    const [currentIndex, setCurrentIndex] = useState(0);
    const [answers, setAnswers] = useState<Record<string, { answer: string; correctAnswer: string }>>({});
    const [result, setResult] = useState<TestResult | null>(null);

    // Timer
    const [timeRemaining, setTimeRemaining] = useState<number>(600); // 10 minutes default
    const [startTime, setStartTime] = useState<number>(0);
    const timerRef = useRef<NodeJS.Timeout | null>(null);

    useEffect(() => {
        if (slug) {
            loadTopic();
        }
        return () => {
            if (timerRef.current) clearInterval(timerRef.current);
        };
    }, [slug]);

    const loadTopic = async () => {
        try {
            setState('loading');
            const topicData = await curriculumService.getTopic(slug!);
            setTopic({ id: topicData.id, name: topicData.name });
            setState('ready');
        } catch (err) {
            console.log('Failed to load topic:', err);
            Alert.alert('Error', 'Failed to load topic');
            router.back();
        }
    };

    const startTest = async () => {
        if (!topic) return;

        try {
            setState('loading');
            const response = await testService.startTest(topic.id, 10);

            setTestId(response.test_id);
            setQuestions(shuffleArray(response.questions));
            setTimeRemaining(response.time_limit_seconds || 600);
            setStartTime(Date.now());
            setCurrentIndex(0);
            setAnswers({});
            setState('in_progress');

            // Start timer
            timerRef.current = setInterval(() => {
                setTimeRemaining(prev => {
                    if (prev <= 1) {
                        submitTest(true);
                        return 0;
                    }
                    return prev - 1;
                });
            }, 1000);
        } catch (err) {
            console.log('Failed to start test:', err);
            Alert.alert('Error', 'Failed to start test. Please try again.');
            setState('ready');
        }
    };

    const shuffleArray = <T,>(array: T[]): T[] => {
        const shuffled = [...array];
        for (let i = shuffled.length - 1; i > 0; i--) {
            const j = Math.floor(Math.random() * (i + 1));
            [shuffled[i], shuffled[j]] = [shuffled[j], shuffled[i]];
        }
        return shuffled;
    };

    const selectAnswer = (questionId: string, answer: string, correctAnswer: string) => {
        setAnswers(prev => ({
            ...prev,
            [questionId]: { answer, correctAnswer }
        }));
    };

    const goToQuestion = (index: number) => {
        if (index >= 0 && index < questions.length) {
            setCurrentIndex(index);
        }
    };

    const submitTest = async (autoSubmit = false) => {
        if (!autoSubmit) {
            const unanswered = questions.length - Object.keys(answers).length;
            if (unanswered > 0) {
                Alert.alert(
                    'Confirm Submit',
                    `You have ${unanswered} unanswered question(s). Submit anyway?`,
                    [
                        { text: 'Cancel', style: 'cancel' },
                        { text: 'Submit', onPress: () => performSubmit() }
                    ]
                );
                return;
            }
        }
        performSubmit();
    };

    const performSubmit = async () => {
        if (timerRef.current) clearInterval(timerRef.current);
        setState('submitting');

        try {
            const duration = Math.round((Date.now() - startTime) / 1000);
            const answerItems: TestAnswerItem[] = questions.map(q => ({
                question_id: q.question_id,
                question: q.question,
                answer: answers[q.question_id]?.answer || '',
                correct_answer: answers[q.question_id]?.correctAnswer || q.options[0],
                subtopic_id: q.subtopic_id,
            }));

            const testResult = await testService.submitTest(
                testId,
                topic!.id,
                topic!.name,
                answerItems,
                duration
            );

            setResult(testResult);
            setState('results');
        } catch (err) {
            console.log('Failed to submit test:', err);
            Alert.alert('Error', 'Failed to submit test. Please try again.');
            setState('in_progress');
        }
    };

    const formatTime = (seconds: number): string => {
        const mins = Math.floor(seconds / 60);
        const secs = seconds % 60;
        return `${mins}:${secs.toString().padStart(2, '0')}`;
    };

    const getScoreColor = (score: number): string => {
        if (score >= 80) return '#10B981';
        if (score >= 60) return '#F59E0B';
        return '#EF4444';
    };

    // Loading state
    if (state === 'loading' || state === 'submitting') {
        return (
            <SafeAreaView style={styles.safeArea}>
                <View style={styles.centerContainer}>
                    <ActivityIndicator size="large" color="#007AFF" />
                    <Text style={styles.loadingText}>
                        {state === 'loading' ? 'Preparing Test...' : 'Submitting...'}
                    </Text>
                </View>
            </SafeAreaView>
        );
    }

    // Ready to start
    if (state === 'ready') {
        return (
            <SafeAreaView style={styles.safeArea}>
                <View style={styles.header}>
                    <TouchableOpacity onPress={() => router.back()} style={styles.backBtn}>
                        <Text style={styles.backIcon}>←</Text>
                    </TouchableOpacity>
                    <Text style={styles.headerTitle}>Topic Test</Text>
                    <View style={{ width: 40 }} />
                </View>

                <View style={styles.startContainer}>
                    <View style={styles.startCard}>
                        <Text style={styles.startIcon}>📝</Text>
                        <Text style={styles.startTitle}>{topic?.name}</Text>
                        <Text style={styles.startSubtitle}>Topic Test</Text>

                        <View style={styles.infoRow}>
                            <View style={styles.infoItem}>
                                <Text style={styles.infoValue}>10</Text>
                                <Text style={styles.infoLabel}>Questions</Text>
                            </View>
                            <View style={styles.infoDivider} />
                            <View style={styles.infoItem}>
                                <Text style={styles.infoValue}>10</Text>
                                <Text style={styles.infoLabel}>Minutes</Text>
                            </View>
                        </View>

                        <TouchableOpacity style={styles.startButton} onPress={startTest}>
                            <Text style={styles.startButtonText}>Start Test</Text>
                        </TouchableOpacity>
                    </View>
                </View>
            </SafeAreaView>
        );
    }

    // Results
    if (state === 'results' && result) {
        const scorePercent = Math.round((result.correct_questions / result.total_questions) * 100);

        return (
            <SafeAreaView style={styles.safeArea}>
                <ScrollView style={styles.scrollView}>
                    <View style={styles.resultsContainer}>
                        <View style={[styles.scoreCard, { borderColor: getScoreColor(scorePercent) }]}>
                            <Text style={styles.scoreEmoji}>
                                {scorePercent >= 80 ? '🎉' : scorePercent >= 60 ? '👍' : '💪'}
                            </Text>
                            <Text style={[styles.scorePercent, { color: getScoreColor(scorePercent) }]}>
                                {scorePercent}%
                            </Text>
                            <Text style={styles.scoreDetails}>
                                {result.correct_questions} of {result.total_questions} correct
                            </Text>
                        </View>

                        {result.feedback && (
                            <View style={styles.feedbackCard}>
                                <Text style={styles.feedbackTitle}>Feedback</Text>
                                <Text style={styles.feedbackText}>{result.feedback.summary}</Text>

                                {result.feedback.strengths.length > 0 && (
                                    <View style={styles.feedbackSection}>
                                        <Text style={styles.feedbackSectionTitle}>✅ Strengths</Text>
                                        {result.feedback.strengths.map((s, i) => (
                                            <Text key={i} style={styles.feedbackItem}>• {s}</Text>
                                        ))}
                                    </View>
                                )}

                                {result.feedback.recommendations.length > 0 && (
                                    <View style={styles.feedbackSection}>
                                        <Text style={styles.feedbackSectionTitle}>📚 Recommendations</Text>
                                        {result.feedback.recommendations.map((r, i) => (
                                            <Text key={i} style={styles.feedbackItem}>• {r}</Text>
                                        ))}
                                    </View>
                                )}

                                <Text style={styles.encouragement}>{result.feedback.encouragement}</Text>
                            </View>
                        )}

                        <TouchableOpacity
                            style={styles.doneButton}
                            onPress={() => router.back()}
                        >
                            <Text style={styles.doneButtonText}>Done</Text>
                        </TouchableOpacity>
                    </View>
                </ScrollView>
            </SafeAreaView>
        );
    }

    // In progress - Question view
    const currentQuestion = questions[currentIndex];
    const currentAnswer = answers[currentQuestion?.question_id];

    return (
        <SafeAreaView style={styles.safeArea}>
            {/* Header with timer */}
            <View style={styles.testHeader}>
                <TouchableOpacity onPress={() => router.back()}>
                    <Text style={styles.closeIcon}>✕</Text>
                </TouchableOpacity>
                <Text style={styles.testTitle}>Test</Text>
                <View style={[styles.timerBadge, timeRemaining < 60 && styles.timerWarning]}>
                    <Text style={[styles.timerText, timeRemaining < 60 && styles.timerTextWarning]}>
                        ⏱ {formatTime(timeRemaining)}
                    </Text>
                </View>
            </View>

            {/* Progress */}
            <View style={styles.progressBar}>
                <View
                    style={[
                        styles.progressFill,
                        { width: `${((currentIndex + 1) / questions.length) * 100}%` }
                    ]}
                />
            </View>

            <ScrollView style={styles.questionContainer}>
                <Text style={styles.questionNumber}>
                    Question {currentIndex + 1} of {questions.length}
                </Text>

                <Text style={styles.questionText}>{currentQuestion?.question}</Text>

                {currentQuestion?.subtopic_name && (
                    <Text style={styles.subtopicLabel}>{currentQuestion.subtopic_name}</Text>
                )}

                <View style={styles.optionsContainer}>
                    {currentQuestion?.options.map((option, index) => {
                        const isSelected = currentAnswer?.answer === option;
                        return (
                            <TouchableOpacity
                                key={index}
                                style={[styles.optionButton, isSelected && styles.optionSelected]}
                                onPress={() => selectAnswer(
                                    currentQuestion.question_id,
                                    option,
                                    currentQuestion.options[0] // First option is correct
                                )}
                            >
                                <View style={[styles.optionRadio, isSelected && styles.optionRadioSelected]}>
                                    {isSelected && <View style={styles.optionRadioDot} />}
                                </View>
                                <Text style={[styles.optionText, isSelected && styles.optionTextSelected]}>
                                    {option}
                                </Text>
                            </TouchableOpacity>
                        );
                    })}
                </View>
            </ScrollView>

            {/* Question navigator dots */}
            <View style={styles.dotsContainer}>
                {questions.map((q, index) => (
                    <TouchableOpacity
                        key={index}
                        style={[
                            styles.dot,
                            index === currentIndex && styles.dotActive,
                            answers[q.question_id] && styles.dotAnswered,
                        ]}
                        onPress={() => goToQuestion(index)}
                    />
                ))}
            </View>

            {/* Navigation */}
            <View style={styles.navContainer}>
                <TouchableOpacity
                    style={[styles.navButton, currentIndex === 0 && styles.navButtonDisabled]}
                    onPress={() => goToQuestion(currentIndex - 1)}
                    disabled={currentIndex === 0}
                >
                    <Text style={styles.navButtonText}>← Previous</Text>
                </TouchableOpacity>

                {currentIndex < questions.length - 1 ? (
                    <TouchableOpacity
                        style={styles.navButton}
                        onPress={() => goToQuestion(currentIndex + 1)}
                    >
                        <Text style={styles.navButtonText}>Next →</Text>
                    </TouchableOpacity>
                ) : (
                    <TouchableOpacity
                        style={styles.submitButton}
                        onPress={() => submitTest(false)}
                    >
                        <Text style={styles.submitButtonText}>Submit Test</Text>
                    </TouchableOpacity>
                )}
            </View>
        </SafeAreaView>
    );
}

const styles = StyleSheet.create({
    safeArea: {
        flex: 1,
        backgroundColor: '#F8FAFC',
    },
    centerContainer: {
        flex: 1,
        justifyContent: 'center',
        alignItems: 'center',
    },
    loadingText: {
        marginTop: 16,
        fontSize: 16,
        color: '#64748B',
    },
    header: {
        flexDirection: 'row',
        alignItems: 'center',
        justifyContent: 'space-between',
        paddingHorizontal: 16,
        paddingVertical: 12,
        backgroundColor: '#FFFFFF',
        borderBottomWidth: 1,
        borderBottomColor: '#E2E8F0',
    },
    backBtn: {
        padding: 8,
    },
    backIcon: {
        fontSize: 24,
        color: '#1E293B',
    },
    headerTitle: {
        fontSize: 18,
        fontWeight: '600',
        color: '#1E293B',
    },
    startContainer: {
        flex: 1,
        justifyContent: 'center',
        alignItems: 'center',
        padding: 24,
    },
    startCard: {
        backgroundColor: '#FFFFFF',
        borderRadius: 20,
        padding: 32,
        alignItems: 'center',
        width: '100%',
        maxWidth: 340,
        shadowColor: '#000',
        shadowOffset: { width: 0, height: 4 },
        shadowOpacity: 0.1,
        shadowRadius: 12,
        elevation: 5,
    },
    startIcon: {
        fontSize: 48,
        marginBottom: 16,
    },
    startTitle: {
        fontSize: 22,
        fontWeight: '700',
        color: '#1E293B',
        textAlign: 'center',
        marginBottom: 4,
    },
    startSubtitle: {
        fontSize: 16,
        color: '#64748B',
        marginBottom: 24,
    },
    infoRow: {
        flexDirection: 'row',
        alignItems: 'center',
        marginBottom: 32,
    },
    infoItem: {
        alignItems: 'center',
        paddingHorizontal: 24,
    },
    infoValue: {
        fontSize: 28,
        fontWeight: '700',
        color: '#007AFF',
    },
    infoLabel: {
        fontSize: 14,
        color: '#64748B',
    },
    infoDivider: {
        width: 1,
        height: 40,
        backgroundColor: '#E2E8F0',
    },
    startButton: {
        backgroundColor: '#007AFF',
        paddingVertical: 16,
        paddingHorizontal: 48,
        borderRadius: 12,
    },
    startButtonText: {
        color: '#FFFFFF',
        fontSize: 18,
        fontWeight: '600',
    },
    testHeader: {
        flexDirection: 'row',
        alignItems: 'center',
        justifyContent: 'space-between',
        paddingHorizontal: 16,
        paddingVertical: 12,
        backgroundColor: '#FFFFFF',
    },
    closeIcon: {
        fontSize: 24,
        color: '#64748B',
    },
    testTitle: {
        fontSize: 18,
        fontWeight: '600',
        color: '#1E293B',
    },
    timerBadge: {
        backgroundColor: '#F1F5F9',
        paddingHorizontal: 12,
        paddingVertical: 6,
        borderRadius: 20,
    },
    timerWarning: {
        backgroundColor: '#FEE2E2',
    },
    timerText: {
        fontSize: 14,
        fontWeight: '600',
        color: '#1E293B',
    },
    timerTextWarning: {
        color: '#DC2626',
    },
    progressBar: {
        height: 4,
        backgroundColor: '#E2E8F0',
    },
    progressFill: {
        height: '100%',
        backgroundColor: '#007AFF',
    },
    questionContainer: {
        flex: 1,
        padding: 20,
    },
    questionNumber: {
        fontSize: 14,
        color: '#64748B',
        marginBottom: 8,
    },
    questionText: {
        fontSize: 18,
        fontWeight: '600',
        color: '#1E293B',
        lineHeight: 26,
        marginBottom: 8,
    },
    subtopicLabel: {
        fontSize: 12,
        color: '#007AFF',
        backgroundColor: '#EFF6FF',
        paddingHorizontal: 10,
        paddingVertical: 4,
        borderRadius: 12,
        alignSelf: 'flex-start',
        marginBottom: 24,
    },
    optionsContainer: {
        gap: 12,
    },
    optionButton: {
        flexDirection: 'row',
        alignItems: 'center',
        backgroundColor: '#FFFFFF',
        borderWidth: 2,
        borderColor: '#E2E8F0',
        borderRadius: 12,
        padding: 16,
    },
    optionSelected: {
        borderColor: '#007AFF',
        backgroundColor: '#EFF6FF',
    },
    optionRadio: {
        width: 22,
        height: 22,
        borderRadius: 11,
        borderWidth: 2,
        borderColor: '#CBD5E1',
        marginRight: 12,
        justifyContent: 'center',
        alignItems: 'center',
    },
    optionRadioSelected: {
        borderColor: '#007AFF',
    },
    optionRadioDot: {
        width: 12,
        height: 12,
        borderRadius: 6,
        backgroundColor: '#007AFF',
    },
    optionText: {
        flex: 1,
        fontSize: 16,
        color: '#1E293B',
    },
    optionTextSelected: {
        color: '#007AFF',
        fontWeight: '500',
    },
    dotsContainer: {
        flexDirection: 'row',
        justifyContent: 'center',
        flexWrap: 'wrap',
        paddingVertical: 12,
        paddingHorizontal: 20,
        gap: 8,
    },
    dot: {
        width: 10,
        height: 10,
        borderRadius: 5,
        backgroundColor: '#E2E8F0',
    },
    dotActive: {
        backgroundColor: '#007AFF',
        transform: [{ scale: 1.2 }],
    },
    dotAnswered: {
        backgroundColor: '#10B981',
    },
    navContainer: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        padding: 16,
        backgroundColor: '#FFFFFF',
        borderTopWidth: 1,
        borderTopColor: '#E2E8F0',
    },
    navButton: {
        paddingVertical: 12,
        paddingHorizontal: 20,
    },
    navButtonDisabled: {
        opacity: 0.4,
    },
    navButtonText: {
        fontSize: 16,
        color: '#007AFF',
        fontWeight: '600',
    },
    submitButton: {
        backgroundColor: '#10B981',
        paddingVertical: 12,
        paddingHorizontal: 24,
        borderRadius: 8,
    },
    submitButtonText: {
        color: '#FFFFFF',
        fontSize: 16,
        fontWeight: '600',
    },
    scrollView: {
        flex: 1,
    },
    resultsContainer: {
        padding: 24,
    },
    scoreCard: {
        backgroundColor: '#FFFFFF',
        borderRadius: 20,
        padding: 32,
        alignItems: 'center',
        borderWidth: 3,
        marginBottom: 20,
    },
    scoreEmoji: {
        fontSize: 48,
        marginBottom: 12,
    },
    scorePercent: {
        fontSize: 56,
        fontWeight: '700',
    },
    scoreDetails: {
        fontSize: 16,
        color: '#64748B',
        marginTop: 8,
    },
    feedbackCard: {
        backgroundColor: '#FFFFFF',
        borderRadius: 16,
        padding: 20,
        marginBottom: 20,
    },
    feedbackTitle: {
        fontSize: 18,
        fontWeight: '600',
        color: '#1E293B',
        marginBottom: 12,
    },
    feedbackText: {
        fontSize: 15,
        color: '#475569',
        lineHeight: 22,
        marginBottom: 16,
    },
    feedbackSection: {
        marginBottom: 12,
    },
    feedbackSectionTitle: {
        fontSize: 14,
        fontWeight: '600',
        color: '#1E293B',
        marginBottom: 6,
    },
    feedbackItem: {
        fontSize: 14,
        color: '#475569',
        marginLeft: 8,
        marginBottom: 4,
    },
    encouragement: {
        fontSize: 15,
        fontStyle: 'italic',
        color: '#7C3AED',
        marginTop: 12,
        textAlign: 'center',
    },
    doneButton: {
        backgroundColor: '#007AFF',
        paddingVertical: 16,
        borderRadius: 12,
        alignItems: 'center',
    },
    doneButtonText: {
        color: '#FFFFFF',
        fontSize: 18,
        fontWeight: '600',
    },
});
