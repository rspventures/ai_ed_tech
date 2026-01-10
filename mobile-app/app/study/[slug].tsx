import React, { useEffect, useState } from 'react';
import {
    View,
    Text,
    TouchableOpacity,
    StyleSheet,
    SafeAreaView,
    ScrollView,
    ActivityIndicator,
} from 'react-native';
import { useLocalSearchParams, useRouter } from 'expo-router';
import { studyService } from '../../src/services/study';
import { TopicWithSubtopics, Subtopic, LearningPath } from '../../src/types';

interface SubtopicWithProgress extends Subtopic {
    mastery_level: number;
    lesson_completed: boolean;
    practice_count: number;
}

export default function StudyScreen() {
    const router = useRouter();
    const { slug } = useLocalSearchParams<{ slug: string }>();

    const [topic, setTopic] = useState<TopicWithSubtopics | null>(null);
    const [subtopics, setSubtopics] = useState<SubtopicWithProgress[]>([]);
    const [learningPath, setLearningPath] = useState<LearningPath | null>(null);
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);

    useEffect(() => {
        if (slug) {
            loadData();
        }
    }, [slug]);

    const loadData = async () => {
        try {
            setLoading(true);

            // Get topic with subtopics
            const topicData = await studyService.getTopic(slug!);
            setTopic(topicData);

            // Get learning path
            try {
                const path = await studyService.getLearningPath(topicData.id);
                setLearningPath(path);
            } catch {
                console.log('No learning path available');
            }

            // Load subtopic progress
            if (topicData.subtopics && topicData.subtopics.length > 0) {
                const subtopicsWithProgress = await Promise.all(
                    topicData.subtopics.map(async (subtopic: Subtopic) => {
                        try {
                            const progress = await studyService.getSubtopicProgress(subtopic.id);
                            return {
                                ...subtopic,
                                mastery_level: progress.mastery_level,
                                lesson_completed: progress.lesson_completed,
                                practice_count: progress.practice_count
                            };
                        } catch {
                            return {
                                ...subtopic,
                                mastery_level: 0,
                                lesson_completed: false,
                                practice_count: 0
                            };
                        }
                    })
                );
                setSubtopics(subtopicsWithProgress);
            }
        } catch (err) {
            console.log('Failed to load study data:', err);
            setError('Failed to load study materials');
        } finally {
            setLoading(false);
        }
    };

    const handleStartActivity = (type: 'lesson' | 'practice' | 'assessment', resourceId: string) => {
        if (type === 'lesson') {
            router.push(`/lesson/${resourceId}`);
        } else if (type === 'practice') {
            router.push(`/practice/${resourceId}`);
        } else if (type === 'assessment') {
            router.push(`/assessment/${resourceId}`);
        }
    };

    const getDifficultyColor = (difficulty: string): string => {
        switch (difficulty) {
            case 'hard': return '#ef4444';
            case 'medium': return '#f59e0b';
            default: return '#10b981';
        }
    };

    const getMasteryColor = (mastery: number): string => {
        if (mastery >= 0.7) return '#10b981';
        if (mastery >= 0.4) return '#f59e0b';
        return '#6b7280';
    };

    if (loading) {
        return (
            <SafeAreaView style={styles.safeArea}>
                <View style={styles.loadingContainer}>
                    <ActivityIndicator size="large" color="#007AFF" />
                    <Text style={styles.loadingText}>Loading study materials...</Text>
                </View>
            </SafeAreaView>
        );
    }

    if (error || !topic) {
        return (
            <SafeAreaView style={styles.safeArea}>
                <View style={styles.errorContainer}>
                    <Text style={styles.errorText}>{error || 'Topic not found'}</Text>
                    <TouchableOpacity style={styles.backButton} onPress={() => router.back()}>
                        <Text style={styles.backButtonText}>Go Back</Text>
                    </TouchableOpacity>
                </View>
            </SafeAreaView>
        );
    }

    // Default to 0 if null
    const overallMastery = learningPath
        ? Math.round(learningPath.current_mastery * 100)
        : 0;

    return (
        <SafeAreaView style={styles.safeArea}>
            {/* Header */}
            <View style={styles.header}>
                <TouchableOpacity onPress={() => router.back()} style={styles.backBtn}>
                    <Text style={styles.backIcon}>←</Text>
                </TouchableOpacity>
                <Text style={styles.headerTitle} numberOfLines={1}>{topic.name}</Text>
                <View style={{ width: 40 }} />
            </View>

            <ScrollView style={styles.content}>
                {/* Progress Overview */}
                <View style={styles.progressCard}>
                    <View style={styles.progressHeader}>
                        <Text style={styles.progressTitle}>Your Progress</Text>
                        <Text style={styles.progressPercent}>{overallMastery}%</Text>
                    </View>
                    <View style={styles.progressBarContainer}>
                        <View
                            style={[
                                styles.progressBarFill,
                                { width: `${overallMastery}%`, backgroundColor: getMasteryColor(overallMastery / 100) }
                            ]}
                        />
                    </View>
                    {learningPath && (
                        <View style={styles.statsRow}>
                            <View style={styles.statItem}>
                                <Text style={styles.statValue}>
                                    {learningPath.completed_lessons}/{learningPath.total_lessons}
                                </Text>
                                <Text style={styles.statLabel}>Lessons</Text>
                            </View>
                            <View style={styles.statItem}>
                                <Text style={styles.statValue}>{learningPath.completed_practice}</Text>
                                <Text style={styles.statLabel}>Practice</Text>
                            </View>
                            <View style={styles.statItem}>
                                <Text style={styles.statValue}>{overallMastery}%</Text>
                                <Text style={styles.statLabel}>Mastery</Text>
                            </View>
                        </View>
                    )}
                </View>

                {/* Take Test Button */}
                <TouchableOpacity
                    style={styles.takeTestButton}
                    onPress={() => router.push(`/test/${slug}`)}
                >
                    <Text style={styles.takeTestIcon}>📝</Text>
                    <View style={styles.takeTestContent}>
                        <Text style={styles.takeTestTitle}>Take Topic Test</Text>
                        <Text style={styles.takeTestDesc}>10 questions • 10 minutes</Text>
                    </View>
                    <Text style={styles.takeTestArrow}>→</Text>
                </TouchableOpacity>

                {/* Recommended Next Action */}
                {learningPath && learningPath.next_action.action_type !== 'complete' && (
                    <TouchableOpacity
                        style={styles.recommendedCard}
                        onPress={() => handleStartActivity(
                            learningPath.next_action.action_type,
                            learningPath.next_action.resource_id
                        )}
                    >
                        <View style={styles.recommendedBadge}>
                            <Text style={styles.recommendedBadgeText}>UP NEXT</Text>
                        </View>
                        <Text style={styles.recommendedTitle}>
                            {learningPath.next_action.resource_name}
                        </Text>
                        <Text style={styles.recommendedReason}>
                            {learningPath.next_action.reason}
                        </Text>
                        <View style={styles.recommendedButton}>
                            <Text style={styles.recommendedButtonText}>Start →</Text>
                        </View>
                    </TouchableOpacity>
                )}

                {/* Subtopics Section */}
                <Text style={styles.sectionTitle}>
                    All Subtopics ({subtopics.length})
                </Text>

                {subtopics.length > 0 ? (
                    subtopics.map((subtopic, index) => {
                        const masteryPercent = Math.round(subtopic.mastery_level * 100);

                        return (
                            <TouchableOpacity
                                key={subtopic.id}
                                style={styles.subtopicCard}
                                onPress={() => {
                                    // Default logic: If lesson not done, do lesson. Else practice.
                                    if (!subtopic.lesson_completed) {
                                        handleStartActivity('lesson', subtopic.id);
                                    } else {
                                        handleStartActivity('practice', subtopic.id);
                                    }
                                }}
                            >
                                <View style={styles.subtopicHeader}>
                                    <View style={[
                                        styles.subtopicNumber,
                                        { backgroundColor: masteryPercent >= 70 ? '#10b981' : '#e5e7eb' }
                                    ]}>
                                        <Text style={[
                                            styles.subtopicNumberText,
                                            { color: masteryPercent >= 70 ? '#fff' : '#666' }
                                        ]}>
                                            {masteryPercent >= 70 ? '✓' : index + 1}
                                        </Text>
                                    </View>
                                    <View style={styles.subtopicInfo}>
                                        <View style={styles.subtopicTitleRow}>
                                            <Text style={styles.subtopicName}>{subtopic.name}</Text>
                                            <View style={[
                                                styles.difficultyBadge,
                                                { backgroundColor: getDifficultyColor(subtopic.difficulty) + '20' }
                                            ]}>
                                                <Text style={[
                                                    styles.difficultyText,
                                                    { color: getDifficultyColor(subtopic.difficulty) }
                                                ]}>
                                                    {subtopic.difficulty}
                                                </Text>
                                            </View>
                                        </View>

                                        {/* Progress bar */}
                                        <View style={styles.subtopicProgress}>
                                            <View style={styles.subtopicProgressBar}>
                                                <View
                                                    style={[
                                                        styles.subtopicProgressFill,
                                                        {
                                                            width: `${masteryPercent}%`,
                                                            backgroundColor: getMasteryColor(subtopic.mastery_level)
                                                        }
                                                    ]}
                                                />
                                            </View>
                                            <Text style={styles.subtopicProgressText}>{masteryPercent}%</Text>
                                        </View>
                                    </View>
                                    <Text style={styles.arrow}>→</Text>
                                </View>

                                {/* Status indicators */}
                                <View style={styles.subtopicStatus}>
                                    {subtopic.lesson_completed && (
                                        <Text style={styles.statusTag}>📚 Lesson Done</Text>
                                    )}
                                    {subtopic.practice_count > 0 && (
                                        <Text style={styles.statusTag}>💪 {subtopic.practice_count} Practice</Text>
                                    )}
                                </View>
                            </TouchableOpacity>
                        );
                    })
                ) : (
                    <View style={styles.emptyContainer}>
                        <Text style={styles.emptyText}>No subtopics available yet.</Text>
                    </View>
                )}

                {/* Topic Complete Banner */}
                {learningPath && learningPath.next_action.action_type === 'complete' && (
                    <View style={styles.completeCard}>
                        <Text style={styles.completeEmoji}>🎉</Text>
                        <Text style={styles.completeTitle}>Topic Mastered!</Text>
                        <Text style={styles.completeText}>
                            Congratulations! You've completed all subtopics.
                        </Text>
                    </View>
                )}
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
    progressCard: {
        backgroundColor: '#fff',
        borderRadius: 16,
        padding: 20,
        marginBottom: 16,
        shadowColor: '#000',
        shadowOffset: { width: 0, height: 2 },
        shadowOpacity: 0.05,
        shadowRadius: 4,
        elevation: 2,
    },
    progressHeader: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
        marginBottom: 12,
    },
    progressTitle: {
        fontSize: 18,
        fontWeight: 'bold',
        color: '#1a1a2e',
    },
    progressPercent: {
        fontSize: 24,
        fontWeight: 'bold',
        color: '#007AFF',
    },
    progressBarContainer: {
        height: 10,
        backgroundColor: '#e5e7eb',
        borderRadius: 5,
        overflow: 'hidden',
        marginBottom: 16,
    },
    progressBarFill: {
        height: '100%',
        borderRadius: 5,
    },
    statsRow: {
        flexDirection: 'row',
        justifyContent: 'space-around',
    },
    statItem: {
        alignItems: 'center',
    },
    statValue: {
        fontSize: 18,
        fontWeight: 'bold',
        color: '#1a1a2e',
    },
    statLabel: {
        fontSize: 12,
        color: '#666',
        marginTop: 2,
    },
    recommendedCard: {
        backgroundColor: '#007AFF',
        borderRadius: 16,
        padding: 20,
        marginBottom: 16,
    },
    recommendedBadge: {
        backgroundColor: 'rgba(255,255,255,0.2)',
        paddingHorizontal: 10,
        paddingVertical: 4,
        borderRadius: 12,
        alignSelf: 'flex-start',
        marginBottom: 8,
    },
    recommendedBadgeText: {
        color: '#fff',
        fontSize: 10,
        fontWeight: 'bold',
    },
    recommendedTitle: {
        fontSize: 18,
        fontWeight: 'bold',
        color: '#fff',
        marginBottom: 4,
    },
    recommendedReason: {
        fontSize: 14,
        color: 'rgba(255,255,255,0.8)',
        marginBottom: 12,
    },
    recommendedButton: {
        backgroundColor: 'rgba(255,255,255,0.2)',
        paddingHorizontal: 16,
        paddingVertical: 10,
        borderRadius: 8,
        alignSelf: 'flex-start',
    },
    recommendedButtonText: {
        color: '#fff',
        fontWeight: 'bold',
    },
    sectionTitle: {
        fontSize: 18,
        fontWeight: 'bold',
        color: '#1a1a2e',
        marginBottom: 12,
    },
    subtopicCard: {
        backgroundColor: '#fff',
        borderRadius: 12,
        padding: 16,
        marginBottom: 10,
        shadowColor: '#000',
        shadowOffset: { width: 0, height: 1 },
        shadowOpacity: 0.05,
        shadowRadius: 2,
        elevation: 1,
    },
    subtopicHeader: {
        flexDirection: 'row',
        alignItems: 'center',
    },
    subtopicNumber: {
        width: 32,
        height: 32,
        borderRadius: 16,
        justifyContent: 'center',
        alignItems: 'center',
    },
    subtopicNumberText: {
        fontSize: 14,
        fontWeight: 'bold',
    },
    subtopicInfo: {
        flex: 1,
        marginLeft: 12,
    },
    subtopicTitleRow: {
        flexDirection: 'row',
        alignItems: 'center',
        justifyContent: 'space-between',
        marginBottom: 8,
    },
    subtopicName: {
        fontSize: 16,
        fontWeight: '600',
        color: '#1a1a2e',
        flex: 1,
    },
    difficultyBadge: {
        paddingHorizontal: 8,
        paddingVertical: 2,
        borderRadius: 8,
        marginLeft: 8,
    },
    difficultyText: {
        fontSize: 10,
        fontWeight: '600',
        textTransform: 'capitalize',
    },
    subtopicProgress: {
        flexDirection: 'row',
        alignItems: 'center',
    },
    subtopicProgressBar: {
        flex: 1,
        height: 6,
        backgroundColor: '#e5e7eb',
        borderRadius: 3,
        overflow: 'hidden',
    },
    subtopicProgressFill: {
        height: '100%',
        borderRadius: 3,
    },
    subtopicProgressText: {
        fontSize: 12,
        color: '#666',
        marginLeft: 8,
        minWidth: 35,
    },
    arrow: {
        fontSize: 18,
        color: '#ccc',
        marginLeft: 8,
    },
    subtopicStatus: {
        flexDirection: 'row',
        marginTop: 8,
        gap: 8,
    },
    statusTag: {
        fontSize: 11,
        color: '#666',
        backgroundColor: '#f3f4f6',
        paddingHorizontal: 8,
        paddingVertical: 4,
        borderRadius: 6,
    },
    completeCard: {
        backgroundColor: '#10b981',
        borderRadius: 16,
        padding: 24,
        alignItems: 'center',
        marginTop: 8,
    },
    completeEmoji: {
        fontSize: 48,
        marginBottom: 8,
    },
    completeTitle: {
        fontSize: 22,
        fontWeight: 'bold',
        color: '#fff',
        marginBottom: 4,
    },
    completeText: {
        fontSize: 14,
        color: 'rgba(255,255,255,0.9)',
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
    errorContainer: {
        flex: 1,
        justifyContent: 'center',
        alignItems: 'center',
        padding: 20,
    },
    errorText: {
        color: '#ff3b30',
        marginBottom: 16,
    },
    backButton: {
        paddingHorizontal: 20,
        paddingVertical: 10,
        backgroundColor: '#007AFF',
        borderRadius: 8,
    },
    backButtonText: {
        color: '#fff',
        fontWeight: '600',
    },
    emptyContainer: {
        padding: 40,
        alignItems: 'center',
        backgroundColor: '#fff',
        borderRadius: 12,
    },
    emptyText: {
        color: '#666',
    },
    takeTestButton: {
        flexDirection: 'row',
        alignItems: 'center',
        backgroundColor: '#FFFFFF',
        borderRadius: 12,
        padding: 16,
        marginHorizontal: 20,
        marginBottom: 16,
        borderWidth: 2,
        borderColor: '#007AFF',
        shadowColor: '#007AFF',
        shadowOffset: { width: 0, height: 2 },
        shadowOpacity: 0.1,
        shadowRadius: 4,
        elevation: 2,
    },
    takeTestIcon: {
        fontSize: 28,
        marginRight: 12,
    },
    takeTestContent: {
        flex: 1,
    },
    takeTestTitle: {
        fontSize: 16,
        fontWeight: '600',
        color: '#007AFF',
    },
    takeTestDesc: {
        fontSize: 13,
        color: '#64748B',
        marginTop: 2,
    },
    takeTestArrow: {
        fontSize: 20,
        color: '#007AFF',
        fontWeight: '600',
    },
});
