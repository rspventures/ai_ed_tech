import React, { useEffect, useState } from 'react';
import {
    View,
    Text,
    StyleSheet,
    SafeAreaView,
    ScrollView,
    TouchableOpacity,
    TextInput,
    Alert,
    ActivityIndicator,
    Switch
} from 'react-native';
import { useRouter } from 'expo-router';
import { userService, StudentProfile } from '../src/services/user';
import { useAuth } from '../src/context/AuthContext';

const AVATARS = [
    { id: 'owl', emoji: '🦉', name: 'Wise Owl', color: '#8B5CF6' },
    { id: 'robot', emoji: '🤖', name: 'Smart Bot', color: '#3B82F6' },
    { id: 'fox', emoji: '🦊', name: 'Clever Fox', color: '#F97316' },
    { id: 'cat', emoji: '🐱', name: 'Curious Cat', color: '#EC4899' },
    { id: 'dog', emoji: '🐕', name: 'Loyal Pup', color: '#10B981' },
    { id: 'dragon', emoji: '🐉', name: 'Magic Dragon', color: '#EF4444' },
];

const GRADES = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12];

const THEME_COLORS = [
    '#6366f1', '#8B5CF6', '#EC4899', '#EF4444',
    '#F97316', '#10B981', '#3B82F6', '#06B6D4'
];

export default function SettingsScreen() {
    const router = useRouter();
    const { signOut } = useAuth();

    const [profile, setProfile] = useState<StudentProfile | null>(null);
    const [loading, setLoading] = useState(true);
    const [saving, setSaving] = useState(false);

    // Form state
    const [displayName, setDisplayName] = useState('');
    const [gradeLevel, setGradeLevel] = useState(3);
    const [selectedAvatar, setSelectedAvatar] = useState('');
    const [themeColor, setThemeColor] = useState('#6366f1');

    useEffect(() => {
        loadProfile();
    }, []);

    const loadProfile = async () => {
        try {
            setLoading(true);
            const data = await userService.getProfile();
            setProfile(data);
            setDisplayName(data.display_name || '');
            setGradeLevel(data.grade_level || 3);
            setSelectedAvatar(data.preferences?.avatar_id || data.avatar_url || 'owl');
            setThemeColor(data.theme_color || '#6366f1');
        } catch (error) {
            console.log('Failed to load profile:', error);
            // Alert.alert('Error', 'Could not load profile');
        } finally {
            setLoading(false);
        }
    };

    const handleSave = async () => {
        try {
            setSaving(true);
            await userService.updateProfile({
                display_name: displayName,
                grade_level: gradeLevel,
                theme_color: themeColor,
                avatar_url: selectedAvatar,
                preferences: {
                    ...(profile?.preferences || {}),
                    avatar_id: selectedAvatar
                }
            });
            Alert.alert('Success', 'Settings saved successfully!');

            // Refresh local profile data
            const updated = await userService.getProfile();
            setProfile(updated);

        } catch (error) {
            console.log('Save failed:', error);
            Alert.alert('Error', 'Failed to save settings.');
        } finally {
            setSaving(false);
        }
    };

    const handleLogout = async () => {
        Alert.alert(
            'Logout',
            'Are you sure you want to logout?',
            [
                { text: 'Cancel', style: 'cancel' },
                {
                    text: 'Logout',
                    style: 'destructive',
                    onPress: async () => {
                        await signOut();
                        router.replace('/login');
                    }
                }
            ]
        );
    };

    if (loading) {
        return (
            <SafeAreaView style={styles.safeArea}>
                <View style={styles.loadingContainer}>
                    <ActivityIndicator size="large" color="#007AFF" />
                </View>
            </SafeAreaView>
        );
    }

    return (
        <SafeAreaView style={styles.safeArea}>
            <View style={styles.header}>
                <TouchableOpacity onPress={() => router.back()} style={styles.backBtn}>
                    <Text style={styles.backIcon}>←</Text>
                </TouchableOpacity>
                <Text style={styles.headerTitle}>Settings</Text>
                <TouchableOpacity onPress={handleSave} disabled={saving} style={styles.saveBtn}>
                    {saving ? <ActivityIndicator color="#007AFF" size="small" /> : <Text style={styles.saveText}>Save</Text>}
                </TouchableOpacity>
            </View>

            <ScrollView style={styles.content}>
                {/* Profile Section */}
                <View style={styles.section}>
                    <Text style={styles.sectionTitle}>Profile</Text>
                    <View style={styles.card}>
                        <Text style={styles.label}>Display Name</Text>
                        <TextInput
                            style={styles.input}
                            value={displayName}
                            onChangeText={setDisplayName}
                            placeholder="Your Nickname"
                        />

                        <Text style={[styles.label, { marginTop: 16 }]}>Full Name</Text>
                        <TextInput
                            style={[styles.input, { backgroundColor: '#f0f0f0', color: '#888' }]}
                            value={profile ? `${profile.first_name} ${profile.last_name}` : ''}
                            editable={false}
                        />
                    </View>
                </View>

                {/* Academic Section */}
                <View style={styles.section}>
                    <Text style={styles.sectionTitle}>Academic Level</Text>
                    <View style={styles.card}>
                        <Text style={styles.label}>Grade Level: {gradeLevel}</Text>
                        <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.gradeScroll}>
                            {GRADES.map(g => (
                                <TouchableOpacity
                                    key={g}
                                    style={[
                                        styles.gradeBtn,
                                        gradeLevel === g && styles.gradeBtnActive,
                                        { borderColor: themeColor }
                                    ]}
                                    onPress={() => setGradeLevel(g)}
                                >
                                    <Text style={[
                                        styles.gradeText,
                                        gradeLevel === g && styles.gradeTextActive
                                    ]}>{g}</Text>
                                </TouchableOpacity>
                            ))}
                        </ScrollView>
                    </View>
                </View>

                {/* Appearance Section */}
                <View style={styles.section}>
                    <Text style={styles.sectionTitle}>Appearance</Text>
                    <View style={styles.card}>

                        {/* Avatar */}
                        <Text style={styles.label}>Choose Avatar</Text>
                        <ScrollView horizontal showsHorizontalScrollIndicator={false} style={styles.avatarScroll}>
                            {AVATARS.map(avatar => (
                                <TouchableOpacity
                                    key={avatar.id}
                                    style={[
                                        styles.avatarBtn,
                                        selectedAvatar === avatar.id && styles.avatarBtnActive
                                    ]}
                                    onPress={() => setSelectedAvatar(avatar.id)}
                                >
                                    <Text style={styles.avatarEmoji}>{avatar.emoji}</Text>
                                    <View style={[styles.avatarBadge, { backgroundColor: avatar.color }]} />
                                </TouchableOpacity>
                            ))}
                        </ScrollView>

                        {/* Theme Color */}
                        <Text style={[styles.label, { marginTop: 24 }]}>Theme Color</Text>
                        <View style={styles.colorRow}>
                            {THEME_COLORS.map(color => (
                                <TouchableOpacity
                                    key={color}
                                    style={[
                                        styles.colorBtn,
                                        { backgroundColor: color },
                                        themeColor === color && styles.colorBtnActive
                                    ]}
                                    onPress={() => setThemeColor(color)}
                                />
                            ))}
                        </View>
                    </View>
                </View>

                {/* Logout Button */}
                <TouchableOpacity style={styles.logoutBtn} onPress={handleLogout}>
                    <Text style={styles.logoutText}>Log Out</Text>
                </TouchableOpacity>

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
    saveBtn: {
        paddingHorizontal: 12,
        paddingVertical: 6,
    },
    saveText: {
        color: '#007AFF',
        fontWeight: '600',
        fontSize: 16,
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
    section: {
        marginBottom: 24,
    },
    sectionTitle: {
        fontSize: 18,
        fontWeight: 'bold',
        color: '#1a1a2e',
        marginBottom: 12,
        marginLeft: 4,
    },
    card: {
        backgroundColor: '#fff',
        borderRadius: 16,
        padding: 16,
        shadowColor: '#000',
        shadowOffset: { width: 0, height: 2 },
        shadowOpacity: 0.05,
        shadowRadius: 4,
        elevation: 2,
    },
    label: {
        fontSize: 14,
        fontWeight: '600',
        color: '#666',
        marginBottom: 8,
    },
    input: {
        backgroundColor: '#f9fafb',
        borderWidth: 1,
        borderColor: '#e5e7eb',
        borderRadius: 12,
        padding: 12,
        fontSize: 16,
        color: '#1f2937',
    },
    gradeScroll: {
        marginTop: 8,
    },
    gradeBtn: {
        width: 44,
        height: 44,
        borderRadius: 22,
        borderWidth: 2,
        borderColor: '#e5e7eb',
        justifyContent: 'center',
        alignItems: 'center',
        marginRight: 10,
        backgroundColor: '#fff',
    },
    gradeBtnActive: {
        backgroundColor: '#f0f9ff',
        borderColor: '#007AFF',
    },
    gradeText: {
        fontSize: 16,
        fontWeight: '600',
        color: '#666',
    },
    gradeTextActive: {
        color: '#007AFF',
    },
    avatarScroll: {
        marginTop: 8,
        paddingBottom: 8,
    },
    avatarBtn: {
        width: 64,
        height: 64,
        borderRadius: 32,
        backgroundColor: '#f9fafb',
        justifyContent: 'center',
        alignItems: 'center',
        marginRight: 12,
        borderWidth: 2,
        borderColor: 'transparent',
    },
    avatarBtnActive: {
        borderColor: '#007AFF',
        backgroundColor: '#fff',
    },
    avatarEmoji: {
        fontSize: 32,
    },
    avatarBadge: {
        position: 'absolute',
        bottom: 0,
        right: 0,
        width: 12,
        height: 12,
        borderRadius: 6,
        borderWidth: 1,
        borderColor: '#fff',
    },
    colorRow: {
        flexDirection: 'row',
        flexWrap: 'wrap',
        gap: 12,
    },
    colorBtn: {
        width: 40,
        height: 40,
        borderRadius: 20,
    },
    colorBtnActive: {
        borderWidth: 3,
        borderColor: '#fff',
        shadowColor: '#000',
        shadowOffset: { width: 0, height: 2 },
        shadowOpacity: 0.2,
        shadowRadius: 4,
        elevation: 4,
    },
    logoutBtn: {
        backgroundColor: '#fff',
        borderRadius: 12,
        padding: 16,
        alignItems: 'center',
        marginTop: 8,
        borderWidth: 1,
        borderColor: '#fee2e2',
    },
    logoutText: {
        color: '#ef4444',
        fontSize: 16,
        fontWeight: '600',
    },
});
