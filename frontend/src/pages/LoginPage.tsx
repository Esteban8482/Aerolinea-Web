import { useEffect, useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { api, ApiError } from '../api'
import {
  AuthLayout,
  Button,
  Field,
  PasswordField,
  Feedback,
} from '../components/UI'

type Step =
  | 'login'
  | 'recover-email'
  | 'recover-token'
  | 'recover-password'
  | 'recover-success'

interface LoginPageProps {
  onLoginSuccess: () => void
}

export default function LoginPage({ onLoginSuccess }: LoginPageProps) {
  const navigate = useNavigate()

  const [step, setStep] = useState<Step>('login')

  /* ---------- login ---------- */
  const [identifier, setIdentifier] = useState('')
  const [password, setPassword] = useState('')
  const [loginError, setLoginError] = useState('')
  const [loginBusy, setLoginBusy] = useState(false)

  /* ---------- recuperación ---------- */
  const [recoveryEmail, setRecoveryEmail] = useState('')
  const [recoveryToken, setRecoveryToken] = useState('')
  const [newPassword, setNewPassword] = useState('')
  const [newPasswordConfirm, setNewPasswordConfirm] = useState('')
  const [recoverError, setRecoverError] = useState('')
  const [recoverBusy, setRecoverBusy] = useState(false)

  /* ---------- leer token del fragmento URL (#token=...) ---------- */
  useEffect(() => {
    const token = new URLSearchParams(window.location.hash.slice(1)).get(
      'token',
    )
    if (token) {
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
      const intended = new URLSearchParams(window.location.search).get('next')
      navigate(
        intended?.startsWith('/') && !intended.startsWith('//')
          ? intended
          : '/',
      )
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
      setRecoverError(
        'Ingrese el código de verificación que recibió por correo.',
      )
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
          const msgs = Object.values(err.details).flat().map(String).join(' ')
          setRecoverError(
            msgs || 'El código es inválido o ha expirado. Solicite uno nuevo.',
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

  if (step === 'recover-success')
    return (
      <AuthLayout title="Contraseña actualizada">
        <Feedback variant="success">
          Tu contraseña se actualizó. Las sesiones anteriores se cerraron;
          inicia sesión con tu nueva contraseña.
        </Feedback>
        <Button onClick={resetToLogin}>Ir a iniciar sesión</Button>
      </AuthLayout>
    )

  if (step === 'login')
    return (
      <AuthLayout
        title="Inicia sesión"
        eyebrow="Bienvenido a Alas"
        description="Accede a tu cuenta y continúa con tu próximo viaje."
      >
        {loginError && <Feedback>{loginError}</Feedback>}
        <form className="auth-form" onSubmit={handleLogin}>
          <Field
            id="login-id"
            label="Correo electrónico"
            placeholder="Correo o identificador"
            value={identifier}
            onChange={(e) => setIdentifier(e.target.value)}
            autoComplete="username"
            required
          />
          <PasswordField
            id="login-pass"
            label="Contraseña"
            placeholder="Tu contraseña"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            autoComplete="current-password"
            required
          />
          <Button type="submit" busy={loginBusy}>
            {loginBusy ? 'Iniciando sesión…' : 'Iniciar sesión'}
          </Button>
          <button
            type="button"
            className="auth-link"
            onClick={() => {
              setStep('recover-email')
              setLoginError('')
            }}
          >
            ¿Olvidaste tu contraseña?
          </button>
        </form>
        <p className="auth-footer">
          ¿No tienes una cuenta? <Link to="/registro">Crear cuenta</Link>
        </p>
      </AuthLayout>
    )

  return (
    <AuthLayout
      title={
        step === 'recover-password'
          ? 'Restablecer contraseña'
          : 'Recupera tu contraseña'
      }
      eyebrow="Seguridad de tu cuenta"
      description={
        step === 'recover-email'
          ? 'Ingresa el correo asociado a tu cuenta. Si podemos identificarla, te enviaremos instrucciones.'
          : undefined
      }
    >
      {recoverError && <Feedback>{recoverError}</Feedback>}
      {step === 'recover-email' && (
        <form
          className="auth-form auth-form--compact"
          onSubmit={handleRecoveryRequest}
        >
          <Field
            id="recover-email"
            label="Correo electrónico"
            type="email"
            placeholder="nombre@correo.com"
            value={recoveryEmail}
            onChange={(e) => setRecoveryEmail(e.target.value)}
            autoComplete="email"
            required
          />
          <Button type="submit" busy={recoverBusy}>
            {recoverBusy ? 'Enviando…' : 'Enviar instrucciones'}
          </Button>
        </form>
      )}
      {step === 'recover-token' && (
        <>
          <Feedback variant="info">
            Si la cuenta existe, recibirás instrucciones de recuperación. Revisa
            tu correo y abre el enlace o copia su código.
          </Feedback>
          <form className="auth-form" onSubmit={handleTokenSubmit}>
            <Field
              id="recover-token"
              label="Código de verificación"
              value={recoveryToken}
              onChange={(e) => setRecoveryToken(e.target.value)}
              required
            />
            <Button type="submit">Continuar</Button>
          </form>
        </>
      )}
      {step === 'recover-password' && (
        <form className="auth-form" onSubmit={handlePasswordReset}>
          <PasswordField
            label="Nueva contraseña"
            value={newPassword}
            onChange={(e) => setNewPassword(e.target.value)}
            autoComplete="new-password"
            required
            hint="Mínimo 12 caracteres; no debe ser exclusivamente numérica, común ni similar a tus datos."
          />
          <PasswordField
            label="Confirmar nueva contraseña"
            value={newPasswordConfirm}
            onChange={(e) => setNewPasswordConfirm(e.target.value)}
            autoComplete="new-password"
            required
          />
          <Button type="submit" busy={recoverBusy}>
            {recoverBusy ? 'Actualizando…' : 'Guardar contraseña'}
          </Button>
        </form>
      )}
      <button
        type="button"
        className="auth-link auth-link--back"
        onClick={resetToLogin}
      >
        Volver al inicio de sesión
      </button>
    </AuthLayout>
  )
}
