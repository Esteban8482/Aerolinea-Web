import { useEffect, useRef, useState } from 'react'
import { api } from '../api'
import RemoteSelect, { type Choice } from './RemoteSelect'

interface Props {
  side: 'origin' | 'destination'
  value: number | ''
  opposite: number | ''
  date: string
  passengers: number
  travelClass: string
  label?: string
  onChange: (id: number | '') => void
}

export default function FlightCitySelect({
  side,
  value,
  opposite,
  date,
  passengers,
  travelClass,
  label,
  onChange,
}: Props) {
  const [choice, setChoice] = useState<Choice | null>(null)
  const params = new URLSearchParams({ side, passengers: String(passengers) })
  if (opposite) params.set(side === 'origin' ? 'destination_id' : 'origin_id', String(opposite))
  if (date) params.set('date', date)
  if (travelClass) params.set('travel_class', travelClass)
  const endpoint = `/flights/city-options/?${params.toString()}`
  const onChangeRef = useRef(onChange)
  onChangeRef.current = onChange
  useEffect(() => {
    let active = true
    if (!value) {
      setChoice(null)
      return () => { active = false }
    }
    api.get(`${endpoint}&selected_id=${value}`)
      .then(data => {
        if (!active) return
        if (data.results.length === 0) {
          setChoice(null)
          onChangeRef.current('')
        } else {
          setChoice(data.results[0])
        }
      })
      .catch(() => {
        // Preserve the existing identifier/label on a transient network failure.
        if (active) setChoice(current => current?.id === value ? current : { id: value })
      })
    return () => { active = false }
  }, [endpoint, value])
  return (
    <RemoteSelect
      label={label ?? (side === 'origin' ? 'Ciudad de origen' : 'Ciudad de destino')}
      endpoint={endpoint}
      value={value ? choice : null}
      onChange={selected => {
        setChoice(selected)
        onChange(selected?.id ?? '')
      }}
    />
  )
}
