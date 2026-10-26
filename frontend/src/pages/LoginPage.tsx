import { useEffect, useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api, ApiError } from '../api'

type Step = 'login' | 'recover-email' | 'recover-token' | 'recover-password' | 'recover-success'

interface LoginPageProps {
  onLoginSuccess: () => void
}

export default function LoginPage({ onLoginSuccess }: LoginPageProps) {
  const navigate = useNavigate()

  const [step, setStep] = useState<Step>('login')

  /* ---------- login ---------- */
  const [identifier, setIdentifier] = useState('')
  const [password, setPassword] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [loginError, setLoginError] = useState('')
  const [loginBusy, setLoginBusy] = useState(false)

  /* ---------- recuperación ---------- */
  const [recoveryEmail, setRecoveryEmail] = useState('')
  const [recoveryToken, setRecoveryToken] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [newPasswordConfirm, setNewPasswordConfirm] = useState('')
  const [showNewPassword, setShowNewPassword] = useState(false)
  const [recoverError, setRecoverError] = useState('')
  const [recoverBusy, setRecoverBusy] = useState(false)

  /* ---------- leer token del fragmento URL (#token=...) ---------- */
  useEffect(() => {
    const match = window.location.hash.match(/token=([^&]+)/)
    if (match) {
      const token = decodeURIComponent(match[1])
      setRecoveryToken(token)
      setStep('recover-password')
      window.history.replaceState(
        null,
        '',
        window.location.pathname + window.location.search,
      )
    }
  }, [])

  /* ---------- enviar login ---------- */
  async function handleLogin(e: FormEvent) {
    e.preventDefault()
    setLoginError('')
    if (!identifier.trim() || !password) {
      setLoginError('Ingrese su correo electrónico y contraseña.')
      return
    }

    setLoginBusy(true)
    const credentials = identifier.includes('@')
      ? { email: identifier, password }
      : { root_id: identifier, password }

    try {
      await api.post('/auth/login/', credentials)
      onLoginSuccess()
      navigate('/')
    } catch (err) {
      if (err instanceof ApiError) {
        if (err.status === 429) {
          setLoginError(
            'Demasiados intentos. Su cuenta ha sido bloqueada temporalmente. Intente de nuevo en unos minutos.',
          )
        } else if (err.status === 401) {
          setLoginError('Correo electrónico o contraseña incorrectos.')
        } else {
          setLoginError(err.message)
        }
      } else {
        setLoginError(
          'No fue posible contactar el servidor. Verifique su conexión.',
        )
      }
    } finally {
      setLoginBusy(false)
    }
  }

  /* ---------- solicitar recuperación ---------- */
  async function handleRecoveryRequest(e: FormEvent) {
    e.preventDefault()
    setRecoverError('')
    if (!recoveryEmail.trim()) {
      setRecoverError('Ingrese su correo electrónico.')
      return
    }
    if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(recoveryEmail)) {
      setRecoverError('Ingrese un correo electrónico válido.')
      return
    }

    setRecoverBusy(true)
    try {
      await api.post('/auth/password-recovery/', { email: recoveryEmail })
      setStep('recover-token')
    } catch (err) {
      if (err instanceof ApiError) {
        if (err.status === 429) {
          setRecoverError(
            'Se ha excedido el límite de solicitudes. Espere unos minutos.',
          )
        } else {
          setRecoverError(err.message)
        }
      } else {
        setRecoverError('No fue posible contactar el servidor.')
      }
    } finally {
      setRecoverBusy(false)
    }
  }

  /* ---------- validar token (pasar al paso de nueva contraseña) ---------- */
  function handleTokenSubmit(e: FormEvent) {
    e.preventDefault()
    setRecoverError('')
    if (!recoveryToken.trim()) {
      setRecoverError('Ingrese el código de verificación que recibió por correo.')
      return
    }
    setStep('recover-password')
  }

  /* ---------- restablecer contraseña ---------- */
  async function handlePasswordReset(e: FormEvent) {
    e.preventDefault()
    setRecoverError('')

    if (!newPassword) {
      setRecoverError('Ingrese la nueva contraseña.')
      return
    }
    if (newPassword.length < 12) {
      setRecoverError('La contraseña debe tener al menos 12 caracteres.')
      return
    }
    if (newPassword !== newPasswordConfirm) {
      setRecoverError('Las contraseñas no coinciden.')
      return
    }

    setRecoverBusy(true)
    try {
      await api.post('/auth/password-reset/', {
        token: recoveryToken,
        password: newPassword,
        password_confirmation: newPasswordConfirm,
      })
      setStep('recover-success')
    } catch (err) {
      if (err instanceof ApiError) {
        if (err.status === 400) {
          const msgs = Object.values(err.details)
            .flat()
            .map(String)
            .join(' ')
          setRecoverError(
            msgs ||
              'El código es inválido o ha expirado. Solicite uno nuevo.',
          )
        } else if (err.status === 410) {
          setRecoverError(
            'El código de verificación ha expirado. Solicite uno nuevo.',
          )
        } else if (err.status === 429) {
          setRecoverError(
            'Se ha excedido el límite de solicitudes. Espere unos minutos.',
          )
        } else {
          setRecoverError(err.message)
        }
      } else {
        setRecoverError('No fue posible contactar el servidor.')
      }
    } finally {
      setRecoverBusy(false)
    }
  }

  /* ---------- helpers de render ---------- */
  function resetToLogin() {
    setStep('login')
    setRecoverError('')
    setRecoveryEmail('')
    setRecoveryToken('')
    setNewPassword('')
    setNewPasswordConfirm('')
  }

  const stepNumber =
    step === 'recover-email' ? 1 : step === 'recover-token' ? 2 : 3

  /* ---------- render: éxito de restablecimiento ---------- */
  if (step === 'recover-success') {
    return (
      <div className="page page--narrow">
        <div className="form-container">
          <h1 className="form-title">Contraseña actualizada</h1>
          <div className="alert alert--success">
            <span className="alert__title">¡Listo!</span>
            <span className="alert__body">
              Su contraseña ha sido restablecida exitosamente. Todas las sesiones
              anteriores han sido cerradas. Inicie sesión con su nueva contraseña.
            </span>
          </div>
          <button
            type="button"
            className="btn btn--primary btn--full"
            onClick={resetToLogin}
          >
            Ir a iniciar sesión
          </button>
        </div>
      </div>
    )
  }

  /* ---------- render: formulario de login ---------- */
  if (step === 'login') {
    return (
      <div className="page page--narrow">
        <div className="form-container">
          <h1 className="form-title">Iniciar sesión</h1>
          <p className="form-subtitle">
            Ingrese sus credenciales para acceder a su cuenta.
          </p>

          {loginError && (
            <div className="alert alert--error">
              <span className="alert__body">{loginError}</span>
            </div>
          )}

          <form onSubmit={handleLogin} noValidate>
            <div className="form-group mb-2">
              <label className="form-label" htmlFor="login-id">
                Correo electrónico
              </label>
              <input
                id="login-id"
                type="email"
                className="form-input"
                value={identifier}
                onChange={(e) => setIdentifier(e.target.value)}
                autoComplete="username"
                placeholder="correo@ejemplo.com"
              />
            </div>

            <div className="form-group mb-2">
              <label className="form-label" htmlFor="login-pass">
                Contraseña
              </label>
              <div className="password-wrapper">
                <input
                  id="login-pass"
                  type={showPassword ? 'text' : 'password'}
                  className="form-input"
                  value={password}
                  onChange={(e) => setPassword(e.target.value)}
                  autoComplete="current-password"
                />
                <button
                  type="button"
                  className="password-toggle"
                  onClick={() => setShowPassword(!showPassword)}
                  aria-label={
                    showPassword ? 'Ocultar contraseña' : 'Mostrar contraseña'
                  }
                >
                  {showPassword ? 'Ocultar' : 'Ver'}
                </button>
              </div>
            </div>

            <button
              type="submit"
              className="btn btn--primary btn--full"
              disabled={loginBusy}
            >
              {loginBusy ? 'Iniciando sesión...' : 'Iniciar sesión'}
            </button>
          </form>

          <div className="login-footer">
            <button
              type="button"
              className="login-link"
              onClick={() => {
                setStep('recover-email')
                setLoginError('')
              }}
            >
              ¿Olvidó su contraseña?
            </button>
          </div>

          <div className="login-footer">
            ¿No tiene una cuenta?{' '}
            <Link to="/registro">Registrarse</Link>
          </div>
        </div>
      </div>
    )
  }

  /* ---------- render: pasos de recuperación ---------- */
  return (
    <div className="page page--narrow">
      <div className="form-container">
        <button type="button" className="login-back" onClick={resetToLogin}>
          ← Volver a iniciar sesión
        </button>

        <h1 className="form-title">Recuperar contraseña</h1>

        {/* Indicador de paso */}
        <div className="step-indicator">
          {[1, 2, 3].map((n) => (
            <div
              key={n}
              className={`step-indicator__step ${n <= stepNumber ? 'step-indicator__step--active' : ''}`}
            />
          ))}
        </div>

        {recoverError && (
          <div className="alert alert--error">
            <span className="alert__body">{recoverError}</span>
          </div>
        )}

        {/* Paso 1: correo electrónico */}
        {step === 'recover-email' && (
          <>
            <p className="form-subtitle">
              Ingrese el correo electrónico asociado a su cuenta. Le enviaremos
              un código de verificación.
            </p>
            <form onSubmit={handleRecoveryRequest} noValidate>
              <div className="form-group mb-2">
                <label className="form-label" htmlFor="recover-email">
                  Correo electrónico
                </label>
                <input
                  id="recover-email"
                  type="email"
                  className="form-input"
                  value={recoveryEmail}
                  onChange={(e) => setRecoveryEmail(e.target.value)}
                  autoComplete="email"
                  placeholder="correo@ejemplo.com"
                />
              </div>
              <button
                type="submit"
                className="btn btn--primary btn--full"
                disabled={recoverBusy}
              >
                {recoverBusy ? 'Enviando...' : 'Enviar código'}
              </button>
            </form>
          </>
        )}

        {/* Paso 2: código de verificación */}
        {step === 'recover-token' && (
          <>
            <div className="alert alert--info">
              <span className="alert__body">
                Si la cuenta existe, hemos enviado un correo con un enlace de
                recuperación a <strong>{recoveryEmail}</strong>. Revise su
                bandeja de entrada y copie el código o haga clic en el enlace
                del correo.
              </span>
            </div>
            <form onSubmit={handleTokenSubmit} noValidate>
              <div className="form-group mb-2">
                <label className="form-label" htmlFor="recover-token">
                  Código de verificación
                </label>
                <input
                  id="recover-token"
                  className="form-input"
                  value={recoveryToken}
                  onChange={(e) => setRecoveryToken(e.target.value)}
                  placeholder="Pegue aquí el código del correo"
                />
                <span className="form-hint">
                  El código se encuentra en el enlace de recuperación que
                  recibió por correo electrónico.
                </span>
              </div>
              <button
                type="submit"
                className="btn btn--primary btn--full"
                disabled={!recoveryToken.trim()}
              >
                Continuar
              </button>
            </form>
          </>
        )}

        {/* Paso 3: nueva contraseña */}
        {step === 'recover-password' && (
          <>
            <p className="form-subtitle">
              Ingrese su nueva contraseña. Debe tener al menos 12 caracteres.
            </p>
            <form onSubmit={handlePasswordReset} noValidate>
              <div className="form-group mb-2">
                <label className="form-label" htmlFor="new-pass">
                  Nueva contraseña
                </label>
                <div className="password-wrapper">
                  <input
                    id="new-pass"
                    type={showNewPassword ? 'text' : 'password'}
                    className="form-input"
                    value={newPassword}
                    onChange={(e) => setNewPassword(e.target.value)}
                    autoComplete="new-password"
                  />
                  <button
                    type="button"
                    className="password-toggle"
                    onClick={() => setShowNewPassword(!showNewPassword)}
                    aria-label={
                      showNewPassword
                        ? 'Ocultar contraseña'
                        : 'Mostrar contraseña'
                    }
                  >
                    {showNewPassword ? 'Ocultar' : 'Ver'}
                  </button>
                </div>
                <span className="form-hint">Mínimo 12 caracteres.</span>
              </div>

              <div className="form-group mb-2">
                <label className="form-label" htmlFor="confirm-pass">
                  Confirmar contraseña
                </label>
                <input
                  id="confirm-pass"
                  type="password"
                  className="form-input"
                  value={newPasswordConfirm}
                  onChange={(e) => setNewPasswordConfirm(e.target.value)}
                  autoComplete="new-password"
                />
              </div>

              <button
                type="submit"
                className="btn btn--primary btn--full"
                disabled={recoverBusy}
              >
                {recoverBusy ? 'Actualizando...' : 'Actualizar contraseña'}
              </button>
            </form>
          </>
        )}
      </div>
    </div>
  )
}

