import React, { useState, useEffect, useCallback } from 'react';
import {
    View,
    Text,
    StyleSheet,
    TouchableOpacity,
    ScrollView,
    ActivityIndicator,
    Animated,
    Dimensions,
} from 'react-native';
import { useLocalSearchParams, router } from 'expo-router';
import { Ionicons } from '@expo/vector-icons';
import { studyService } from '../../src/services/study';
import { curriculumService } from '../../src/services/curriculum';
import { FlashcardDeck, FlashcardDeckListItem, FlashcardItem, TopicWithSubtopics } from '../../src/types';

const { width } = Dimensions.get('window');

/**
 * FlashcardsPage - Mobile Flashcard Viewer
 * 
 * Features:
 * - Browse flashcard decks by topic
 * - Tap-to-flip cards
 * - Swipe navigation
 * - Progress tracking
 */
export default function FlashcardsPage() {
    const { topicSlug } = useLocalSearchParams<{ topicSlug: string }>();

    // State
    const [loading, setLoading] = useState(true);
    const [loadingDeck, setLoadingDeck] = useState(false);
    const [error, setError] = useState<string | null>(null);
    const [topic, setTopic] = useState<TopicWithSubtopics | null>(null);
    const [deckList, setDeckList] = useState<FlashcardDeckListItem[]>([]);
    const [currentDeck, setCurrentDeck] = useState<FlashcardDeck | null>(null);
    const [currentIndex, setCurrentIndex] = useState(0);
    const [isFlipped, setIsFlipped] = useState(false);
    const [reviewedCards, setReviewedCards] = useState<Set<number>>(new Set());

    // Animation
    const flipAnim = useState(new Animated.Value(0))[0];

    useEffect(() => {
        if (topicSlug) {
            loadTopicData();
        }
    }, [topicSlug]);

    const loadTopicData = async () => {
        if (!topicSlug) return;
        setLoading(true);
        try {
            const topicData = await studyService.getTopic(topicSlug);
            setTopic(topicData);

            const decks = await studyService.listFlashcardDecks(topicData.id);
            setDeckList(decks);
        } catch (err) {
            console.error('Failed to load topic:', err);
            setError('Failed to load flashcard decks');
        } finally {
            setLoading(false);
        }
    };

    const loadDeck = async (subtopicId: string) => {
        setLoadingDeck(true);
        try {
            const deck = await studyService.getFlashcards(subtopicId);
            setCurrentDeck(deck);
            setCurrentIndex(0);
            setIsFlipped(false);
            setReviewedCards(new Set());
        } catch (err) {
            console.error('Failed to load deck:', err);
            setError('Failed to load flashcard deck');
        } finally {
            setLoadingDeck(false);
        }
    };

    const handleFlip = () => {
        const toValue = isFlipped ? 0 : 1;
        Animated.spring(flipAnim, {
            toValue,
            friction: 8,
            tension: 10,
            useNativeDriver: true,
        }).start();

        if (!isFlipped) {
            setReviewedCards(prev => new Set(prev).add(currentIndex));
        }
        setIsFlipped(!isFlipped);
    };

    const handleNext = () => {
        if (currentDeck && currentIndex < currentDeck.cards.length - 1) {
            setCurrentIndex(currentIndex + 1);
            setIsFlipped(false);
            flipAnim.setValue(0);
        }
    };

    const handlePrev = () => {
        if (currentIndex > 0) {
            setCurrentIndex(currentIndex - 1);
            setIsFlipped(false);
            flipAnim.setValue(0);
        }
    };

    const handleBackToList = () => {
        setCurrentDeck(null);
    };

    const frontAnimatedStyle = {
        transform: [
            {
                rotateY: flipAnim.interpolate({
                    inputRange: [0, 1],
                    outputRange: ['0deg', '180deg'],
                }),
            },
        ],
    };

    const backAnimatedStyle = {
        transform: [
            {
                rotateY: flipAnim.interpolate({
                    inputRange: [0, 1],
                    outputRange: ['180deg', '360deg'],
                }),
            },
        ],
    };

    const progress = currentDeck
        ? (reviewedCards.size / currentDeck.cards.length) * 100
        : 0;

    // Loading state
    if (loading) {
        return (
            <View style={styles.centered}>
                <ActivityIndicator size="large" color="#6366f1" />
                <Text style={styles.loadingText}>Loading flashcards...</Text>
            </View>
        );
    }

    // Error state
    if (error) {
        return (
            <View style={styles.centered}>
                <Ionicons name="alert-circle" size={48} color="#ef4444" />
                <Text style={styles.errorText}>{error}</Text>
                <TouchableOpacity style={styles.button} onPress={() => router.back()}>
                    <Text style={styles.buttonText}>Go Back</Text>
                </TouchableOpacity>
            </View>
        );
    }

    // Studying a deck
    if (currentDeck) {
        const currentCard = currentDeck.cards[currentIndex];

        return (
            <View style={styles.container}>
                {/* Header */}
                <View style={styles.header}>
                    <TouchableOpacity onPress={handleBackToList} style={styles.backButton}>
                        <Ionicons name="arrow-back" size={24} color="#fff" />
                    </TouchableOpacity>
                    <Text style={styles.title} numberOfLines={1}>{currentDeck.title}</Text>
                </View>

                {/* Progress */}
                <View style={styles.progressContainer}>
                    <View style={styles.progressBar}>
                        <View style={[styles.progressFill, { width: `${progress}%` }]} />
                    </View>
                    <Text style={styles.progressText}>
                        {reviewedCards.size} / {currentDeck.cards.length} reviewed
                    </Text>
                </View>

                {/* Flashcard */}
                {loadingDeck ? (
                    <View style={styles.cardContainer}>
                        <ActivityIndicator size="large" color="#6366f1" />
                    </View>
                ) : (
                    <TouchableOpacity
                        style={styles.cardContainer}
                        onPress={handleFlip}
                        activeOpacity={0.9}
                    >
                        {/* Front */}
                        <Animated.View style={[styles.card, styles.cardFront, frontAnimatedStyle]}>
                            <Ionicons name="bulb" size={32} color="#6366f1" style={styles.cardIcon} />
                            <Text style={styles.cardText}>{currentCard?.front}</Text>
                            <Text style={styles.flipHint}>Tap to reveal</Text>
                        </Animated.View>

                        {/* Back */}
                        <Animated.View style={[styles.card, styles.cardBack, backAnimatedStyle]}>
                            <Ionicons name="checkmark-circle" size={32} color="#10b981" style={styles.cardIcon} />
                            <Text style={styles.cardText}>{currentCard?.back}</Text>
                            <Text style={styles.flipHint}>Tap to flip back</Text>
                        </Animated.View>
                    </TouchableOpacity>
                )}

                {/* Navigation */}
                <View style={styles.navigation}>
                    <TouchableOpacity
                        style={[styles.navButton, currentIndex === 0 && styles.navButtonDisabled]}
                        onPress={handlePrev}
                        disabled={currentIndex === 0}
                    >
                        <Ionicons name="chevron-back" size={24} color="#fff" />
                        <Text style={styles.navButtonText}>Prev</Text>
                    </TouchableOpacity>

                    <Text style={styles.cardCount}>
                        {currentIndex + 1} / {currentDeck.cards.length}
                    </Text>

                    <TouchableOpacity
                        style={[styles.navButton, currentIndex >= currentDeck.cards.length - 1 && styles.navButtonDisabled]}
                        onPress={handleNext}
                        disabled={currentIndex >= currentDeck.cards.length - 1}
                    >
                        <Text style={styles.navButtonText}>Next</Text>
                        <Ionicons name="chevron-forward" size={24} color="#fff" />
                    </TouchableOpacity>
                </View>
            </View>
        );
    }

    // Deck list view
    return (
        <View style={styles.container}>
            {/* Header */}
            <View style={styles.header}>
                <TouchableOpacity onPress={() => router.back()} style={styles.backButton}>
                    <Ionicons name="arrow-back" size={24} color="#fff" />
                </TouchableOpacity>
                <Text style={styles.title}>Flashcards</Text>
            </View>

            <Text style={styles.subtitle}>{topic?.name}</Text>

            <ScrollView style={styles.deckList} showsVerticalScrollIndicator={false}>
                {deckList.map((deck) => (
                    <TouchableOpacity
                        key={deck.subtopic_id}
                        style={styles.deckCard}
                        onPress={() => loadDeck(deck.subtopic_id)}
                    >
                        <View style={styles.deckInfo}>
                            <Text style={styles.deckName}>{deck.subtopic_name}</Text>
                            <Text style={styles.deckCardCount}>
                                {deck.card_count > 0 ? `${deck.card_count} cards` : 'Not generated'}
                            </Text>
                        </View>
                        <Ionicons name="chevron-forward" size={24} color="#6366f1" />
                    </TouchableOpacity>
                ))}

                {deckList.length === 0 && (
                    <View style={styles.emptyState}>
                        <Ionicons name="layers-outline" size={48} color="#6b7280" />
                        <Text style={styles.emptyText}>No flashcard decks available</Text>
                    </View>
                )}
            </ScrollView>
        </View>
    );
}

const styles = StyleSheet.create({
    container: {
        flex: 1,
        backgroundColor: '#0f0f23',
        paddingTop: 50,
    },
    centered: {
        flex: 1,
        backgroundColor: '#0f0f23',
        justifyContent: 'center',
        alignItems: 'center',
        padding: 20,
    },
    header: {
        flexDirection: 'row',
        alignItems: 'center',
        paddingHorizontal: 16,
        marginBottom: 16,
    },
    backButton: {
        padding: 8,
        marginRight: 12,
    },
    title: {
        fontSize: 24,
        fontWeight: 'bold',
        color: '#fff',
        flex: 1,
    },
    subtitle: {
        fontSize: 16,
        color: '#9ca3af',
        paddingHorizontal: 16,
        marginBottom: 16,
    },
    loadingText: {
        color: '#9ca3af',
        marginTop: 12,
        fontSize: 16,
    },
    errorText: {
        color: '#ef4444',
        marginTop: 12,
        fontSize: 16,
        textAlign: 'center',
    },
    button: {
        backgroundColor: '#6366f1',
        paddingHorizontal: 24,
        paddingVertical: 12,
        borderRadius: 8,
        marginTop: 16,
    },
    buttonText: {
        color: '#fff',
        fontWeight: '600',
    },
    progressContainer: {
        paddingHorizontal: 16,
        marginBottom: 24,
    },
    progressBar: {
        height: 6,
        backgroundColor: 'rgba(255,255,255,0.1)',
        borderRadius: 3,
        overflow: 'hidden',
    },
    progressFill: {
        height: '100%',
        backgroundColor: '#6366f1',
        borderRadius: 3,
    },
    progressText: {
        color: '#9ca3af',
        fontSize: 12,
        marginTop: 8,
        textAlign: 'center',
    },
    cardContainer: {
        flex: 1,
        justifyContent: 'center',
        alignItems: 'center',
        paddingHorizontal: 20,
    },
    card: {
        width: width - 40,
        height: 280,
        backgroundColor: '#1a1a2e',
        borderRadius: 20,
        padding: 24,
        justifyContent: 'center',
        alignItems: 'center',
        position: 'absolute',
        backfaceVisibility: 'hidden',
        borderWidth: 2,
    },
    cardFront: {
        borderColor: 'rgba(99, 102, 241, 0.5)',
    },
    cardBack: {
        borderColor: 'rgba(16, 185, 129, 0.5)',
    },
    cardIcon: {
        marginBottom: 16,
    },
    cardText: {
        fontSize: 20,
        color: '#fff',
        textAlign: 'center',
        lineHeight: 28,
    },
    flipHint: {
        position: 'absolute',
        bottom: 20,
        color: '#6b7280',
        fontSize: 12,
    },
    navigation: {
        flexDirection: 'row',
        justifyContent: 'space-between',
        alignItems: 'center',
        paddingHorizontal: 16,
        paddingVertical: 20,
    },
    navButton: {
        flexDirection: 'row',
        alignItems: 'center',
        backgroundColor: '#6366f1',
        paddingHorizontal: 16,
        paddingVertical: 10,
        borderRadius: 8,
        gap: 4,
    },
    navButtonDisabled: {
        opacity: 0.5,
    },
    navButtonText: {
        color: '#fff',
        fontWeight: '600',
    },
    cardCount: {
        color: '#9ca3af',
        fontSize: 16,
    },
    deckList: {
        flex: 1,
        paddingHorizontal: 16,
    },
    deckCard: {
        backgroundColor: '#1a1a2e',
        borderRadius: 12,
        padding: 16,
        marginBottom: 12,
        flexDirection: 'row',
        alignItems: 'center',
        justifyContent: 'space-between',
    },
    deckInfo: {
        flex: 1,
    },
    deckName: {
        fontSize: 16,
        fontWeight: '600',
        color: '#fff',
        marginBottom: 4,
    },
    deckCardCount: {
        fontSize: 14,
        color: '#9ca3af',
    },
    emptyState: {
        alignItems: 'center',
        paddingVertical: 48,
    },
    emptyText: {
        color: '#6b7280',
        marginTop: 12,
        fontSize: 16,
    },
});
