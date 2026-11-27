import { useEffect, useId, useState } from 'react'
import { api } from '../api'
export default function CatalogueSelect({ category, label, value, onChange }: { category: string; label: string; value: string; onChange: (code: string) => void }) {
  const id = useId()
  const [options, setOptions] = useState<{code: string; label: string}[]>([])
  const [error, setError] = useState(false)
  useEffect(() => {
    let active = true
    setError(false)
    api.get(`/reference/options/?category=${encodeURIComponent(category)}`).then(data => { if (active) setOptions(data.results) }).catch(() => { if (active) setError(true) })
    return () => { active = false }
  }, [category])
  return <div className="form-group"><label className="form-label" htmlFor={id}>{label}</label><select id={id} className="form-select" value={value} onChange={e => onChange(e.target.value)} disabled={!options.length}><option value="">Selecciona una opción</option>{options.map(x => <option key={x.code} value={x.code}>{x.label}</option>)}</select>{error && <small role="alert">No se pudo cargar el catálogo. Recarga la página.</small>}</div>
}
