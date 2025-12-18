/**
 * Student Store - Manages the current student's preferences
 * Used for personalizing the UI with avatar and theme colors
 */
import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { Student, UserProfile } from '@/types'
import { authService } from '@/services/auth'

// Avatar emoji mappings - matches SettingsPage options
export const AVATAR_OPTIONS = [
    { id: 'owl', emoji: '🦉', label: 'Wise Owl' },
    { id: 'robot', emoji: '🤖', label: 'Smart Bot' },
    { id: 'fox', emoji: '🦊', label: 'Clever Fox' },
    { id: 'cat', emoji: '🐱', label: 'Curious Cat' },
    { id: 'dog', emoji: '🐕', label: 'Loyal Pup' },
    { id: 'dragon', emoji: '🐉', label: 'Magic Dragon' },
] as const

// Theme color configurations - using CSS gradient strings for inline styles
// (Tailwind classes can't be used dynamically as they get purged at build time)
export const THEME_COLORS: Record<string, { primary: string; secondary: string; gradient: string; name: string }> = {
    '#6366f1': { primary: '#6366f1', secondary: '#a855f7', gradient: 'linear-gradient(135deg, #6366f1, #a855f7)', name: 'Indigo' },
    '#8b5cf6': { primary: '#8b5cf6', secondary: '#a855f7', gradient: 'linear-gradient(135deg, #8b5cf6, #a855f7)', name: 'Violet' },
    '#8B5CF6': { primary: '#8B5CF6', secondary: '#a855f7', gradient: 'linear-gradient(135deg, #8B5CF6, #a855f7)', name: 'Purple' },
    '#ec4899': { primary: '#ec4899', secondary: '#f43f5e', gradient: 'linear-gradient(135deg, #ec4899, #f43f5e)', name: 'Pink' },
    '#EC4899': { primary: '#EC4899', secondary: '#f43f5e', gradient: 'linear-gradient(135deg, #EC4899, #f43f5e)', name: 'Pink' },
    '#f43f5e': { primary: '#f43f5e', secondary: '#ef4444', gradient: 'linear-gradient(135deg, #f43f5e, #ef4444)', name: 'Rose' },
    '#EF4444': { primary: '#EF4444', secondary: '#dc2626', gradient: 'linear-gradient(135deg, #EF4444, #dc2626)', name: 'Red' },
    '#f97316': { primary: '#f97316', secondary: '#f59e0b', gradient: 'linear-gradient(135deg, #f97316, #f59e0b)', name: 'Orange' },
    '#F97316': { primary: '#F97316', secondary: '#f59e0b', gradient: 'linear-gradient(135deg, #F97316, #f59e0b)', name: 'Orange' },
    '#eab308': { primary: '#eab308', secondary: '#f59e0b', gradient: 'linear-gradient(135deg, #eab308, #f59e0b)', name: 'Gold' },
    '#22c55e': { primary: '#22c55e', secondary: '#10b981', gradient: 'linear-gradient(135deg, #22c55e, #10b981)', name: 'Green' },
    '#10B981': { primary: '#10B981', secondary: '#14b8a6', gradient: 'linear-gradient(135deg, #10B981, #14b8a6)', name: 'Emerald' },
    '#14b8a6': { primary: '#14b8a6', secondary: '#06b6d4', gradient: 'linear-gradient(135deg, #14b8a6, #06b6d4)', name: 'Teal' },
    '#3B82F6': { primary: '#3B82F6', secondary: '#6366f1', gradient: 'linear-gradient(135deg, #3B82F6, #6366f1)', name: 'Blue' },
    '#06B6D4': { primary: '#06B6D4', secondary: '#0891b2', gradient: 'linear-gradient(135deg, #06B6D4, #0891b2)', name: 'Cyan' },
}

interface StudentState {
    student: Student | null
    isLoading: boolean
    error: string | null

    // Actions
    fetchStudent: () => Promise<void>
    setStudent: (student: Student) => void
    clearStudent: () => void

    // Helpers
    getAvatarEmoji: () => string
    getThemeGradient: () => string
    getThemeColor: () => string
}

export const useStudentStore = create<StudentState>()(
    persist(
        (set, get) => ({
            student: null,
            isLoading: false,
            error: null,

            fetchStudent: async () => {
                set({ isLoading: true, error: null })
                try {
                    const profile: UserProfile = await authService.getProfile()
                    const student = profile.students?.[0] || null
                    set({ student, isLoading: false })

                    // Apply theme color to document
                    if (student?.theme_color) {
                        document.documentElement.style.setProperty('--theme-color', student.theme_color)
                    }
                } catch (error) {
                    set({ error: 'Failed to load student data', isLoading: false })
                }
            },

            setStudent: (student) => {
                set({ student })
                if (student?.theme_color) {
                    document.documentElement.style.setProperty('--theme-color', student.theme_color)
                }
            },

            clearStudent: () => set({ student: null }),

            getAvatarEmoji: () => {
                const { student } = get()
                if (!student?.avatar_url) return '🚀'
                const avatar = AVATAR_OPTIONS.find(a => a.id === student.avatar_url)
                return avatar?.emoji || '🚀'
            },

            getThemeGradient: () => {
                const { student } = get()
                if (!student?.theme_color) return 'from-indigo-500 to-purple-500'
                return THEME_COLORS[student.theme_color]?.gradient || 'from-indigo-500 to-purple-500'
            },

            getThemeColor: () => {
                const { student } = get()
                return student?.theme_color || '#6366f1'
            },
        }),
        {
            name: 'student-storage',
            partialize: (state) => ({
                student: state.student,
            }),
        }
    )
)
