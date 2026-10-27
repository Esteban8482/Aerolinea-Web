import { useCallback, useEffect, useState } from 'react'
import { Routes, Route } from 'react-router-dom'
import { api } from './api'
import Header from './components/Header'
import HomePage from './pages/HomePage'
import RegisterPage from './pages/RegisterPage'
import LoginPage from './pages/LoginPage'
import ProfilePage from './pages/ProfilePage'
import VerifyEmailPage from './pages/VerifyEmailPage'
import ResetPasswordPage from './pages/ResetPasswordPage'

interface Session {
  authenticated: boolean
  role: string | null
  is_email_verified: boolean
}

export default function App() {
  const [session, setSession] = useState<Session>({
    authenticated: false,
    role: null,
    is_email_verified: false,
  })

  const refreshSession = useCallback(async () => {
    try {
      const data = await api.get('/auth/session/')
      setSession({
        authenticated: Boolean(data.authenticated),
        role: data.role ?? null,
        is_email_verified: Boolean(data.is_email_verified),
      })
    } catch {
      setSession({ authenticated: false, role: null, is_email_verified: false })
    }
  }, [])

  useEffect(() => {
    refreshSession()
  }, [refreshSession])

  async function handleLogout() {
    try {
      await api.post('/auth/logout/', {})
    } catch {
      // Si falla el logout, limpiamos el estado local de todas formas.
    }
    setSession({ authenticated: false, role: null, is_email_verified: false })
  }

  return (
    <div className="app-layout">
      <Header
        authenticated={session.authenticated}
        role={session.role}
        onLogout={handleLogout}
      />
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/registro" element={<RegisterPage />} />
        <Route
          path="/login"
          element={<LoginPage onLoginSuccess={refreshSession} />}
        />
        <Route
          path="/perfil"
          element={<ProfilePage session={session} />}
        />
        <Route path="/verificar" element={<VerifyEmailPage />} />
        <Route path="/restablecer" element={<ResetPasswordPage />} />
      </Routes>
    </div>
  )
}
