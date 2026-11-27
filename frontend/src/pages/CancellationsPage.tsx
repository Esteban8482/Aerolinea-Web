import { useCallback, useEffect, useState } from 'react'
import { Link, useParams } from 'react-router-dom'
import { api, ApiError } from '../api'
import type { Tiquete, Vuelo } from '../types/flight'
export interface Resolution { id: number; locator: string; purchaser_id: number; status: 'PENDING' | 'RELOCATED' | 'REFUNDED'; flight: Vuelo; destination: Vuelo | null; tickets: Tiquete[]; alternatives?: Vuelo[]; resolved_at: string | null; refunded_amount: string }
export const resolutionLabels = { PENDING: 'Pendiente', RELOCATED: 'Reubicado', REFUNDED: 'Reembolsado' }
export default function CancellationsPage({ session }: { session: { authenticated: boolean; role: string | null } }) {
  const { id } = useParams()
  const [rows, setRows] = useState<Resolution[]>([])
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  const [busy, setBusy] = useState(false)
  const load = useCallback(async () => {
    if (!session.authenticated || session.role !== 'CLIENTE') { setLoading(false); return }
    setLoading(true)
    try { const data = await api.get(`/sales/cancellations/${id ? id + '/' : ''}`); setRows(id ? [data] : data) } catch (e) { setError(e instanceof ApiError ? e.message : 'No se pudo consultar la cancelación.') } finally { setLoading(false) }
  }, [id, session.authenticated, session.role])
  useEffect(() => { load() }, [load])
  async function decide(row: Resolution, flight?: Vuelo) {
    const message = flight ? `¿Confirmas reubicar a los ${row.tickets.length} viajeros al vuelo ${flight.codigo_vuelo}, salida ${new Date(flight.salida_utc).toLocaleString('es-CO')}, sin pago adicional?` : '¿Confirmas el reembolso de los importes originales de este grupo a tu billetera?'
    if (!window.confirm(message)) return
    setBusy(true); setError('')
    try { await api.post(`/sales/cancellations/${row.id}/`, { decision: flight ? 'RELOCATE' : 'REFUND', destination_id: flight?.id, confirmed: true }); await load() } catch (e) { setError(e instanceof ApiError ? e.message : 'No se confirmó el resultado. Consulta o reintenta la misma decisión.'); await load() } finally { setBusy(false) }
  }
  if (!session.authenticated) return <main className="page"><h1>Gestionar cancelación</h1><p>Inicia sesión con la cuenta que realizó la compra.</p><Link to={`/login?next=${encodeURIComponent('/cancelaciones' + (id ? '/' + id : ''))}`}>Iniciar sesión</Link></main>
  if (session.role !== 'CLIENTE') return <main className="page">Esta gestión corresponde al comprador.</main>
  return <main className="page"><h1>Cancelaciones de vuelos</h1><p>Lamentamos los inconvenientes ocasionados. Selecciona la alternativa que mejor se adapte a tus necesidades.</p>
    {error && <p role="alert" className="alert alert--error">{error}</p>}{loading && <p role="status">Consultando…</p>}
    {!loading && !rows.length && <p>No tienes cancelaciones pendientes o resueltas.</p>}
    {rows.map(row => <section className="form-container" key={row.id}><h2>{row.locator} · {row.flight.codigo_vuelo}</h2><p>{row.flight.origen} → {row.flight.destino} · {resolutionLabels[row.status]}</p>
      <ul>{row.tickets.map(t => <li key={t.id}>{t.viajero.nombres} {t.viajero.apellidos} — {t.clase} — pagado ${t.precio_pagado} COP</li>)}</ul>
      {!id && <Link className="btn btn--primary" to={`/cancelaciones/${row.id}`}>Gestionar / consultar resolución</Link>}
      {id && row.status === 'PENDING' && <><h3>Alternativas sin cargo adicional</h3><p>El grupo completo conserva su clase e importe original.</p>
        {!row.alternatives?.length && <p>No hay alternativas compatibles disponibles. Puedes solicitar el reembolso.</p>}
        {row.alternatives?.map(f => <article key={f.id} className="journey-ticket"><div><strong>{f.codigo_vuelo} · {f.origen} → {f.destino}</strong><p>Salida {new Date(f.salida_utc).toLocaleString('es-CO')} · Llegada {new Date(f.llegada_utc).toLocaleString('es-CO')}</p><p>Duración: {f.tiempo_vuelo_min} min · Cupos económica: {f.cupos_disponibles_economica}, primera: {f.cupos_disponibles_primera}</p><button className="btn btn--primary" disabled={busy} onClick={() => decide(row, f)}>Seleccionar reubicación sin cargo</button></div></article>)}
        <button className="btn btn--secondary" disabled={busy} onClick={() => decide(row)}>Realizar reembolso</button></>}
      {row.destination && <p>Reubicación confirmada: {row.destination.codigo_vuelo} · {new Date(row.destination.salida_utc).toLocaleString('es-CO')}. Consulta los nuevos tiquetes en tu perfil.</p>}
      {row.status === 'REFUNDED' && <p>Reembolso confirmado: ${row.refunded_amount} COP.</p>}
    </section>)}<Link to="/perfil">Volver al perfil</Link>
  </main>
}
