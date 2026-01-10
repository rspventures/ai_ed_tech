import React, { createContext, useContext, useState, useEffect, ReactNode } from 'react';
import AsyncStorage from '@react-native-async-storage/async-storage';
import { authService } from '../services/auth';
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

    const checkUser = async () => {
        try {
            // Per user requirement: Always ask for login on launch.
            // We clear any existing tokens to ensure a fresh start.
            await AsyncStorage.removeItem('access_token');
            await AsyncStorage.removeItem('refresh_token');
            setUser(null);
        } catch (error) {
            console.log('Session clear failed:', error);
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
                authService.logout(refreshToken).catch(err => console.log('Logout API failed', err));
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
