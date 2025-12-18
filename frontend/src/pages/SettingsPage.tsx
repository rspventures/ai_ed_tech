import { useState, useEffect } from 'react'
import { useNavigate } from 'react-router-dom'
import {
    Settings as SettingsIcon,
    User,
    GraduationCap,
    Palette,
    Lock,
    ArrowLeft,
    Check,
    Loader2,
    Save
} from 'lucide-react'
import { useAuthStore } from '@/stores/authStore'
import { useStudentStore } from '@/stores/studentStore'
import api from '@/services/api'

// Avatar options - fun learning companions
const AVATARS = [
    { id: 'owl', emoji: '🦉', name: 'Wise Owl', color: '#8B5CF6' },
    { id: 'robot', emoji: '🤖', name: 'Smart Bot', color: '#3B82F6' },
    { id: 'fox', emoji: '🦊', name: 'Clever Fox', color: '#F97316' },
    { id: 'cat', emoji: '🐱', name: 'Curious Cat', color: '#EC4899' },
    { id: 'dog', emoji: '🐕', name: 'Loyal Pup', color: '#10B981' },
    { id: 'dragon', emoji: '🐉', name: 'Magic Dragon', color: '#EF4444' },
]

// Grade levels
const GRADES = [1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12]

// Theme colors
const THEME_COLORS = [
    { value: '#6366f1', name: 'Indigo' },
    { value: '#8B5CF6', name: 'Purple' },
    { value: '#EC4899', name: 'Pink' },
    { value: '#EF4444', name: 'Red' },
    { value: '#F97316', name: 'Orange' },
    { value: '#10B981', name: 'Emerald' },
    { value: '#3B82F6', name: 'Blue' },
    { value: '#06B6D4', name: 'Cyan' },
]

interface StudentSettings {
    first_name: string
    last_name: string
    display_name: string
    grade_level: number
    avatar_url: string
    theme_color: string
    preferences: {
        avatar_id?: string
        focus_subjects?: string[]
        sound_enabled?: boolean
        [key: string]: unknown
    }
}

const SettingsPage = () => {
    const { user, logout } = useAuthStore()
    const { fetchStudent } = useStudentStore()
    const navigate = useNavigate()
    const [loading, setLoading] = useState(true)
    const [saving, setSaving] = useState(false)
    const [success, setSuccess] = useState(false)
    const [error, setError] = useState<string | null>(null)

    const [settings, setSettings] = useState<StudentSettings>({
        first_name: '',
        last_name: '',
        display_name: '',
        grade_level: 3,
        avatar_url: '',
        theme_color: '#6366f1',
        preferences: {}
    })

    useEffect(() => {
        fetchSettings()
    }, [])

    const fetchSettings = async () => {
        try {
            setLoading(true)
            const response = await api.get('/users/me')
            if (response.data.students && response.data.students.length > 0) {
                const student = response.data.students[0]
                setSettings({
                    first_name: student.first_name || '',
                    last_name: student.last_name || '',
                    display_name: student.display_name || '',
                    grade_level: student.grade_level || 3,
                    avatar_url: student.avatar_url || '',
                    theme_color: student.theme_color || '#6366f1',
                    preferences: student.preferences || {}
                })
            }
        } catch (err) {
            console.error('Failed to fetch settings:', err)
        } finally {
            setLoading(false)
        }
    }

    const handleSave = async () => {
        try {
            setSaving(true)
            setError(null)

            // Save to backend - include avatar_url for dashboard display
            await api.patch('/users/students/me', {
                display_name: settings.display_name,
                grade_level: settings.grade_level,
                theme_color: settings.theme_color,
                avatar_url: settings.preferences?.avatar_id || settings.avatar_url, // Use selected avatar
                preferences: settings.preferences
            })

            // Refresh the student store so Dashboard updates immediately
            await fetchStudent()

            setSuccess(true)
            setTimeout(() => setSuccess(false), 3000)
        } catch (err: any) {
            setError(err.response?.data?.detail || 'Failed to save settings')
        } finally {
            setSaving(false)
        }
    }

    const handleAvatarSelect = (avatarId: string) => {
        setSettings(prev => ({
            ...prev,
            preferences: {
                ...prev.preferences,
                avatar_id: avatarId
            }
        }))
    }

    const handleGradeChange = (grade: number) => {
        setSettings(prev => ({
            ...prev,
            grade_level: grade
        }))
    }

    const handleColorChange = (color: string) => {
        setSettings(prev => ({
            ...prev,
            theme_color: color
        }))
    }

    if (loading) {
        return (
            <div className="min-h-screen bg-gradient-to-br from-[#0f0f23] via-[#1a1a2e] to-[#16213e] flex items-center justify-center">
                <Loader2 className="w-8 h-8 text-purple-500 animate-spin" />
            </div>
        )
    }

    return (
        <div className="min-h-screen bg-gradient-to-br from-[#0f0f23] via-[#1a1a2e] to-[#16213e] text-white">
            {/* Header */}
            <header className="bg-black/30 backdrop-blur-md border-b border-white/10 sticky top-0 z-50">
                <div className="max-w-4xl mx-auto px-6 py-4 flex items-center justify-between">
                    <button
                        onClick={() => navigate('/dashboard')}
                        className="flex items-center gap-2 text-gray-400 hover:text-white transition-colors"
                    >
                        <ArrowLeft className="w-5 h-5" />
                        Back to Dashboard
                    </button>

                    <div className="flex items-center gap-3">
                        <SettingsIcon className="w-6 h-6 text-purple-400" />
                        <h1 className="text-xl font-bold">Settings</h1>
                    </div>

                    <button
                        onClick={handleSave}
                        disabled={saving}
                        className={`flex items-center gap-2 px-4 py-2 rounded-lg font-medium transition-all ${saving
                            ? 'bg-gray-600 cursor-not-allowed'
                            : success
                                ? 'bg-green-600 hover:bg-green-700'
                                : 'bg-purple-600 hover:bg-purple-700'
                            }`}
                    >
                        {saving ? (
                            <Loader2 className="w-4 h-4 animate-spin" />
                        ) : success ? (
                            <Check className="w-4 h-4" />
                        ) : (
                            <Save className="w-4 h-4" />
                        )}
                        {saving ? 'Saving...' : success ? 'Saved!' : 'Save Changes'}
                    </button>
                </div>
            </header>

            {/* Main Content */}
            <main className="max-w-4xl mx-auto px-6 py-8 space-y-8">

                {/* Error Alert */}
                {error && (
                    <div className="bg-red-500/20 border border-red-500/50 rounded-xl p-4 text-red-300">
                        {error}
                    </div>
                )}

                {/* Profile Section */}
                <section className="bg-white/5 backdrop-blur-sm rounded-2xl border border-white/10 p-6">
                    <div className="flex items-center gap-3 mb-6">
                        <User className="w-6 h-6 text-purple-400" />
                        <h2 className="text-xl font-semibold">Profile</h2>
                    </div>

                    <div className="grid md:grid-cols-2 gap-6">
                        <div>
                            <label className="block text-sm text-gray-400 mb-2">Display Name</label>
                            <input
                                type="text"
                                value={settings.display_name}
                                onChange={(e) => setSettings(prev => ({ ...prev, display_name: e.target.value }))}
                                placeholder="Your nickname"
                                className="w-full px-4 py-3 bg-black/30 border border-white/10 rounded-xl text-white placeholder-gray-500 focus:border-purple-500 focus:ring-1 focus:ring-purple-500 transition-all"
                            />
                        </div>

                        <div>
                            <label className="block text-sm text-gray-400 mb-2">Full Name</label>
                            <input
                                type="text"
                                value={`${settings.first_name} ${settings.last_name}`}
                                disabled
                                className="w-full px-4 py-3 bg-black/20 border border-white/5 rounded-xl text-gray-400 cursor-not-allowed"
                            />
                            <p className="text-xs text-gray-500 mt-1">Contact support to change your name</p>
                        </div>
                    </div>
                </section>

                {/* Academic Settings */}
                <section className="bg-white/5 backdrop-blur-sm rounded-2xl border border-white/10 p-6">
                    <div className="flex items-center gap-3 mb-6">
                        <GraduationCap className="w-6 h-6 text-blue-400" />
                        <h2 className="text-xl font-semibold">Academic Settings</h2>
                    </div>

                    <div>
                        <label className="block text-sm text-gray-400 mb-3">Grade Level</label>
                        <p className="text-xs text-gray-500 mb-4">
                            This affects the difficulty of lessons and quizzes generated by our AI tutor.
                        </p>
                        <div className="grid grid-cols-6 md:grid-cols-12 gap-2">
                            {GRADES.map(grade => (
                                <button
                                    key={grade}
                                    onClick={() => handleGradeChange(grade)}
                                    className={`py-3 rounded-xl font-semibold transition-all ${settings.grade_level === grade
                                        ? 'bg-gradient-to-r from-purple-600 to-blue-600 text-white shadow-lg shadow-purple-500/30'
                                        : 'bg-black/30 text-gray-400 hover:bg-black/50 hover:text-white'
                                        }`}
                                >
                                    {grade}
                                </button>
                            ))}
                        </div>
                    </div>
                </section>

                {/* Personalization */}
                <section className="bg-white/5 backdrop-blur-sm rounded-2xl border border-white/10 p-6">
                    <div className="flex items-center gap-3 mb-6">
                        <Palette className="w-6 h-6 text-pink-400" />
                        <h2 className="text-xl font-semibold">Personalization</h2>
                    </div>

                    {/* Avatar Selection */}
                    <div className="mb-8">
                        <label className="block text-sm text-gray-400 mb-3">Choose Your Learning Companion</label>
                        <div className="grid grid-cols-3 md:grid-cols-6 gap-4">
                            {AVATARS.map(avatar => (
                                <button
                                    key={avatar.id}
                                    onClick={() => handleAvatarSelect(avatar.id)}
                                    className={`relative p-4 rounded-2xl flex flex-col items-center gap-2 transition-all ${settings.preferences?.avatar_id === avatar.id
                                        ? 'bg-gradient-to-br from-purple-600/30 to-blue-600/30 border-2 border-purple-500 scale-105'
                                        : 'bg-black/30 border border-white/10 hover:border-purple-500/50'
                                        }`}
                                >
                                    <span className="text-4xl">{avatar.emoji}</span>
                                    <span className="text-xs text-gray-300">{avatar.name}</span>
                                    {settings.preferences?.avatar_id === avatar.id && (
                                        <div className="absolute -top-2 -right-2 w-6 h-6 bg-purple-600 rounded-full flex items-center justify-center">
                                            <Check className="w-4 h-4" />
                                        </div>
                                    )}
                                </button>
                            ))}
                        </div>
                    </div>

                    {/* Theme Color */}
                    <div>
                        <label className="block text-sm text-gray-400 mb-3">Theme Color</label>
                        <div className="flex flex-wrap gap-3">
                            {THEME_COLORS.map(color => (
                                <button
                                    key={color.value}
                                    onClick={() => handleColorChange(color.value)}
                                    className={`w-12 h-12 rounded-xl transition-all ${settings.theme_color === color.value
                                        ? 'ring-2 ring-white ring-offset-2 ring-offset-[#1a1a2e] scale-110'
                                        : 'hover:scale-105'
                                        }`}
                                    style={{ backgroundColor: color.value }}
                                    title={color.name}
                                />
                            ))}
                        </div>
                    </div>
                </section>

                {/* Account Security */}
                <section className="bg-white/5 backdrop-blur-sm rounded-2xl border border-white/10 p-6">
                    <div className="flex items-center gap-3 mb-6">
                        <Lock className="w-6 h-6 text-yellow-400" />
                        <h2 className="text-xl font-semibold">Account & Security</h2>
                    </div>

                    <div className="space-y-4">
                        <button
                            className="w-full flex items-center justify-between px-4 py-3 bg-black/30 rounded-xl hover:bg-black/50 transition-all group"
                        >
                            <span className="text-gray-300 group-hover:text-white">Change Password</span>
                            <ArrowLeft className="w-5 h-5 text-gray-500 rotate-180 group-hover:text-purple-400" />
                        </button>

                        <button
                            onClick={() => {
                                logout()
                                navigate('/login')
                            }}
                            className="w-full flex items-center justify-between px-4 py-3 bg-red-500/20 rounded-xl hover:bg-red-500/30 transition-all text-red-400"
                        >
                            <span>Log Out</span>
                            <ArrowLeft className="w-5 h-5 rotate-180" />
                        </button>
                    </div>
                </section>

            </main>
        </div>
    )
}

export default SettingsPage
