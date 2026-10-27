import { Link } from 'react-router-dom'

interface ProfilePageProps {
  session: {
    authenticated: boolean
    role: string | null
    is_email_verified: boolean
  }
}

// La iteración 1 del backend solo expone el estado de sesión
// (/auth/session/): rol y verificación de correo. El detalle del
// perfil (nombres, documento, saldo, etc.) llegará cuando exista
// un endpoint propio; mientras tanto esta página muestra el
// resumen de cuenta disponible en el contrato vigente.
export default function ProfilePage({ session }: ProfilePageProps) {
  if (!session.authenticated) {
    return (
      <div className="page page--narrow">
        <div className="form-container">
          <h1 className="form-title">Sesión requerida</h1>
          <p className="form-subtitle">
            Debe iniciar sesión para poder visualizar los datos de su perfil.
          </p>
          <Link to="/login" className="btn btn--primary btn--full">
            Iniciar sesión
          </Link>
        </div>
      </div>
    )
  }

  return (
    <div className="page page--narrow">
      <div className="form-container">
        <h1 className="form-title">Mi perfil</h1>
        <p className="form-subtitle">Resumen de su cuenta</p>

        <div className="profile-item">
          <span className="profile-item__label">Rol</span>
          <span className="profile-item__value">{session.role}</span>
        </div>
        <div className="profile-item">
          <span className="profile-item__label">Correo</span>
          <span className="profile-item__value">
            {session.is_email_verified ? 'Verificado' : 'Sin verificar'}
          </span>
        </div>

        {!session.is_email_verified && (
          <div className="alert alert--warning">
            <span className="alert__body">
              Su correo aún no ha sido verificado. Revise su bandeja de
              entrada y siga el enlace de verificación.
            </span>
          </div>
        )}

        <div className="profile-actions">
          <Link to="/" className="btn btn--secondary">
            ← Volver al inicio
          </Link>
        </div>
      </div>
    </div>
  )
}