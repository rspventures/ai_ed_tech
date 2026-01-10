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
} from 'react-native';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { assessmentService } from '../../src/services/assessment';
import { curriculumService } from '../../src/services/curriculum';
import {
    AssessmentStartResponse,
    AssessmentResult,
    Question,
    AssessmentSubmissionItem,
    Topic
} from '../../src/types';

type AssessmentState = 'intro' | 'active' | 'submitting' | 'results';

export default function AssessmentScreen() {
    const router = useRouter();
    const { id } = useLocalSearchParams<{ id: string }>(); // Treating id as topicId (or slug if needed)

    const [status, setStatus] = useState<AssessmentState>('intro');
    const [loading, setLoading] = useState(true);
    const [topic, setTopic] = useState<Topic | null>(null);
    const [assessmentData, setAssessmentData] = useState<AssessmentStartResponse | null>(null);
    const [currentQuestionIndex, setCurrentQuestionIndex] = useState(0);
    const [answers, setAnswers] = useState<Record<string, string>>({});
    const [result, setResult] = useState<AssessmentResult | null>(null);
    const [startTime, setStartTime] = useState<number>(Date.now());

    useEffect(() => {
        if (id) {
            loadTopic();
        }
    }, [id]);

    const loadTopic = async () => {
        try {
            setLoading(true);
            // Try fetching topic by ID or Slug. 
            // Since we might have passed an ID, let's assume getText (which takes slug) might fail if it expects a slug?
            // Actually curriculumService.getTopic takes a slug. 
            // If we passed an ID, we might need a getTopicById.
            // For now, let's assume id passed IS the slug or the service handles both.
            // Adjust: StudyScreen passed resourceId. If it came from `learningPath`, it's usually an ID. 
            // `getTopic` in `curriculum.ts` calls `/curriculum/topics/{slug}`. 
            // If the backend supports ID there, great. If not, this might be tricky.
            // Workaround: We proceed without topic details if fetch fails, solely relying on assessment start.

            try {
                const data = await curriculumService.getTopic(id!);
                setTopic(data);
            } catch (e) {
                console.log('Topic fetch failed, proceeding with ID as is');
            }

            setLoading(false);
        } catch (err) {
            console.log('Failed to load topic:', err);
            Alert.alert('Error', 'Failed to load assessment context.');
            router.back();
        }
    };

    const startAssessment = async () => {
        try {
            setLoading(true);
            // Use topic.id if we loaded it, otherwise use the param id
            const topicId = topic?.id || id!;
            const data = await assessmentService.startAssessment(topicId);
            setAssessmentData(data);
            setStartTime(Date.now());
            setStatus('active');
        } catch (err) {
            console.log('Failed to start assessment:', err);
            Alert.alert('Error', 'Failed to start assessment. Please try again.');
        } finally {
            setLoading(false);
        }
    };

    const handleAnswer = (option: string) => {
        if (!assessmentData) return;
        const question = assessmentData.questions[currentQuestionIndex];
        setAnswers(prev => ({
            ...prev,
            [question.question_id]: option
        }));
    };

    const nextQuestion = () => {
        if (!assessmentData) return;
        if (currentQuestionIndex < assessmentData.questions.length - 1) {
            setCurrentQuestionIndex(prev => prev + 1);
        } else {
            submitAssessment();
        }
    };

    const submitAssessment = async () => {
        if (!assessmentData) return;

        setStatus('submitting');
        try {
            const submissionItems: AssessmentSubmissionItem[] = assessmentData.questions.map(q => ({
                question_id: q.question_id,
                question: q.question,
                options: q.options,
                answer: answers[q.question_id] || '',
                correct_answer: '' // Server validates
            }));

            const resultData = await assessmentService.submitAssessment({
                topic_id: topic?.id || id!,
                answers: submissionItems,
                assessment_session_id: assessmentData.assessment_id,
                topic_name: topic?.name
            });

            setResult(resultData);
            setStatus('results');
        } catch (err) {
            console.log('Failed to submit:', err);
            Alert.alert('Error', 'Failed to submit assessment.');
            setStatus('active');
        }
    };

    if (loading && status === 'intro' && !topic) {
        return (
            <SafeAreaView style={styles.safeArea}>
                <View style={styles.loadingContainer}>
                    <ActivityIndicator size="large" color="#007AFF" />
                </View>
            </SafeAreaView>
        );
    }

    // 1. INTRO SCREEN
    if (status === 'intro') {
        return (
            <SafeAreaView style={styles.safeArea}>
                <View style={styles.header}>
                    <TouchableOpacity onPress={() => router.back()} style={styles.backBtn}>
                        <Text style={styles.backIcon}>✕</Text>
                    </TouchableOpacity>
                    <Text style={styles.headerTitle}>Assessment</Text>
                    <View style={{ width: 40 }} />
                </View>

                <View style={styles.introContainer}>
                    <Text style={styles.introTitle}>{topic?.name || 'Topic'} Assessment</Text>
                    <Text style={styles.introText}>
                        Ready to test your knowledge? This assessment will evaluate your mastery of the topic.
                    </Text>

                    <View style={styles.infoCard}>
                        <Text style={styles.infoItem}>• Untimed</Text>
                        <Text style={styles.infoItem}>• Comprehensive Feedback</Text>
                        <Text style={styles.infoItem}>• multiple choice</Text>
                    </View>

                    <TouchableOpacity
                        style={styles.startButton}
                        onPress={startAssessment}
                    >
                        {loading ? (
                            <ActivityIndicator color="#fff" />
                        ) : (
                            <Text style={styles.startButtonText}>Start Assessment</Text>
                        )}
                    </TouchableOpacity>
                </View>
            </SafeAreaView>
        );
    }

    // 2. ACTIVE QUIZ
    if (status === 'active' && assessmentData) {
        const question = assessmentData.questions[currentQuestionIndex];
        const currentAnswer = answers[question.question_id];
        const isLast = currentQuestionIndex === assessmentData.questions.length - 1;
        const progress = (currentQuestionIndex / assessmentData.questions.length) * 100;

        return (
            <SafeAreaView style={styles.safeArea}>
                {/* Progress Header */}
                <View style={styles.header}>
                    <TouchableOpacity onPress={() => {
                        Alert.alert('Quit?', 'Progress will be lost.', [
                            { text: 'Cancel', style: 'cancel' },
                            { text: 'Quit', style: 'destructive', onPress: () => router.back() }
                        ]);
                    }} style={styles.backBtn}>
                        <Text style={styles.backIcon}>✕</Text>
                    </TouchableOpacity>
                    <View style={styles.progressTrack}>
                        <View style={[styles.progressFill, { width: `${progress}%` }]} />
                    </View>
                    <Text style={styles.progressText}>
                        {currentQuestionIndex + 1}/{assessmentData.questions.length}
                    </Text>
                </View>

                <ScrollView style={styles.content}>
                    <Text style={styles.questionText}>{question.question}</Text>

                    <View style={styles.optionsContainer}>
                        {question.options.map((option, index) => (
                            <TouchableOpacity
                                key={index}
                                style={[
                                    styles.optionCard,
                                    currentAnswer === option && styles.optionSelected
                                ]}
                                onPress={() => handleAnswer(option)}
                            >
                                <View style={[
                                    styles.radioCircle,
                                    currentAnswer === option && styles.radioSelected
                                ]} />
                                <Text style={styles.optionText}>{option}</Text>
                            </TouchableOpacity>
                        ))}
                    </View>
                </ScrollView>

                <View style={styles.footer}>
                    <TouchableOpacity
                        style={[styles.actionButton, !currentAnswer && styles.actionButtonDisabled]}
                        onPress={nextQuestion}
                        disabled={!currentAnswer}
                    >
                        <Text style={styles.actionButtonText}>
                            {isLast ? 'Finish' : 'Next'}
                        </Text>
                    </TouchableOpacity>
                </View>
            </SafeAreaView>
        );
    }

    // 3. RESULTS SCREEN
    if (status === 'results' && result) {
        const passed = result.score >= 70;

        return (
            <SafeAreaView style={styles.safeArea}>
                <ScrollView style={styles.content}>
                    <View style={[styles.resultHeader, passed ? styles.resultSuccess : styles.resultFail]}>
                        <Text style={styles.resultEmoji}>{passed ? '🏆' : '🎯'}</Text>
                        <Text style={styles.resultTitle}>
                            {passed ? 'Great Job!' : 'Keep Practicing!'}
                        </Text>
                        <Text style={styles.scoreText}>
                            {Math.round(result.score)}%
                        </Text>
                        <Text style={styles.resultSubtitle}>
                            You got {result.correct_questions} out of {result.total_questions} correct
                        </Text>
                    </View>

                    {/* Feedback */}
                    {result.feedback && (
                        <View style={styles.feedbackSection}>
                            {result.feedback.strengths.length > 0 && (
                                <View style={styles.feedbackCard}>
                                    <Text style={styles.feedbackHeader}>🌟 Strengths</Text>
                                    {result.feedback.strengths.map((s, i) => (
                                        <Text key={i} style={styles.feedbackItem}>• {s}</Text>
                                    ))}
                                </View>
                            )}

                            {result.feedback.areas_of_improvement.length > 0 && (
                                <View style={styles.feedbackCard}>
                                    <Text style={styles.feedbackHeader}>📈 Areas to Improve</Text>
                                    {result.feedback.areas_of_improvement.map((s, i) => (
                                        <Text key={i} style={styles.feedbackItem}>• {s}</Text>
                                    ))}
                                </View>
                            )}
                        </View>
                    )}

                    <TouchableOpacity
                        style={styles.doneButton}
                        onPress={() => router.back()}
                    >
                        <Text style={styles.doneButtonText}>Back to Topic</Text>
                    </TouchableOpacity>
                    <View style={{ height: 40 }} />
                </ScrollView>
            </SafeAreaView>
        );
    }

    // Submitting state
    if (status === 'submitting') {
        return (
            <SafeAreaView style={styles.safeArea}>
                <View style={styles.loadingContainer}>
                    <ActivityIndicator size="large" color="#007AFF" />
                    <Text style={styles.loadingText}>Submitting Results...</Text>
                </View>
            </SafeAreaView>
        );
    }

    return null;
}

const styles = StyleSheet.create({
    safeArea: {
        flex: 1,
        backgroundColor: '#f5f7fa',
    },
    header: {
        flexDirection: 'row',
        alignItems: 'center',
        padding: 16,
        backgroundColor: '#fff',
        borderBottomWidth: 1,
        borderBottomColor: '#e0e0e0',
    },
    backBtn: {
        width: 40,
        height: 40,
        justifyContent: 'center',
        alignItems: 'center',
    },
    backIcon: {
        fontSize: 24,
        color: '#666',
    },
    headerTitle: {
        fontSize: 18,
        fontWeight: 'bold',
        color: '#1a1a2e',
        flex: 1,
        textAlign: 'center',
    },
    loadingContainer: {
        flex: 1,
        justifyContent: 'center',
        alignItems: 'center',
    },
    loadingText: {
        marginTop: 12,
        color: '#666',
    },
    introContainer: {
        flex: 1,
        padding: 24,
        alignItems: 'center',
        justifyContent: 'center',
    },
    introTitle: {
        fontSize: 28,
        fontWeight: 'bold',
        color: '#1a1a2e',
        textAlign: 'center',
        marginBottom: 16,
    },
    introText: {
        fontSize: 16,
        color: '#666',
        textAlign: 'center',
        marginBottom: 32,
        lineHeight: 24,
    },
    infoCard: {
        backgroundColor: '#fff',
        padding: 24,
        borderRadius: 16,
        width: '100%',
        marginBottom: 32,
        shadowColor: '#000',
        shadowOffset: { width: 0, height: 2 },
        shadowOpacity: 0.05,
        shadowRadius: 4,
        elevation: 2,
    },
    infoItem: {
        fontSize: 16,
        color: '#333',
        marginBottom: 12,
        fontWeight: '500',
    },
    startButton: {
        backgroundColor: '#007AFF',
        paddingVertical: 16,
        paddingHorizontal: 32,
        borderRadius: 12,
        width: '100%',
        alignItems: 'center',
    },
    startButtonText: {
        color: '#fff',
        fontSize: 18,
        fontWeight: 'bold',
    },
    progressTrack: {
        flex: 1,
        height: 8,
        backgroundColor: '#e5e7eb',
        borderRadius: 4,
        marginHorizontal: 12,
        overflow: 'hidden',
    },
    progressFill: {
        height: '100%',
        backgroundColor: '#007AFF',
    },
    progressText: {
        fontSize: 14,
        fontWeight: 'bold',
        color: '#666',
        width: 40,
        textAlign: 'right',
    },
    content: {
        flex: 1,
        padding: 16,
    },
    questionText: {
        fontSize: 22,
        fontWeight: 'bold',
        color: '#1a1a2e',
        marginBottom: 24,
        lineHeight: 30,
    },
    optionsContainer: {
        marginBottom: 24,
    },
    optionCard: {
        flexDirection: 'row',
        alignItems: 'center',
        backgroundColor: '#fff',
        padding: 16,
        borderRadius: 12,
        marginBottom: 12,
        borderWidth: 2,
        borderColor: 'transparent',
    },
    optionSelected: {
        borderColor: '#007AFF',
        backgroundColor: '#f0f9ff',
    },
    radioCircle: {
        width: 20,
        height: 20,
        borderRadius: 10,
        borderWidth: 2,
        borderColor: '#ccc',
        marginRight: 12,
    },
    radioSelected: {
        borderColor: '#007AFF',
        backgroundColor: '#007AFF',
    },
    optionText: {
        fontSize: 16,
        color: '#333',
        flex: 1,
    },
    footer: {
        padding: 16,
        backgroundColor: '#fff',
        borderTopWidth: 1,
        borderTopColor: '#e0e0e0',
    },
    actionButton: {
        backgroundColor: '#007AFF',
        paddingVertical: 16,
        borderRadius: 12,
        alignItems: 'center',
    },
    actionButtonDisabled: {
        backgroundColor: '#ccc',
    },
    actionButtonText: {
        color: '#fff',
        fontSize: 16,
        fontWeight: 'bold',
    },
    resultHeader: {
        padding: 32,
        borderRadius: 20,
        alignItems: 'center',
        marginBottom: 24,
    },
    resultSuccess: {
        backgroundColor: '#d1fae5',
    },
    resultFail: {
        backgroundColor: '#fee2e2',
    },
    resultEmoji: {
        fontSize: 48,
        marginBottom: 8,
    },
    resultTitle: {
        fontSize: 24,
        fontWeight: 'bold',
        color: '#1a1a2e',
        marginBottom: 8,
    },
    scoreText: {
        fontSize: 48,
        fontWeight: 'bold',
        color: '#1a1a2e',
        marginBottom: 8,
    },
    resultSubtitle: {
        fontSize: 16,
        color: '#666',
    },
    feedbackSection: {
        marginBottom: 24,
    },
    feedbackCard: {
        backgroundColor: '#fff',
        padding: 20,
        borderRadius: 16,
        marginBottom: 16,
    },
    feedbackHeader: {
        fontSize: 18,
        fontWeight: 'bold',
        color: '#1a1a2e',
        marginBottom: 12,
    },
    feedbackItem: {
        fontSize: 16,
        color: '#444',
        marginBottom: 8,
        lineHeight: 22,
    },
    doneButton: {
        backgroundColor: '#10b981',
        paddingVertical: 16,
        borderRadius: 12,
        alignItems: 'center',
        marginBottom: 24,
    },
    doneButtonText: {
        color: '#fff',
        fontSize: 18,
        fontWeight: 'bold',
    },
});
