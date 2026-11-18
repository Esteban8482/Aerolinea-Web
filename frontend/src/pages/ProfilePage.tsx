import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, ApiError } from '../api'
import type { Compra, PerfilUsuario, Reserva, Silla } from '../types/flight'

interface ProfilePageProps {
  session: {
    authenticated: boolean
    role: string | null
    is_email_verified: boolean
  }
}

export default function ProfilePage({ session }: ProfilePageProps) {
  const [profile, setProfile] = useState<PerfilUsuario | null>(null)
  const [compras, setCompras] = useState<Compra[]>([])
  const [reservas, setReservas] = useState<Reserva[]>([])
  const [loading, setLoading] = useState(true)
  const [notification, setNotification] = useState<{ type: 'success' | 'error'; message: string } | null>(null)

  // Estado para depósito
  const [depositMonto, setDepositMonto] = useState('500000')
  const [depositing, setDepositing] = useState(false)

  // Estado para cambio de silla (CU-17)
  const [selectedTicketId, setSelectedTicketId] = useState<number | null>(null)
  const [seatMap, setSeatMap] = useState<Silla[]>([])
  const [loadingSeatMap, setLoadingSeatMap] = useState(false)
  const [changingSeat, setChangingSeat] = useState(false)

  const loadData = useCallback(async () => {
    if (!session.authenticated) return
    setLoading(true)
    try {
      const [profData, comprasData, reservasData] = await Promise.all([
        api.get('/auth/profile/'),
        api.get('/sales/purchases/'),
        api.get('/sales/reservations/'),
      ])
      setProfile(profData)
      setCompras(comprasData)
      setReservas(reservasData)
    } catch {
      // Ignorar errores transitorios
    } finally {
      setLoading(false)
    }
  }, [session.authenticated])

  useEffect(() => {
    loadData()
  }, [loadData])

  async function handleDeposit() {
    setDepositing(true)
    setNotification(null)
    try {
      await api.post('/sales/wallet/deposit/', { monto: depositMonto, referencia: 'Recarga de saldo en línea' })
      setNotification({ type: 'success', message: '¡Recarga exitosa! Tu saldo ha sido actualizado.' })
      await loadData()
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : 'Error al realizar el depósito.'
      setNotification({ type: 'error', message: msg })
    } finally {
      setDepositing(false)
    }
  }

  async function handleCancelPurchase(compraId: number) {
    if (!window.confirm('¿Estás seguro de cancelar esta compra? El valor pagado será reembolsado íntegramente a tu billetera.')) return
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
    if (!window.confirm('¿Confirmas el pago de esta reserva con cargo al saldo de tu billetera?')) return
    setNotification(null)
    try {
      const res = await api.post('/sales/purchases/', { reserva_id: reservaId })
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
          <Link to="/login" className="btn btn--primary btn--full">Iniciar sesión</Link>
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

      {/* TARJETA DE PERFIL Y BILLETERA */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(300px, 1fr))', gap: '1.5rem', marginBottom: '2rem' }}>
        <div className="form-container" style={{ margin: 0 }}>
          <h2 className="form-title" style={{ fontSize: '1.4rem' }}>👤 Mis Datos Personales</h2>
          <p className="form-subtitle">Información de la cuenta</p>

          <div className="profile-item"><span className="profile-item__label">Nombre</span><span className="profile-item__value">{profile?.first_name} {profile?.last_name}</span></div>
          <div className="profile-item"><span className="profile-item__label">Correo</span><span className="profile-item__value">{profile?.email}</span></div>
          <div className="profile-item"><span className="profile-item__label">Documento</span><span className="profile-item__value">{profile?.document_type} {profile?.document_number}</span></div>
          <div className="profile-item"><span className="profile-item__label">Rol</span><span className="profile-item__value">{profile?.role}</span></div>
          <div className="profile-item"><span className="profile-item__label">Estado</span><span className="profile-item__value">{profile?.is_email_verified ? 'Verificado' : 'Sin verificar'}</span></div>
        </div>

        <div className="form-container" style={{ margin: 0, background: '#f8fafc', border: '1px solid #e2e8f0' }}>
          <h2 className="form-title" style={{ fontSize: '1.4rem', color: '#0f172a' }}>💳 Billetera Virtual</h2>
          <p className="form-subtitle">Saldo disponible para reservas y compras</p>

          <div style={{ margin: '1.5rem 0', padding: '1.2rem', background: 'white', borderRadius: '0.75rem', border: '1px solid #cbd5e1' }}>
            <span style={{ fontSize: '0.85rem', color: '#64748b' }}>Saldo actual</span>
            <div style={{ fontSize: '2rem', fontWeight: 800, color: '#16a34a' }}>
              ${profile?.wallet_balance || '0.00'} COP
            </div>
          </div>

          <div style={{ display: 'flex', gap: '0.5rem', alignItems: 'center' }}>
            <input
              type="number"
              className="form-control"
              value={depositMonto}
              onChange={(e) => setDepositMonto(e.target.value)}
              step="50000"
              min="50000"
              style={{ padding: '0.6rem', borderRadius: '0.4rem', border: '1px solid #cbd5e1', width: '150px' }}
            />
            <button
              type="button"
              onClick={handleDeposit}
              disabled={depositing}
              className="btn btn--primary"
              style={{ flex: 1, padding: '0.6rem' }}
            >
              {depositing ? 'Recargando...' : '➕ Recargar Billetera'}
            </button>
          </div>
        </div>
      </div>

      {/* SECCIÓN MIS COMPRAS (CU-13, CU-14, CU-17) */}
      <section style={{ marginBottom: '3rem' }}>
        <h2 style={{ fontSize: '1.5rem', color: '#0f172a', marginBottom: '1rem' }}>🛫 Mis Viajes Confirmados (Compras)</h2>
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
                    {compra.estado === 'CONFIRMADA' && (
                      <button
                        type="button"
                        onClick={() => handleCancelPurchase(compra.id)}
                        className="btn btn--secondary"
                        style={{ fontSize: '0.85rem', padding: '0.3rem 0.7rem', color: '#dc2626', borderColor: '#fca5a5' }}
                      >
                        Cancelar y Reembolsar
                      </button>
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
                        <span style={{ fontWeight: 700, color: '#0f172a' }}>💺 Silla #{t.silla.numero_silla}</span>
                        {compra.estado === 'CONFIRMADA' && t.numero_cambios_silla === 0 && (
                          <button
                            type="button"
                            onClick={() => openSeatMap(t.vuelo.id, t.id)}
                            className="btn btn--primary"
                            style={{ fontSize: '0.75rem', padding: '0.2rem 0.5rem' }}
                          >
                            Cambiar Silla (CU-17)
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

      {/* SECCIÓN MIS RESERVAS (CU-12, CU-13, CU-14) */}
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
                        💳 Pagar con Billetera (CU-13)
                      </button>
                      <button
                        type="button"
                        onClick={() => handleCancelReservation(reserva.id)}
                        className="btn btn--secondary"
                        style={{ fontSize: '0.85rem', padding: '0.4rem 0.8rem', color: '#dc2626' }}
                      >
                        Liberar Reserva (CU-14)
                      </button>
                    </>
                  )}
                </div>
              </div>
            ))}
          </div>
        )}
      </section>

      {/* MODAL PARA CAMBIO DE SILLA (CU-17) */}
      {selectedTicketId !== null && (
        <div style={{ position: 'fixed', inset: 0, background: 'rgba(0,0,0,0.5)', display: 'flex', alignItems: 'center', justifyContent: 'center', zIndex: 100 }}>
          <div style={{ background: 'white', padding: '2rem', borderRadius: '1rem', maxWidth: '600px', width: '90%', maxHeight: '80vh', overflowY: 'auto' }}>
            <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: '1.5rem' }}>
              <h3 style={{ margin: 0, fontSize: '1.3rem' }}>💺 Mapa de Sillas del Vuelo</h3>
              <button type="button" onClick={() => setSelectedTicketId(null)} style={{ border: 'none', background: 'transparent', fontSize: '1.5rem', cursor: 'pointer' }}>✕</button>
            </div>

            {loadingSeatMap ? (
              <p>Cargando disponibilidad de sillas...</p>
            ) : (
              <div>
                <p style={{ fontSize: '0.9rem', color: '#64748b', marginBottom: '1rem' }}>
                  Selecciona una silla en estado <strong>DISPONIBLE</strong> de la misma clase para reasignar tu tiquete (máximo 1 cambio permitido).
                </p>
                <div style={{ display: 'grid', gridTemplateColumns: 'repeat(6, 1fr)', gap: '0.5rem', maxHeight: '350px', overflowY: 'auto', padding: '0.5rem', border: '1px solid #e2e8f0', borderRadius: '0.5rem' }}>
                  {seatMap.map((s) => (
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
    </div>
  )
}
