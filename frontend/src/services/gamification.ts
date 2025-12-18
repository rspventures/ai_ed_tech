/**
 * Gamification Service - API client for XP, levels, and streaks
 */
import { api } from './api'

export interface GamificationStats {
    xp_total: number
    level: number
    level_progress: number  // 0.0 to 1.0
    xp_to_next_level: number
    current_streak: number
    longest_streak: number
    last_activity: string | null
}

export interface XPAwardResponse {
    xp_earned: number
    new_xp_total: number
    level_up: boolean
    new_level: number
    xp_to_next_level: number
    current_streak: number
}

export interface StreakResponse {
    current_streak: number
    longest_streak: number
    bonus_xp: number
    message: string
    xp_total: number
    level: number
}

// Level names for display
export const LEVEL_NAMES: Record<number, string> = {
    1: 'Curious Explorer',
    2: 'Eager Learner',
    3: 'Rising Star',
    4: 'Knowledge Seeker',
    5: 'Smart Cookie',
    6: 'Bright Mind',
    7: 'Super Scholar',
    8: 'Brain Champion',
    9: 'Wisdom Master',
    10: 'Learning Legend',
    11: 'Genius Hero',
    12: 'Ultimate Scholar',
    13: 'Grand Master',
    14: 'Enlightened One',
    15: 'Supreme Sage',
}

// Level XP thresholds (should match backend)
export const LEVEL_THRESHOLDS: Record<number, number> = {
    1: 0,
    2: 100,
    3: 250,
    4: 500,
    5: 800,
    6: 1200,
    7: 1700,
    8: 2300,
    9: 3000,
    10: 4000,
    11: 5200,
    12: 6600,
    13: 8200,
    14: 10000,
    15: 12000,
}

export const gamificationService = {
    /**
     * Get the current student's gamification stats
     */
    async getStats(): Promise<GamificationStats> {
        const response = await api.get('/gamification/stats')
        return response.data
    },

    /**
     * Award XP for an activity
     */
    async awardXP(activity: string, multiplier: number = 1.0): Promise<XPAwardResponse> {
        const response = await api.post('/gamification/xp', { activity, multiplier })
        return response.data
    },

    /**
     * Update streak (call on any activity)
     */
    async updateStreak(): Promise<StreakResponse> {
        const response = await api.post('/gamification/streak')
        return response.data
    },

    /**
     * Get level info (thresholds)
     */
    async getLevelInfo(): Promise<{ thresholds: Record<number, number>, rewards: Record<string, number> }> {
        const response = await api.get('/gamification/levels')
        return response.data
    },

    /**
     * Get level name for display
     */
    getLevelName(level: number): string {
        return LEVEL_NAMES[level] || `Level ${level}`
    }
}
