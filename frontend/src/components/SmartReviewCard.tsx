import React, { useState, useEffect } from 'react';
import { useNavigate } from 'react-router-dom';
import {
    Brain,
    Sparkles,
    Clock,
    Target,
    ChevronRight,
    Loader2,
    AlertCircle,
    CheckCircle2,
    Flame
} from 'lucide-react';
import api from '@/services/api';

interface ReviewItem {
    subtopic_id: string;
    subtopic_name: string;
    topic_name: string;
    subject_name: string;
    mastery_level: number;
    days_since_review: number;
    priority: 'high' | 'medium' | 'low';
    review_reason: string;
}

interface DailyReview {
    items: ReviewItem[];
    total_due: number;
    ai_insight: string;
    high_priority_count: number;
}

const SmartReviewCard: React.FC = () => {
    const navigate = useNavigate();
    const [loading, setLoading] = useState(true);
    const [error, setError] = useState<string | null>(null);
    const [review, setReview] = useState<DailyReview | null>(null);

    useEffect(() => {
        fetchDailyReview();
    }, []);

    const fetchDailyReview = async () => {
        try {
            setLoading(true);
            setError(null);
            const response = await api.get('/review/daily');
            setReview(response.data);
        } catch (err: any) {
            // Silently fail if no reviews - this is expected for new users
            if (err.response?.status !== 404) {
                setError(err.response?.data?.detail || 'Could not load reviews');
            }
            setReview(null);
        } finally {
            setLoading(false);
        }
    };

    const getPriorityColor = (priority: string) => {
        switch (priority) {
            case 'high': return 'text-red-400 bg-red-500/20';
            case 'medium': return 'text-yellow-400 bg-yellow-500/20';
            default: return 'text-green-400 bg-green-500/20';
        }
    };

    const getMasteryColor = (level: number) => {
        if (level >= 0.8) return 'from-green-500 to-emerald-500';
        if (level >= 0.6) return 'from-blue-500 to-cyan-500';
        if (level >= 0.4) return 'from-yellow-500 to-orange-500';
        return 'from-red-500 to-pink-500';
    };

    if (loading) {
        return (
            <div className="bg-gradient-to-br from-purple-900/30 to-blue-900/30 rounded-2xl border border-purple-500/20 p-6">
                <div className="flex items-center justify-center py-8">
                    <Loader2 className="w-8 h-8 text-purple-400 animate-spin" />
                </div>
            </div>
        );
    }

    if (error) {
        return (
            <div className="bg-gradient-to-br from-purple-900/30 to-blue-900/30 rounded-2xl border border-purple-500/20 p-6">
                <div className="flex items-center gap-3 text-gray-400">
                    <AlertCircle className="w-5 h-5" />
                    <span>{error}</span>
                </div>
            </div>
        );
    }

    if (!review || review.total_due === 0) {
        return (
            <div className="bg-gradient-to-br from-green-900/30 to-emerald-900/30 rounded-2xl border border-green-500/20 p-6">
                <div className="flex items-center gap-4">
                    <div className="w-14 h-14 rounded-2xl bg-green-500/20 flex items-center justify-center">
                        <CheckCircle2 className="w-7 h-7 text-green-400" />
                    </div>
                    <div>
                        <h3 className="text-lg font-semibold text-white">All Caught Up! 🎉</h3>
                        <p className="text-sm text-gray-400">
                            No topics due for review. Keep learning new things!
                        </p>
                    </div>
                </div>
            </div>
        );
    }

    return (
        <div className="bg-gradient-to-br from-purple-900/30 to-blue-900/30 rounded-2xl border border-purple-500/20 overflow-hidden">
            {/* Header */}
            <div className="p-6 border-b border-white/10">
                <div className="flex items-center justify-between">
                    <div className="flex items-center gap-4">
                        <div className="w-14 h-14 rounded-2xl bg-gradient-to-br from-purple-600 to-blue-600 flex items-center justify-center shadow-lg shadow-purple-500/30">
                            <Brain className="w-7 h-7 text-white" />
                        </div>
                        <div>
                            <h3 className="text-lg font-semibold text-white flex items-center gap-2">
                                Smart Review
                                <Sparkles className="w-4 h-4 text-yellow-400" />
                            </h3>
                            <p className="text-sm text-gray-400">
                                {review.total_due} topic{review.total_due !== 1 ? 's' : ''} ready for review
                            </p>
                        </div>
                    </div>

                    {review.high_priority_count > 0 && (
                        <div className="flex items-center gap-2 px-3 py-1.5 bg-red-500/20 rounded-lg">
                            <Flame className="w-4 h-4 text-red-400" />
                            <span className="text-sm font-medium text-red-400">
                                {review.high_priority_count} urgent
                            </span>
                        </div>
                    )}
                </div>

                {/* AI Insight */}
                <div className="mt-4 p-4 bg-white/5 rounded-xl border border-white/10">
                    <p className="text-sm text-gray-300 leading-relaxed">
                        {review.ai_insight}
                    </p>
                </div>
            </div>

            {/* Review Items */}
            <div className="p-4 space-y-3 max-h-[300px] overflow-y-auto">
                {review.items.slice(0, 5).map((item) => (
                    <button
                        key={item.subtopic_id}
                        onClick={() => navigate(`/study?subtopic=${item.subtopic_id}`)}
                        className="w-full flex items-center gap-4 p-4 bg-black/20 rounded-xl hover:bg-black/40 transition-all group"
                    >
                        {/* Mastery indicator */}
                        <div className="relative w-12 h-12 flex-shrink-0">
                            <div className={`absolute inset-0 rounded-xl bg-gradient-to-br ${getMasteryColor(item.mastery_level)} opacity-20`} />
                            <div className="absolute inset-0 flex items-center justify-center">
                                <span className="text-lg font-bold">
                                    {Math.round(item.mastery_level * 100)}%
                                </span>
                            </div>
                        </div>

                        {/* Info */}
                        <div className="flex-1 text-left">
                            <h4 className="font-medium text-white group-hover:text-purple-300 transition-colors">
                                {item.subtopic_name}
                            </h4>
                            <p className="text-xs text-gray-500">
                                {item.subject_name} • {item.topic_name}
                            </p>
                            <div className="flex items-center gap-3 mt-1">
                                <span className={`text-xs px-2 py-0.5 rounded-full ${getPriorityColor(item.priority)}`}>
                                    {item.priority}
                                </span>
                                <span className="text-xs text-gray-500 flex items-center gap-1">
                                    <Clock className="w-3 h-3" />
                                    {item.days_since_review}d ago
                                </span>
                            </div>
                        </div>

                        {/* Arrow */}
                        <ChevronRight className="w-5 h-5 text-gray-500 group-hover:text-purple-400 group-hover:translate-x-1 transition-all" />
                    </button>
                ))}
            </div>

            {/* Footer */}
            {review.total_due > 5 && (
                <div className="p-4 border-t border-white/10">
                    <button
                        onClick={() => navigate('/review')}
                        className="w-full flex items-center justify-center gap-2 py-3 bg-purple-600 hover:bg-purple-700 rounded-xl font-medium transition-colors"
                    >
                        <Target className="w-4 h-4" />
                        Start Review Session ({review.total_due} topics)
                    </button>
                </div>
            )}
        </div>
    );
};

export default SmartReviewCard;
