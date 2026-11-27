import { useEffect, useState } from 'react'
import { api, ApiError } from '../api'
import type { Silla, Tiquete } from '../types/flight'
export default function SeatManager({ ticket, token, onChanged }: { ticket: Tiquete; token?: string; onChanged: () => void }) {
  const [open, setOpen] = useState(false)
  const [seats, setSeats] = useState<Silla[]>([])
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  const eligible = ticket.estado === 'ACTIVO' && ticket.vuelo.estado === 'PROGRAMADO' && ticket.estado_checkin !== 'CONFIRMADO' && ticket.numero_cambios_silla === 0 && Date.now() < new Date(ticket.vuelo.salida_utc).getTime()
  async function load() { try { setSeats(await api.get(`/sales/flights/${ticket.vuelo.id}/seats/`)) } catch { setError('No se pudo cargar la disponibilidad.') } }
  useEffect(() => { if (open) load() }, [open, ticket.vuelo.id])
  async function change(seat: Silla) {
    if (!window.confirm(`¿Confirmas cambiar a la silla ${seat.numero_silla}? Solo se permite un cambio voluntario antes del check-in.`)) return
    setBusy(true); setError('')
    try {
      if (token) await api.postWithHeaders(`/sales/check-in/tickets/${ticket.id}/seat/`, { seat_id: seat.id }, { 'X-Checkin-Token': token })
      else await api.post(`/sales/tickets/${ticket.id}/change-seat/`, { nueva_silla_id: seat.id })
      setOpen(false); onChanged()
    } catch (e) { setError(e instanceof ApiError ? e.message : 'No se confirmó el cambio. Consulta tu silla antes de reintentar.'); await load() } finally { setBusy(false) }
  }
  return <div><p>Silla actual: {ticket.silla.numero_silla} · {ticket.clase}. {ticket.numero_cambios_silla > 0 ? 'Ya utilizaste tu cambio voluntario.' : 'Un cambio voluntario permitido antes del check-in.'}</p>
    {eligible && <button type="button" className="btn btn--secondary btn--small" onClick={() => setOpen(!open)}>Elegir otra silla</button>}
    {error && <p role="alert">{error}</p>}
    {open && <div className="seat-options" aria-label="Sillas de la clase comprada">{seats.filter(s => s.clase === ticket.clase).map(s => <button type="button" className="btn btn--secondary btn--small" disabled={busy || !eligible || s.estado !== 'DISPONIBLE'} key={s.id} onClick={() => change(s)}>{s.numero_silla} · {s.id === ticket.silla.id ? 'Tu silla' : s.estado === 'DISPONIBLE' ? 'Disponible' : 'No disponible'}</button>)}</div>}
  </div>
}
