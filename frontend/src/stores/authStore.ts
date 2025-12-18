import { create } from 'zustand'
import { persist } from 'zustand/middleware'
import type { User, LoginCredentials, RegisterData } from '@/types'
import { authService } from '@/services/auth'
import { getErrorMessage } from '@/services/api'

interface AuthState {
    user: User | null
    isAuthenticated: boolean
    isLoading: boolean
    error: string | null

    // Actions
    login: (credentials: LoginCredentials) => Promise<void>
    register: (data: RegisterData) => Promise<void>
    logout: () => Promise<void>
    checkAuth: () => Promise<void>
    clearError: () => void
}

export const useAuthStore = create<AuthState>()(
    persist(
        (set) => ({
            user: null,
            isAuthenticated: false,
            isLoading: true,
            error: null,

            login: async (credentials) => {
                set({ isLoading: true, error: null })
                try {
                    const tokens = await authService.login(credentials)
                    localStorage.setItem('access_token', tokens.access_token)
                    localStorage.setItem('refresh_token', tokens.refresh_token)

                    const user = await authService.getCurrentUser()
                    set({ user, isAuthenticated: true, isLoading: false })
                } catch (error) {
                    set({
                        error: getErrorMessage(error),
                        isLoading: false,
                        isAuthenticated: false
                    })
                    throw error
                }
            },

            register: async (data) => {
                set({ isLoading: true, error: null })
                try {
                    await authService.register(data)
                    set({ isLoading: false })
                } catch (error) {
                    set({ error: getErrorMessage(error), isLoading: false })
                    throw error
                }
            },

            logout: async () => {
                const refreshToken = localStorage.getItem('refresh_token')
                if (refreshToken) {
                    try {
                        await authService.logout(refreshToken)
                    } catch {
                        // Ignore logout errors
                    }
                }

                localStorage.removeItem('access_token')
                localStorage.removeItem('refresh_token')
                set({ user: null, isAuthenticated: false, error: null })
            },

            checkAuth: async () => {
                const token = localStorage.getItem('access_token')
                if (!token) {
                    set({ isLoading: false, isAuthenticated: false })
                    return
                }

                try {
                    const user = await authService.getCurrentUser()
                    set({ user, isAuthenticated: true, isLoading: false })
                } catch {
                    localStorage.removeItem('access_token')
                    localStorage.removeItem('refresh_token')
                    set({ isLoading: false, isAuthenticated: false })
                }
            },

            clearError: () => set({ error: null }),
        }),
        {
            name: 'auth-storage',
            partialize: (state) => ({
                isAuthenticated: state.isAuthenticated,
                user: state.user,
            }),
        }
    )
)

// Initialize auth check on app load
if (typeof window !== 'undefined') {
    useAuthStore.getState().checkAuth()
}
