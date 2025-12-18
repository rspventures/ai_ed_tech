import { useState, useEffect } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Sparkles, Mail, Lock, ArrowRight, AlertCircle } from 'lucide-react'
import { useAuthStore } from '@/stores/authStore'

export default function LoginPage() {
    const navigate = useNavigate()
    const { login, isAuthenticated, error, clearError, isLoading } = useAuthStore()

    const [email, setEmail] = useState('')
    const [password, setPassword] = useState('')
    const [formError, setFormError] = useState('')

    useEffect(() => {
        if (isAuthenticated) {
            navigate('/dashboard')
        }
    }, [isAuthenticated, navigate])

    useEffect(() => {
        return () => clearError()
    }, [clearError])

    const handleSubmit = async (e: React.FormEvent) => {
        e.preventDefault()
        setFormError('')

        if (!email || !password) {
            setFormError('Please fill in all fields')
            return
        }

        try {
            await login({ email, password })
            navigate('/dashboard')
        } catch {
            // Error is handled by the store
        }
    }

    return (
        <div className="min-h-screen flex items-center justify-center p-4">
            {/* Background decoration */}
            <div className="absolute inset-0 overflow-hidden pointer-events-none">
                <div className="absolute top-1/4 left-1/4 w-96 h-96 bg-primary-500/20 rounded-full blur-3xl animate-pulse-slow" />
                <div className="absolute bottom-1/4 right-1/4 w-96 h-96 bg-accent-500/20 rounded-full blur-3xl animate-pulse-slow" />
            </div>

            <div className="w-full max-w-md relative">
                {/* Logo and title */}
                <div className="text-center mb-8">
                    <div className="inline-flex items-center justify-center w-16 h-16 bg-gradient-to-br from-primary-500 to-accent-500 rounded-2xl mb-4 shadow-lg shadow-primary-500/30">
                        <Sparkles className="w-8 h-8 text-white" />
                    </div>
                    <h1 className="text-3xl font-bold gradient-text mb-2">Welcome Back</h1>
                    <p className="text-gray-400">Sign in to continue your learning journey</p>
                </div>

                {/* Login form */}
                <form onSubmit={handleSubmit} className="glass-card space-y-6">
                    {(error || formError) && (
                        <div className="flex items-center gap-3 p-4 bg-red-500/10 border border-red-500/20 rounded-xl text-red-400">
                            <AlertCircle className="w-5 h-5 flex-shrink-0" />
                            <p className="text-sm">{error || formError}</p>
                        </div>
                    )}

                    <div className="space-y-4">
                        <div>
                            <label htmlFor="email" className="block text-sm font-medium text-gray-300 mb-2">
                                Email Address
                            </label>
                            <div className="relative">
                                <Mail className="absolute left-4 top-1/2 -translate-y-1/2 w-5 h-5 text-gray-400" />
                                <input
                                    id="email"
                                    type="email"
                                    value={email}
                                    onChange={(e) => setEmail(e.target.value)}
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
                                    type="password"
                                    value={password}
                                    onChange={(e) => setPassword(e.target.value)}
                                    className="input-field pl-12"
                                    placeholder="••••••••"
                                    autoComplete="current-password"
                                />
                            </div>
                        </div>
                    </div>

                    <div className="flex items-center justify-between text-sm">
                        <label className="flex items-center gap-2 cursor-pointer">
                            <input type="checkbox" className="w-4 h-4 rounded border-gray-600 bg-white/5 text-primary-500 focus:ring-primary-500" />
                            <span className="text-gray-400">Remember me</span>
                        </label>
                        <a href="#" className="text-primary-400 hover:text-primary-300 transition-colors">
                            Forgot password?
                        </a>
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
                                Sign In
                                <ArrowRight className="w-5 h-5" />
                            </>
                        )}
                    </button>
                </form>

                {/* Register link */}
                <p className="text-center mt-6 text-gray-400">
                    Don't have an account?{' '}
                    <Link to="/register" className="text-primary-400 hover:text-primary-300 font-medium transition-colors">
                        Create one
                    </Link>
                </p>
            </div>
        </div>
    )
}
