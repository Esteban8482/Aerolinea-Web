import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, ApiError } from '../api'

type Status = 'loading' | 'success' | 'error' | 'no-token'

export default function VerifyEmailPage() {
  const [status, setStatus] = useState<Status>('loading')
  const [message, setMessage] = useState('')

  useEffect(() => {
    const match = window.location.hash.match(/token=([^&]+)/)
    if (!match) {
      setStatus('no-token')
      return
    }

    const token = decodeURIComponent(match[1])
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
            setMessage('Su correo electrónico ya ha sido verificado anteriormente.')
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
    <div className="page page--narrow">
      <div className="form-container">
        <h1 className="form-title">Verificación de correo</h1>

        {status === 'loading' && (
          <p className="form-subtitle">Verificando su correo electrónico...</p>
        )}

        {status === 'no-token' && (
          <>
            <div className="alert alert--error">
              <span className="alert__body">
                No se encontró un código de verificación en la dirección. Haga
                clic en el enlace completo que recibió por correo electrónico.
              </span>
            </div>
            <Link to="/login" className="btn btn--primary btn--full">
              Ir a iniciar sesión
            </Link>
          </>
        )}

        {status === 'success' && (
          <>
            <div className="alert alert--success">
              <span className="alert__title">¡Correo verificado!</span>
              <span className="alert__body">
                Su dirección de correo electrónico ha sido verificada
                exitosamente. Ya puede iniciar sesión y utilizar todos los
                servicios.
              </span>
            </div>
            <Link to="/login" className="btn btn--primary btn--full">
              Iniciar sesión
            </Link>
          </>
        )}

        {status === 'error' && (
          <>
            <div className="alert alert--error">
              <span className="alert__title">No se pudo verificar</span>
              <span className="alert__body">{message}</span>
            </div>
            <Link to="/login" className="btn btn--secondary btn--full">
              Ir a iniciar sesión
            </Link>
          </>
        )}
      </div>
    </div>
  )
}

