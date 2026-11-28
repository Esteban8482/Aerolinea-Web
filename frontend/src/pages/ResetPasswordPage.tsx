import { useEffect, useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { api, ApiError } from '../api'
import { AuthLayout, Button, Feedback, PasswordField } from '../components/UI'

/**
 * Página de restablecimiento de contraseña.
 * Se accede desde el enlace enviado al correo: /restablecer#token=…
 * También se puede acceder manualmente desde el flujo del LoginPage.
 */
export default function ResetPasswordPage() {
  const [token] = useState(
    () => new URLSearchParams(window.location.hash.slice(1)).get('token') ?? '',
  )
  const [password, setPassword] = useState('')
  const [confirm, setConfirm] = useState('')
  const [error, setError] = useState('')
  const [busy, setBusy] = useState(false)
  const [success, setSuccess] = useState(false)
  const noToken = !token
  useEffect(() => {
    window.history.replaceState(
      null,
      '',
      window.location.pathname + window.location.search,
    )
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
          const msgs = Object.values(err.details).flat().map(String).join(' ')
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

  if (success)
    return (
      <AuthLayout title="Contraseña actualizada">
        <Feedback variant="success">
          Tu contraseña se actualizó y las sesiones anteriores se cerraron.
          Inicia sesión con tu nueva contraseña.
        </Feedback>
        <Link to="/login" className="btn btn--primary">
          Iniciar sesión
        </Link>
      </AuthLayout>
    )
  if (noToken)
    return (
      <AuthLayout title="Restablecer contraseña">
        <Feedback>
          No se encontró un código de restablecimiento. Abre el enlace completo
          del correo o solicita uno nuevo.
        </Feedback>
        <Link to="/login" className="btn btn--secondary">
          Volver al inicio de sesión
        </Link>
      </AuthLayout>
    )
  return (
    <AuthLayout
      title="Restablecer contraseña"
      description="Crea una nueva contraseña para acceder nuevamente a tu cuenta."
    >
      {error && <Feedback>{error}</Feedback>}
      <form className="auth-form" onSubmit={handleSubmit}>
        <PasswordField
          id="reset-pass"
          label="Nueva contraseña"
          placeholder="Mínimo 12 caracteres"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          autoComplete="new-password"
          required
          hint="Mínimo 12 caracteres; no debe ser exclusivamente numérica, común ni similar a tus datos."
        />
        <PasswordField
          id="reset-confirm"
          label="Confirmar nueva contraseña"
          placeholder="Repetir contraseña"
          value={confirm}
          onChange={(e) => setConfirm(e.target.value)}
          autoComplete="new-password"
          required
        />
        <Button type="submit" busy={busy}>
          {busy ? 'Actualizando…' : 'Guardar contraseña'}
        </Button>
      </form>
      <Link to="/login" className="btn btn--secondary">
        Volver al inicio de sesión
      </Link>
    </AuthLayout>
  )
}
