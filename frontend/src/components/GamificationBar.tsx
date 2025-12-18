/**
 * GamificationBar - Displays XP, level, and streak in a compact header bar
 */
import { useState, useEffect } from 'react'
import {
    Flame,
    Star,
    TrendingUp,
    Sparkles,
    Trophy
} from 'lucide-react'
import { gamificationService, GamificationStats, LEVEL_NAMES } from '@/services/gamification'

interface GamificationBarProps {
    compact?: boolean
}

export default function GamificationBar({ compact = false }: GamificationBarProps) {
    const [stats, setStats] = useState<GamificationStats | null>(null)
    const [loading, setLoading] = useState(true)

    useEffect(() => {
        loadStats()
    }, [])

    const loadStats = async () => {
        try {
            const data = await gamificationService.getStats()
            setStats(data)
        } catch (err) {
            console.error('Failed to load gamification stats:', err)
        } finally {
            setLoading(false)
        }
    }

    if (loading || !stats) {
        return (
            <div className="flex items-center gap-4 animate-pulse">
                <div className="w-20 h-8 bg-white/10 rounded-lg"></div>
                <div className="w-16 h-8 bg-white/10 rounded-lg"></div>
            </div>
        )
    }

    const levelName = LEVEL_NAMES[stats.level] || `Level ${stats.level}`

    if (compact) {
        return (
            <div className="flex items-center gap-3">
                {/* Streak */}
                <div className={`flex items-center gap-1.5 px-2.5 py-1.5 rounded-lg ${stats.current_streak > 0
                        ? 'bg-orange-500/20 text-orange-400'
                        : 'bg-gray-500/20 text-gray-400'
                    }`}>
                    <Flame className={`w-4 h-4 ${stats.current_streak > 0 ? 'animate-pulse' : ''}`} />
                    <span className="text-sm font-bold">{stats.current_streak}</span>
                </div>

                {/* XP */}
                <div className="flex items-center gap-1.5 px-2.5 py-1.5 bg-purple-500/20 text-purple-400 rounded-lg">
                    <Star className="w-4 h-4" />
                    <span className="text-sm font-bold">{stats.xp_total}</span>
                </div>
            </div>
        )
    }

    return (
        <div className="flex items-center gap-4">
            {/* Streak Display */}
            <div className={`flex items-center gap-2 px-3 py-2 rounded-xl transition-all ${stats.current_streak > 0
                    ? 'bg-gradient-to-r from-orange-500/20 to-red-500/20 border border-orange-500/30'
                    : 'bg-gray-500/10 border border-gray-500/20'
                }`}>
                <div className={`w-8 h-8 rounded-lg flex items-center justify-center ${stats.current_streak > 0
                        ? 'bg-orange-500/30'
                        : 'bg-gray-500/20'
                    }`}>
                    <Flame className={`w-5 h-5 ${stats.current_streak > 0
                            ? 'text-orange-400 animate-pulse'
                            : 'text-gray-500'
                        }`} />
                </div>
                <div>
                    <p className={`text-lg font-bold ${stats.current_streak > 0 ? 'text-orange-400' : 'text-gray-400'
                        }`}>
                        {stats.current_streak}
                    </p>
                    <p className="text-xs text-gray-500">day streak</p>
                </div>
            </div>

            {/* Level & XP */}
            <div className="flex items-center gap-3 px-3 py-2 bg-gradient-to-r from-purple-500/20 to-blue-500/20 border border-purple-500/30 rounded-xl">
                {/* Level Badge */}
                <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-purple-600 to-blue-600 flex items-center justify-center shadow-lg shadow-purple-500/20">
                    <span className="text-lg font-bold text-white">{stats.level}</span>
                </div>

                <div className="flex flex-col">
                    <div className="flex items-center gap-2">
                        <span className="text-sm font-semibold text-white">{levelName}</span>
                        <Sparkles className="w-3 h-3 text-yellow-400" />
                    </div>

                    {/* XP Progress Bar */}
                    <div className="flex items-center gap-2">
                        <div className="w-24 h-2 bg-black/30 rounded-full overflow-hidden">
                            <div
                                className="h-full bg-gradient-to-r from-purple-500 to-blue-500 transition-all duration-500"
                                style={{ width: `${stats.level_progress * 100}%` }}
                            />
                        </div>
                        <span className="text-xs text-gray-400">
                            {stats.xp_to_next_level} XP to next
                        </span>
                    </div>
                </div>
            </div>

            {/* Total XP Badge */}
            <div className="flex items-center gap-2 px-3 py-2 bg-yellow-500/10 border border-yellow-500/30 rounded-xl">
                <Trophy className="w-5 h-5 text-yellow-400" />
                <div>
                    <p className="text-lg font-bold text-yellow-400">{stats.xp_total}</p>
                    <p className="text-xs text-gray-500">Total XP</p>
                </div>
            </div>
        </div>
    )
}
