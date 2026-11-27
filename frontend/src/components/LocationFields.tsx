import { useState } from 'react'
import RemoteSelect, { type Choice } from './RemoteSelect'
export default function LocationFields({ label, onChange }: { label: string; onChange: (id: string) => void }) {
  const [country, setCountry] = useState<Choice | null>(null)
  const [subdivision, setSubdivision] = useState<Choice | null>(null)
  const [city, setCity] = useState<Choice | null>(null)
  const [hasSubdivisions, setHasSubdivisions] = useState<boolean | null>(null)
  return <fieldset className="form-section"><legend>{label}</legend>
    <RemoteSelect label={`País — ${label}`} endpoint="/reference/countries/" value={country} onChange={value => { setCountry(value); setSubdivision(null); setCity(null); setHasSubdivisions(null); onChange('') }} />
    <RemoteSelect label={`División territorial — ${label}`} endpoint={country ? `/reference/subdivisions/?country_id=${country.id}` : null} value={subdivision} onCount={count => setHasSubdivisions(count > 0)} onChange={value => { setSubdivision(value); setCity(null); onChange('') }} />
    <RemoteSelect label={`Ciudad — ${label}`} endpoint={country && (subdivision || hasSubdivisions === false) ? `/reference/cities/?country_id=${country.id}${subdivision ? `&subdivision_id=${subdivision.id}` : ''}` : null} value={city} onChange={value => { setCity(value); onChange(value ? String(value.id) : '') }} />
  </fieldset>
}
