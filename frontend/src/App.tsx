import { useCallback, useEffect, useRef, useState } from 'react'
import { Routes, Route, Navigate } from 'react-router-dom'
import { api } from './api'
import CancellationsPage from './pages/CancellationsPage'
import Header from './components/Header'
import HomePage from './pages/HomePage'
import RegisterPage from './pages/RegisterPage'
import LoginPage from './pages/LoginPage'
import ProfilePage from './pages/ProfilePage'
import AdministratorsPage from './pages/AdministratorsPage'
import FlightsPage from './pages/FlightsPage'
import CheckInPage from './pages/CheckInPage'
import VerifyEmailPage from './pages/VerifyEmailPage'
import ResetPasswordPage from './pages/ResetPasswordPage'
import AddCardPage from './pages/AddCardPage'

interface Session {
  authenticated: boolean
  role: string | null
  is_email_verified: boolean
}

export default function App() {
  const sessionGeneration = useRef(0)
  const logoutPending = useRef(false)
  const [loading, setLoading] = useState(true)
  const [logoutBusy, setLogoutBusy] = useState(false)
  const [sessionError, setSessionError] = useState('')
  const [session, setSession] = useState<Session>({
    authenticated: false,
    role: null,
    is_email_verified: false,
  })

  const refreshSession = useCallback(async () => {
    if (logoutPending.current) return
    const generation = ++sessionGeneration.current
    try {
      const data = await api.get('/auth/session/')
      if (generation !== sessionGeneration.current) return
      setSessionError('')
      setSession({
        authenticated: Boolean(data.authenticated),
        role: data.role ?? null,
        is_email_verified: Boolean(data.is_email_verified),
      })
    } catch {
      if (generation !== sessionGeneration.current) return
      setSessionError('No fue posible comprobar la sesión. Reintenta antes de continuar.')
    } finally { setLoading(false) }
  }, [])

  useEffect(() => {
    refreshSession()
  }, [refreshSession])

  useEffect(() => {
    const expired = () => { sessionGeneration.current++; setSession({ authenticated: false, role: null, is_email_verified: false }); setSessionError('Tu sesión terminó. Inicia sesión de nuevo para continuar.') }
    window.addEventListener('session-expired', expired)
    return () => window.removeEventListener('session-expired', expired)
  }, [])

  useEffect(() => {
    if (!session.authenticated) return
    let lastSent = Date.now()
    let pending = false
    const activity = () => {
      if (document.visibilityState !== 'visible' || pending || Date.now() - lastSent < 61000) return
      pending = true; lastSent = Date.now()
      api.post('/auth/session/activity/', {}).then(() => refreshSession()).catch(() => {}).finally(() => { pending = false })
    }
    window.addEventListener('pointerdown', activity)
    window.addEventListener('keydown', activity)
    window.addEventListener('scroll', activity, { passive: true })
    return () => { window.removeEventListener('pointerdown', activity); window.removeEventListener('keydown', activity); window.removeEventListener('scroll', activity) }
  }, [session.authenticated, refreshSession])

  useEffect(() => {
    const refresh = () => { refreshSession() }
    window.addEventListener('focus', refresh)
    return () => window.removeEventListener('focus', refresh)
  }, [refreshSession])

  async function handleLogout() {
    if (logoutPending.current) return
    logoutPending.current = true
    sessionGeneration.current++
    setLogoutBusy(true)
    try {
      await api.post('/auth/logout/', {})
      sessionGeneration.current++
      setSession({ authenticated: false, role: null, is_email_verified: false })
      setSessionError('')
    } catch { setSessionError('No se pudo confirmar el cierre de sesión. Reintenta.') }
    finally { logoutPending.current = false; setLogoutBusy(false) }
  }

  function clearSessionAfterPasswordChange() {
    sessionGeneration.current++
    setSession({ authenticated: false, role: null, is_email_verified: false })
    setSessionError('')
  }

  if (loading) return <main className="page" role="status">Comprobando sesión…</main>

  return (
    <div className="app-layout">
      <Header
        authenticated={session.authenticated}
        role={session.role}
        logoutBusy={logoutBusy}
        onLogout={handleLogout}
      />
      {sessionError && (
        <div className="alert alert--error" role="alert">
          <span className="alert__body">{sessionError}</span>
          <button
            type="button"
            className="btn btn--secondary btn--small"
            onClick={() => {
              setSessionError('')
              refreshSession()
            }}
          >
            Reintentar
          </button>
        </div>
      )}
      <Routes>
        <Route path="/" element={<HomePage />} />
        <Route path="/vuelos" element={<FlightsPage session={session} />} />
        <Route path="/cancelaciones" element={<CancellationsPage session={session} />} />
        <Route path="/cancelaciones/:id" element={<CancellationsPage session={session} />} />
        <Route path="/check-in" element={<CheckInPage session={session} />} />
        <Route path="/catalogo" element={<Navigate to="/vuelos" replace />} />
        <Route path="/registro" element={<RegisterPage />} />
        <Route
          path="/login"
          element={<LoginPage onLoginSuccess={refreshSession} />}
        />
        <Route
          path="/perfil"
          element={
            <ProfilePage
              session={session}
              onPasswordChanged={clearSessionAfterPasswordChange}
            />
          }
        />
        <Route
          path="/administradores"
          element={<AdministratorsPage session={session} />}
        />
        <Route path="/verificar" element={<VerifyEmailPage />} />
        <Route path="/restablecer" element={<ResetPasswordPage />} />
        <Route
          path="/metodos/nueva"
          element={<AddCardPage session={session} />}
        />
      </Routes>
    </div>
  )
}
