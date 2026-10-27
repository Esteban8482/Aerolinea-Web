import { useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, ApiError } from '../api'

interface ProfileData {
  id: number
  username: string
  email: string | null
  first_name: string
  last_name: string
  document_number: string
  document_type: string
  birth_date: string | null
  birth_place: string
  billing_address: string
  gender: string
  role: string
  is_email_verified: boolean
  wallet_balance: string
}

interface ProfilePageProps {
  session: {
    authenticated: boolean
    role: string | null
    is_email_verified: boolean
  }
}

export default function ProfilePage({ session }: ProfilePageProps) {
  const [profile, setProfile] = useState<ProfileData | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState('')

  useEffect(() => {
    if (!session.authenticated) {
      setLoading(false)
      return
    }

    api
      .get('/auth/profile/')
      .then((data) => {
        setProfile(data as ProfileData)
      })
      .catch((err) => {
        if (err instanceof ApiError) {
          setError(err.message)
        } else {
          setError('No fue posible cargar la información de su perfil.')
        }
      })
      .finally(() => {
        setLoading(false)
      })
  }, [session.authenticated])

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

  if (loading) {
    return (
      <div className="page page--narrow">
        <div className="form-container">
          <h1 className="form-title">Mi perfil</h1>
          <p className="form-subtitle">Cargando su información...</p>
        </div>
      </div>
    )
  }

  if (error) {
    return (
      <div className="page page--narrow">
        <div className="form-container">
          <h1 className="form-title">Mi perfil</h1>
          <div className="alert alert--error">
            <span className="alert__title">Error al cargar perfil</span>
            <span className="alert__body">{error}</span>
          </div>
          <Link to="/" className="btn btn--secondary btn--full">
            Volver al inicio
          </Link>
        </div>
      </div>
    )
  }

  function formatBirthDate(dateStr: string | null): string {
    if (!dateStr) return 'No registrada'
    const parts = dateStr.split('-')
    if (parts.length === 3) {
      return `${parts[2]}/${parts[1]}/${parts[0]}`
    }
    return dateStr
  }

  return (
    <div className="page page--wide">
      <div className="profile-container">
        <div className="profile-header">
          <div>
            <h1 className="profile-title">
              {profile?.first_name || profile?.last_name
                ? `${profile.first_name} ${profile.last_name}`
                : profile?.username || 'Mi Perfil'}
            </h1>
            <p className="profile-role">
              Rol: <strong>{profile?.role}</strong> · Usuario:{' '}
              <strong>{profile?.username}</strong>
            </p>
          </div>
          <div className="profile-badge-zone">
            {profile?.is_email_verified ? (
              <span className="badge badge--success">✓ Correo verificado</span>
            ) : (
              <span className="badge badge--warning">⚠ Correo sin verificar</span>
            )}
          </div>
        </div>

        <div className="profile-grid">
          {/* Tarjeta 1: Datos Personales */}
          <div className="profile-card">
            <h2 className="profile-card__title">Datos personales</h2>
            <div className="profile-card__content">
              <div className="profile-item">
                <span className="profile-item__label">Nombres y apellidos</span>
                <span className="profile-item__value">
                  {profile?.first_name} {profile?.last_name}
                </span>
              </div>
              <div className="profile-item">
                <span className="profile-item__label">Documento de identidad</span>
                <span className="profile-item__value">
                  {profile?.document_number || 'No registrado'}
                </span>
              </div>
              <div className="profile-item">
                <span className="profile-item__label">Fecha de nacimiento</span>
                <span className="profile-item__value">
                  {formatBirthDate(profile?.birth_date ?? null)}
                </span>
              </div>
              <div className="profile-item">
                <span className="profile-item__label">Lugar de nacimiento</span>
                <span className="profile-item__value">
                  {profile?.birth_place || 'No registrado'}
                </span>
              </div>
              <div className="profile-item">
                <span className="profile-item__label">Género</span>
                <span className="profile-item__value">
                  {profile?.gender || 'No registrado'}
                </span>
              </div>
            </div>
          </div>

          {/* Tarjeta 2: Contacto y Facturación */}
          <div className="profile-card">
            <h2 className="profile-card__title">Contacto y facturación</h2>
            <div className="profile-card__content">
              <div className="profile-item">
                <span className="profile-item__label">Correo electrónico</span>
                <span className="profile-item__value">
                  {profile?.email || 'No registrado'}
                </span>
              </div>
              <div className="profile-item">
                <span className="profile-item__label">Dirección de facturación</span>
                <span className="profile-item__value">
                  {profile?.billing_address || 'No registrada'}
                </span>
              </div>
              <div className="profile-item">
                <span className="profile-item__label">Saldo en Billetera Alas</span>
                <span className="profile-item__value profile-item__value--highlight">
                  ${profile?.wallet_balance ?? '0.00'} COP
                </span>
              </div>
              <div className="profile-item">
                <span className="profile-item__label">Identificador de cuenta</span>
                <span className="profile-item__value">#{profile?.id}</span>
              </div>
            </div>
          </div>
        </div>

        <div className="profile-actions">
          <Link to="/" className="btn btn--secondary">
            ← Volver al inicio
          </Link>
        </div>
      </div>
    </div>
  )
}

