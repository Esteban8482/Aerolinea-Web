import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, ApiError } from '../api'
import { Mail } from 'lucide-react'
import { AuthLayout, Feedback, Loading } from '../components/UI'

type Status = 'loading' | 'success' | 'error' | 'no-token'

export default function VerifyEmailPage() {
  const [status, setStatus] = useState<Status>('loading')
  const [message, setMessage] = useState('')

  const started = useRef(false)
  useEffect(() => {
    if (started.current) return
    started.current = true
    const token = new URLSearchParams(window.location.hash.slice(1)).get(
      'token',
    )
    if (!token) {
      setStatus('no-token')
      return
    }

    // Limpiar el token de la barra de direcciones por seguridad.
    window.history.replaceState(
      null,
      '',
      window.location.pathname + window.location.search,
    )

    api
      .post('/auth/verify-email/', { token })
      .then(() => {
        setStatus('success')
      })
      .catch((err) => {
        setStatus('error')
        if (err instanceof ApiError) {
          if (err.status === 410) {
            setMessage(
              'El enlace de verificación ha expirado. Solicite un nuevo correo de verificación desde su cuenta.',
            )
          } else if (err.status === 409) {
            setMessage(
              'Su correo electrónico ya ha sido verificado anteriormente.',
            )
          } else {
            setMessage(
              err.message ||
                'El enlace de verificación no es válido. Solicite uno nuevo.',
            )
          }
        } else {
          setMessage('No fue posible contactar el servidor. Intente de nuevo.')
        }
      })
  }, [])

  return (
    <AuthLayout
      title={status === 'success' ? 'Correo verificado' : 'Verifica tu correo'}
      eyebrow="Verificación de cuenta"
      icon={<Mail size={22} />}
    >
      {status === 'loading' && <Loading>Verificando tu correo…</Loading>}
      {status === 'no-token' && (
        <Feedback>
          No se encontró un código de verificación. Abre el enlace completo que
          recibiste por correo.
        </Feedback>
      )}
      {status === 'error' && <Feedback>{message}</Feedback>}
      {status === 'success' && (
        <Feedback variant="success">
          Tu correo se verificó correctamente. Ya puedes acceder a los servicios
          de tu cuenta.
        </Feedback>
      )}
      {status !== 'loading' && (
        <>
          <Link to="/login" className="btn btn--primary">
            Iniciar sesión
          </Link>
          <Link to="/perfil" className="btn btn--secondary">
            Ir a mi cuenta
          </Link>
          <p className="form-hint">
            Desde tu cuenta puedes solicitar otro correo de verificación.
          </p>
        </>
      )}
    </AuthLayout>
  )
}
