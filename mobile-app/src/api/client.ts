import axios, { AxiosError } from 'axios';
import AsyncStorage from '@react-native-async-storage/async-storage';
import Constants from 'expo-constants';
import { TokenResponse, ApiError } from '../types';

// Read production URL from app.json extra.apiBaseUrl.
// To change the API URL, update "extra.apiBaseUrl" in app.json — do NOT hardcode here.
// The fallback below is for Android emulator local development only.
const API_BASE_URL: string =
    (Constants.expoConfig?.extra?.apiBaseUrl as string) ||
    'http://10.0.2.2:8000/api/v1';

// Create axios instance
const api = axios.create({
    baseURL: API_BASE_URL,
    headers: {
        'Content-Type': 'application/json',
    },
    timeout: 10000,
});

// Request interceptor - add auth token
api.interceptors.request.use(
    async (config) => {
        const token = await AsyncStorage.getItem('access_token');
        if (token) {
            config.headers.Authorization = `Bearer ${token}`;
        }
        return config;
    },
    (error) => Promise.reject(error)
);

// Allow the app (AuthContext) to react to an unrecoverable session expiry —
// e.g. clear the user and redirect to /login. Set once at startup.
let sessionExpiredHandler: (() => void) | null = null;
export function setSessionExpiredHandler(handler: (() => void) | null): void {
    sessionExpiredHandler = handler;
}

async function clearSessionAndSignal(): Promise<never> {
    await AsyncStorage.removeItem('access_token');
    await AsyncStorage.removeItem('refresh_token');
    // Notify the app so it can redirect to login (previously SESSION_EXPIRED was
    // thrown but never handled, stranding the user — D7).
    try {
        sessionExpiredHandler?.();
    } catch {
        // never let the handler break the rejection path
    }
    return Promise.reject(new Error('SESSION_EXPIRED'));
}

// Response interceptor - handle token refresh
api.interceptors.response.use(
    (response) => response,
    async (error: AxiosError<ApiError>) => {
        // `_retry` guards against an infinite refresh/retry loop when the retried
        // request also returns 401 (D7).
        const originalRequest = error.config as
            | (typeof error.config & { _retry?: boolean })
            | undefined;

        if (error.response?.status === 401 && originalRequest && !originalRequest._retry) {
            const isRefreshCall = originalRequest.url?.includes('/auth/refresh');
            const refreshToken = await AsyncStorage.getItem('refresh_token');

            if (refreshToken && !isRefreshCall) {
                originalRequest._retry = true;
                try {
                    const response = await axios.post<TokenResponse>(
                        `${API_BASE_URL}/auth/refresh`,
                        { refresh_token: refreshToken }
                    );

                    const { access_token, refresh_token: newRefreshToken } = response.data;
                    await AsyncStorage.setItem('access_token', access_token);
                    await AsyncStorage.setItem('refresh_token', newRefreshToken);

                    // Retry the original request once with the new token.
                    originalRequest.headers.Authorization = `Bearer ${access_token}`;
                    return api(originalRequest);
                } catch {
                    return clearSessionAndSignal();
                }
            }

            // No refresh token, the refresh call itself 401'd, or already retried:
            // the session is unrecoverable.
            return clearSessionAndSignal();
        }

        return Promise.reject(error);
    }
);

// WebSocket base URL derived from the HTTP base URL (http→ws, https→wss)
export const WS_BASE_URL: string = API_BASE_URL.replace(/^http/, 'ws').replace('/api/v1', '');

// Helper to extract error message
export function getErrorMessage(error: unknown): string {
    if (axios.isAxiosError(error)) {
        const axiosError = error as AxiosError<ApiError>;
        return axiosError.response?.data?.detail || error.message;
    }
    if (error instanceof Error) {
        return error.message;
    }
    return 'An unexpected error occurred';
}

export default api;
