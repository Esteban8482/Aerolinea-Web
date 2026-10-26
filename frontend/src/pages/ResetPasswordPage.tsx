import { useEffect, useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { api, ApiError } from '../api'

/**
 * Página de restablecimiento de contraseña.
 * Se accede desde el enlace enviado al correo: /restablecer#token=…
 * También se puede acceder manualmente desde el flujo del LoginPage.
 */
export default function ResetPasswordPage() {
  const [token, setToken] = useState('')
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [showPassword, setShowPassword] = useState(false)
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [success, setSuccess] = useState(false)
  const [noToken, setNoToken] = useState(false)

  useEffect(() => {
    const match = window.location.hash.match(/token=([^&]+)/)
    if (match) {
      setToken(decodeURIComponent(match[1]))
      window.history.replaceState(
        null,
        '',
        window.location.pathname + window.location.search,
      )
    } else {
      setNoToken(true)
    }
  }, [])

  async function handleSubmit(e: FormEvent) {
    e.preventDefault()
    setError('')

    if (!password) {
      setError('Ingrese la nueva contraseña.')
      return
    }
    if (password.length < 12) {
      setError('La contraseña debe tener al menos 12 caracteres.')
      return
    }
    if (password !== confirm) {
      setError('Las contraseñas no coinciden.')
      return
    }

    setBusy(true)
    try {
      await api.post('/auth/password-reset/', {
        token,
        password,
        password_confirmation: confirm,
      })
      setSuccess(true)
    } catch (err) {
      if (err instanceof ApiError) {
        if (err.status === 400 || err.status === 410) {
          const msgs = Object.values(err.details)
            .flat()
            .map(String)
            .join(' ')
          setError(
            msgs ||
              'El enlace es inválido o ha expirado. Solicite uno nuevo desde la pantalla de inicio de sesión.',
          )
        } else if (err.status === 429) {
          setError(
            'Se ha excedido el límite de solicitudes. Espere unos minutos.',
          )
        } else {
          setError(err.message)
        }
      } else {
        setError('No fue posible contactar el servidor.')
      }
    } finally {
      setBusy(false)
    }
  }

  if (success) {
    return (
      <div className="page page--narrow">
        <div className="form-container">
          <h1 className="form-title">Contraseña actualizada</h1>
          <div className="alert alert--success">
            <span className="alert__title">¡Listo!</span>
            <span className="alert__body">
              Su contraseña ha sido restablecida exitosamente. Todas las sesiones
              anteriores han sido cerradas. Inicie sesión con su nueva
              contraseña.
            </span>
          </div>
          <Link to="/login" className="btn btn--primary btn--full">
            Iniciar sesión
          </Link>
        </div>
      </div>
    )
  }

  if (noToken) {
    return (
      <div className="page page--narrow">
        <div className="form-container">
          <h1 className="form-title">Restablecer contraseña</h1>
          <div className="alert alert--error">
            <span className="alert__body">
              No se encontró un código de restablecimiento en la dirección. Haga
              clic en el enlace completo que recibió por correo electrónico, o
              solicite uno nuevo.
            </span>
          </div>
          <Link to="/login" className="btn btn--primary btn--full">
            Ir a iniciar sesión
          </Link>
        </div>
      </div>
    )
  }

  return (
    <div className="page page--narrow">
      <div className="form-container">
        <h1 className="form-title">Nueva contraseña</h1>
        <p className="form-subtitle">
          Ingrese su nueva contraseña. Debe tener al menos 12 caracteres.
        </p>

        {error && (
          <div className="alert alert--error">
            <span className="alert__body">{error}</span>
          </div>
        )}

        <form onSubmit={handleSubmit} noValidate>
          <div className="form-group mb-2">
            <label className="form-label" htmlFor="reset-pass">
              Nueva contraseña
            </label>
            <div className="password-wrapper">
              <input
                id="reset-pass"
                type={showPassword ? 'text' : 'password'}
                className="form-input"
                value={password}
                onChange={(e) => setPassword(e.target.value)}
                autoComplete="new-password"
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
            <span className="form-hint">Mínimo 12 caracteres.</span>
          </div>

          <div className="form-group mb-2">
            <label className="form-label" htmlFor="reset-confirm">
              Confirmar contraseña
            </label>
            <input
              id="reset-confirm"
              type="password"
              className="form-input"
              value={confirm}
              onChange={(e) => setConfirm(e.target.value)}
              autoComplete="new-password"
            />
          </div>

          <button
            type="submit"
            className="btn btn--primary btn--full"
            disabled={busy}
          >
            {busy ? 'Actualizando...' : 'Actualizar contraseña'}
          </button>
        </form>

        <div className="login-footer">
          <Link to="/login">Volver a iniciar sesión</Link>
        </div>
      </div>
    </div>
  )
}

