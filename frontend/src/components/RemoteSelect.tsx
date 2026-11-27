import { useEffect, useId, useRef, useState } from 'react'
import { api } from '../api'

export interface Choice { id: number; name?: string; nombre?: string; label?: string }
interface Props {
  label: string; endpoint: string | null; value: Choice | null
  onChange: (value: Choice | null) => void
  onCount?: (count: number) => void
}
export default function RemoteSelect({ label, endpoint, value, onChange, onCount }: Props) {
  const id = useId()
  const [query, setQuery] = useState('')
  const [rows, setRows] = useState<Choice[]>([])
  const [next, setNext] = useState<string | null>(null)
  const [busy, setBusy] = useState(false)
  const [error, setError] = useState('')
  useEffect(() => { setQuery('') }, [endpoint])
  const generation = useRef(0)
  const countCallback = useRef(onCount)
  countCallback.current = onCount
  useEffect(() => {
    const current = ++generation.current
    setRows([]); setNext(null); setError('')
    if (!endpoint) { setBusy(false); return }
    setBusy(true)
    const timer = window.setTimeout(() => {
      api.get(`${endpoint}${endpoint.includes('?') ? '&' : '?'}q=${encodeURIComponent(query)}`)
        .then(data => {
          if (current !== generation.current) return
          setRows(data.results); setNext(data.next); if (!query) countCallback.current?.(data.count)
        }).catch(() => { if (current === generation.current) setError('No se pudieron cargar las opciones.') })
        .finally(() => { if (current === generation.current) setBusy(false) })
    }, 250)
    return () => { window.clearTimeout(timer); generation.current++ }
  }, [endpoint, query])
  async function more() {
    if (!next || busy) return
    const current = generation.current
    setBusy(true)
    try {
      const data = await api.get(new URL(next, window.location.origin).pathname.replace('/api/v1', '') + new URL(next, window.location.origin).search)
      if (current === generation.current) { setRows(prev => [...prev, ...data.results]); setNext(data.next) }
    } catch { if (current === generation.current) setError('No se pudo cargar la siguiente página.') }
    finally { if (current === generation.current) setBusy(false) }
  }
  const options = value && !rows.some(x => x.id === value.id) ? [value, ...rows] : rows
  return <div className="form-group">
    <label className="form-label" htmlFor={id}>{label}</label>
    <input className="form-input" aria-label={`Buscar ${label}`} placeholder="Escribe para buscar opciones" value={query} disabled={!endpoint} onChange={e => setQuery(e.target.value)} />
    <select id={id} className="form-select" value={value?.id ?? ''} disabled={!endpoint || busy} onChange={e => onChange(options.find(x => x.id === Number(e.target.value)) ?? null)}>
      <option value="">{busy ? 'Cargando…' : 'Selecciona una opción'}</option>
      {options.map(x => <option key={x.id} value={x.id}>{x.label ?? x.name ?? x.nombre}</option>)}
    </select>
    {!busy && endpoint && rows.length === 0 && <small role="status">No hay opciones disponibles.</small>}
    {error && <small role="alert">{error}</small>}
    {next && <button type="button" className="btn btn--secondary btn--small" disabled={busy} onClick={more}>Más opciones</button>}
  </div>
}
