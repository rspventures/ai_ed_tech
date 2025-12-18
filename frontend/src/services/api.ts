import axios, { AxiosError, AxiosResponse } from 'axios'
import type { TokenResponse, ApiError } from '@/types'

const API_BASE_URL = import.meta.env.VITE_API_URL || '/api/v1'

// Create axios instance
export const api = axios.create({
    baseURL: API_BASE_URL,
    headers: {
        'Content-Type': 'application/json',
    },
})

// Request interceptor - add auth token
api.interceptors.request.use(
    (config) => {
        const token = localStorage.getItem('access_token')
        if (token) {
            config.headers.Authorization = `Bearer ${token}`
        }
        return config
    },
    (error) => Promise.reject(error)
)

// Response interceptor - handle token refresh
api.interceptors.response.use(
    (response: AxiosResponse) => response,
    async (error: AxiosError<ApiError>) => {
        const originalRequest = error.config

        // If 401 and we have a refresh token, try to refresh
        if (error.response?.status === 401 && originalRequest) {
            const refreshToken = localStorage.getItem('refresh_token')

            if (refreshToken) {
                try {
                    const response = await axios.post<TokenResponse>(
                        `${API_BASE_URL}/auth/refresh`,
                        { refresh_token: refreshToken }
                    )

                    const { access_token, refresh_token: newRefreshToken } = response.data
                    localStorage.setItem('access_token', access_token)
                    localStorage.setItem('refresh_token', newRefreshToken)

                    // Retry original request
                    originalRequest.headers.Authorization = `Bearer ${access_token}`
                    return api(originalRequest)
                } catch {
                    // Refresh failed - clear tokens and redirect to login
                    localStorage.removeItem('access_token')
                    localStorage.removeItem('refresh_token')
                    window.location.href = '/login'
                }
            }
        }

        return Promise.reject(error)
    }
)

// Helper to extract error message
export function getErrorMessage(error: unknown): string {
    if (axios.isAxiosError(error)) {
        const axiosError = error as AxiosError<ApiError>
        return axiosError.response?.data?.detail || error.message
    }
    if (error instanceof Error) {
        return error.message
    }
    return 'An unexpected error occurred'
}

// Default export for convenience
export default api

