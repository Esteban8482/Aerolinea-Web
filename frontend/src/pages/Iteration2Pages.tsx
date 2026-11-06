import { useMemo, useState, type FormEvent } from 'react'
import {
  cities,
  formatCurrency,
  formatDate,
  loadFlights,
  loadWallet,
  saveFlights,
  saveWallet,
  type Flight,
  type WalletState,
} from '../mockData'

type Notice = { ok: boolean; message: string } | null

function Notice({ notice }: { notice: Notice }) {
  if (!notice) return null
  return <div className={`iteration-notice ${notice.ok ? 'iteration-notice--ok' : 'iteration-notice--error'}`} role="status">{notice.message}</div>
}

function FlightCard({ flight, onSelect }: { flight: Flight; onSelect?: (flight: Flight) => void }) {
  return (
    <article className="flight-card">
      <div className="flight-card__top">
        <span className="flight-code">{flight.code}</span>
        <span className={`status-pill status-pill--${flight.status === 'Agotado' ? 'muted' : 'ok'}`}>{flight.status}</span>
      </div>
      <div className="flight-route">
        <div><strong>{flight.originCode}</strong><span>{flight.origin}</span></div>
        <div className="flight-route__line"><span>✈</span><small>{flight.duration}</small></div>
        <div><strong>{flight.destinationCode}</strong><span>{flight.destination}</span></div>
      </div>
      <div className="flight-card__details">
        <span>{formatDate(flight.departure)}</span>
        <span>{flight.available} cupos disponibles</span>
        <strong>{formatCurrency(flight.price)}</strong>
      </div>
      {flight.promotion && <span className="promotion-label">{flight.promotion}</span>}
      {onSelect && <button className="btn btn--small" type="button" onClick={() => onSelect(flight)} disabled={flight.available === 0}>Ver detalle</button>}
    </article>
  )
}

export function FlightSearchPage() {
  const [flights] = useState(loadFlights)
  const [origin, setOrigin] = useState('')
  const [destination, setDestination] = useState('')
  const [date, setDate] = useState('')
  const [passengers, setPassengers] = useState('1')
  const [type, setType] = useState('Todos')
  const [maxPrice, setMaxPrice] = useState('')
  const [searched, setSearched] = useState(false)
  const [notice, setNotice] = useState<Notice>(null)
  const [selected, setSelected] = useState<Flight | null>(null)

  const results = useMemo(() => flights.filter((flight) =>
    (!origin || flight.originCode === origin) &&
    (!destination || flight.destinationCode === destination) &&
    (!date || flight.departure.startsWith(date)) &&
    (type === 'Todos' || flight.type === type) &&
    (!maxPrice || flight.price <= Number(maxPrice)) &&
    flight.status === 'Programado' &&
    flight.available >= Number(passengers),
  ), [date, destination, flights, maxPrice, origin, passengers, type])

  function search(event: FormEvent) {
    event.preventDefault()
    setNotice(null)
    if (!origin || !destination || !date) {
      setNotice({ ok: false, message: 'Completa origen, destino y fecha de salida.' })
      return
    }
    if (origin === destination) {
      setNotice({ ok: false, message: 'El origen y el destino deben ser diferentes.' })
      return
    }
    if (Number(passengers) < 1 || Number(passengers) > 5) {
      setNotice({ ok: false, message: 'La búsqueda admite entre 1 y 5 pasajeros.' })
      return
    }
    setSearched(true)
  }

  return (
    <main className="iteration-page page--wide">
      <div className="iteration-heading"><span className="eyebrow">HU-005 · Búsqueda</span><h1>Encuentra tu próximo vuelo</h1><p>Compara rutas, horarios, precios y disponibilidad en un solo lugar.</p></div>
      <form className="iteration-panel search-form" onSubmit={search}>
        <label>Origen<select value={origin} onChange={(event) => setOrigin(event.target.value)}><option value="">Todas las ciudades</option>{cities.map((city) => <option key={city.code} value={city.code}>{city.name} ({city.code})</option>)}</select></label>
        <label>Destino<select value={destination} onChange={(event) => setDestination(event.target.value)}><option value="">Todos los destinos</option>{cities.map((city) => <option key={city.code} value={city.code}>{city.name} ({city.code})</option>)}</select></label>
        <label>Fecha de ida<input type="date" value={date} onChange={(event) => setDate(event.target.value)} /></label>
        <label>Pasajeros<select value={passengers} onChange={(event) => setPassengers(event.target.value)}>{[1, 2, 3, 4, 5].map((value) => <option key={value} value={value}>{value}</option>)}</select></label>
        <label>Tipo de vuelo<select value={type} onChange={(event) => setType(event.target.value)}><option>Todos</option><option>Nacional</option><option>Internacional</option></select></label>
        <label>Precio máximo<input type="number" min="0" placeholder="Sin límite" value={maxPrice} onChange={(event) => setMaxPrice(event.target.value)} /></label>
        <button className="btn btn--primary iteration-form__submit" type="submit">Buscar vuelos</button>
      </form>
      <Notice notice={notice} />
      {searched && <section className="iteration-results"><div className="section-title"><h2>{results.length} vuelos encontrados</h2><span>Para {passengers} pasajero(s)</span></div>{results.length ? <div className="flight-grid">{results.map((flight) => <FlightCard key={flight.id} flight={flight} onSelect={setSelected} />)}</div> : <div className="empty-state"><strong>No encontramos vuelos con esos criterios</strong><span>Prueba otra fecha, ciudad o amplía el precio máximo.</span></div>}</section>}
      {selected && <div className="detail-panel"><button className="close-button" type="button" onClick={() => setSelected(null)}>Cerrar</button><span className="eyebrow">Detalle del vuelo</span><h2>{selected.code}: {selected.origin} → {selected.destination}</h2><p>Salida: {formatDate(selected.departure)} · Duración: {selected.duration}</p><p>Precio por persona: <strong>{formatCurrency(selected.price)}</strong></p><button className="btn" type="button" onClick={() => setNotice({ ok: true, message: 'En el prototipo, la reserva se habilitará en la siguiente historia.' })}>Continuar</button></div>}
    </main>
  )
}

export function FlightCatalogPage() {
  const [flights] = useState(loadFlights)
  const [city, setCity] = useState('')
  const [sort, setSort] = useState('date')
  const listedFlights = useMemo(() => flights.filter((flight) => flight.originCode === city && flight.status === 'Programado').sort((a, b) => sort === 'price' ? a.price - b.price : a.departure.localeCompare(b.departure)), [city, flights, sort])
  return (
    <main className="iteration-page page--wide">
      <div className="iteration-heading"><span className="eyebrow">HU-006 · Catálogo</span><h1>Vuelos desde tu ciudad</h1><p>Consulta la oferta programada y elige tu próximo destino.</p></div>
      <div className="iteration-panel catalog-controls"><label>Ciudad de origen<select value={city} onChange={(event) => setCity(event.target.value)}><option value="">Selecciona una ciudad</option>{cities.map((item) => <option key={item.code} value={item.code}>{item.name} ({item.code})</option>)}</select></label><label>Ordenar por<select value={sort} onChange={(event) => setSort(event.target.value)}><option value="date">Fecha de salida</option><option value="price">Precio menor</option></select></label></div>
      {city && (listedFlights.length ? <section className="iteration-results"><div className="section-title"><h2>{listedFlights.length} vuelos desde {cities.find((item) => item.code === city)?.name}</h2></div><div className="flight-grid">{listedFlights.map((flight) => <FlightCard key={flight.id} flight={flight} />)}</div></section> : <div className="empty-state"><strong>No hay vuelos programados desde esta ciudad</strong><span>Selecciona otra ciudad para consultar el catálogo.</span></div>)}
    </main>
  )
}

export function ScheduleFlightPage() {
  const [flights, setFlights] = useState(loadFlights)
  const [form, setForm] = useState({ type: 'Nacional', origin: '', destination: '', departure: '', price: '' })
  const [notice, setNotice] = useState<Notice>(null)
  const update = (key: keyof typeof form, value: string) => setForm((current) => ({ ...current, [key]: value }))
  function submit(event: FormEvent) {
    event.preventDefault()
    setNotice(null)
    if (!form.origin || !form.destination || !form.departure || !form.price) {
      setNotice({ ok: false, message: 'Completa todos los campos obligatorios.' })
      return
    }
    if (form.origin === form.destination || Number(form.price) <= 0) {
      setNotice({ ok: false, message: 'La ruta debe ser válida y el precio debe ser positivo.' })
      return
    }
    const originCity = cities.find((city) => city.code === form.origin)!
    const destinationCity = cities.find((city) => city.code === form.destination)!
    const next: Flight = {
      id: crypto.randomUUID(),
      code: `ALA-${String(flights.length + 1).padStart(3, '0')}`,
      type: form.type as Flight['type'],
      origin: originCity.name,
      originCode: originCity.code,
      destination: destinationCity.name,
      destinationCode: destinationCity.code,
      departure: form.departure,
      duration: form.type === 'Nacional' ? '1h 15min' : '8h 40min',
      price: Number(form.price),
      capacity: form.type === 'Nacional' ? 150 : 250,
      available: form.type === 'Nacional' ? 150 : 250,
      status: 'Programado',
    }
    const updated = [next, ...flights]
    setFlights(updated)
    saveFlights(updated)
    setForm({ type: 'Nacional', origin: '', destination: '', departure: '', price: '' })
    setNotice({ ok: true, message: `Vuelo ${next.code} programado correctamente. Capacidad asignada: ${next.capacity} sillas.` })
  }
  return (
    <main className="iteration-page page--wide">
      <div className="iteration-heading"><span className="eyebrow">HU-001 · Administración</span><h1>Programar un vuelo</h1><p>Registra una nueva ruta y calcula automáticamente su capacidad.</p></div>
      <form className="iteration-panel admin-form" onSubmit={submit}><label>Tipo de vuelo<select value={form.type} onChange={(event) => update('type', event.target.value)}><option>Nacional</option><option>Internacional</option></select></label><label>Origen<select value={form.origin} onChange={(event) => update('origin', event.target.value)}><option value="">Selecciona</option>{cities.map((city) => <option key={city.code} value={city.code}>{city.name} ({city.code})</option>)}</select></label><label>Destino<select value={form.destination} onChange={(event) => update('destination', event.target.value)}><option value="">Selecciona</option>{cities.map((city) => <option key={city.code} value={city.code}>{city.name} ({city.code})</option>)}</select></label><label>Fecha y hora de salida<input type="datetime-local" value={form.departure} onChange={(event) => update('departure', event.target.value)} /></label><label>Precio por persona<input type="number" min="1" value={form.price} onChange={(event) => update('price', event.target.value)} placeholder="$ 0" /></label><div className="form-summary"><strong>Reglas aplicadas</strong><span>{form.type === 'Nacional' ? '150 sillas · 25 primera clase · 125 económica' : '250 sillas · 50 primera clase · 200 económica'}</span><span>El código y la duración se generan automáticamente.</span></div><button className="btn btn--primary" type="submit">Guardar vuelo</button></form>
      <Notice notice={notice} />
      <section className="iteration-results"><div className="section-title"><h2>Vuelos programados</h2><span>{flights.length} en el prototipo</span></div><div className="flight-grid">{flights.slice(0, 4).map((flight) => <FlightCard key={flight.id} flight={flight} />)}</div></section>
    </main>
  )
}

export function WalletPage() {
  const [wallet, setWallet] = useState<WalletState>(loadWallet)
  const [methodForm, setMethodForm] = useState({ type: 'Tarjeta', label: '', number: '' })
  const [amount, setAmount] = useState('')
  const [notice, setNotice] = useState<Notice>(null)
  function addMethod(event: FormEvent) {
    event.preventDefault()
    if (!methodForm.label || methodForm.number.replace(/\D/g, '').length < 4) {
      setNotice({ ok: false, message: 'Ingresa un nombre y un número válido para el medio de pago.' })
      return
    }
    const digits = methodForm.number.replace(/\D/g, '')
    const next = { ...wallet, methods: [{ id: crypto.randomUUID(), type: methodForm.type as 'Tarjeta' | 'Cuenta bancaria', label: methodForm.label, lastFour: digits.slice(-4) }, ...wallet.methods] }
    setWallet(next)
    saveWallet(next)
    setMethodForm({ type: 'Tarjeta', label: '', number: '' })
    setNotice({ ok: true, message: 'Medio de pago agregado y almacenado de forma enmascarada.' })
  }
  function deposit(event: FormEvent) {
    event.preventDefault()
    const value = Number(amount)
    if (!wallet.methods.length) {
      setNotice({ ok: false, message: 'Agrega un medio de pago antes de depositar.' })
      return
    }
    if (!Number.isFinite(value) || value <= 0) {
      setNotice({ ok: false, message: 'El depósito debe ser un valor positivo.' })
      return
    }
    const method = wallet.methods[0]
    const nextBalance = wallet.balance + value
    const next = { ...wallet, balance: nextBalance, movements: [{ id: crypto.randomUUID(), date: new Date().toISOString(), type: 'Depósito' as const, method: `${method.label} •••• ${method.lastFour}`, amount: value, balance: nextBalance }, ...wallet.movements] }
    setWallet(next)
    saveWallet(next)
    setAmount('')
    setNotice({ ok: true, message: `Depósito registrado. Tu nuevo saldo es ${formatCurrency(nextBalance)}.` })
  }
  return (
    <main className="iteration-page page--wide">
      <div className="iteration-heading"><span className="eyebrow">HU-010 · Gestión financiera</span><h1>Tu billetera</h1><p>Administra medios de pago y deposita fondos para tus próximos viajes.</p></div>
      <div className="wallet-balance"><span>Saldo disponible</span><strong>{formatCurrency(wallet.balance)}</strong><small>Prototipo local · sin conexión bancaria real</small></div>
      <Notice notice={notice} />
      <div className="wallet-grid"><section className="iteration-panel"><h2>Agregar medio de pago</h2><form className="stack-form" onSubmit={addMethod}><label>Tipo<select value={methodForm.type} onChange={(event) => setMethodForm({ ...methodForm, type: event.target.value })}><option>Tarjeta</option><option>Cuenta bancaria</option></select></label><label>Nombre descriptivo<input value={methodForm.label} onChange={(event) => setMethodForm({ ...methodForm, label: event.target.value })} placeholder="Ej. Visa débito" /></label><label>Número<input value={methodForm.number} onChange={(event) => setMethodForm({ ...methodForm, number: event.target.value })} inputMode="numeric" placeholder="No se almacena completo" /></label><button className="btn" type="submit">Agregar medio</button></form></section><section className="iteration-panel"><h2>Depositar fondos</h2><form className="stack-form" onSubmit={deposit}><label>Medio seleccionado<select disabled><option>{wallet.methods[0] ? `${wallet.methods[0].label} •••• ${wallet.methods[0].lastFour}` : 'Sin medios registrados'}</option></select></label><label>Valor a depositar<input type="number" min="1" value={amount} onChange={(event) => setAmount(event.target.value)} placeholder="$ 0" /></label><button className="btn btn--primary" type="submit">Confirmar depósito</button></form></section></div>
      <section className="iteration-panel"><h2>Medios registrados</h2>{wallet.methods.map((method) => <div className="payment-row" key={method.id}><span className="payment-icon">▣</span><div><strong>{method.label}</strong><span>{method.type} ·•••• {method.lastFour}</span></div><span className="status-pill status-pill--ok">Activo</span></div>)}</section>
      <section className="iteration-panel"><h2>Movimientos recientes</h2><div className="movement-list">{wallet.movements.map((movement) => <div className="movement-row" key={movement.id}><div><strong>{movement.type}</strong><span>{formatDate(movement.date)} · {movement.method}</span></div><strong className="movement-amount">+ {formatCurrency(movement.amount)}</strong><span>{formatCurrency(movement.balance)}</span></div>)}</div></section>
    </main>
  )
}
