import { useEffect, useState } from 'react'
import { api } from '../api'
import RemoteSelect, { type Choice } from './RemoteSelect'
export default function LocationFields({
  label,
  onChange,
  onDetails,
}: {
  label: string
  onChange: (id: string) => void
  onDetails?: (details: { country: string; subdivision: string; city: string }) => void
}) {
  const [country, setCountry] = useState<Choice | null>(null)
  const [subdivision, setSubdivision] = useState<Choice | null>(null)
  const [city, setCity] = useState<Choice | null>(null)
  const [hasSubdivisions, setHasSubdivisions] = useState<boolean | null>(null)
  // One paginated request determines whether the intermediate level is applicable.
  // Never download the worldwide dataset, and ignore a previous country's response.
  useEffect(() => {
    let active = true
    if (country)
      api
        .get(`/reference/subdivisions/?country_id=${country.id}`)
        .then((data) => {
          if (active) setHasSubdivisions(data.count > 0)
        })
        .catch(() => {
          /* The subdivision dropdown provides retry and error feedback. */
        })
    return () => {
      active = false
    }
  }, [country])
  return (
    <fieldset className="form-section">
      <legend>{label}</legend>
      <RemoteSelect
        label="País"
        endpoint="/reference/countries/"
        value={country}
        onChange={(value) => {
          setCountry(value)
          setSubdivision(null)
          setCity(null)
          setHasSubdivisions(null)
          onChange('')
          onDetails?.({ country: value ? String(value.id) : '', subdivision: '', city: '' })
        }}
      />
      <RemoteSelect
        label="División territorial"
        endpoint={
          country ? `/reference/subdivisions/?country_id=${country.id}` : null
        }
        value={subdivision}
        onCount={(count) => setHasSubdivisions(count > 0)}
        onChange={(value) => {
          setSubdivision(value)
          setCity(null)
          onChange('')
          onDetails?.({
            country: country ? String(country.id) : '',
            subdivision: value ? String(value.id) : '',
            city: '',
          })
        }}
      />
      <RemoteSelect
        label="Ciudad"
        endpoint={
          country && (subdivision || hasSubdivisions === false)
            ? `/reference/cities/?country_id=${country.id}${subdivision ? `&subdivision_id=${subdivision.id}` : ''}`
            : null
        }
        value={city}
        onChange={(value) => {
          setCity(value)
          onChange(value ? String(value.id) : '')
          onDetails?.({
            country: country ? String(country.id) : '',
            subdivision: subdivision ? String(subdivision.id) : '',
            city: value ? String(value.id) : '',
          })
        }}
      />
    </fieldset>
  )
}
