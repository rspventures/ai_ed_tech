import React, { useEffect, useState } from 'react';
import {
    View,
    Text,
    StyleSheet,
    SafeAreaView,
    ScrollView,
    TouchableOpacity,
    ActivityIndicator,
    Alert,
} from 'react-native';
import { useRouter } from 'expo-router';
import * as DocumentPicker from 'expo-document-picker';
import { documentService, Document } from '../../src/services/documents';

export default function DocumentsScreen() {
    const router = useRouter();
    const [documents, setDocuments] = useState<Document[]>([]);
    const [loading, setLoading] = useState(true);
    const [uploading, setUploading] = useState(false);

    useEffect(() => {
        loadDocuments();
    }, []);

    const loadDocuments = async () => {
        try {
            setLoading(true);
            const data = await documentService.listDocuments();
            setDocuments(data.documents);
        } catch (error) {
            console.log('Error loading documents:', error);
        } finally {
            setLoading(false);
        }
    };

    const handleUpload = async () => {
        try {
            const result = await DocumentPicker.getDocumentAsync({
                type: ['application/pdf', 'text/plain'],
                copyToCacheDirectory: true,
            });

            if (result.canceled) return;

            setUploading(true);
            const file = result.assets[0];
            await documentService.uploadDocument(file);

            Alert.alert('Success', 'Document uploaded successfully!');
            loadDocuments();
        } catch (error) {
            console.log('Upload error:', error);
            Alert.alert('Error', 'Failed to upload document');
        } finally {
            setUploading(false);
        }
    };

    const getStatusColor = (status: string) => {
        switch (status) {
            case 'completed': return '#10B981';
            case 'processing': return '#F59E0B';
            case 'failed': return '#EF4444';
            default: return '#6B7280';
        }
    };

    return (
        <SafeAreaView style={styles.safeArea}>
            <View style={styles.header}>
                <TouchableOpacity onPress={() => router.back()} style={styles.backBtn}>
                    <Text style={styles.backIcon}>←</Text>
                </TouchableOpacity>
                <Text style={styles.headerTitle}>Study Documents</Text>
                <TouchableOpacity onPress={handleUpload} disabled={uploading}>
                    {uploading ? (
                        <ActivityIndicator color="#007AFF" />
                    ) : (
                        <Text style={styles.addBtn}>+ Add</Text>
                    )}
                </TouchableOpacity>
            </View>

            {loading ? (
                <View style={styles.loadingContainer}>
                    <ActivityIndicator size="large" color="#007AFF" />
                </View>
            ) : (
                <ScrollView style={styles.content}>
                    {documents.length === 0 ? (
                        <View style={styles.emptyContainer}>
                            <Text style={styles.emptyText}>No documents uploaded yet.</Text>
                            <Text style={styles.emptySubText}>Upload PDF notes to chat with them.</Text>
                            <TouchableOpacity style={styles.uploadBtn} onPress={handleUpload}>
                                <Text style={styles.uploadBtnText}>Upload Document</Text>
                            </TouchableOpacity>
                        </View>
                    ) : (
                        documents.map((doc) => (
                            <TouchableOpacity
                                key={doc.id}
                                style={styles.docCard}
                                onPress={() => router.push(`/documents/${doc.id}`)}
                            >
                                <View style={styles.docIcon}>
                                    <Text style={{ fontSize: 24 }}>📄</Text>
                                </View>
                                <View style={styles.docInfo}>
                                    <Text style={styles.docName} numberOfLines={1}>{doc.original_filename}</Text>
                                    <View style={styles.metaRow}>
                                        <View style={[styles.statusBadge, { backgroundColor: getStatusColor(doc.status) }]}>
                                            <Text style={styles.statusText}>{doc.status}</Text>
                                        </View>
                                        <Text style={styles.dateText}>
                                            {new Date(doc.created_at).toLocaleDateString()}
                                        </Text>
                                    </View>
                                </View>
                                <Text style={styles.chevron}>›</Text>
                            </TouchableOpacity>
                        ))
                    )}
                </ScrollView>
            )}
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
    addBtn: {
        color: '#007AFF',
        fontWeight: 'bold',
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
    emptyContainer: {
        flex: 1,
        alignItems: 'center',
        justifyContent: 'center',
        paddingTop: 100,
    },
    emptyText: {
        fontSize: 18,
        fontWeight: 'bold',
        color: '#1a1a2e',
        marginBottom: 8,
    },
    emptySubText: {
        color: '#666',
        marginBottom: 24,
    },
    uploadBtn: {
        backgroundColor: '#007AFF',
        paddingHorizontal: 24,
        paddingVertical: 12,
        borderRadius: 8,
    },
    uploadBtnText: {
        color: '#fff',
        fontWeight: 'bold',
    },
    docCard: {
        flexDirection: 'row',
        alignItems: 'center',
        backgroundColor: '#fff',
        padding: 16,
        borderRadius: 12,
        marginBottom: 12,
        shadowColor: '#000',
        shadowOffset: { width: 0, height: 2 },
        shadowOpacity: 0.05,
        shadowRadius: 4,
        elevation: 2,
    },
    docIcon: {
        width: 48,
        height: 48,
        backgroundColor: '#f0f9ff',
        borderRadius: 8,
        justifyContent: 'center',
        alignItems: 'center',
        marginRight: 16,
    },
    docInfo: {
        flex: 1,
    },
    docName: {
        fontSize: 16,
        fontWeight: '600',
        color: '#1a1a2e',
        marginBottom: 4,
    },
    metaRow: {
        flexDirection: 'row',
        alignItems: 'center',
    },
    statusBadge: {
        paddingHorizontal: 6,
        paddingVertical: 2,
        borderRadius: 4,
        marginRight: 8,
    },
    statusText: {
        color: '#fff',
        fontSize: 10,
        fontWeight: 'bold',
        textTransform: 'uppercase',
    },
    dateText: {
        fontSize: 12,
        color: '#999',
    },
    chevron: {
        fontSize: 24,
        color: '#ccc',
        marginLeft: 8,
    },
});
