import { useEffect, useId, useState } from 'react'
import { api } from '../api'

interface CatalogueOption {
  code: string
  label: string
}

interface Props {
  category: string
  label: string
  value: string
  onChange: (code: string) => void
}

export default function CatalogueSelect({ category, label, value, onChange }: Props) {
  const id = useId()
  const [options, setOptions] = useState<CatalogueOption[]>([])
  const [error, setError] = useState('')
  const [loading, setLoading] = useState(true)
  useEffect(() => {
    let active = true
    setLoading(true)
    setError('')
    api.get(`/reference/options/?category=${encodeURIComponent(category)}`)
      .then(data => {
        if (active) setOptions(data.results)
      })
      .catch(() => {
        if (active) setError('No se pudo cargar el catálogo.')
      })
      .finally(() => {
        if (active) setLoading(false)
      })
    return () => { active = false }
  }, [category])
  return (
    <div className="form-group">
      <label className="form-label" htmlFor={id}>{label}</label>
      <select
        id={id}
        className="form-select"
        value={value}
        onChange={event => onChange(event.target.value)}
        disabled={loading || Boolean(error) || options.length === 0}
        aria-busy={loading}
      >
        <option value="">
          {loading ? 'Cargando…' : error || (options.length ? 'Selecciona una opción' : 'No hay opciones disponibles.')}
        </option>
        {options.map(option => (
          <option key={option.code} value={option.code}>{option.label}</option>
        ))}
      </select>
      {error && <small role="alert">{error}</small>}
    </div>
  )
}
