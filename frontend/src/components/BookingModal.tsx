import { useEffect, useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { CircleCheck, Clock3, UsersRound, Wallet, X } from 'lucide-react'
import { api, ApiError } from '../api'
import { useConfirmedPurchase, useOperationKey } from '../operations'
import WalletPanel from './WalletPanel'
import CatalogueSelect from './CatalogueSelect'
import { Dialog } from './UI'
import type { PerfilUsuario, Vuelo } from '../types/flight'

export interface ViajeroFormData {
  documento: string
  tipo_documento: string
  nombres: string
  apellidos: string
  fecha_nacimiento: string
  genero: string
  telefono: string
  correo: string
  nombre_contacto: string
  telefono_contacto: string
}

interface BookingModalProps {
  vuelo: Vuelo
  vueloRegreso?: Vuelo | null
  session: {
    authenticated: boolean
    role: string | null
    is_email_verified: boolean
  }
  initialClase?: 'ECONOMICA' | 'PRIMERA_CLASE'
  initialPasajeros?: number
  onClose: () => void
  onSuccess: (mensaje: string) => void
}

function emptyViajero(): ViajeroFormData {
  return {
    documento: '',
    tipo_documento: 'CC',
    nombres: '',
    apellidos: '',
    fecha_nacimiento: '',
    genero: 'M',
    telefono: '',
    correo: '',
    nombre_contacto: '',
    telefono_contacto: '',
  }
}

export default function BookingModal({
  vuelo,
  vueloRegreso = null,
  session,
  initialClase = 'ECONOMICA',
  initialPasajeros = 1,
  onClose,
  onSuccess,
}: BookingModalProps) {
  const purchase = useConfirmedPurchase()
  const operationKey = useOperationKey()
  const [showFunding, setShowFunding] = useState(false)
  const [clase, setClase] = useState<'ECONOMICA' | 'PRIMERA_CLASE'>(initialClase)
  const [numPasajeros, setNumPasajeros] = useState<number>(initialPasajeros)
  const [viajeros, setViajeros] = useState<ViajeroFormData[]>(() => {
    return Array.from({ length: initialPasajeros }, () => emptyViajero())
  })

  const [walletBalance, setWalletBalance] = useState<number | null>(null)
  const [insufficient, setInsufficient] = useState<{ total: string; balance: string; difference: string } | null>(null)
  const [busy, setBusy] = useState(false)
  const [errorMsg, setErrorMsg] = useState('')
  const [confirmation, setConfirmation] = useState<{
    type: 'RESERVA' | 'COMPRA'
    localizador?: string
    limiteVigencia?: string
  } | null>(null)
  const [purchaseApproval, setPurchaseApproval] = useState<{
    total: string
    balance: string
    resolve: (accepted: boolean) => void
  } | null>(null)

  // Cargar saldo de billetera si el usuario es cliente
  useEffect(() => {
    if (session.authenticated && session.role === 'CLIENTE') {
      api
        .get('/auth/profile/')
        .then((data: PerfilUsuario) => {
          const bal = parseFloat(data.wallet_balance || '0')
          setWalletBalance(isNaN(bal) ? 0 : bal)

          // Autocompletar el primer viajero con datos del perfil
          setViajeros((prev) => {
            const next = [...prev]
            if (next[0] && !next[0].documento) {
              next[0] = {
                ...next[0],
                documento: data.document_number || '',
                tipo_documento: data.document_type || 'CC',
                nombres: data.first_name || '',
                apellidos: data.last_name || '',
                fecha_nacimiento: data.birth_date || '',
                genero: data.gender || 'M',
                correo: data.email || '',
              }
            }
            return next
          })
        })
        .catch(() => {})
    }
  }, [session.authenticated, session.role])

  // Ajustar cantidad de formularios de viajeros si cambia numPasajeros
  const handlePasajerosChange = (nuevoTotal: number) => {
    const total = Math.max(1, Math.min(5, nuevoTotal))
    setNumPasajeros(total)
    setViajeros((prev) => {
      const next = [...prev]
      while (next.length < total) {
        next.push(emptyViajero())
      }
      return next.slice(0, total)
    })
  }

  const updateViajero = (index: number, field: keyof ViajeroFormData, value: string) => {
    setViajeros((prev) => {
      const copy = [...prev]
      copy[index] = { ...copy[index], [field]: value }
      return copy
    })
    setErrorMsg('')
  }

  // Cálculos de tarifa
  const costoUnitarioIda =
    clase === 'ECONOMICA'
      ? parseFloat(vuelo.precio_vigente_economica)
      : parseFloat(vuelo.precio_vigente_primera)

  const costoUnitarioRegreso = vueloRegreso
    ? clase === 'ECONOMICA'
      ? parseFloat(vueloRegreso.precio_vigente_economica)
      : parseFloat(vueloRegreso.precio_vigente_primera)
    : 0

  const costoTotal = (costoUnitarioIda + costoUnitarioRegreso) * numPasajeros

  // Validaciones de negocio en cliente
  const validarFormulario = (): boolean => {
    for (let i = 0; i < viajeros.length; i++) {
      const v = viajeros[i]
      if (!v.documento.trim() || !v.nombres.trim() || !v.apellidos.trim() || !v.fecha_nacimiento || !v.correo.trim()) {
        setErrorMsg(`Por favor completa todos los campos obligatorios del Pasajero #${i + 1}.`)
        return false
      }
    }

    // Unicidad de documentos
    const docs = viajeros.map((v) => `${v.tipo_documento}:${v.documento.trim().toUpperCase()}`)
    if (new Set(docs).size !== docs.length) {
      setErrorMsg('No puede haber pasajeros con el mismo número de documento en la reserva.')
      return false
    }

    // Al menos un adulto (>= 18 años)
    const today = new Date(vuelo.fecha_salida + "T12:00:00")
    const hasAdult = viajeros.some((v) => {
      if (!v.fecha_nacimiento) return false
      const birth = new Date(v.fecha_nacimiento + "T12:00:00")
      let age = today.getFullYear() - birth.getFullYear()
      const m = today.getMonth() - birth.getMonth()
      if (m < 0 || (m === 0 && today.getDate() < birth.getDate())) {
        age--
      }
      return age >= 18
    })

    if (!hasAdult) {
      setErrorMsg('Al menos uno de los viajeros debe ser mayor de edad (18 años o más).')
      return false
    }

    return true
  }

  // Acción: Apartar Reserva (HU-012)
  const handleReservar = async (e: FormEvent) => {
    e.preventDefault()
    if (!validarFormulario()) return

    setBusy(true)
    setErrorMsg('')
    try {
      const payload = {
        vuelo_id: vuelo.id,
        vuelo_regreso_id: vueloRegreso ? vueloRegreso.id : undefined,
        tipo_trayecto: vueloRegreso ? 'COMPLETO' : 'UNICO',
        clase,
        viajeros: viajeros.map((v) => ({
          documento: v.documento.trim(),
          tipo_documento: v.tipo_documento,
          nombres: v.nombres.trim(),
          apellidos: v.apellidos.trim(),
          fecha_nacimiento: v.fecha_nacimiento,
          genero: v.genero,
          telefono: v.telefono.trim(),
          correo: v.correo.trim(),
          nombre_contacto: v.nombre_contacto.trim(),
          telefono_contacto: v.telefono_contacto.trim(),
        })),
      }

      const res = await api.postWithHeaders('/sales/reservations/', payload, { 'Idempotency-Key': operationKey.forRequest({ action: 'reserve', ...payload }) })
      operationKey.clear()
      setConfirmation({
        type: 'RESERVA',
        limiteVigencia: res.limite_vigencia,
      })
      onSuccess('¡Reserva creada exitosamente! Puedes consultarla en tu perfil.')
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : 'Error al procesar la reserva.'
      setErrorMsg(msg)
    } finally {
      setBusy(false)
    }
  }

  // Acción: Comprar con Billetera (HU-013)
  const handleComprar = async (e: FormEvent) => {
    e.preventDefault()
    if (!validarFormulario()) return

    setBusy(true)
    setErrorMsg('')
    try {
      const payload = {
        vuelo_id: vuelo.id,
        vuelo_regreso_id: vueloRegreso ? vueloRegreso.id : undefined,
        tipo_trayecto: vueloRegreso ? 'COMPLETO' : 'UNICO',
        clase,
        viajeros: viajeros.map((v) => ({
          documento: v.documento.trim(),
          tipo_documento: v.tipo_documento,
          nombres: v.nombres.trim(),
          apellidos: v.apellidos.trim(),
          fecha_nacimiento: v.fecha_nacimiento,
          genero: v.genero,
          telefono: v.telefono.trim(),
          correo: v.correo.trim(),
          nombre_contacto: v.nombre_contacto.trim(),
          telefono_contacto: v.telefono_contacto.trim(),
        })),
      }

      const res = await purchase(
        payload,
        { vuelo_id: vuelo.id, vuelo_regreso_id: vueloRegreso?.id, clase, tipo_trayecto: payload.tipo_trayecto, passenger_count: viajeros.length },
        (info) => new Promise<boolean>((resolve) => {
          setPurchaseApproval({ ...info, resolve })
        }),
      )
      if (!res) return
      setConfirmation({
        type: 'COMPRA',
        localizador: res.localizador,
      })
      onSuccess(`¡Compra exitosa! Código localizador: ${res.localizador}`)
    } catch (err) {
      if (err instanceof ApiError && err.code === 'insufficient_wallet_balance') {
        setInsufficient({
          total: String(err.details.total ?? ''),
          balance: String(err.details.balance ?? ''),
          difference: String(err.details.difference ?? ''),
        })
        setShowFunding(true)
      }
      const msg = err instanceof ApiError ? err.message : 'Error al procesar la compra.'
      setErrorMsg(msg)
    } finally {
      setBusy(false)
    }
  }

  return (
    <div className="modal-backdrop" role="dialog" aria-modal="true" style={{ overflowY: 'auto', padding: '2rem 1rem' }}>
      <div className="modal-box" style={{ maxWidth: '820px', width: '100%', margin: 'auto' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'flex-start', borderBottom: '1px solid #e2e8f0', paddingBottom: '1rem', marginBottom: '1.5rem' }}>
          <div>
            <h2 className="modal-box__title" style={{ margin: 0, fontSize: '1.5rem' }}>
              {confirmation ? 'Confirmación de Operación' : 'Reserva y Compra de Tiquetes'}
            </h2>
            <p style={{ margin: '0.25rem 0 0 0', color: 'var(--color-text-secondary)', fontSize: '0.9rem' }}>
              Vuelo {vuelo.codigo_vuelo} · {vuelo.origen} ➔ {vuelo.destino} ({vuelo.tipo_vuelo})
              {vueloRegreso && ` · Regreso: ${vueloRegreso.codigo_vuelo} (${vueloRegreso.origen} ➔ ${vueloRegreso.destino})`}
            </p>
          </div>
          <button
            type="button"
            onClick={onClose}
            className="icon-button"
            aria-label="Cerrar ventana"
          >
            <X aria-hidden="true" size={20} />
          </button>
        </div>

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

        {/* PANTALLA DE ÉXITO TRAS COMPLETAR */}
        {confirmation ? (
          <div style={{ textAlign: 'center', padding: '2rem 1rem' }}>
            {confirmation.type === 'COMPRA' ? (
              <>
                <div className="booking-success__icon">
                  <CircleCheck aria-hidden="true" size={56} />
                </div>
                <h3 style={{ color: 'var(--color-primary)', fontSize: '1.6rem', marginBottom: '0.5rem' }}>
                  ¡Compra Confirmada Exitosamente!
                </h3>
                <p style={{ fontSize: '1.05rem', color: '#334155', marginBottom: '1.5rem' }}>
                  Tu compra ha sido procesada y debitada de tu billetera virtual.
                </p>

                <div style={{ background: '#f8fafc', border: '2px dashed var(--color-primary)', padding: '1.5rem', borderRadius: '0.5rem', display: 'inline-block', marginBottom: '2rem' }}>
                  <span style={{ fontSize: '0.85rem', color: '#64748b', textTransform: 'uppercase', letterSpacing: '1px' }}>
                    Localizador de Reserva
                  </span>
                  <div style={{ fontSize: '2.2rem', fontWeight: 800, color: 'var(--color-primary)', letterSpacing: '3px' }}>
                    {confirmation.localizador}
                  </div>
                  <span style={{ fontSize: '0.85rem', color: '#64748b' }}>
                    Se han asignado aleatoriamente las sillas de cada viajero en la cabina.
                  </span>
                </div>
              </>
            ) : (
              <>
                <div style={{ fontSize: '3.5rem', marginBottom: '1rem' }}>⏳</div>
                <h3 style={{ color: '#d97706', fontSize: '1.6rem', marginBottom: '0.5rem' }}>
                  ¡Cupos Reservados Exitosamente!
                </h3>
                <p style={{ fontSize: '1.05rem', color: '#334155', marginBottom: '1.5rem' }}>
                  Tus cupos han sido retenidos temporalmente sin costo inmediato.
                </p>

                <div style={{ background: '#fffbeb', border: '1px solid #fde68a', padding: '1.5rem', borderRadius: '0.5rem', display: 'inline-block', marginBottom: '2rem' }}>
                  <span style={{ fontSize: '0.85rem', color: '#92400e', fontWeight: 700 }}>
                    Fecha y hora límite de pago:
                  </span>
                  <div style={{ fontSize: '1.4rem', fontWeight: 700, color: '#b45309', margin: '0.5rem 0' }}>
                    {confirmation.limiteVigencia
                      ? new Date(confirmation.limiteVigencia).toLocaleString('es-CO')
                      : 'Próximas 24 horas'}
                  </div>
                  <p style={{ margin: 0, fontSize: '0.85rem', color: '#78350f' }}>
                    Puedes confirmar y pagar tu reserva en cualquier momento desde <strong>Mi Perfil</strong> antes del vencimiento.
                  </p>
                </div>
              </>
            )}

            <div style={{ display: 'flex', gap: '1rem', justifyContent: 'center' }}>
              <Link to="/perfil" className="btn btn--primary">
                Ir a Mi Perfil
              </Link>
              <button type="button" onClick={onClose} className="btn btn--secondary">
                Cerrar
              </button>
            </div>
          </div>
        ) : (
          /* FORMULARIO DE RESERVA / COMPRA */
          <>
            {showFunding && session.role === 'CLIENTE' && session.is_email_verified && (
              <div className="funding-recovery">
                {insufficient && (
                  <div className="notice notice--warning">
                    <strong>Saldo insuficiente</strong>
                    <p>Necesitas ${insufficient.difference} COP adicionales para completar la compra.</p>
                    <div>Saldo disponible: <strong>${insufficient.balance} COP</strong></div>
                    <div>Total cotizado: <strong>${insufficient.total} COP</strong></div>
                  </div>
                )}
                <WalletPanel onBalance={(balance) => setWalletBalance(Number(balance))} />
                <button
                  type="button"
                  className="btn btn--primary"
                  onClick={() => {
                    setInsufficient(null)
                    setShowFunding(false)
                    setErrorMsg('Actualizamos el saldo. Revisa el nuevo importe antes de confirmar nuevamente.')
                  }}
                >
                  Volver a revisar compra
                </button>
              </div>
            )}
            <button type="button" className="btn btn--secondary" onClick={() => setShowFunding(!showFunding)}>
              {showFunding ? 'Ocultar billetera' : 'Recargar billetera'}
            </button>
        <form noValidate>
            {errorMsg && (
              <div className="alert alert--error" style={{ marginBottom: '1.5rem' }}>
                <span className="alert__body">{errorMsg}</span>
              </div>
            )}

            {/* SELECCIÓN DE CLASE Y PASAJEROS */}
            <div style={{ background: '#f8fafc', padding: '1.25rem', borderRadius: '0.5rem', border: '1px solid #e2e8f0', marginBottom: '1.5rem' }}>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '1rem' }}>
                <CatalogueSelect category="travel_class" label="Clase de cabina" value={clase} onChange={value => setClase(value as 'ECONOMICA' | 'PRIMERA_CLASE')} />

                <div className="form-group" style={{ margin: 0 }}>
                  <label className="form-label">Cantidad de Pasajeros</label>
                  <select
                    className="form-select"
                    value={numPasajeros}
                    onChange={(e) => handlePasajerosChange(Number(e.target.value))}
                  >
                    <option value={1}>1 Pasajero</option>
                    <option value={2}>2 Pasajeros</option>
                    <option value={3}>3 Pasajeros</option>
                    <option value={4}>4 Pasajeros</option>
                    <option value={5}>5 Pasajeros (máximo permitido)</option>
                  </select>
                </div>
              </div>

              <div style={{ marginTop: '1rem', paddingTop: '0.8rem', borderTop: '1px solid #cbd5e1', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                <div>
                  <span style={{ fontSize: '0.85rem', color: '#64748b' }}>Tarifa total ({numPasajeros} {numPasajeros === 1 ? 'viajero' : 'viajeros'}):</span>
                  <div style={{ fontSize: '1.4rem', fontWeight: 800, color: 'var(--color-primary)' }}>
                    ${costoTotal.toLocaleString('es-CO')} COP
                  </div>
                </div>

                {session.authenticated && session.role === 'CLIENTE' && (
                  <div style={{ textAlign: 'right' }}>
                    <span style={{ fontSize: '0.85rem', color: '#64748b' }}>Saldo en tu billetera:</span>
                    <div style={{ fontWeight: 700, color: walletBalance !== null && walletBalance >= costoTotal ? '#16a34a' : '#dc2626' }}>
                      ${(walletBalance ?? 0).toLocaleString('es-CO')} COP
                    </div>
                  </div>
                )}
              </div>
            </div>

            {/* FORMULARIOS DE PASAJEROS */}
            <div style={{ marginBottom: '1.5rem' }}>
              <h3 className="booking-section-heading" style={{ fontSize: '1.15rem', marginBottom: '0.75rem', color: '#0f172a' }}>
                <UsersRound aria-hidden="true" size={20} />
                <span>Información de los viajeros</span>
              </h3>
              <p style={{ fontSize: '0.85rem', color: '#64748b', marginBottom: '1rem' }}>
                Al menos un pasajero debe ser mayor de edad (18 años o más).
              </p>

              <div style={{ display: 'flex', flexDirection: 'column', gap: '1.25rem' }}>
                {viajeros.map((viajero, idx) => (
                  <div
                    key={idx}
                    style={{
                      border: '1px solid #cbd5e1',
                      borderRadius: '0.5rem',
                      padding: '1.25rem',
                      background: '#ffffff',
                    }}
                  >
                    <div style={{ fontWeight: 700, fontSize: '0.95rem', color: 'var(--color-primary)', marginBottom: '0.8rem' }}>
                      Pasajero #{idx + 1} {idx === 0 && '(Adulto titular/contacto)'}
                    </div>

                    <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '0.75rem' }}>
                      <CatalogueSelect category="document_type" label="Tipo de documento" value={viajero.tipo_documento} onChange={value => updateViajero(idx, 'tipo_documento', value)} />

                      <div className="form-group" style={{ margin: 0 }}>
                        <label className="form-label" style={{ fontSize: '0.8rem' }}>Número de Documento *</label>
                        <input
                          type="text"
                          className="form-input"
                          placeholder="Ej. 1088123456"
                          value={viajero.documento}
                          onChange={(e) => updateViajero(idx, 'documento', e.target.value)}
                          required
                        />
                      </div>

                      <div className="form-group" style={{ margin: 0 }}>
                        <label className="form-label" style={{ fontSize: '0.8rem' }}>Nombres *</label>
                        <input
                          type="text"
                          className="form-input"
                          placeholder="Nombres completos"
                          value={viajero.nombres}
                          onChange={(e) => updateViajero(idx, 'nombres', e.target.value)}
                          required
                        />
                      </div>

                      <div className="form-group" style={{ margin: 0 }}>
                        <label className="form-label" style={{ fontSize: '0.8rem' }}>Apellidos *</label>
                        <input
                          type="text"
                          className="form-input"
                          placeholder="Apellidos completos"
                          value={viajero.apellidos}
                          onChange={(e) => updateViajero(idx, 'apellidos', e.target.value)}
                          required
                        />
                      </div>

                      <div className="form-group" style={{ margin: 0 }}>
                        <label className="form-label" style={{ fontSize: '0.8rem' }}>Fecha de Nacimiento *</label>
                        <input
                          type="date"
                          className="form-input"
                          value={viajero.fecha_nacimiento}
                          onChange={(e) => updateViajero(idx, 'fecha_nacimiento', e.target.value)}
                          required
                        />
                      </div>

                      <CatalogueSelect category="gender" label="Género" value={viajero.genero} onChange={value => updateViajero(idx, 'genero', value)} />

                      <div className="form-group" style={{ margin: 0 }}>
                        <label className="form-label" style={{ fontSize: '0.8rem' }}>Correo Electrónico *</label>
                        <input
                          type="email"
                          className="form-input"
                          placeholder="correo@ejemplo.com"
                          value={viajero.correo}
                          onChange={(e) => updateViajero(idx, 'correo', e.target.value)}
                          required
                        />
                      </div>

                      <div className="form-group" style={{ margin: 0 }}>
                        <label className="form-label" style={{ fontSize: '0.8rem' }}>Teléfono Móvil</label>
                        <input
                          type="tel"
                          className="form-input"
                          placeholder="Ej. 3001234567"
                          value={viajero.telefono}
                          onChange={(e) => updateViajero(idx, 'telefono', e.target.value)}
                        />
                      </div>
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* BOTONES DE ACCIÓN SEGÚN AUTENTICACIÓN */}
            {!session.authenticated ? (
              <div style={{ background: '#f8fafc', padding: '1.25rem', borderRadius: '0.5rem', textAlign: 'center', border: '1px solid #cbd5e1' }}>
                <p style={{ margin: '0 0 1rem 0', fontWeight: 600, color: '#334155' }}>
                  Para apartar tu reserva o comprar tiquetes debes identificarte con tu cuenta de cliente.
                </p>
                <div style={{ display: 'flex', gap: '1rem', justifyContent: 'center' }}>
                  <Link to="/login" className="btn btn--primary">
                    Iniciar sesión
                  </Link>
                  <Link to="/registro" className="btn btn--secondary">
                    Registrarse gratis
                  </Link>
                  <button type="button" onClick={onClose} className="btn btn--secondary">
                    Volver
                  </button>
                </div>
              </div>
            ) : session.role !== 'CLIENTE' ? (
              <div style={{ background: '#fffbeb', padding: '1.25rem', borderRadius: '0.5rem', textAlign: 'center', border: '1px solid #fde68a' }}>
                <p style={{ margin: 0, color: '#92400e', fontWeight: 600 }}>
                  Tu rol actual es <strong>{session.role}</strong>. Las cuentas administrativas no realizan compras ni reservas comerciales.
                </p>
                <button type="button" onClick={onClose} className="btn btn--secondary" style={{ marginTop: '1rem' }}>
                  Cerrar
                </button>
              </div>
            ) : (
              <div style={{ display: 'flex', gap: '1rem', justifyContent: 'flex-end', flexWrap: 'wrap', borderTop: '1px solid #e2e8f0', paddingTop: '1.25rem' }}>
                <button type="button" onClick={onClose} className="btn btn--secondary" disabled={busy}>
                  Cancelar
                </button>

                <button
                  type="button"
                  onClick={handleReservar}
                  className="btn btn--secondary"
                  disabled={busy}
                  style={{ borderColor: 'var(--color-primary)', color: 'var(--color-primary)' }}
                >
                  {busy ? 'Procesando...' : <><Clock3 aria-hidden="true" size={16} /> Apartar reserva temporal</>}
                </button>

                <button
                  type="button"
                  onClick={handleComprar}
                  className="btn btn--primary"
                  disabled={busy}
                >
                  {busy ? 'Procesando pago...' : <><Wallet aria-hidden="true" size={16} /> Pagar ${costoTotal.toLocaleString('es-CO')} COP con billetera</>}
                </button>
              </div>
            )}
          </form></>
        )}
      </div>
    </div>
  )
}
