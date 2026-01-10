/**
 * AI Tutor Platform - Exam Screen
 * Subject-level exam with multi-topic selection
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
} from 'react-native';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { examService, ExamQuestion, ExamSubmissionItem, ExamResult, TopicBreakdown } from '../../src/services/exam';
import { curriculumService } from '../../src/services/curriculum';

type ExamState = 'loading' | 'setup' | 'in_progress' | 'submitting' | 'results';

interface Topic {
    id: string;
    name: string;
    selected: boolean;
}

export default function ExamScreen() {
    const router = useRouter();
    const { slug } = useLocalSearchParams<{ slug: string }>();

    // Exam state
    const [state, setState] = useState<ExamState>('loading');
    const [subject, setSubject] = useState<{ id: string; name: string } | null>(null);
    const [topics, setTopics] = useState<Topic[]>([]);
    const [numQuestions, setNumQuestions] = useState<number>(15);
    const [examId, setExamId] = useState<string>('');
    const [questions, setQuestions] = useState<ExamQuestion[]>([]);
    const [currentIndex, setCurrentIndex] = useState(0);
    const [answers, setAnswers] = useState<Record<string, { answer: string; correctAnswer: string }>>({});
    const [result, setResult] = useState<ExamResult | null>(null);

    // Timer
    const [timeRemaining, setTimeRemaining] = useState<number>(1800); // 30 minutes default
    const [startTime, setStartTime] = useState<number>(0);
    const timerRef = useRef<NodeJS.Timeout | null>(null);

    useEffect(() => {
        if (slug) {
            loadSubject();
        }
        return () => {
            if (timerRef.current) clearInterval(timerRef.current);
        };
    }, [slug]);

    const loadSubject = async () => {
        try {
            setState('loading');
            const subjectData = await curriculumService.getSubject(slug!);
            setSubject({ id: subjectData.id, name: subjectData.name });

            // Load topics for this subject
            const topicsData = subjectData.topics || [];
            setTopics(topicsData.map((t: any) => ({
                id: t.id,
                name: t.name,
                selected: true, // Select all by default
            })));

            setState('setup');
        } catch (err) {
            console.log('Failed to load subject:', err);
            Alert.alert('Error', 'Failed to load subject');
            router.back();
        }
    };

    const toggleTopic = (topicId: string) => {
        setTopics(prev => prev.map(t =>
            t.id === topicId ? { ...t, selected: !t.selected } : t
        ));
    };

    const selectAllTopics = () => {
        setTopics(prev => prev.map(t => ({ ...t, selected: true })));
    };

    const deselectAllTopics = () => {
        setTopics(prev => prev.map(t => ({ ...t, selected: false })));
    };

    const startExam = async () => {
        const selectedTopics = topics.filter(t => t.selected);
        if (selectedTopics.length === 0) {
            Alert.alert('Error', 'Please select at least one topic');
            return;
        }

        try {
            setState('loading');
            const response = await examService.startExam({
                subject_id: subject!.id,
                topic_ids: selectedTopics.map(t => t.id),
                num_questions: numQuestions,
            });

            setExamId(response.exam_id);
            setQuestions(shuffleArray(response.questions));
            setTimeRemaining(response.time_limit_seconds || 1800);
            setStartTime(Date.now());
            setCurrentIndex(0);
            setAnswers({});
            setState('in_progress');

            // Start timer
            timerRef.current = setInterval(() => {
                setTimeRemaining(prev => {
                    if (prev <= 1) {
                        submitExam(true);
                        return 0;
                    }
                    return prev - 1;
                });
            }, 1000);
        } catch (err) {
            console.log('Failed to start exam:', err);
            Alert.alert('Error', 'Failed to start exam. Please try again.');
            setState('setup');
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

    const submitExam = async (autoSubmit = false) => {
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
            const answerItems: ExamSubmissionItem[] = questions.map(q => ({
                question_id: q.question_id,
                question: q.question,
                options: q.options,
                answer: answers[q.question_id]?.answer || '',
                correct_answer: answers[q.question_id]?.correctAnswer || q.options[0],
                topic_id: q.topic_id,
            }));

            const examResult = await examService.submitExam({
                exam_id: examId,
                subject_id: subject!.id,
                subject_name: subject!.name,
                topic_ids: topics.filter(t => t.selected).map(t => t.id),
                answers: answerItems,
                duration_seconds: duration,
            });

            setResult(examResult);
            setState('results');
        } catch (err) {
            console.log('Failed to submit exam:', err);
            Alert.alert('Error', 'Failed to submit exam. Please try again.');
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
                    <ActivityIndicator size="large" color="#7C3AED" />
                    <Text style={styles.loadingText}>
                        {state === 'loading' ? 'Preparing Exam...' : 'Submitting...'}
                    </Text>
                </View>
            </SafeAreaView>
        );
    }

    // Setup - Topic selection
    if (state === 'setup') {
        const selectedCount = topics.filter(t => t.selected).length;

        return (
            <SafeAreaView style={styles.safeArea}>
                <View style={styles.header}>
                    <TouchableOpacity onPress={() => router.back()} style={styles.backBtn}>
                        <Text style={styles.backIcon}>←</Text>
                    </TouchableOpacity>
                    <Text style={styles.headerTitle}>Subject Exam</Text>
                    <View style={{ width: 40 }} />
                </View>

                <ScrollView style={styles.setupScroll}>
                    <View style={styles.setupCard}>
                        <Text style={styles.setupIcon}>📚</Text>
                        <Text style={styles.setupTitle}>{subject?.name} Exam</Text>

                        {/* Question count selector */}
                        <Text style={styles.sectionLabel}>Number of Questions</Text>
                        <View style={styles.questionCountRow}>
                            {[10, 15, 20].map(count => (
                                <TouchableOpacity
                                    key={count}
                                    style={[
                                        styles.countButton,
                                        numQuestions === count && styles.countButtonActive
                                    ]}
                                    onPress={() => setNumQuestions(count)}
                                >
                                    <Text style={[
                                        styles.countButtonText,
                                        numQuestions === count && styles.countButtonTextActive
                                    ]}>
                                        {count}
                                    </Text>
                                </TouchableOpacity>
                            ))}
                        </View>

                        {/* Topic selection */}
                        <View style={styles.topicHeader}>
                            <Text style={styles.sectionLabel}>Select Topics ({selectedCount}/{topics.length})</Text>
                            <View style={styles.topicActions}>
                                <TouchableOpacity onPress={selectAllTopics}>
                                    <Text style={styles.actionLink}>All</Text>
                                </TouchableOpacity>
                                <Text style={styles.actionDivider}>|</Text>
                                <TouchableOpacity onPress={deselectAllTopics}>
                                    <Text style={styles.actionLink}>None</Text>
                                </TouchableOpacity>
                            </View>
                        </View>

                        <View style={styles.topicsGrid}>
                            {topics.map(topic => (
                                <TouchableOpacity
                                    key={topic.id}
                                    style={[
                                        styles.topicChip,
                                        topic.selected && styles.topicChipSelected
                                    ]}
                                    onPress={() => toggleTopic(topic.id)}
                                >
                                    <View style={[
                                        styles.checkbox,
                                        topic.selected && styles.checkboxChecked
                                    ]}>
                                        {topic.selected && <Text style={styles.checkmark}>✓</Text>}
                                    </View>
                                    <Text style={[
                                        styles.topicName,
                                        topic.selected && styles.topicNameSelected
                                    ]}>
                                        {topic.name}
                                    </Text>
                                </TouchableOpacity>
                            ))}
                        </View>

                        <TouchableOpacity
                            style={[styles.startButton, selectedCount === 0 && styles.startButtonDisabled]}
                            onPress={startExam}
                            disabled={selectedCount === 0}
                        >
                            <Text style={styles.startButtonText}>Start Exam</Text>
                        </TouchableOpacity>
                    </View>
                </ScrollView>
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
                                {scorePercent >= 80 ? '🏆' : scorePercent >= 60 ? '👍' : '💪'}
                            </Text>
                            <Text style={[styles.scorePercent, { color: getScoreColor(scorePercent) }]}>
                                {scorePercent}%
                            </Text>
                            <Text style={styles.scoreDetails}>
                                {result.correct_questions} of {result.total_questions} correct
                            </Text>
                            <Text style={styles.subjectLabel}>{result.subject_name}</Text>
                        </View>

                        {/* Topic breakdown */}
                        {result.topic_breakdown && result.topic_breakdown.length > 0 && (
                            <View style={styles.breakdownCard}>
                                <Text style={styles.breakdownTitle}>Topic Breakdown</Text>
                                {result.topic_breakdown.map((tb: TopicBreakdown, idx: number) => (
                                    <View key={idx} style={styles.breakdownRow}>
                                        <Text style={styles.breakdownTopic}>{tb.topic_name}</Text>
                                        <View style={styles.breakdownBar}>
                                            <View style={[
                                                styles.breakdownFill,
                                                { width: `${tb.percentage}%`, backgroundColor: getScoreColor(tb.percentage) }
                                            ]} />
                                        </View>
                                        <Text style={[styles.breakdownPercent, { color: getScoreColor(tb.percentage) }]}>
                                            {Math.round(tb.percentage)}%
                                        </Text>
                                    </View>
                                ))}
                            </View>
                        )}

                        {result.feedback && (
                            <View style={styles.feedbackCard}>
                                <Text style={styles.feedbackTitle}>Analysis</Text>
                                <Text style={styles.feedbackText}>{result.feedback.overall_interpretation}</Text>

                                {result.feedback.strengths.length > 0 && (
                                    <View style={styles.feedbackSection}>
                                        <Text style={styles.feedbackSectionTitle}>✅ Strengths</Text>
                                        {result.feedback.strengths.map((s, i) => (
                                            <Text key={i} style={styles.feedbackItem}>• {s}</Text>
                                        ))}
                                    </View>
                                )}

                                {result.feedback.areas_to_focus.length > 0 && (
                                    <View style={styles.feedbackSection}>
                                        <Text style={styles.feedbackSectionTitle}>📌 Focus Areas</Text>
                                        {result.feedback.areas_to_focus.map((a, i) => (
                                            <Text key={i} style={styles.feedbackItem}>• {a}</Text>
                                        ))}
                                    </View>
                                )}

                                <Text style={styles.encouragement}>{result.feedback.encouraging_message}</Text>
                            </View>
                        )}

                        <TouchableOpacity style={styles.doneButton} onPress={() => router.back()}>
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
            <View style={styles.examHeader}>
                <TouchableOpacity onPress={() => router.back()}>
                    <Text style={styles.closeIcon}>✕</Text>
                </TouchableOpacity>
                <Text style={styles.examTitle}>Exam</Text>
                <View style={[styles.timerBadge, timeRemaining < 120 && styles.timerWarning]}>
                    <Text style={[styles.timerText, timeRemaining < 120 && styles.timerTextWarning]}>
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
                <View style={styles.questionMeta}>
                    <Text style={styles.questionNumber}>
                        Question {currentIndex + 1} of {questions.length}
                    </Text>
                    <Text style={styles.topicBadge}>{currentQuestion?.topic_name}</Text>
                </View>

                <Text style={styles.questionText}>{currentQuestion?.question}</Text>

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
                                    currentQuestion.options[0]
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
                <ScrollView horizontal showsHorizontalScrollIndicator={false}>
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
                </ScrollView>
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
                        onPress={() => submitExam(false)}
                    >
                        <Text style={styles.submitButtonText}>Submit Exam</Text>
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
    setupScroll: {
        flex: 1,
    },
    setupCard: {
        backgroundColor: '#FFFFFF',
        margin: 16,
        borderRadius: 16,
        padding: 24,
    },
    setupIcon: {
        fontSize: 48,
        textAlign: 'center',
        marginBottom: 12,
    },
    setupTitle: {
        fontSize: 22,
        fontWeight: '700',
        color: '#1E293B',
        textAlign: 'center',
        marginBottom: 24,
    },
    sectionLabel: {
        fontSize: 14,
        fontWeight: '600',
        color: '#64748B',
        marginBottom: 12,
    },
    questionCountRow: {
        flexDirection: 'row',
        gap: 12,
        marginBottom: 24,
    },
    countButton: {
        flex: 1,
        paddingVertical: 14,
        borderRadius: 10,
        borderWidth: 2,
        borderColor: '#E2E8F0',
        alignItems: 'center',
    },
    countButtonActive: {
        borderColor: '#7C3AED',
        backgroundColor: '#F3E8FF',
    },
    countButtonText: {
        fontSize: 18,
        fontWeight: '600',
        color: '#64748B',
    },
    countButtonTextActive: {
        color: '#7C3AED',
    },
    topicHeader: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: 12,
    },
    topicActions: {
        flexDirection: 'row',
        alignItems: 'center',
    },
    actionLink: {
        fontSize: 14,
        color: '#7C3AED',
        fontWeight: '500',
    },
    actionDivider: {
        marginHorizontal: 8,
        color: '#CBD5E1',
    },
    topicsGrid: {
        gap: 10,
        marginBottom: 24,
    },
    topicChip: {
        flexDirection: 'row',
        alignItems: 'center',
        paddingVertical: 12,
        paddingHorizontal: 14,
        borderRadius: 10,
        borderWidth: 1.5,
        borderColor: '#E2E8F0',
        backgroundColor: '#FFFFFF',
    },
    topicChipSelected: {
        borderColor: '#7C3AED',
        backgroundColor: '#FAF5FF',
    },
    checkbox: {
        width: 22,
        height: 22,
        borderRadius: 6,
        borderWidth: 2,
        borderColor: '#CBD5E1',
        marginRight: 12,
        justifyContent: 'center',
        alignItems: 'center',
    },
    checkboxChecked: {
        backgroundColor: '#7C3AED',
        borderColor: '#7C3AED',
    },
    checkmark: {
        color: '#FFFFFF',
        fontSize: 14,
        fontWeight: '700',
    },
    topicName: {
        fontSize: 15,
        color: '#475569',
    },
    topicNameSelected: {
        color: '#7C3AED',
        fontWeight: '500',
    },
    startButton: {
        backgroundColor: '#7C3AED',
        paddingVertical: 16,
        borderRadius: 12,
        alignItems: 'center',
    },
    startButtonDisabled: {
        backgroundColor: '#CBD5E1',
    },
    startButtonText: {
        color: '#FFFFFF',
        fontSize: 18,
        fontWeight: '600',
    },
    examHeader: {
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
    examTitle: {
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
        backgroundColor: '#7C3AED',
    },
    questionContainer: {
        flex: 1,
        padding: 20,
    },
    questionMeta: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: 12,
    },
    questionNumber: {
        fontSize: 14,
        color: '#64748B',
    },
    topicBadge: {
        fontSize: 12,
        color: '#7C3AED',
        backgroundColor: '#F3E8FF',
        paddingHorizontal: 10,
        paddingVertical: 4,
        borderRadius: 12,
    },
    questionText: {
        fontSize: 18,
        fontWeight: '600',
        color: '#1E293B',
        lineHeight: 26,
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
        borderColor: '#7C3AED',
        backgroundColor: '#FAF5FF',
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
        borderColor: '#7C3AED',
    },
    optionRadioDot: {
        width: 12,
        height: 12,
        borderRadius: 6,
        backgroundColor: '#7C3AED',
    },
    optionText: {
        flex: 1,
        fontSize: 16,
        color: '#1E293B',
    },
    optionTextSelected: {
        color: '#7C3AED',
        fontWeight: '500',
    },
    dotsContainer: {
        paddingVertical: 12,
        paddingHorizontal: 20,
    },
    dot: {
        width: 10,
        height: 10,
        borderRadius: 5,
        backgroundColor: '#E2E8F0',
        marginHorizontal: 4,
    },
    dotActive: {
        backgroundColor: '#7C3AED',
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
        color: '#7C3AED',
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
    subjectLabel: {
        fontSize: 14,
        color: '#7C3AED',
        marginTop: 8,
        fontWeight: '500',
    },
    breakdownCard: {
        backgroundColor: '#FFFFFF',
        borderRadius: 16,
        padding: 20,
        marginBottom: 20,
    },
    breakdownTitle: {
        fontSize: 18,
        fontWeight: '600',
        color: '#1E293B',
        marginBottom: 16,
    },
    breakdownRow: {
        flexDirection: 'row',
        alignItems: 'center',
        marginBottom: 12,
    },
    breakdownTopic: {
        flex: 1,
        fontSize: 14,
        color: '#475569',
    },
    breakdownBar: {
        width: 100,
        height: 8,
        backgroundColor: '#E2E8F0',
        borderRadius: 4,
        marginHorizontal: 12,
        overflow: 'hidden',
    },
    breakdownFill: {
        height: '100%',
        borderRadius: 4,
    },
    breakdownPercent: {
        width: 40,
        fontSize: 14,
        fontWeight: '600',
        textAlign: 'right',
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
        backgroundColor: '#7C3AED',
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
