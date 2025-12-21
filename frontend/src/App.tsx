import { BrowserRouter as Router, Routes, Route, Navigate } from 'react-router-dom'
import { useAuthStore } from '@/stores/authStore'
import LoginPage from '@/pages/LoginPage'
import RegisterPage from '@/pages/RegisterPage'
import DashboardPage from '@/pages/DashboardPage'
import SubjectPage from '@/pages/SubjectPage'
import PracticePage from '@/pages/PracticePage'
import AssessmentPage from '@/pages/AssessmentPage'
import ExamPage from '@/pages/ExamPage'
import TestPage from '@/pages/TestPage'
import StudyPage from '@/pages/StudyPage'
import ParentDashboardPage from '@/pages/ParentDashboardPage'
import SettingsPage from '@/pages/SettingsPage'
import DocumentsPage from '@/pages/DocumentsPage'
import VisualsPage from '@/pages/VisualsPage'
import { TutorChat } from '@/components/TutorChat'

function App() {
    return (
        <Router>
            <div className="min-h-screen bg-gradient-to-br from-[#0f0f23] via-[#1a1a2e] to-[#16213e]">
                <Routes>
                    <Route path="/login" element={<LoginPage />} />
                    <Route path="/register" element={<RegisterPage />} />
                    <Route
                        path="/dashboard"
                        element={
                            <ProtectedRoute>
                                <DashboardPage />
                            </ProtectedRoute>
                        }
                    />
                    <Route
                        path="/subjects/:slug"
                        element={
                            <ProtectedRoute>
                                <SubjectPage />
                            </ProtectedRoute>
                        }
                    />
                    <Route
                        path="/practice"
                        element={
                            <ProtectedRoute>
                                <PracticePage />
                            </ProtectedRoute>
                        }
                    />
                    <Route
                        path="/practice/:topicSlug"
                        element={
                            <ProtectedRoute>
                                <PracticePage />
                            </ProtectedRoute>
                        }
                    />
                    <Route
                        path="/assessments/:topicSlug"
                        element={
                            <ProtectedRoute>
                                <AssessmentPage />
                            </ProtectedRoute>
                        }
                    />
                    <Route
                        path="/exams/:subjectSlug"
                        element={
                            <ProtectedRoute>
                                <ExamPage />
                            </ProtectedRoute>
                        }
                    />
                    <Route
                        path="/tests/:topicSlug"
                        element={
                            <ProtectedRoute>
                                <TestPage />
                            </ProtectedRoute>
                        }
                    />
                    <Route
                        path="/study/:topicSlug"
                        element={
                            <ProtectedRoute>
                                <StudyPage />
                            </ProtectedRoute>
                        }
                    />
                    <Route
                        path="/parent"
                        element={
                            <ProtectedRoute>
                                <ParentDashboardPage />
                            </ProtectedRoute>
                        }
                    />
                    <Route
                        path="/settings"
                        element={
                            <ProtectedRoute>
                                <SettingsPage />
                            </ProtectedRoute>
                        }
                    />
                    <Route
                        path="/documents"
                        element={
                            <ProtectedRoute>
                                <DocumentsPage />
                            </ProtectedRoute>
                        }
                    />
                    <Route
                        path="/visuals"
                        element={
                            <ProtectedRoute>
                                <VisualsPage />
                            </ProtectedRoute>
                        }
                    />
                    <Route path="/" element={<Navigate to="/dashboard" replace />} />
                </Routes>
            </div>
        </Router>
    )
}

function ProtectedRoute({ children }: { children: React.ReactNode }) {
    const { isAuthenticated, isLoading } = useAuthStore()

    if (isLoading) {
        return (
            <div className="min-h-screen flex items-center justify-center">
                <div className="animate-spin w-8 h-8 border-4 border-primary-500 border-t-transparent rounded-full" />
            </div>
        )
    }

    if (!isAuthenticated) {
        return <Navigate to="/login" replace />
    }

    return (
        <>
            {children}
            {/* Global AI Tutor Chat - available on all pages */}
            <TutorChat contextType="general" />
        </>
    )
}

export default App
