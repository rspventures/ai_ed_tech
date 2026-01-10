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
import { studyService } from '../../src/services/study';
import { Lesson } from '../../src/types';

export default function LessonScreen() {
    const router = useRouter();
    const { id } = useLocalSearchParams<{ id: string }>(); // This is subtopicId

    const [lesson, setLesson] = useState<Lesson | null>(null);
    const [loading, setLoading] = useState(true);
    const [completing, setCompleting] = useState(false);
    const [startTime, setStartTime] = useState<number>(Date.now());

    // Track partial scroll for "read" verification if needed, 
    // but for now simple timer + button is enough.

    useEffect(() => {
        if (id) {
            loadLesson();
        }
    }, [id]);

    const loadLesson = async () => {
        try {
            setLoading(true);
            const data = await studyService.getLesson(id!);
            setLesson(data);
            setStartTime(Date.now());
        } catch (err) {
            console.log('Failed to load lesson:', err);
            Alert.alert('Error', 'Failed to load lesson content.');
            router.back();
        } finally {
            setLoading(false);
        }
    };

    const handleComplete = async () => {
        if (!lesson) return;

        setCompleting(true);
        try {
            const timeSpentSeconds = Math.round((Date.now() - startTime) / 1000);
            // Ensure at least 5 seconds recorded for accidental clicks
            const finalTime = Math.max(timeSpentSeconds, 5);

            await studyService.completeLesson(lesson.id, finalTime);

            Alert.alert(
                'Lesson Completed! 🎉',
                'Great job! You\'ve mastered this lesson.',
                [
                    {
                        text: 'Back to Study Plan',
                        onPress: () => router.back()
                    }
                ]
            );
        } catch (err) {
            console.log('Failed to complete lesson:', err);
            Alert.alert('Error', 'Failed to save progress. Please try again.');
        } finally {
            setCompleting(false);
        }
    };

    if (loading) {
        return (
            <SafeAreaView style={styles.safeArea}>
                <View style={styles.loadingContainer}>
                    <ActivityIndicator size="large" color="#007AFF" />
                    <Text style={styles.loadingText}>Generating Lesson...</Text>
                </View>
            </SafeAreaView>
        );
    }

    if (!lesson) {
        return null; // Should have navigated back on error
    }

    return (
        <SafeAreaView style={styles.safeArea}>
            {/* Header */}
            <View style={styles.header}>
                <TouchableOpacity onPress={() => router.back()} style={styles.backBtn}>
                    <Text style={styles.backIcon}>←</Text>
                </TouchableOpacity>
                <Text style={styles.headerTitle} numberOfLines={1}>{lesson.title}</Text>
                <View style={{ width: 40 }} />
            </View>

            <ScrollView style={styles.content}>

                {/* Summary Card */}
                <View style={styles.summaryCard}>
                    <Text style={styles.sectionHeader}>Summary</Text>
                    <Text style={styles.summaryText}>{lesson.summary}</Text>
                </View>

                {/* Main Content */}
                <View style={styles.section}>
                    {!lesson.content || typeof lesson.content === 'string' ? (
                        <Text style={styles.contentText}>{lesson.content as string}</Text>
                    ) : (
                        <View>
                            {/* Hook */}
                            <Text style={styles.hookText}>{(lesson.content).hook}</Text>

                            {/* Intro */}
                            <Text style={styles.contentText}>{(lesson.content).introduction}</Text>

                            {/* Sections */}
                            {(lesson.content).sections && (lesson.content).sections.map((section, idx) => (
                                <View key={idx} style={styles.subSection}>
                                    <Text style={styles.subSectionTitle}>{section.title}</Text>
                                    <Text style={styles.contentText}>{section.content}</Text>
                                </View>
                            ))}

                            {/* Fun Fact */}
                            {(lesson.content).fun_fact && (
                                <View style={styles.funFactCard}>
                                    <Text style={styles.funFactTitle}>Did you know?</Text>
                                    <Text style={styles.funFactText}>{(lesson.content).fun_fact}</Text>
                                </View>
                            )}
                        </View>
                    )}
                </View>

                {/* Key Points */}
                {lesson.key_points && lesson.key_points.length > 0 && (
                    <View style={styles.section}>
                        <Text style={styles.sectionHeader}>Key Points</Text>
                        <View style={styles.card}>
                            {lesson.key_points.map((point, index) => (
                                <View key={index} style={styles.bulletItem}>
                                    <Text style={styles.bullet}>•</Text>
                                    <Text style={styles.bulletText}>{point}</Text>
                                </View>
                            ))}
                        </View>
                    </View>
                )}

                {/* Examples */}
                {lesson.examples && lesson.examples.length > 0 && (
                    <View style={styles.section}>
                        <Text style={styles.sectionHeader}>Examples</Text>
                        {lesson.examples.map((example, index) => (
                            <View key={index} style={styles.exampleCard}>
                                <Text style={styles.exampleLabel}>Example {index + 1}</Text>
                                <Text style={styles.exampleText}>{example}</Text>
                            </View>
                        ))}
                    </View>
                )}

                {/* Completion Area */}
                <View style={styles.footer}>
                    <TouchableOpacity
                        style={[
                            styles.completeButton,
                            completing && styles.completeButtonDisabled,
                            lesson.is_completed && styles.completedButton
                        ]}
                        onPress={handleComplete}
                        disabled={completing || lesson.is_completed}
                    >
                        {completing ? (
                            <ActivityIndicator color="#fff" />
                        ) : lesson.is_completed ? (
                            <Text style={styles.completeButtonText}>✓ Completed</Text>
                        ) : (
                            <Text style={styles.completeButtonText}>Complete Lesson</Text>
                        )}
                    </TouchableOpacity>
                </View>

                <View style={{ height: 40 }} />
            </ScrollView>
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
        color: '#007AFF',
    },
    headerTitle: {
        fontSize: 18,
        fontWeight: 'bold',
        color: '#1a1a2e',
        flex: 1,
        textAlign: 'center',
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
    summaryCard: {
        backgroundColor: '#fff',
        borderRadius: 16,
        padding: 20,
        marginBottom: 24,
        borderLeftWidth: 4,
        borderLeftColor: '#007AFF',
        shadowColor: '#000',
        shadowOffset: { width: 0, height: 2 },
        shadowOpacity: 0.05,
        shadowRadius: 4,
        elevation: 2,
    },
    summaryText: {
        fontSize: 16,
        color: '#444',
        lineHeight: 24,
    },
    section: {
        marginBottom: 24,
    },
    sectionHeader: {
        fontSize: 20,
        fontWeight: 'bold',
        color: '#1a1a2e',
        marginBottom: 12,
    },
    contentTitle: {
        fontSize: 24,
        fontWeight: 'bold',
        color: '#1a1a2e',
        marginBottom: 16,
    },
    contentText: {
        fontSize: 16,
        color: '#333',
        lineHeight: 26,
    },
    card: {
        backgroundColor: '#fff',
        borderRadius: 12,
        padding: 16,
    },
    bulletItem: {
        flexDirection: 'row',
        marginBottom: 12,
    },
    bullet: {
        fontSize: 18,
        color: '#007AFF',
        marginRight: 8,
        marginTop: -2,
    },
    bulletText: {
        fontSize: 16,
        color: '#333',
        flex: 1,
        lineHeight: 22,
    },
    exampleCard: {
        backgroundColor: '#fff',
        borderRadius: 12,
        padding: 16,
        marginBottom: 12,
        borderWidth: 1,
        borderColor: '#e5e7eb',
    },
    exampleLabel: {
        fontSize: 12,
        fontWeight: 'bold',
        color: '#666',
        textTransform: 'uppercase',
        marginBottom: 8,
    },
    exampleText: {
        fontSize: 16,
        color: '#333',
        lineHeight: 24,
        fontStyle: 'italic',
    },
    footer: {
        marginTop: 20,
        marginBottom: 20,
    },
    completeButton: {
        backgroundColor: '#007AFF',
        paddingVertical: 16,
        borderRadius: 12,
        alignItems: 'center',
        shadowColor: '#007AFF',
        shadowOffset: { width: 0, height: 4 },
        shadowOpacity: 0.2,
        shadowRadius: 8,
        elevation: 4,
    },
    completeButtonDisabled: {
        backgroundColor: '#ccc',
        shadowOpacity: 0,
    },
    completedButton: {
        backgroundColor: '#10b981',
        shadowColor: '#10b981',
    },
    completeButtonText: {
        color: '#fff',
        fontSize: 18,
        fontWeight: 'bold',
    },
    hookText: {
        fontSize: 18,
        fontStyle: 'italic',
        color: '#1a1a2e',
        marginBottom: 16,
        lineHeight: 28,
        fontWeight: '500',
    },
    subSection: {
        marginTop: 24,
        marginBottom: 16,
    },
    subSectionTitle: {
        fontSize: 18,
        fontWeight: 'bold',
        color: '#1a1a2e',
        marginBottom: 8,
    },
    funFactCard: {
        backgroundColor: '#fffbeb',
        borderRadius: 12,
        padding: 16,
        marginTop: 24,
        borderLeftWidth: 4,
        borderLeftColor: '#f59e0b',
    },
    funFactTitle: {
        fontSize: 14,
        fontWeight: 'bold',
        color: '#b45309',
        textTransform: 'uppercase',
        marginBottom: 8,
    },
    funFactText: {
        fontSize: 16,
        color: '#78350f',
        lineHeight: 24,
    },
});
