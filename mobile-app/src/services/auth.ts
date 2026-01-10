import api from '../api/client';
import { User, TokenResponse, LoginCredentials, RegisterData } from '../types';

export const authService = {
    /**
     * Login with email and password
     */
    async login(credentials: LoginCredentials): Promise<TokenResponse> {
        const response = await api.post<TokenResponse>('/auth/login', credentials);
        return response.data;
    },

    /**
     * Register a new user
     */
    async register(data: RegisterData): Promise<void> {
        await api.post('/auth/register', data);
    },

    /**
     * Logout (invalidate refresh token on server)
     */
    async logout(refreshToken: string): Promise<void> {
        try {
            await api.post('/auth/logout', { refresh_token: refreshToken });
        } catch {
            // Ignore errors during logout
        }
    },

    /**
     * Get current authenticated user
     */
    async getCurrentUser(): Promise<User> {
        const response = await api.get<User>('/auth/me');
        return response.data;
    },
};
