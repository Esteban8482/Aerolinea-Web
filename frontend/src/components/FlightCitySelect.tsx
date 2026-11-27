import { useEffect, useRef, useState } from 'react'
import { api } from '../api'
import RemoteSelect, { type Choice } from './RemoteSelect'
export default function FlightCitySelect({ side, value, opposite, date, passengers, travelClass, onChange }: { side: 'origin' | 'destination'; value: number | ''; opposite: number | ''; date: string; passengers: number; travelClass: string; onChange: (id: number | '') => void }) {
  const [choice, setChoice] = useState<Choice | null>(null)
  const params = new URLSearchParams({ side, passengers: String(passengers) })
  if (opposite) params.set(side === 'origin' ? 'destination_id' : 'origin_id', String(opposite))
  if (date) params.set('date', date)
  if (travelClass) params.set('travel_class', travelClass)
  const endpoint = `/flights/city-options/?${params}`
  const change = useRef(onChange)
  change.current = onChange
  useEffect(() => {
    let active = true
    if (value) api.get(`${endpoint}&selected_id=${value}`).then(data => { if (active && data.count === 0) change.current('') }).catch(() => {})
    return () => { active = false }
  }, [endpoint, value])
  return <RemoteSelect label={side === 'origin' ? 'Ciudad de origen' : 'Ciudad de destino'} endpoint={`/flights/city-options/?${params}`} value={value ? choice : null} onChange={selected => { setChoice(selected); onChange(selected?.id ?? '') }} />
}
