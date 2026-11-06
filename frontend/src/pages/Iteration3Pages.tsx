import { useMemo, useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import {
  formatCurrency,
  formatDate,
  loadFlights,
  loadWallet,
  saveFlights,
  saveWallet,
  type Flight,
} from '../mockData'

type Traveler = {
  document: string
  name: string
  birthDate: string
  email: string
}

type Notice = { ok: boolean; message: string } | null

const emptyTraveler: Traveler = { document: '', name: '', birthDate: '', email: '' }
const reservationKey = 'alas-iteration-3-reservations'
const purchaseKey = 'alas-iteration-3-purchases'

function isAdult(birthDate: string) {
  if (!birthDate) return false
  const birth = new Date(`${birthDate}T00:00:00`)
  const today = new Date()
  let age = today.getFullYear() - birth.getFullYear()
  const beforeBirthday =
    today.getMonth() < birth.getMonth() ||
    (today.getMonth() === birth.getMonth() && today.getDate() < birth.getDate())
  if (beforeBirthday) age -= 1
  return age >= 18
}

function Notice({ notice }: { notice: Notice }) {
  if (!notice) return null
  return <div className={`iteration-notice ${notice.ok ? 'iteration-notice--ok' : 'iteration-notice--error'}`} role="status">{notice.message}</div>
}

function FlightChoice({ flight, selected, onSelect }: { flight: Flight; selected: boolean; onSelect: () => void }) {
  return (
    <button className={`commerce-flight ${selected ? 'commerce-flight--selected' : ''}`} type="button" onClick={onSelect}>
      <span className="flight-code">{flight.code}</span>
      <strong>{flight.originCode} → {flight.destinationCode}</strong>
      <span>{formatDate(flight.departure)} · {flight.duration}</span>
      <b>{formatCurrency(flight.price)} por persona</b>
      <small>{flight.available} cupos disponibles</small>
    </button>
  )
}

function TravelerForm({ traveler, onChange, index }: { traveler: Traveler; onChange: (value: Traveler) => void; index: number }) {
  const update = (key: keyof Traveler, value: string) => onChange({ ...traveler, [key]: value })
  return (
    <fieldset className="traveler-form">
      <legend>Viajero {index + 1}</legend>
      <label>Documento<input value={traveler.document} onChange={(event) => update('document', event.target.value)} placeholder="Número de documento" /></label>
      <label>Nombre completo<input value={traveler.name} onChange={(event) => update('name', event.target.value)} placeholder="Nombres y apellidos" /></label>
      <label>Fecha de nacimiento<input type="date" value={traveler.birthDate} onChange={(event) => update('birthDate', event.target.value)} /></label>
      <label>Correo del viajero<input type="email" value={traveler.email} onChange={(event) => update('email', event.target.value)} placeholder="correo@example.com" /></label>
    </fieldset>
  )
}

function CommercePage({ mode }: { mode: 'reservation' | 'purchase' }) {
  const [flights, setFlights] = useState(loadFlights)
  const [selectedId, setSelectedId] = useState('')
  const [ticketCount, setTicketCount] = useState('1')
  const [travelClass, setTravelClass] = useState('Económica')
  const [travelers, setTravelers] = useState<Traveler[]>([emptyTraveler])
  const [notice, setNotice] = useState<Notice>(null)
  const selectedFlight = flights.find((flight) => flight.id === selectedId)
  const total = (selectedFlight?.price ?? 0) * travelers.length
  const wallet = loadWallet()
  const availableFlights = useMemo(() => flights.filter((flight) => flight.status === 'Programado' && flight.available > 0), [flights])

  function changeTicketCount(value: string) {
    const count = Math.min(5, Math.max(1, Number(value) || 1))
    setTicketCount(String(count))
    setTravelers((current) => Array.from({ length: count }, (_, index) => current[index] ?? { ...emptyTraveler }))
  }

  function submit(event: FormEvent) {
    event.preventDefault()
    setNotice(null)
    if (!selectedFlight) {
      setNotice({ ok: false, message: 'Selecciona un vuelo para continuar.' })
      return
    }
    if (travelers.some((traveler) => !traveler.document || !traveler.name || !traveler.birthDate || !traveler.email)) {
      setNotice({ ok: false, message: 'Completa todos los datos de cada viajero.' })
      return
    }
    const documents = travelers.map((traveler) => traveler.document)
    if (new Set(documents).size !== documents.length) {
      setNotice({ ok: false, message: 'No puedes repetir el mismo viajero en un vuelo.' })
      return
    }
    if (!travelers.some((traveler) => isAdult(traveler.birthDate))) {
      setNotice({ ok: false, message: 'La operación debe incluir al menos un viajero mayor de edad.' })
      return
    }
    if (travelers.length > selectedFlight.available) {
      setNotice({ ok: false, message: 'No hay suficientes cupos disponibles para esta operación.' })
      return
    }
    if (mode === 'purchase' && wallet.balance < total) {
      setNotice({ ok: false, message: `Saldo insuficiente. Necesitas ${formatCurrency(total)} y tienes ${formatCurrency(wallet.balance)}.` })
      return
    }

    const nextFlights = flights.map((flight) => flight.id === selectedFlight.id
      ? { ...flight, available: flight.available - travelers.length, status: flight.available - travelers.length === 0 ? 'Agotado' as const : flight.status }
      : flight)
    setFlights(nextFlights)
    saveFlights(nextFlights)
    const reference = `ALA-${Math.floor(100000 + Math.random() * 900000)}`
    if (mode === 'reservation') {
      localStorage.setItem(reservationKey, JSON.stringify({ reference, flight: selectedFlight.code, travelers, travelClass, expires: '24 horas' }))
      setNotice({ ok: true, message: `Reserva ${reference} creada. Vigencia: 24 horas o hasta una hora antes de la salida.` })
    } else {
      const nextWallet = {
        ...wallet,
        balance: wallet.balance - total,
        movements: [{
          id: crypto.randomUUID(),
          date: new Date().toISOString(),
          type: 'Compra' as const,
          method: `Compra ${reference}`,
          amount: -total,
          balance: wallet.balance - total,
        }, ...wallet.movements],
      }
      saveWallet(nextWallet)
      localStorage.setItem(purchaseKey, JSON.stringify({ reference, flight: selectedFlight.code, travelers, travelClass, total }))
      setNotice({ ok: true, message: `Compra ${reference} confirmada por ${formatCurrency(total)}. Los códigos de reserva y sillas se asignaron en el prototipo.` })
    }
    setSelectedId('')
    setTravelers([{ ...emptyTraveler }])
    setTicketCount('1')
  }

  return (
    <main className="iteration-page page--wide">
      <div className="iteration-heading">
        <span className="eyebrow">{mode === 'reservation' ? 'HU-012 · Reservas' : 'HU-013 · Compras'}</span>
        <h1>{mode === 'reservation' ? 'Reserva tus tiquetes' : 'Compra tus tiquetes'}</h1>
        <p>{mode === 'reservation' ? 'Aparta tus cupos sin pagar y conviértelos en compra antes del vencimiento.' : 'Confirma tu viaje usando el saldo disponible de tu billetera.'}</p>
      </div>
      <Notice notice={notice} />
      <section className="iteration-panel">
        <div className="section-title"><h2>1. Selecciona tu vuelo</h2><span>{availableFlights.length} opciones disponibles</span></div>
        <div className="commerce-flights">{availableFlights.map((flight) => <FlightChoice key={flight.id} flight={flight} selected={flight.id === selectedId} onSelect={() => setSelectedId(flight.id)} />)}</div>
      </section>
      <form onSubmit={submit}>
        <section className="iteration-panel commerce-options">
          <h2>2. Configura tus tiquetes</h2>
          <label>Cantidad de tiquetes<select value={ticketCount} onChange={(event) => changeTicketCount(event.target.value)}>{[1, 2, 3, 4, 5].map((value) => <option key={value} value={value}>{value}</option>)}</select></label>
          <label>Clase<select value={travelClass} onChange={(event) => setTravelClass(event.target.value)}><option>Económica</option><option>Primera</option></select></label>
          <div className="commerce-total"><span>Total estimado</span><strong>{formatCurrency(total)}</strong></div>
        </section>
        <section className="iteration-panel">
          <h2>3. Datos de los viajeros</h2>
          <p className="form-help">Debe haber al menos un viajero mayor de edad y no se permiten personas repetidas.</p>
          <div className="traveler-grid">{travelers.map((traveler, index) => <TravelerForm key={index} index={index} traveler={traveler} onChange={(value) => setTravelers((current) => current.map((item, itemIndex) => itemIndex === index ? value : item))} />)}</div>
        </section>
        <section className="commerce-confirmation">
          {mode === 'purchase' && <span>Saldo disponible: <strong>{formatCurrency(wallet.balance)}</strong></span>}
          {mode === 'reservation' && <span>La reserva no genera cobro inmediato.</span>}
          <button className="btn btn--primary" type="submit">{mode === 'reservation' ? 'Confirmar reserva' : 'Confirmar compra'}</button>
        </section>
      </form>
      {mode === 'purchase' && <p className="commerce-footnote">¿Necesitas fondos? <Link to="/billetera">Ir a mi billetera</Link></p>}
    </main>
  )
}

export function ReservationPage() {
  return <CommercePage mode="reservation" />
}

export function PurchasePage() {
  return <CommercePage mode="purchase" />
}
