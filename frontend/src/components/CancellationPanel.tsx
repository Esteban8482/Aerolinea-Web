import { useEffect, useState } from 'react'
import { api } from '../api'
import { resolutionLabels, type Resolution } from '../pages/CancellationsPage'
export default function CancellationPanel({ flightId }: { flightId: number }) {
  const [data, setData] = useState<{passengers: number; purchases: number; reservations: number; summary: Record<string, number>; resolutions: Resolution[]} | null>(null)
  const [error, setError] = useState('')
  function load() { api.get(`/sales/flights/${flightId}/cancellation-panel/`).then(setData).catch(() => setError('No se pudo cargar el estado de resolución.')) }
  useEffect(load, [flightId])
  return <section><h3>Pasajeros y resolución de cancelación</h3>{error && <p role="alert">{error}</p>}{!data ? <p>Cargando…</p> : <><p>Pasajeros: {data.passengers} · Compras: {data.purchases} · Reservas vigentes: {data.reservations}</p><p>Pendientes: {data.summary.PENDING} · Reubicados: {data.summary.RELOCATED} · Reembolsados: {data.summary.REFUNDED}</p>{data.resolutions.map(r => <div key={r.id}><strong>{r.locator} · Comprador #{r.purchaser_id} · {resolutionLabels[r.status]}</strong><ul>{r.tickets.map(t => <li key={t.id}>{t.viajero.nombres} {t.viajero.apellidos} · {t.codigo_tiquete} · {resolutionLabels[r.status]}</li>)}</ul>{r.resolved_at && <p>{new Date(r.resolved_at).toLocaleString('es-CO')} · {r.destination?.codigo_vuelo ?? `Reembolso $${r.refunded_amount} COP`}</p>}</div>)}</>}<button type="button" onClick={load}>Actualizar estado</button></section>
}
