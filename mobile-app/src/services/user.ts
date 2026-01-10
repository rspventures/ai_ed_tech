import api from '../api/client';
import { User } from '../types';

export interface StudentProfile {
    id: string;
    user_id: string;
    display_name: string;
    grade_level: number;
    avatar_url: string;
    theme_color: string;
    first_name: string;
    last_name: string;
    preferences: Record<string, any>;
}

export const userService = {
    /**
     * Get current student profile
     */
    async getProfile(): Promise<StudentProfile> {
        try {
            // Try fetch student profile
            const response = await api.get<{ students: StudentProfile[] }>('/users/me');
            if (response.data.students && response.data.students.length > 0) {
                return response.data.students[0];
            }
            throw new Error('No student profile found');
        } catch (err) {
            // Fallback to basic user info if needed, but for now just rethrow
            throw err;
        }
    },

    /**
     * Update student profile
     */
    async updateProfile(data: Partial<StudentProfile>): Promise<StudentProfile> {
        const response = await api.patch<StudentProfile>('/users/students/me', data);
        return response.data;
    }
};
