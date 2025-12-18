import { api } from './api'
import type {
    User,
    TokenResponse,
    LoginCredentials,
    RegisterData,
    UserProfile
} from '@/types'

export const authService = {
    async register(data: RegisterData): Promise<User> {
        const response = await api.post<User>('/auth/register', data)
        return response.data
    },

    async login(credentials: LoginCredentials): Promise<TokenResponse> {
        const response = await api.post<TokenResponse>('/auth/login', credentials)
        return response.data
    },

    async logout(refreshToken: string): Promise<void> {
        await api.post('/auth/logout', { refresh_token: refreshToken })
    },

    async refreshToken(refreshToken: string): Promise<TokenResponse> {
        const response = await api.post<TokenResponse>('/auth/refresh', {
            refresh_token: refreshToken,
        })
        return response.data
    },

    async getCurrentUser(): Promise<User> {
        const response = await api.get<User>('/auth/me')
        return response.data
    },

    async getProfile(): Promise<UserProfile> {
        const response = await api.get<UserProfile>('/users/me')
        return response.data
    },
}
