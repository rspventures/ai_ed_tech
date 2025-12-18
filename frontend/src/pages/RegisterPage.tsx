import { useState, useEffect } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Sparkles, Mail, Lock, User, ArrowRight, AlertCircle, CheckCircle } from 'lucide-react'
import { useAuthStore } from '@/stores/authStore'

export default function RegisterPage() {
    const navigate = useNavigate()
    const { register, isAuthenticated, error, clearError, isLoading } = useAuthStore()

    const [formData, setFormData] = useState({
        first_name: '',
        last_name: '',
        email: '',
        password: '',
        confirmPassword: '',
    })
    const [formError, setFormError] = useState('')
    const [success, setSuccess] = useState(false)

    useEffect(() => {
        if (isAuthenticated) {
            navigate('/dashboard')
        }
    }, [isAuthenticated, navigate])

    useEffect(() => {
        return () => clearError()
    }, [clearError])

    const handleChange = (e: React.ChangeEvent<HTMLInputElement>) => {
        setFormData((prev) => ({
            ...prev,
            [e.target.name]: e.target.value,
        }))
    }

    const validatePassword = (password: string): string | null => {
        if (password.length < 8) return 'Password must be at least 8 characters'
        if (!/[A-Z]/.test(password)) return 'Password must contain an uppercase letter'
        if (!/[a-z]/.test(password)) return 'Password must contain a lowercase letter'
        if (!/[0-9]/.test(password)) return 'Password must contain a number'
        if (!/[!@#$%^&*()_+\-=[\]{}|;:,.<>?]/.test(password)) return 'Password must contain a special character'
        return null
    }

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault()
        setFormError('')

        // Validation
        const { first_name, last_name, email, password, confirmPassword } = formData

        if (!first_name || !last_name || !email || !password || !confirmPassword) {
            setFormError('Please fill in all fields')
            return
        }

        const passwordError = validatePassword(password)
        if (passwordError) {
            setFormError(passwordError)
            return
        }

        if (password !== confirmPassword) {
            setFormError('Passwords do not match')
            return
        }

        try {
            await register({ first_name, last_name, email, password })
            setSuccess(true)
        } catch {
            // Error is handled by the store
        }
    }

    if (success) {
        return (
            <div className="min-h-screen flex items-center justify-center p-4">
                <div className="glass-card text-center max-w-md">
                    <div className="inline-flex items-center justify-center w-16 h-16 bg-gradient-to-br from-green-500 to-emerald-500 rounded-full mb-4">
                        <CheckCircle className="w-8 h-8 text-white" />
                    </div>
                    <h2 className="text-2xl font-bold text-white mb-2">Registration Successful!</h2>
                    <p className="text-gray-400 mb-6">
                        Your account has been created. Please check your email to verify your account.
                    </p>
                    <Link to="/login" className="btn-primary inline-flex items-center gap-2">
                        Continue to Login
                        <ArrowRight className="w-5 h-5" />
                    </Link>
                </div>
            </div>
        )
    }

    return (
        <div className="min-h-screen flex items-center justify-center p-4 py-12">
            {/* Background decoration */}
            <div className="absolute inset-0 overflow-hidden pointer-events-none">
                <div className="absolute top-1/4 right-1/4 w-96 h-96 bg-accent-500/20 rounded-full blur-3xl animate-pulse-slow" />
                <div className="absolute bottom-1/4 left-1/4 w-96 h-96 bg-primary-500/20 rounded-full blur-3xl animate-pulse-slow" />
            </div>

            <div className="w-full max-w-md relative">
                {/* Logo and title */}
                <div className="text-center mb-8">
                    <div className="inline-flex items-center justify-center w-16 h-16 bg-gradient-to-br from-accent-500 to-primary-500 rounded-2xl mb-4 shadow-lg shadow-accent-500/30">
                        <Sparkles className="w-8 h-8 text-white" />
                    </div>
                    <h1 className="text-3xl font-bold gradient-text mb-2">Create Account</h1>
                    <p className="text-gray-400">Start your personalized learning journey</p>
                </div>

                {/* Register form */}
                <form onSubmit={handleSubmit} className="glass-card space-y-6">
                    {(error || formError) && (
                        <div className="flex items-center gap-3 p-4 bg-red-500/10 border border-red-500/20 rounded-xl text-red-400">
                            <AlertCircle className="w-5 h-5 flex-shrink-0" />
                            <p className="text-sm">{error || formError}</p>
                        </div>
                    )}

                    <div className="space-y-4">
                        <div className="grid grid-cols-2 gap-4">
                            <div>
                                <label htmlFor="first_name" className="block text-sm font-medium text-gray-300 mb-2">
                                    First Name
                                </label>
                                <div className="relative">
                                    <User className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
                                    <input
                                        id="first_name"
                                        name="first_name"
                                        type="text"
                                        value={formData.first_name}
                                        onChange={handleChange}
                                        className="input-field pl-12"
                                        placeholder="John"
                                    />
                                </div>
                            </div>
                            <div>
                                <label htmlFor="last_name" className="block text-sm font-medium text-gray-300 mb-2">
                                    Last Name
                                </label>
                                <input
                                    id="last_name"
                                    name="last_name"
                                    type="text"
                                    value={formData.last_name}
                                    onChange={handleChange}
                                    className="input-field"
                                    placeholder="Doe"
                                />
                            </div>
                        </div>

                        <div>
                            <label htmlFor="email" className="block text-sm font-medium text-gray-300 mb-2">
                                Email Address
                            </label>
                            <div className="relative">
                                <Mail className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
                                <input
                                    id="email"
                                    name="email"
                                    type="email"
                                    value={formData.email}
                                    onChange={handleChange}
                                    className="input-field pl-12"
                                    placeholder="you@example.com"
                                    autoComplete="email"
                                />
                            </div>
                        </div>

                        <div>
                            <label htmlFor="password" className="block text-sm font-medium text-gray-300 mb-2">
                                Password
                            </label>
                            <div className="relative">
                                <Lock className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
                                <input
                                    id="password"
                                    name="password"
                                    type="password"
                                    value={formData.password}
                                    onChange={handleChange}
                                    className="input-field pl-12"
                                    placeholder="••••••••"
                                    autoComplete="new-password"
                                />
                            </div>
                            <p className="mt-2 text-xs text-gray-500">
                                Min 8 characters with uppercase, lowercase, number & special character
                            </p>
                        </div>

                        <div>
                            <label htmlFor="confirmPassword" className="block text-sm font-medium text-gray-300 mb-2">
                                Confirm Password
                            </label>
                            <div className="relative">
                                <Lock className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
                                <input
                                    id="confirmPassword"
                                    name="confirmPassword"
                                    type="password"
                                    value={formData.confirmPassword}
                                    onChange={handleChange}
                                    className="input-field pl-12"
                                    placeholder="••••••••"
                                    autoComplete="new-password"
                                />
                            </div>
                        </div>
                    </div>

                    <button
                        type="submit"
                        disabled={isLoading}
                        className="btn-primary w-full flex items-center justify-center gap-2 disabled:opacity-50 disabled:cursor-not-allowed"
                    >
                        {isLoading ? (
                            <div className="w-5 h-5 border-2 border-white/30 border-t-white rounded-full animate-spin" />
                        ) : (
                            <>
                                Create Account
                                <ArrowRight className="w-5 h-5" />
                            </>
                        )}
                    </button>
                </form>

                {/* Login link */}
                <p className="text-center mt-6 text-gray-400">
                    Already have an account?{' '}
                    <Link to="/login" className="text-primary-400 hover:text-primary-300 font-medium transition-colors">
                        Sign in
                    </Link>
                </p>
            </div>
        </div>
    )
}
