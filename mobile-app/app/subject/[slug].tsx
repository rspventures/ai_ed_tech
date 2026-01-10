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
import { curriculumService } from '../../src/services/curriculum';
import { userService } from '../../src/services/user';
import { SubjectWithTopics, Topic, EnrichedProgress } from '../../src/types';

export default function SubjectDetailScreen() {
    const router = useRouter();
    const { slug } = useLocalSearchParams<{ slug: string }>();

    const [subject, setSubject] = useState<SubjectWithTopics | null>(null);
    const [filteredTopics, setFilteredTopics] = useState<Topic[]>([]);
    const [progress, setProgress] = useState<EnrichedProgress[]>([]);
    const [studentGrade, setStudentGrade] = useState<number>(1);
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

            // Fetch student profile to get grade level
            let gradeLevel = 1;
            try {
                const profile = await userService.getProfile();
                gradeLevel = profile.grade_level || 1;
                setStudentGrade(gradeLevel);
            } catch {
                console.log('Could not fetch profile, defaulting to grade 1');
            }

            const [subjectData, progressData] = await Promise.all([
                curriculumService.getSubject(slug!),
                curriculumService.getProgress(),
            ]);
            setSubject(subjectData);
            setProgress(progressData);

            // Filter topics by student's grade level
            if (subjectData.topics && subjectData.topics.length > 0) {
                const gradeFilteredTopics = subjectData.topics.filter(
                    (t: Topic) => t.grade_level === gradeLevel
                );
                setFilteredTopics(gradeFilteredTopics);
            } else {
                setFilteredTopics([]);
            }
        } catch (err) {
            console.log('Failed to load subject:', err);
            setError('Failed to load subject');
        } finally {
            setLoading(false);
        }
    };

    // Get mastery for a topic
    const getTopicMastery = (topicId: string): number => {
        const topicProgress = progress.find(p => p.topic_id === topicId);
        return topicProgress ? Math.round(topicProgress.mastery_level * 100) : 0;
    };

    // Get color for subject
    const getSubjectColor = (color: string): string => {
        const colorMap: Record<string, string> = {
            '#6366f1': '#6366f1',
            '#10b981': '#10b981',
            '#f59e0b': '#f59e0b',
            '#ef4444': '#ef4444',
        };
        return colorMap[color] || '#007AFF';
    };

    // Get status label based on mastery
    const getStatusLabel = (mastery: number): { label: string; color: string } => {
        if (mastery >= 80) return { label: 'Mastered', color: '#10b981' };
        if (mastery >= 50) return { label: 'In Progress', color: '#f59e0b' };
        if (mastery > 0) return { label: 'Started', color: '#6366f1' };
        return { label: 'New', color: '#9ca3af' };
    };

    if (loading) {
        return (
            <SafeAreaView style={styles.safeArea}>
                <View style={styles.loadingContainer}>
                    <ActivityIndicator size="large" color="#007AFF" />
                    <Text style={styles.loadingText}>Loading subject...</Text>
                </View>
            </SafeAreaView>
        );
    }

    if (error || !subject) {
        return (
            <SafeAreaView style={styles.safeArea}>
                <View style={styles.errorContainer}>
                    <Text style={styles.errorText}>{error || 'Subject not found'}</Text>
                    <TouchableOpacity style={styles.backButton} onPress={() => router.back()}>
                        <Text style={styles.backButtonText}>Go Back</Text>
                    </TouchableOpacity>
                </View>
            </SafeAreaView>
        );
    }

    const subjectColor = getSubjectColor(subject.color);

    return (
        <SafeAreaView style={styles.safeArea}>
            {/* Header */}
            <View style={styles.header}>
                <TouchableOpacity onPress={() => router.back()} style={styles.backBtn}>
                    <Text style={styles.backIcon}>←</Text>
                </TouchableOpacity>
                <Text style={styles.headerTitle}>{subject.name}</Text>
                <View style={{ width: 40 }} />
            </View>

            <ScrollView style={styles.content}>
                {/* Subject Card */}
                <View style={[styles.subjectCard, { borderLeftColor: subjectColor }]}>
                    <View style={[styles.subjectIcon, { backgroundColor: subjectColor }]}>
                        <Text style={styles.subjectIconText}>{subject.name.charAt(0)}</Text>
                    </View>
                    <View style={styles.subjectInfo}>
                        <Text style={styles.subjectName}>{subject.name}</Text>
                        <Text style={styles.subjectDesc}>
                            {subject.description || 'Explore topics and master new skills!'}
                        </Text>
                        <Text style={styles.topicCount}>
                            {filteredTopics.length} Topics (Grade {studentGrade})
                        </Text>
                    </View>
                </View>

                {/* Take Exam Button */}
                <TouchableOpacity
                    style={styles.takeExamButton}
                    onPress={() => router.push(`/exam/${slug}`)}
                >
                    <Text style={styles.takeExamIcon}>📚</Text>
                    <View style={styles.takeExamContent}>
                        <Text style={styles.takeExamTitle}>Take Subject Exam</Text>
                        <Text style={styles.takeExamDesc}>Select topics • Customizable questions</Text>
                    </View>
                    <Text style={styles.takeExamArrow}>→</Text>
                </TouchableOpacity>

                {/* Topics Section */}
                <Text style={styles.sectionTitle}>Topics for Grade {studentGrade}</Text>

                {filteredTopics.length > 0 ? (
                    filteredTopics.map((topic: Topic) => {
                        const mastery = getTopicMastery(topic.id);
                        const status = getStatusLabel(mastery);

                        return (
                            <TouchableOpacity
                                key={topic.id}
                                style={styles.topicCard}
                                onPress={() => {
                                    router.push(`/study/${topic.slug}`);
                                }}
                            >
                                <View style={styles.topicHeader}>
                                    <View style={styles.topicTitleRow}>
                                        <Text style={styles.topicName}>{topic.name}</Text>
                                        <View style={[styles.statusBadge, { backgroundColor: status.color + '20' }]}>
                                            <Text style={[styles.statusText, { color: status.color }]}>
                                                {status.label}
                                            </Text>
                                        </View>
                                    </View>
                                    <Text style={styles.topicDesc}>
                                        {topic.description || `Grade ${topic.grade_level}`}
                                    </Text>
                                </View>

                                {/* Progress */}
                                <View style={styles.progressContainer}>
                                    <View style={styles.progressHeader}>
                                        <Text style={styles.progressLabel}>Mastery</Text>
                                        <Text style={styles.progressValue}>{mastery}%</Text>
                                    </View>
                                    <View style={styles.progressBar}>
                                        <View
                                            style={[
                                                styles.progressFill,
                                                {
                                                    width: `${mastery}%`,
                                                    backgroundColor: status.color
                                                },
                                            ]}
                                        />
                                    </View>
                                </View>

                                {/* Arrow */}
                                <Text style={styles.arrow}>→</Text>
                            </TouchableOpacity>
                        );
                    })
                ) : (
                    <View style={styles.emptyContainer}>
                        <Text style={styles.emptyText}>No topics available yet.</Text>
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
    },
    content: {
        flex: 1,
        padding: 16,
    },
    subjectCard: {
        backgroundColor: '#fff',
        borderRadius: 16,
        padding: 20,
        marginBottom: 24,
        flexDirection: 'row',
        alignItems: 'center',
        borderLeftWidth: 4,
        shadowColor: '#000',
        shadowOffset: { width: 0, height: 2 },
        shadowOpacity: 0.05,
        shadowRadius: 4,
        elevation: 2,
    },
    subjectIcon: {
        width: 56,
        height: 56,
        borderRadius: 14,
        justifyContent: 'center',
        alignItems: 'center',
    },
    subjectIconText: {
        color: '#fff',
        fontSize: 24,
        fontWeight: 'bold',
    },
    subjectInfo: {
        marginLeft: 16,
        flex: 1,
    },
    subjectName: {
        fontSize: 22,
        fontWeight: 'bold',
        color: '#1a1a2e',
    },
    subjectDesc: {
        fontSize: 14,
        color: '#666',
        marginTop: 4,
    },
    topicCount: {
        fontSize: 12,
        color: '#007AFF',
        marginTop: 8,
        fontWeight: '600',
    },
    sectionTitle: {
        fontSize: 18,
        fontWeight: 'bold',
        color: '#1a1a2e',
        marginBottom: 16,
    },
    topicCard: {
        backgroundColor: '#fff',
        borderRadius: 12,
        padding: 16,
        marginBottom: 12,
        shadowColor: '#000',
        shadowOffset: { width: 0, height: 1 },
        shadowOpacity: 0.05,
        shadowRadius: 3,
        elevation: 1,
    },
    topicHeader: {
        marginBottom: 12,
    },
    topicTitleRow: {
        flexDirection: 'row',
        alignItems: 'center',
        justifyContent: 'space-between',
        marginBottom: 4,
    },
    topicName: {
        fontSize: 16,
        fontWeight: '600',
        color: '#1a1a2e',
        flex: 1,
    },
    statusBadge: {
        paddingHorizontal: 10,
        paddingVertical: 4,
        borderRadius: 12,
    },
    statusText: {
        fontSize: 12,
        fontWeight: '600',
    },
    topicDesc: {
        fontSize: 13,
        color: '#666',
    },
    progressContainer: {
        marginBottom: 8,
    },
    progressHeader: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        marginBottom: 6,
    },
    progressLabel: {
        fontSize: 12,
        color: '#666',
    },
    progressValue: {
        fontSize: 12,
        fontWeight: '600',
        color: '#1a1a2e',
    },
    progressBar: {
        height: 6,
        backgroundColor: '#e0e0e0',
        borderRadius: 3,
        overflow: 'hidden',
    },
    progressFill: {
        height: '100%',
        borderRadius: 3,
    },
    arrow: {
        position: 'absolute',
        right: 16,
        top: '50%',
        fontSize: 20,
        color: '#ccc',
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
    takeExamButton: {
        flexDirection: 'row',
        alignItems: 'center',
        backgroundColor: '#FFFFFF',
        borderRadius: 12,
        padding: 16,
        marginHorizontal: 20,
        marginBottom: 16,
        borderWidth: 2,
        borderColor: '#7C3AED',
        shadowColor: '#7C3AED',
        shadowOffset: { width: 0, height: 2 },
        shadowOpacity: 0.1,
        shadowRadius: 4,
        elevation: 2,
    },
    takeExamIcon: {
        fontSize: 28,
        marginRight: 12,
    },
    takeExamContent: {
        flex: 1,
    },
    takeExamTitle: {
        fontSize: 16,
        fontWeight: '600',
        color: '#7C3AED',
    },
    takeExamDesc: {
        fontSize: 13,
        color: '#64748B',
        marginTop: 2,
    },
    takeExamArrow: {
        fontSize: 20,
        color: '#7C3AED',
        fontWeight: '600',
    },
});
