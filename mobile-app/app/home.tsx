import React, { useEffect, useState } from 'react';
import {
    View,
    Text,
    TouchableOpacity,
    StyleSheet,
    SafeAreaView,
    ScrollView,
    ActivityIndicator,
    RefreshControl,
} from 'react-native';
import { useRouter } from 'expo-router';
import { useAuth } from '../src/context/AuthContext';
import { curriculumService } from '../src/services/curriculum';
import { Subject, EnrichedProgress } from '../src/types';

export default function HomeScreen() {
    const router = useRouter();
    const { user, signOut } = useAuth();

    const [subjects, setSubjects] = useState<Subject[]>([]);
    const [progress, setProgress] = useState<EnrichedProgress[]>([]);
    const [loading, setLoading] = useState(true);
    const [refreshing, setRefreshing] = useState(false);

    useEffect(() => {
        loadData();
    }, []);

    const loadData = async () => {
        try {
            const [subjectsData, progressData] = await Promise.all([
                curriculumService.getSubjects(),
                curriculumService.getProgress(),
            ]);
            setSubjects(subjectsData);
            setProgress(progressData);
        } catch (error) {
            console.log('Failed to load dashboard data:', error);
        } finally {
            setLoading(false);
            setRefreshing(false);
        }
    };

    const onRefresh = () => {
        setRefreshing(true);
        loadData();
    };

    const handleLogout = async () => {
        await signOut();
        router.replace('/login');
    };

    // Calculate stats from progress data
    const totalQuestions = progress.reduce((sum, p) => sum + p.questions_attempted, 0);
    const maxStreak = progress.reduce((max, p) => Math.max(max, p.current_streak), 0);
    const totalCorrect = progress.reduce((sum, p) => sum + p.questions_correct, 0);
    const accuracy = totalQuestions > 0 ? Math.round((totalCorrect / totalQuestions) * 100) : 0;

    // Get mastery for a subject
    const getSubjectMastery = (subjectName: string): number => {
        const subjectProgress = progress.filter(p => p.subject_name === subjectName);
        if (subjectProgress.length === 0) return 0;
        const avgMastery = subjectProgress.reduce((sum, p) => sum + p.mastery_level, 0) / subjectProgress.length;
        return Math.round(avgMastery * 100);
    };

    // Get color for subject
    const getSubjectColor = (color: string): string => {
        const colorMap: Record<string, string> = {
            '#6366f1': '#6366f1', // indigo
            '#10b981': '#10b981', // emerald
            '#f59e0b': '#f59e0b', // amber
            '#ef4444': '#ef4444', // red
        };
        return colorMap[color] || '#007AFF';
    };

    return (
        <SafeAreaView style={styles.safeArea}>
            {/* Header */}
            <View style={styles.header}>
                <View>
                    <Text style={styles.greeting}>Welcome back,</Text>
                    <Text style={styles.userName}>{user?.first_name} {user?.last_name}</Text>
                </View>

                <TouchableOpacity onPress={() => router.push('/settings')} style={styles.settingsBtn}>
                    <Text style={styles.settingsIcon}>⚙️</Text>
                </TouchableOpacity>
            </View>

            <ScrollView
                style={styles.content}
                refreshControl={
                    <RefreshControl refreshing={refreshing} onRefresh={onRefresh} />
                }
            >
                {/* Stats Row */}
                <View style={styles.statsRow}>
                    <View style={styles.statCard}>
                        <Text style={styles.statValue}>{totalQuestions}</Text>
                        <Text style={styles.statLabel}>Questions</Text>
                    </View>
                    <View style={styles.statCard}>
                        <Text style={styles.statValue}>{maxStreak} 🔥</Text>
                        <Text style={styles.statLabel}>Streak</Text>
                    </View>
                    <View style={styles.statCard}>
                        <Text style={styles.statValue}>{accuracy}%</Text>
                        <Text style={styles.statLabel}>Accuracy</Text>
                    </View>
                </View>

                {/* Study Tools Section */}
                <View style={styles.toolsSection}>
                    <Text style={styles.sectionTitle}>Tools</Text>
                    <TouchableOpacity
                        style={styles.toolCard}
                        onPress={() => router.push('/documents')}
                    >
                        <Text style={styles.toolIcon}>📄</Text>
                        <View>
                            <Text style={styles.toolTitle}>Documents</Text>
                            <Text style={styles.toolDesc}>Upload & chat with PDFs</Text>
                        </View>
                    </TouchableOpacity>
                </View>

                {/* Subjects Section */}
                <Text style={styles.sectionTitle}>Your Subjects</Text>

                {loading ? (
                    <View style={styles.loadingContainer}>
                        <ActivityIndicator size="large" color="#007AFF" />
                    </View>
                ) : subjects.length === 0 ? (
                    <View style={styles.emptyContainer}>
                        <Text style={styles.emptyText}>No subjects available yet.</Text>
                    </View>
                ) : (
                    subjects.map((subject) => {
                        const mastery = getSubjectMastery(subject.name);
                        const subjectColor = getSubjectColor(subject.color);

                        return (
                            <TouchableOpacity
                                key={subject.id}
                                style={styles.subjectCard}
                                onPress={() => router.push(`/subject/${subject.slug}`)}
                            >
                                <View style={styles.subjectHeader}>
                                    <View style={[styles.subjectIcon, { backgroundColor: subjectColor }]}>
                                        <Text style={styles.subjectIconText}>
                                            {subject.name.charAt(0)}
                                        </Text>
                                    </View>
                                    <View style={styles.subjectInfo}>
                                        <Text style={styles.subjectName}>{subject.name}</Text>
                                        <Text style={styles.subjectDesc}>
                                            {subject.description || 'Start learning today!'}
                                        </Text>
                                    </View>
                                </View>

                                {/* Progress Bar */}
                                <View style={styles.progressContainer}>
                                    <View style={styles.progressHeader}>
                                        <Text style={styles.progressLabel}>Mastery</Text>
                                        <Text style={styles.progressValue}>{mastery}%</Text>
                                    </View>
                                    <View style={styles.progressBar}>
                                        <View
                                            style={[
                                                styles.progressFill,
                                                { width: `${mastery}%`, backgroundColor: subjectColor },
                                            ]}
                                        />
                                    </View>
                                </View>
                            </TouchableOpacity>
                        );
                    })
                )}
            </ScrollView>
        </SafeAreaView >
    );
}

const styles = StyleSheet.create({
    safeArea: {
        flex: 1,
        backgroundColor: '#f5f7fa',
    },
    header: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
        padding: 20,
        paddingTop: 10,
        backgroundColor: '#fff',
        borderBottomWidth: 1,
        borderBottomColor: '#e0e0e0',
    },
    greeting: {
        fontSize: 14,
        color: '#666',
    },
    userName: {
        fontSize: 20,
        fontWeight: 'bold',
        color: '#1a1a2e',
    },
    settingsBtn: {
        padding: 8,
        borderRadius: 20,
        backgroundColor: '#f5f7fa',
    },
    settingsIcon: {
        fontSize: 24,
    },
    content: {
        flex: 1,
        padding: 16,
    },
    statsRow: {
        flexDirection: 'row',
        gap: 12,
        marginBottom: 24,
    },
    statCard: {
        flex: 1,
        backgroundColor: '#fff',
        borderRadius: 12,
        padding: 16,
        alignItems: 'center',
        shadowColor: '#000',
        shadowOffset: { width: 0, height: 2 },
        shadowOpacity: 0.05,
        shadowRadius: 4,
        elevation: 2,
    },
    statValue: {
        fontSize: 24,
        fontWeight: 'bold',
        color: '#1a1a2e',
    },
    statLabel: {
        fontSize: 12,
        color: '#666',
        marginTop: 4,
    },
    toolsSection: {
        marginBottom: 24,
    },
    toolCard: {
        flexDirection: 'row',
        alignItems: 'center',
        backgroundColor: '#fff',
        padding: 16,
        borderRadius: 12,
        shadowColor: '#000',
        shadowOffset: { width: 0, height: 2 },
        shadowOpacity: 0.05,
        shadowRadius: 4,
        elevation: 2,
    },
    toolIcon: {
        fontSize: 24,
        marginRight: 16,
    },
    toolTitle: {
        fontSize: 16,
        fontWeight: 'bold',
        color: '#1a1a2e',
    },
    toolDesc: {
        fontSize: 12,
        color: '#666',
    },
    sectionTitle: {
        fontSize: 18,
        fontWeight: 'bold',
        color: '#1a1a2e',
        marginBottom: 16,
    },
    loadingContainer: {
        padding: 40,
        alignItems: 'center',
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
    subjectCard: {
        backgroundColor: '#fff',
        borderRadius: 16,
        padding: 16,
        marginBottom: 12,
        shadowColor: '#000',
        shadowOffset: { width: 0, height: 2 },
        shadowOpacity: 0.05,
        shadowRadius: 4,
        elevation: 2,
    },
    subjectHeader: {
        flexDirection: 'row',
        alignItems: 'center',
        marginBottom: 16,
    },
    subjectIcon: {
        width: 48,
        height: 48,
        borderRadius: 12,
        justifyContent: 'center',
        alignItems: 'center',
    },
    subjectIconText: {
        color: '#fff',
        fontSize: 20,
        fontWeight: 'bold',
    },
    subjectInfo: {
        marginLeft: 12,
        flex: 1,
    },
    subjectName: {
        fontSize: 18,
        fontWeight: '600',
        color: '#1a1a2e',
    },
    subjectDesc: {
        fontSize: 14,
        color: '#666',
        marginTop: 2,
    },
    progressContainer: {
        marginTop: 8,
    },
    progressHeader: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        marginBottom: 8,
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
        height: 8,
        backgroundColor: '#e0e0e0',
        borderRadius: 4,
        overflow: 'hidden',
    },
    progressFill: {
        height: '100%',
        borderRadius: 4,
    },
});
