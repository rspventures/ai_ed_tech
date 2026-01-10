import React, { useEffect, useState } from 'react';
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
import { practiceService } from '../../src/services/practice';
import { Question, QuestionFeedback } from '../../src/types';

export default function PracticeScreen() {
    const router = useRouter();
    const { id } = useLocalSearchParams<{ id: string }>(); // subtopicId

    const [question, setQuestion] = useState<Question | null>(null);
    const [selectedOption, setSelectedOption] = useState<string | null>(null);
    const [feedback, setFeedback] = useState<QuestionFeedback | null>(null);
    const [loading, setLoading] = useState(true);
    const [submitting, setSubmitting] = useState(false);
    const [showHint, setShowHint] = useState(false);

    useEffect(() => {
        loadQuestion();
    }, [id]);

    const loadQuestion = async () => {
        try {
            setLoading(true);
            setFeedback(null);
            setSelectedOption(null);
            setShowHint(false);

            // Assuming ID is subtopic_id. If it fails, we might need logic to distinguish.
            const data = await practiceService.startPractice({ subtopic_id: id });
            setQuestion(data);
        } catch (err) {
            console.log('Failed to load question:', err);
            Alert.alert('Error', 'Failed to generate question. Please try again.');
            router.back();
        } finally {
            setLoading(false);
        }
    };

    const handleSubmit = async () => {
        if (!question || !selectedOption) return;

        setSubmitting(true);
        try {
            const result = await practiceService.submitAnswer(question.question_id, selectedOption);
            setFeedback(result);
        } catch (err) {
            console.log('Failed to submit answer:', err);
            Alert.alert('Error', 'Failed to submit answer.');
        } finally {
            setSubmitting(false);
        }
    };

    const getOptionStyle = (option: string) => {
        // Base style
        let style = { ...styles.optionCard };

        // Selection style
        if (selectedOption === option) {
            style = { ...style, ...styles.optionSelected };
        }

        // Feedback style
        if (feedback) {
            const isCorrect = feedback.correct_answer === option ||
                (Array.isArray(feedback.correct_answer) && feedback.correct_answer.includes(option));

            if (isCorrect) {
                style = { ...style, ...styles.optionCorrect };
            } else if (selectedOption === option && !feedback.is_correct) {
                style = { ...style, ...styles.optionWrong };
            }
        }

        return style;
    };

    if (loading) {
        return (
            <SafeAreaView style={styles.safeArea}>
                <View style={styles.loadingContainer}>
                    <ActivityIndicator size="large" color="#007AFF" />
                    <Text style={styles.loadingText}>Generating Question...</Text>
                </View>
            </SafeAreaView>
        );
    }

    if (!question) return null;

    return (
        <SafeAreaView style={styles.safeArea}>
            {/* Header */}
            <View style={styles.header}>
                <TouchableOpacity onPress={() => router.back()} style={styles.backBtn}>
                    <Text style={styles.backIcon}>✕</Text>
                </TouchableOpacity>
                <Text style={styles.headerTitle}>Practice</Text>
                <View style={{ width: 40 }} />
            </View>

            <ScrollView style={styles.content}>
                {/* Progress/Badges */}
                <View style={styles.metaRow}>
                    <View style={[styles.badge,
                    question.difficulty === 'hard' ? styles.badgeHard :
                        question.difficulty === 'medium' ? styles.badgeMedium : styles.badgeEasy
                    ]}>
                        <Text style={styles.badgeText}>{question.difficulty}</Text>
                    </View>
                    <Text style={styles.subtopicLabel}>{question.subtopic}</Text>
                </View>

                {/* Question */}
                <Text style={styles.questionText}>{question.question}</Text>

                {/* Options */}
                <View style={styles.optionsContainer}>
                    {question.options.map((option, index) => (
                        <TouchableOpacity
                            key={index}
                            style={getOptionStyle(option)}
                            onPress={() => !feedback && setSelectedOption(option)}
                            disabled={!!feedback}
                        >
                            <View style={[styles.radioCircle, selectedOption === option && styles.radioSelected]} />
                            <Text style={styles.optionText}>{option}</Text>
                        </TouchableOpacity>
                    ))}
                </View>

                {/* Hint Section */}
                {!feedback && (
                    <TouchableOpacity
                        style={styles.hintButton}
                        onPress={() => setShowHint(!showHint)}
                    >
                        <Text style={styles.hintButtonText}>
                            {showHint ? 'Hide Hint' : 'Show Hint'}
                        </Text>
                    </TouchableOpacity>
                )}

                {showHint && !feedback && (
                    <View style={styles.hintCard}>
                        <Text style={styles.hintTitle}>💡 Hint</Text>
                        <Text style={styles.hintText}>{question.hint}</Text>
                    </View>
                )}

                {/* Feedback Section */}
                {feedback && (
                    <View style={[styles.feedbackCard, feedback.is_correct ? styles.feedbackSuccess : styles.feedbackError]}>
                        <Text style={styles.feedbackTitle}>
                            {feedback.is_correct ? 'Correct! 🎉' : 'Incorrect'}
                        </Text>
                        <Text style={styles.feedbackText}>{feedback.feedback}</Text>
                        <Text style={styles.explanationText}>{feedback.explanation}</Text>
                        {!feedback.is_correct && (
                            <Text style={styles.correctAnswerText}>
                                Correct Answer: {Array.isArray(feedback.correct_answer) ? feedback.correct_answer.join(', ') : feedback.correct_answer}
                            </Text>
                        )}
                    </View>
                )}
            </ScrollView>

            {/* Footer Actions */}
            <View style={styles.footer}>
                {!feedback ? (
                    <TouchableOpacity
                        style={[styles.actionButton, (!selectedOption || submitting) && styles.actionButtonDisabled]}
                        onPress={handleSubmit}
                        disabled={!selectedOption || submitting}
                    >
                        {submitting ? (
                            <ActivityIndicator color="#fff" />
                        ) : (
                            <Text style={styles.actionButtonText}>Check Answer</Text>
                        )}
                    </TouchableOpacity>
                ) : (
                    <TouchableOpacity
                        style={[styles.actionButton, styles.nextButton]}
                        onPress={loadQuestion}
                    >
                        <Text style={styles.actionButtonText}>Next Question</Text>
                    </TouchableOpacity>
                )}
            </View>
        </SafeAreaView>
    );
}

const styles = StyleSheet.create({
    safeArea: {
        flex: 1,
        backgroundColor: '#f5f7fa',
    },
    header: {
        flexDirection: 'row',
        alignItems: 'center',
        justifyContent: 'space-between',
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
    },
    content: {
        flex: 1,
        padding: 16,
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
    metaRow: {
        flexDirection: 'row',
        alignItems: 'center',
        marginBottom: 16,
    },
    badge: {
        paddingHorizontal: 8,
        paddingVertical: 4,
        borderRadius: 8,
        marginRight: 8,
    },
    badgeEasy: { backgroundColor: '#d1fae5' },
    badgeMedium: { backgroundColor: '#fef3c7' },
    badgeHard: { backgroundColor: '#fee2e2' },
    badgeText: {
        fontSize: 12,
        fontWeight: 'bold',
        color: '#333',
        textTransform: 'uppercase',
    },
    subtopicLabel: {
        fontSize: 14,
        color: '#666',
    },
    questionText: {
        fontSize: 20,
        fontWeight: 'bold',
        color: '#1a1a2e',
        marginBottom: 24,
        lineHeight: 28,
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
    optionCorrect: {
        borderColor: '#10b981',
        backgroundColor: '#ecfdf5',
    },
    optionWrong: {
        borderColor: '#ef4444',
        backgroundColor: '#fef2f2',
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
    hintButton: {
        alignSelf: 'center',
        padding: 10,
    },
    hintButtonText: {
        color: '#007AFF',
        fontWeight: '600',
    },
    hintCard: {
        backgroundColor: '#fffbeb',
        padding: 16,
        borderRadius: 12,
        borderWidth: 1,
        borderColor: '#fcd34d',
        marginTop: 8,
        marginBottom: 24,
    },
    hintTitle: {
        fontWeight: 'bold',
        color: '#b45309',
        marginBottom: 4,
    },
    hintText: {
        color: '#92400e',
    },
    feedbackCard: {
        padding: 20,
        borderRadius: 16,
        marginTop: 8,
        marginBottom: 40,
    },
    feedbackSuccess: {
        backgroundColor: '#ecfdf5',
        borderWidth: 1,
        borderColor: '#10b981',
    },
    feedbackError: {
        backgroundColor: '#fef2f2',
        borderWidth: 1,
        borderColor: '#ef4444',
    },
    feedbackTitle: {
        fontSize: 18,
        fontWeight: 'bold',
        marginBottom: 8,
        color: '#1a1a2e',
    },
    feedbackText: {
        fontSize: 16,
        fontWeight: '600',
        marginBottom: 8,
        color: '#333',
    },
    explanationText: {
        fontSize: 14,
        color: '#4b5563',
        lineHeight: 20,
    },
    correctAnswerText: {
        marginTop: 8,
        fontWeight: 'bold',
        color: '#ef4444',
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
    nextButton: {
        backgroundColor: '#10b981',
    },
    actionButtonDisabled: {
        backgroundColor: '#ccc',
    },
    actionButtonText: {
        color: '#fff',
        fontSize: 16,
        fontWeight: 'bold',
    },
});
