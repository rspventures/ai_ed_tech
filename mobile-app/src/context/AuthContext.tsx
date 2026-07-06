import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { router } from 'expo-router';
import { authService } from '../services/auth';
import { setSessionExpiredHandler } from '../api/client';
import { User, LoginCredentials } from '../types';

interface AuthContextType {
    user: User | null;
    isLoading: boolean;
    signIn: (credentials: LoginCredentials) => Promise<void>;
    signOut: () => Promise<void>;
}

const AuthContext = createContext<AuthContextType | undefined>(undefined);

export function AuthProvider({ children }: { children: ReactNode }) {
    const [user, setUser] = useState<User | null>(null);
    const [isLoading, setIsLoading] = useState(true);

    // Check for existing session on mount
    useEffect(() => {
        checkUser();
    }, []);

    // When the API layer detects an unrecoverable session expiry, clear the
    // user and send them to login (D7: SESSION_EXPIRED was never handled before).
    useEffect(() => {
        setSessionExpiredHandler(() => {
            setUser(null);
            router.replace('/login');
        });
        return () => setSessionExpiredHandler(null);
    }, []);

    const checkUser = async () => {
        // P0.3: restore the session on launch instead of forcing a fresh login
        // every time. If a token exists we validate it by fetching the current
        // user (the axios interceptor silently refreshes an expired access
        // token). Only if there is no token, or refresh fails, do we require
        // login again.
        try {
            const token = await AsyncStorage.getItem('access_token');
            if (!token) {
                setUser(null);
                return;
            }
            const userData = await authService.getCurrentUser();
            setUser(userData);
        } catch {
            // Token invalid/expired and refresh failed → clear and require login.
            await AsyncStorage.removeItem('access_token');
            await AsyncStorage.removeItem('refresh_token');
            setUser(null);
        } finally {
            setIsLoading(false);
        }
    };

    const signIn = async (credentials: LoginCredentials) => {
        const { access_token, refresh_token } = await authService.login(credentials);
        await AsyncStorage.setItem('access_token', access_token);
        await AsyncStorage.setItem('refresh_token', refresh_token);

        const userData = await authService.getCurrentUser();
        setUser(userData);
    };

    const signOut = async () => {
        try {
            const refreshToken = await AsyncStorage.getItem('refresh_token');
            if (refreshToken) {
                // Fire-and-forget the server logout to prevent UI hanging if server is unreachable
                authService.logout(refreshToken).catch(() => {});
            }
        } catch {
            // Ignore errors
        } finally {
            // Always clear local session immediately
            await AsyncStorage.removeItem('access_token');
            await AsyncStorage.removeItem('refresh_token');
            setUser(null);
        }
    };

    return (
        <AuthContext.Provider value={{ user, isLoading, signIn, signOut }}>
            {children}
        </AuthContext.Provider>
    );
}

export function useAuth(): AuthContextType {
    const context = useContext(AuthContext);
    if (!context) {
        throw new Error('useAuth must be used within an AuthProvider');
    }
    return context;
}
