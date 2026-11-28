import { useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import {
  ArrowRight,
  ArrowUpRight,
  BadgeCheck,
  Plane,
  PlaneLanding,
  PlaneTakeoff,
  Search,
  Sparkles,
} from 'lucide-react'
import { api, ApiError } from '../api'
import FlightCitySelect from '../components/FlightCitySelect'
import type { Vuelo } from '../types/flight'

export default function HomePage() {
  const [tipoTrayecto, setTipoTrayecto] = useState<'UNICO' | 'COMPLETO'>('UNICO')
  const [origenId, setOrigenId] = useState<number>(0)
  const [destinoId, setDestinoId] = useState<number>(0)
  const [fechaSalida, setFechaSalida] = useState('')
  const [fechaRegreso, setFechaRegreso] = useState('')
  const [pasajeros, setPasajeros] = useState<number>(1)
  const [clase, setClase] = useState<'' | 'ECONOMICA' | 'PRIMERA_CLASE'>('')

  const [loading, setLoading] = useState(false)
  const [hasSearched, setHasSearched] = useState(false)
  const [searchError, setSearchError] = useState('')
  const [vuelosIda, setVuelosIda] = useState<Vuelo[]>([])
  const [vuelosRegreso, setVuelosRegreso] = useState<Vuelo[]>([])


  async function handleSearch(e: FormEvent) {
    e.preventDefault()
    setSearchError('')
    if (origenId && destinoId && origenId === destinoId) {
      setSearchError('El origen y el destino no pueden ser la misma ciudad.')
      return
    }
    if (tipoTrayecto === 'COMPLETO') {
      if (!fechaSalida || !fechaRegreso) {
        setSearchError('Para ida y regreso debes seleccionar ambas fechas.')
        return
      }
      if (fechaRegreso < fechaSalida) {
        setSearchError('La fecha de regreso no puede ser anterior a la de salida.')
        return
      }
    }
    setLoading(true)
    setHasSearched(true)

    try {
      const payload: Record<string, unknown> = {
        tipo_trayecto: tipoTrayecto,
        pasajeros,
      }
        if (clase) payload.clase = clase
      if (origenId) payload.origen_id = origenId
      if (destinoId) payload.destino_id = destinoId
      if (fechaSalida) payload.fecha_salida = fechaSalida
      if (tipoTrayecto === 'COMPLETO' && fechaRegreso) payload.fecha_regreso = fechaRegreso

      const res = await api.post('/flights/search/', payload)
      setVuelosIda(res.vuelos_ida || [])
      setVuelosRegreso(res.vuelos_regreso || [])
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : 'Error al buscar vuelos.'
      setSearchError(msg)
      setVuelosIda([])
      setVuelosRegreso([])
    } finally {
      setLoading(false)
    }
  }

  return (
    <main className="home-page">
      {/* SECCIÓN HERO CON BOTONES DE ACCIÓN (BUSCAR VUELOS Y CREAR CUENTA) */}
      <section className="home-hero">
        <div className="home-hero__content">
          <span className="home-eyebrow">Vuela diferente · Viaja más lejos</span>
          <h1 className="home-hero__title">
            Tu próximo destino
            <span> empieza aquí.</span>
          </h1>
          <p className="home-hero__subtitle">
            Encuentra nuevas rutas, gestiona tus vuelos y disfruta una experiencia
            simple desde la búsqueda hasta el abordaje.
          </p>
          <div className="home-actions">
            <Link to="/vuelos" className="btn btn--primary">
              Buscar vuelos <ArrowRight aria-hidden="true" size={18} />
            </Link>
            <Link to="/registro" className="btn btn--secondary">
              Crear cuenta
            </Link>
          </div>
          <div className="home-trust">
            <span className="home-trust__avatars" aria-hidden="true">
              <Sparkles size={18} />
            </span>
            <span>Gestiona tus viajes desde tu cuenta</span>
          </div>
        </div>

        <div className="home-hero__visual" aria-label="Resumen de un viaje destacado">
          <div className="home-route-card">
            <div className="home-route-card__top">
              <span>Ruta destacada</span>
              <span className="home-route-card__status">Consulta disponibilidad</span>
            </div>
            <div className="home-route">
              <div>
                <strong>PEI</strong>
                <span>Pereira</span>
              </div>
              <div className="home-route__line">
                <span aria-hidden="true"><Plane size={20} /></span>
              </div>
              <div className="home-route__destination">
                <strong>MAD</strong>
                <span>Madrid</span>
              </div>
            </div>
            <div className="home-route-card__bottom">
              <span>Consulta rutas y horarios disponibles</span>
              <Link to="/vuelos" className="home-route-card__link">
                Ver vuelos <ArrowUpRight aria-hidden="true" size={16} />
              </Link>
            </div>
          </div>
          <div className="home-floating-card home-floating-card--top">
            <span className="home-floating-card__icon">
              <ArrowUpRight aria-hidden="true" size={16} />
            </span>
            <span>Destinos por explorar</span>
          </div>
          <div className="home-floating-card home-floating-card--bottom">
            <span className="home-floating-card__icon">
              <BadgeCheck aria-hidden="true" size={16} />
            </span>
            <span><strong>Reserva fácil</strong><br />en pocos pasos</span>
          </div>
        </div>
      </section>

      {/* MOTOR DE BÚSQUEDA INTERACTIVO */}
      <section className="home-section home-section--search">
        <div className="home-section__heading">
          <div>
            <span className="home-eyebrow">Búsqueda rápida en tiempo real</span>
            <h2>Encuentra y cotiza tu vuelo</h2>
          </div>
        </div>

        <div className="flight-search-box home-search-box">
          <form onSubmit={handleSearch} className="home-search-form">
            <div className="home-trip-options" role="radiogroup" aria-label="Tipo de trayecto">
              <label className="home-trip-option">
                <input
                  type="radio"
                  name="trayecto"
                  checked={tipoTrayecto === 'UNICO'}
                  onChange={() => setTipoTrayecto('UNICO')}
                />
                Solo ida
              </label>
              <label className="home-trip-option">
                <input
                  type="radio"
                  name="trayecto"
                  checked={tipoTrayecto === 'COMPLETO'}
                  onChange={() => setTipoTrayecto('COMPLETO')}
                />
                Ida y regreso
              </label>
            </div>

            <div className="flight-search-grid">
              <FlightCitySelect side="origin" value={origenId} opposite={destinoId} date={fechaSalida} passengers={pasajeros} travelClass={clase} onChange={id => setOrigenId(id || 0)} />
              <FlightCitySelect side="destination" value={destinoId} opposite={origenId} date={fechaSalida} passengers={pasajeros} travelClass={clase} onChange={id => setDestinoId(id || 0)} />

              <div className="form-group">
                <label className="form-label" htmlFor="home-departure-date">Fecha de salida</label>
                <input
                  id="home-departure-date"
                  type="date"
                  className="form-input"
                  value={fechaSalida}
                  onChange={(e) => setFechaSalida(e.target.value)}
                />
              </div>

              {tipoTrayecto === 'COMPLETO' && (
                <div className="form-group">
                  <label className="form-label" htmlFor="home-return-date">Fecha de regreso</label>
                  <input
                    id="home-return-date"
                    type="date"
                    className="form-input"
                    value={fechaRegreso}
                    onChange={(e) => setFechaRegreso(e.target.value)}
                  />
                </div>
              )}

              <div className="form-group">
                <label className="form-label" htmlFor="home-passengers">Pasajeros</label>
                <select
                  id="home-passengers"
                  className="form-select"
                  value={pasajeros}
                  onChange={(e) => setPasajeros(Number(e.target.value))}
                >
                  {[1, 2, 3, 4, 5].map((n) => (
                    <option key={n} value={n}>
                      {n} {n === 1 ? 'viajero' : 'viajeros'}
                    </option>
                  ))}
                </select>
              </div>

              <div className="form-group">
                <label className="form-label" htmlFor="home-class">Clase de viaje</label>
                <select id="home-class" className="form-select" value={clase} onChange={(event) => setClase(event.target.value as '' | 'ECONOMICA' | 'PRIMERA_CLASE')}>
                  <option value="">Cualquier clase disponible</option>
                  <option value="ECONOMICA">Económica</option>
                  <option value="PRIMERA_CLASE">Primera clase</option>
                </select>
              </div>
            </div>

            {searchError && (
              <div className="form-error" role="alert">
                {searchError}
              </div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="btn btn--primary home-search-submit"
              aria-busy={loading}
            >
              {loading ? 'Buscando vuelos...' : <><Search aria-hidden="true" size={18} /> Buscar vuelos disponibles</>}
            </button>
          </form>
        </div>
      </section>

      {/* RESULTADOS DE BÚSQUEDA */}
      {hasSearched && (
        <section className="home-section home-results">
          <div className="home-section__heading">
            <div>
              <span className="home-eyebrow">Resultados de búsqueda</span>
              <h2>Vuelos disponibles para tu viaje</h2>
            </div>
          </div>

          <div className="home-results__content">
            <h3 className="home-results__title">
              <PlaneTakeoff aria-hidden="true" size={20} />
              <span>Vuelos de ida ({vuelosIda.length})</span>
            </h3>
            {vuelosIda.length === 0 ? (
              <p style={{ color: '#64748b' }}>No se encontraron vuelos de ida que coincidan con los criterios seleccionados.</p>
            ) : (
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: '1rem' }}>
                {vuelosIda.map((v) => (
                  <div key={v.id} style={{ background: 'white', padding: '1.2rem', borderRadius: '0.75rem', border: '1px solid #e2e8f0', boxShadow: '0 2px 4px rgba(0,0,0,0.05)' }}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
                      <span style={{ fontWeight: 700, color: 'var(--color-primary)' }}>{v.codigo_vuelo}</span>
                      <span style={{ fontSize: '0.8rem', background: '#dcfce7', color: '#166534', padding: '0.2rem 0.5rem', borderRadius: '0.3rem' }}>
                        {v.tipo_vuelo}
                      </span>
                    </div>
                    <div style={{ fontSize: '1.1rem', fontWeight: 600, color: '#0f172a' }}>
                      {v.origen} ➔ {v.destino}
                    </div>
                    <div style={{ fontSize: '0.85rem', color: '#64748b', margin: '0.4rem 0' }}>
                      Salida: {v.fecha_salida} a las {v.hora_salida}
                      <br />
                      Llegada: {v.fecha_llegada} a las {v.hora_llegada} ({v.tiempo_vuelo_min} min)
                    </div>
                    <div style={{ marginTop: '0.8rem', paddingTop: '0.8rem', borderTop: '1px solid #f1f5f9', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <div>
                        <span style={{ fontSize: '0.75rem', color: '#64748b' }}>Desde</span>
                        <div style={{ fontSize: '1.1rem', fontWeight: 700, color: '#0f172a' }}>
                          ${clase === 'PRIMERA_CLASE' ? v.precio_vigente_primera : v.precio_vigente_economica} COP
                        </div>
                      </div>
                      <Link to="/vuelos" className="btn btn--primary" style={{ padding: '0.4rem 0.8rem', fontSize: '0.85rem' }}>
                        Reservar / Comprar <ArrowUpRight aria-hidden="true" size={16} />
                      </Link>
                    </div>
                  </div>
                ))}
              </div>
            )}

            {tipoTrayecto === 'COMPLETO' && (
              <div style={{ marginTop: '2.5rem' }}>
                <h3 className="home-results__title">
                <PlaneLanding aria-hidden="true" size={20} />
                <span>Vuelos de regreso ({vuelosRegreso.length})</span>
                </h3>
                {vuelosRegreso.length === 0 ? (
                  <p style={{ color: '#64748b' }}>No se encontraron vuelos de regreso para la fecha seleccionada.</p>
                ) : (
                  <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))', gap: '1rem' }}>
                    {vuelosRegreso.map((v) => (
                      <div key={v.id} style={{ background: 'white', padding: '1.2rem', borderRadius: '0.75rem', border: '1px solid #e2e8f0', boxShadow: '0 2px 4px rgba(0,0,0,0.05)' }}>
                        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '0.5rem' }}>
                          <span style={{ fontWeight: 700, color: 'var(--color-primary)' }}>{v.codigo_vuelo}</span>
                          <span style={{ fontSize: '0.8rem', background: '#dcfce7', color: '#166534', padding: '0.2rem 0.5rem', borderRadius: '0.3rem' }}>
                            {v.tipo_vuelo}
                          </span>
                        </div>
                        <div style={{ fontSize: '1.1rem', fontWeight: 600, color: '#0f172a' }}>
                          {v.origen} ➔ {v.destino}
                        </div>
                        <div style={{ fontSize: '0.85rem', color: '#64748b', margin: '0.4rem 0' }}>
                          Salida: {v.fecha_salida} a las {v.hora_salida}
                          <br />
                          Llegada: {v.fecha_llegada} a las {v.hora_llegada}
                        </div>
                        <div style={{ marginTop: '0.8rem', paddingTop: '0.8rem', borderTop: '1px solid #f1f5f9', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                          <div>
                            <span style={{ fontSize: '0.75rem', color: '#64748b' }}>Desde</span>
                            <div style={{ fontSize: '1.1rem', fontWeight: 700, color: '#0f172a' }}>
                              ${clase === 'PRIMERA_CLASE' ? v.precio_vigente_primera : v.precio_vigente_economica} COP
                            </div>
                          </div>
                          <Link to="/vuelos" className="btn btn--primary" style={{ padding: '0.4rem 0.8rem', fontSize: '0.85rem' }}>
                            Reservar / Comprar <ArrowUpRight aria-hidden="true" size={16} />
                          </Link>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>
        </section>
      )}

      {/* DESTINOS DESTACADOS */}
      <section className="home-section">
        <div className="home-section__heading">
          <div>
            <span className="home-eyebrow">Inspírate</span>
            <h2>Destinos que te están esperando</h2>
          </div>
          <Link to="/vuelos" className="home-section__hint" style={{ textDecoration: 'underline' }}>
            Ver todos los vuelos
          </Link>
        </div>
        <div className="destination-grid">
          <Link to="/vuelos" style={{ textDecoration: 'none' }}>
            <article className="destination-card destination-card--pink">
              <span className="destination-card__code">MAD</span>
              <div>
                <h3>Madrid</h3>
                <p>Historia, arte y atardeceres</p>
              </div>
              <ArrowUpRight className="destination-card__arrow" aria-hidden="true" size={20} />
            </article>
          </Link>
          <Link to="/vuelos" style={{ textDecoration: 'none' }}>
            <article className="destination-card destination-card--blue">
              <span className="destination-card__code">BOG</span>
              <div>
                <h3>Bogotá</h3>
                <p>Cultura, gastronomía y negocios</p>
              </div>
              <ArrowUpRight className="destination-card__arrow" aria-hidden="true" size={20} />
            </article>
          </Link>
          <Link to="/vuelos" style={{ textDecoration: 'none' }}>
            <article className="destination-card destination-card--purple">
              <span className="destination-card__code">CTG</span>
              <div>
                <h3>Cartagena</h3>
                <p>Sol, playa y arquitectura colonial</p>
              </div>
              <ArrowUpRight className="destination-card__arrow" aria-hidden="true" size={20} />
            </article>
          </Link>
        </div>
      </section>

      <section className="home-benefits">
        <div>
          <span className="home-eyebrow">Todo en un solo lugar</span>
          <h2>Planea el viaje. Nosotros cuidamos el resto.</h2>
        </div>
        <div className="benefit-list">
          <div className="benefit-item">
            <span>01</span>
            <div>
              <h3>Busca con libertad</h3>
              <p>Explora rutas y encuentra el vuelo que se adapta a tus planes.</p>
            </div>
          </div>
          <div className="benefit-item">
            <span>02</span>
            <div>
              <h3>Gestiona tus tiquetes</h3>
              <p>Ten tus reservas y datos de viaje siempre a la mano.</p>
            </div>
          </div>
          <div className="benefit-item">
            <span>03</span>
            <div>
              <h3>Viaja con tranquilidad</h3>
              <p>Una experiencia clara, segura y pensada para ti.</p>
            </div>
          </div>
        </div>
      </section>

      <section className="home-cta">
        <div>
          <span className="home-eyebrow">Tu aventura comienza hoy</span>
          <h2>¿Listo para despegar?</h2>
        </div>
        <Link to="/vuelos" className="btn btn--light">
          Empezar ahora <ArrowRight aria-hidden="true" size={18} />
        </Link>
      </section>
    </main>
  )
}
