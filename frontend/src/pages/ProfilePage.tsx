import { useCallback, useEffect, useRef, useState, type FormEvent } from 'react'
import { Link, useNavigate } from 'react-router-dom'
import { Armchair, PlaneTakeoff, UserRound, Wallet, X } from 'lucide-react'
import { api, ApiError } from '../api'
import WalletPanel from '../components/WalletPanel'
import { Dialog } from '../components/UI'
import { useConfirmedPurchase } from '../operations'
import type { Compra, PerfilUsuario, Reserva, Silla } from '../types/flight'

interface ProfilePageProps {
  onPasswordChanged: () => void
  session: {
    authenticated: boolean
    role: string | null
    is_email_verified: boolean
  }
}

export default function ProfilePage({ session, onPasswordChanged }: ProfilePageProps) {
  const navigate = useNavigate()
  const [profile, setProfile] = useState<PerfilUsuario | null>(null)
  const [compras, setCompras] = useState<Compra[]>([])
  const [reservas, setReservas] = useState<Reserva[]>([])
  const [loading, setLoading] = useState(true)
  const [notification, setNotification] = useState<{ type: 'success' | 'error'; message: string } | null>(null)

  const purchase = useConfirmedPurchase()
  const [purchaseApproval, setPurchaseApproval] = useState<{
    total: string
    balance: string
    resolve: (accepted: boolean) => void
  } | null>(null)

  // Estado para cambio de silla
  const [selectedTicketId, setSelectedTicketId] = useState<number | null>(null)
  const [seatMap, setSeatMap] = useState<Silla[]>([])
  const [loadingSeatMap, setLoadingSeatMap] = useState(false)
  const [changingSeat, setChangingSeat] = useState(false)
  const [rootPassword, setRootPassword] = useState({
    current_password: '',
    password: '',
    password_confirmation: '',
  })
  const [passwordVisibility, setPasswordVisibility] = useState({
    current: false,
    next: false,
    confirmation: false,
  })
  const [passwordError, setPasswordError] = useState('')
  const [passwordBusy, setPasswordBusy] = useState(false)
  const passwordSubmission = useRef(false)

  function updateRootPassword(field: keyof typeof rootPassword, value: string) {
    setRootPassword((current) => ({ ...current, [field]: value }))
    setPasswordError('')
  }

  async function handleRootPasswordChange(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    if (passwordSubmission.current) return
    setPasswordError('')
    if (!rootPassword.current_password) {
      setPasswordError('Ingresa tu contraseña actual.')
      return
    }
    if (rootPassword.password.length < 12) {
      setPasswordError('La nueva contraseña debe tener al menos 12 caracteres.')
      return
    }
    if (rootPassword.password !== rootPassword.password_confirmation) {
      setPasswordError('Las contraseñas nuevas no coinciden.')
      return
    }

    passwordSubmission.current = true
    setPasswordBusy(true)
    try {
      await api.post('/users/root/password/', rootPassword)
      setRootPassword({ current_password: '', password: '', password_confirmation: '' })
      onPasswordChanged()
      navigate('/login', { replace: true })
    } catch (error) {
      if (error instanceof ApiError) {
        if (error.status === 401 && error.code === 'current_password_invalid') {
          setPasswordError('La contraseña actual no es correcta.')
        } else if (error.status === 429) {
          setPasswordError('Se alcanzó el límite temporal de intentos. Espera 15 minutos antes de volver a intentarlo.')
        } else if (error.status === 400) {
          const details = Object.values(error.details).flat().map(String).join(' ')
          setPasswordError(details || error.message)
        } else {
          setPasswordError(error.message)
        }
      } else {
        setPasswordError('No fue posible contactar el servidor. Inténtalo nuevamente.')
      }
    } finally {
      passwordSubmission.current = false
      setPasswordBusy(false)
    }
  }

  const loadData = useCallback(async () => {
    if (!session.authenticated) return
    setLoading(true)
    try {
      const profData = await api.get('/auth/profile/')
      setProfile(profData)
      if (session.role === 'CLIENTE' && session.is_email_verified) {
        const [comprasData, reservasData] = await Promise.all([api.get('/sales/purchases/'), api.get('/sales/reservations/')])
        setCompras(comprasData); setReservas(reservasData)
      } else { setCompras([]); setReservas([]) }
    } catch (error) {
      const message =
        error instanceof ApiError
          ? error.message
          : 'No fue posible cargar el perfil, las reservas y las compras.'
      setNotification({ type: 'error', message })
    } finally {
      setLoading(false)
    }
  }, [session.authenticated, session.role, session.is_email_verified])

  useEffect(() => {
    loadData()
  }, [loadData])

  async function handleCancelPurchase(compraId: number) {
    if (!window.confirm('¿Deseas cancelar esta compra? El reembolso se calculará por tiquete y se abonará a la billetera del comprador.')) return
    setNotification(null)
    try {
      await api.post(`/sales/purchases/${compraId}/cancel/`, {})
      setNotification({ type: 'success', message: 'Compra cancelada exitosamente y valor reembolsado a tu billetera.' })
      await loadData()
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : 'No se pudo cancelar la compra.'
      setNotification({ type: 'error', message: msg })
    }
  }

  async function handleCancelReservation(reservaId: number) {
    if (!window.confirm('¿Deseas cancelar esta reserva?')) return
    setNotification(null)
    try {
      await api.post(`/sales/reservations/${reservaId}/cancel/`, {})
      setNotification({ type: 'success', message: 'Reserva cancelada exitosamente.' })
      await loadData()
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : 'No se pudo cancelar la reserva.'
      setNotification({ type: 'error', message: msg })
    }
  }

  async function handlePayReservation(reservaId: number) {
    setNotification(null)
    try {
      const res = await purchase(
        { reserva_id: reservaId },
        { reserva_id: reservaId },
        (info) => new Promise<boolean>((resolve) => {
          setPurchaseApproval({ ...info, resolve })
        }),
      )
      if (!res) return
      setNotification({ type: 'success', message: `¡Compra confirmada! Código localizador: ${res.localizador}` })
      await loadData()
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : 'No se pudo procesar el pago de la reserva.'
      setNotification({ type: 'error', message: msg })
    }
  }

  async function openSeatMap(vueloId: number, tiqueteId: number) {
    setSelectedTicketId(tiqueteId)
    setLoadingSeatMap(true)
    try {
      const data = await api.get(`/sales/flights/${vueloId}/seats/`)
      setSeatMap(data)
    } catch {
      setNotification({ type: 'error', message: 'Error al cargar mapa de sillas.' })
    } finally {
      setLoadingSeatMap(false)
    }
  }

  async function handleChangeSeat(nuevaSillaId: number) {
    if (!selectedTicketId) return
    if (!window.confirm('¿Confirmas el único cambio voluntario de silla antes del check-in?')) return
    setChangingSeat(true)
    try {
      await api.post(`/sales/tickets/${selectedTicketId}/change-seat/`, { nueva_silla_id: nuevaSillaId })
      setNotification({ type: 'success', message: '¡Silla cambiada exitosamente!' })
      setSelectedTicketId(null)
      await loadData()
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : 'No se pudo cambiar la silla.'
      setNotification({ type: 'error', message: msg })
    } finally {
      setChangingSeat(false)
    }
  }

  if (!session.authenticated) {
    return (
      <div className="page page--narrow">
        <div className="form-container">
          <h1 className="form-title">Sesión requerida</h1>
          <p className="form-subtitle">Debe iniciar sesión para poder visualizar los datos de su perfil.</p>
          <Link to="/login?next=/perfil" className="btn btn--primary btn--full">Iniciar sesión</Link>
        </div>
      </div>
    )
  }

  return (
    <div className="page" style={{ maxWidth: '1000px', margin: '0 auto', padding: '2rem 1rem' }}>
      {notification && (
        <div className={`alert alert--${notification.type}`} style={{ marginBottom: '1.5rem' }}>
          <span className="alert__body">{notification.message}</span>
        </div>
      )}

      {purchaseApproval && (
        <Dialog
          title="Confirmar compra"
          onClose={() => {
            purchaseApproval.resolve(false)
            setPurchaseApproval(null)
          }}
        >
          <p>Se descontará el total cotizado de tu billetera.</p>
          <div className="movement-summary">
            <span>Total a pagar</span>
            <strong>{new Intl.NumberFormat('es-CO', { style: 'currency', currency: 'COP' }).format(Number(purchaseApproval.total))}</strong>
          </div>
          <div className="movement-summary">
            <span>Saldo disponible</span>
            <strong>{new Intl.NumberFormat('es-CO', { style: 'currency', currency: 'COP' }).format(Number(purchaseApproval.balance))}</strong>
          </div>
          <div className="form-actions">
            <button
              type="button"
              className="btn btn--primary"
              onClick={() => {
                purchaseApproval.resolve(true)
                setPurchaseApproval(null)
              }}
            >
              Confirmar compra
            </button>
            <button
              type="button"
              className="btn btn--secondary"
              onClick={() => {
                purchaseApproval.resolve(false)
                setPurchaseApproval(null)
              }}
            >
              Volver
            </button>
          </div>
        </Dialog>
      )}

      <div className="page-head">
        <div>
          <h1>Mi perfil</h1>
          <p>Consulta tu información personal y accede a tus servicios.</p>
        </div>
      </div>

      {profile && (
        <section className="card" style={{ marginBottom: '1.5rem' }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '1rem', marginBottom: '1.25rem' }}>
            <div className="tile-icon" aria-hidden="true"><UserRound size={22} /></div>
            <div style={{ flex: 1, minWidth: 0 }}>
              <h2 style={{ margin: 0 }}>{profile.first_name} {profile.last_name}</h2>
              <p style={{ margin: '0.25rem 0 0', color: 'var(--color-text-secondary)' }}>{profile.email}</p>
            </div>
            {profile.is_email_verified && <span className="tag tag--success">Correo verificado</span>}
          </div>
          <hr className="divider" />
          <div className="profile-grid">
            <div className="profile-item">
              <span className="profile-item__label">Nombre de usuario</span>
              <span className="profile-item__value">{profile.username}</span>
            </div>
            <div className="profile-item">
              <span className="profile-item__label">Lugar de nacimiento</span>
              <span className="profile-item__value">{profile.birth_place || 'No registrado'}</span>
            </div>
            <div className="profile-item">
              <span className="profile-item__label">Documento</span>
              <span className="profile-item__value">
                {profile.document_number
                  ? `${profile.document_type} •••• ${profile.document_number.slice(-4)}`
                  : 'No registrado'}
              </span>
            </div>
            <div className="profile-item">
              <span className="profile-item__label">Teléfono</span>
              <span className="profile-item__value">{profile.phone || 'No registrado'}</span>
            </div>
          </div>
        </section>
      )}

      {session.role === 'CLIENTE' && session.is_email_verified && (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '1.5rem', marginBottom: '2rem' }}>
          <WalletPanel />
        </div>
      )}
      {session.role === 'ROOT' && (
        <section className="form-container" style={{ maxWidth: '680px', margin: '2rem 0' }}>
          <h2 className="form-title" style={{ fontSize: '1.4rem' }}>Cambiar mi contraseña</h2>
          <p className="form-subtitle">
            Este cambio invalida todas las sesiones ROOT existentes, incluida esta. Después
            tendrás que iniciar sesión manualmente con la nueva contraseña.
          </p>
          {passwordError && (
            <div className="alert alert--error" role="alert" style={{ marginBottom: '1rem' }}>
              <span className="alert__body">{passwordError}</span>
            </div>
          )}
          <form onSubmit={handleRootPasswordChange} noValidate>
            {([
              ['current_password', 'Contraseña actual', 'current'],
              ['password', 'Nueva contraseña', 'next'],
              ['password_confirmation', 'Confirmar nueva contraseña', 'confirmation'],
            ] as const).map(([field, label, visibilityKey]) => (
              <div className="form-group" style={{ marginBottom: '1rem' }} key={field}>
                <label className="form-label" htmlFor={`root-password-${field}`}>
                  {label}<span className="form-label__required">*</span>
                </label>
                <div className="password-wrapper">
                  <input
                    id={`root-password-${field}`}
                    type={passwordVisibility[visibilityKey] ? 'text' : 'password'}
                    className="form-input"
                    value={rootPassword[field]}
                    onChange={(event) => updateRootPassword(field, event.target.value)}
                    autoComplete={field === 'current_password' ? 'current-password' : 'new-password'}
                    required
                    minLength={field === 'current_password' ? undefined : 12}
                    aria-describedby={field === 'password' ? 'root-password-policy' : undefined}
                  />
                  <button
                    type="button"
                    className="password-toggle"
                    onClick={() => setPasswordVisibility((current) => ({
                      ...current,
                      [visibilityKey]: !current[visibilityKey],
                    }))}
                    aria-label={passwordVisibility[visibilityKey] ? 'Ocultar contraseña' : 'Mostrar contraseña'}
                  >
                    {passwordVisibility[visibilityKey] ? 'Ocultar' : 'Ver'}
                  </button>
                </div>
                {field === 'password' && (
                  <span id="root-password-policy" className="form-hint">
                    Mínimo 12 caracteres. También se aplican los validadores locales de seguridad.
                  </span>
                )}
              </div>
            ))}
            <button
              type="submit"
              className="btn btn--primary"
              disabled={
                passwordBusy ||
                !rootPassword.current_password ||
                !rootPassword.password ||
                !rootPassword.password_confirmation
              }
            >
              {passwordBusy ? 'Cambiando contraseña...' : 'Cambiar contraseña'}
            </button>
          </form>
        </section>
      )}
      {session.role === 'CLIENTE' && <>
        <Link className="btn btn--secondary" to="/cancelaciones">Gestionar vuelos cancelados por la aerolínea</Link>
      {/* SECCIÓN MIS COMPRAS */}
      <section style={{ marginBottom: '3rem' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', gap: '1rem', flexWrap: 'wrap', marginBottom: '1rem' }}>
          <h2 className="profile-section-title">
            <PlaneTakeoff aria-hidden="true" size={22} />
            <span>Mis Viajes Confirmados (Compras)</span>
          </h2>
          <Link to="/check-in" className="btn btn--primary btn--small">Check-in y pasabordo</Link>
        </div>
        {compras.length === 0 ? (
          <p style={{ color: '#64748b' }}>No tienes compras activas registradas.</p>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1.2rem' }}>
            {compras.map((compra) => (
              <div key={compra.id} style={{ background: 'white', padding: '1.5rem', borderRadius: '0.8rem', border: '1px solid #e2e8f0', boxShadow: '0 2px 4px rgba(0,0,0,0.05)' }}>
                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', borderBottom: '1px solid #f1f5f9', paddingBottom: '0.8rem', marginBottom: '1rem' }}>
                  <div>
                    <span style={{ fontSize: '0.85rem', color: '#64748b' }}>Localizador comercial: </span>
                    <strong style={{ fontSize: '1.3rem', color: 'var(--color-primary)', letterSpacing: '2px' }}>{compra.localizador}</strong>
                  </div>
                  <div style={{ display: 'flex', alignItems: 'center', gap: '1rem' }}>
                    <span style={{ fontWeight: 700, fontSize: '1.1rem' }}>Total: ${compra.valor_pagado} COP</span>
                    <span style={{ padding: '0.2rem 0.6rem', borderRadius: '0.3rem', fontSize: '0.8rem', fontWeight: 600, background: compra.estado === 'CONFIRMADA' ? '#dcfce7' : '#fee2e2', color: compra.estado === 'CONFIRMADA' ? '#166534' : '#991b1b' }}>
                      {compra.estado}
                    </span>
                    {compra.estado === 'CONFIRMADA' && compra.tiquetes.some(t => t.estado === 'ACTIVO') && compra.tiquetes.filter(t => t.estado === 'ACTIVO').every(t => t.vuelo.estado === 'PROGRAMADO' && Date.now() < new Date(t.vuelo.salida_utc).getTime() - (t.vuelo.tipo_vuelo === 'NACIONAL' ? 1 : 3) * 3600000) && (
                      <button
                        type="button"
                        onClick={() => handleCancelPurchase(compra.id)}
                        disabled={compra.tiquetes.some(t => t.estado === 'PENDIENTE_RESOLUCION')}
                        title={compra.tiquetes.some(t => t.estado === 'PENDIENTE_RESOLUCION') ? 'Resuelve primero la cancelación gestionada por la aerolínea.' : undefined}
                        className="btn btn--secondary"
                        style={{ fontSize: '0.85rem', padding: '0.3rem 0.7rem', color: '#dc2626', borderColor: '#fca5a5' }}
                      >
                        Cancelar y Reembolsar
                      </button>
                    )}
                    {compra.tiquetes.some(t => t.estado === 'PENDIENTE_RESOLUCION') && (
                      <span role="status" className="form-hint">
                        Hay una cancelación pendiente. Resuélvela en la gestión de cancelaciones antes de cancelar esta compra.
                      </span>
                    )}
                  </div>
                </div>

                {/* LISTADO DE TIQUETES Y CAMBIO DE SILLA */}
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: '1rem' }}>
                  {compra.tiquetes.map((t) => (
                    <div key={t.id} style={{ background: '#f8fafc', padding: '1rem', borderRadius: '0.5rem', border: '1px solid #cbd5e1' }}>
                      <div style={{ fontWeight: 600, color: '#0f172a' }}>{t.viajero.nombres} {t.viajero.apellidos}</div>
                      <div style={{ fontSize: '0.85rem', color: '#64748b' }}>Vuelo: {t.vuelo.codigo_vuelo} ({t.vuelo.origen} ➔ {t.vuelo.destino})</div>
                      <div style={{ fontSize: '0.85rem', color: '#64748b' }}>Clase: {t.clase} · Pagado: ${t.precio_pagado} COP</div>
                      <div style={{ marginTop: '0.6rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                        <span className="ticket-seat-label">
                          <Armchair aria-hidden="true" size={16} />
                          Silla #{t.silla.numero_silla}
                        </span>
                        {compra.estado === 'CONFIRMADA' &&
                          t.numero_cambios_silla === 0 &&
                          t.estado_checkin !== 'CONFIRMADO' &&
                          t.estado === 'ACTIVO' && (
                          <button
                            type="button"
                            onClick={() => openSeatMap(t.vuelo.id, t.id)}
                            className="btn btn--primary"
                            style={{ fontSize: '0.75rem', padding: '0.2rem 0.5rem' }}
                          >
                            Cambiar Silla
                          </button>
                        )}
                        {t.numero_cambios_silla > 0 && (
                          <span style={{ fontSize: '0.75rem', color: '#94a3b8' }}>Cambio ya utilizado</span>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* SECCIÓN MIS RESERVAS */}
      <section>
        <h2 style={{ fontSize: '1.5rem', color: '#0f172a', marginBottom: '1rem' }}>⏳ Mis Reservas Temporales</h2>
        {reservas.length === 0 ? (
          <p style={{ color: '#64748b' }}>No tienes reservas activas.</p>
        ) : (
          <div style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            {reservas.map((reserva) => (
              <div key={reserva.id} style={{ background: 'white', padding: '1.2rem', borderRadius: '0.8rem', border: '1px solid #e2e8f0', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                  <div style={{ fontWeight: 600, fontSize: '1.1rem' }}>
                    Vuelo: {reserva.vuelo.codigo_vuelo} ({reserva.vuelo.origen} ➔ {reserva.vuelo.destino})
                  </div>
                  <div style={{ fontSize: '0.85rem', color: '#64748b', marginTop: '0.2rem' }}>
                    Clase: {reserva.clase} · Viajeros: {reserva.viajeros.length}
                    <br />
                    Límite para pagar: <strong style={{ color: '#d97706' }}>{new Date(reserva.limite_vigencia).toLocaleString()}</strong>
                  </div>
                </div>

                <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
                  <span style={{ padding: '0.2rem 0.6rem', borderRadius: '0.3rem', fontSize: '0.8rem', fontWeight: 600, background: reserva.estado === 'VIGENTE' ? '#fef3c7' : '#e2e8f0', color: reserva.estado === 'VIGENTE' ? '#b45309' : '#64748b' }}>
                    {reserva.estado}
                  </span>
                  {reserva.estado === 'VIGENTE' && (
                    <>
                      <button
                        type="button"
                        onClick={() => handlePayReservation(reserva.id)}
                        className="btn btn--primary"
                        style={{ fontSize: '0.85rem', padding: '0.4rem 0.8rem' }}
                      >
                        <Wallet aria-hidden="true" size={16} />
                        Pagar con Billetera
                      </button>
                      <button
                        type="button"
                        onClick={() => handleCancelReservation(reserva.id)}
                        className="btn btn--secondary"
                        style={{ fontSize: '0.85rem', padding: '0.4rem 0.8rem', color: '#dc2626' }}
                      >
                        Liberar Reserva
                      </button>
                    </>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* MODAL PARA CAMBIO DE SILLA */}
      {selectedTicketId !== null && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 100 }}>
          <div style={{ background: 'white', padding: '2rem', borderRadius: '1rem', maxWidth: '600px', width: '90%', maxHeight: '80vh', overflowY: 'auto' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
              <h3 className="profile-seat-map__title">
                <Armchair aria-hidden="true" size={20} />
                <span>Mapa de sillas del vuelo</span>
              </h3>
              <button
                type="button"
                onClick={() => setSelectedTicketId(null)}
                className="icon-button"
                aria-label="Cerrar mapa de sillas"
              >
                <X aria-hidden="true" size={20} />
              </button>
            </div>

            {loadingSeatMap ? (
              <p>Cargando disponibilidad de sillas...</p>
            ) : (
              <div>
                <p style={{ fontSize: '0.9rem', color: '#64748b', marginBottom: '1rem' }}>
                  Selecciona una silla en estado <strong>DISPONIBLE</strong> de la misma clase para reasignar tu tiquete (máximo 1 cambio permitido).
                </p>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(6, 1fr)', gap: '0.5rem', maxHeight: '350px', overflowY: 'auto', padding: '0.5rem', border: '1px solid #e2e8f0', borderRadius: '0.5rem' }}>
                  {seatMap.filter(s => s.clase === compras.flatMap(c => c.tiquetes).find(t => t.id === selectedTicketId)?.clase).map((s) => (
                    <button
                      key={s.id}
                      type="button"
                      disabled={s.estado !== 'DISPONIBLE' || changingSeat}
                      onClick={() => handleChangeSeat(s.id)}
                      style={{
                        padding: '0.6rem 0.2rem',
                        fontSize: '0.8rem',
                        fontWeight: 700,
                        borderRadius: '0.3rem',
                        border: '1px solid #cbd5e1',
                        cursor: s.estado === 'DISPONIBLE' ? 'pointer' : 'not-allowed',
                        background: s.estado === 'DISPONIBLE' ? '#dcfce7' : '#fee2e2',
                        color: s.estado === 'DISPONIBLE' ? '#166534' : '#991b1b',
                      }}
                    >
                      #{s.numero_silla}
                      <br />
                      <span style={{ fontSize: '0.65rem' }}>{s.clase === 'PRIMERA_CLASE' ? '1ª' : 'Eco'}</span>
                    </button>
                  ))}
                </div>
              </div>
            )}
          </div>
        </div>
      )}
      </>}
    </div>
  )
}
