import { useEffect, useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { api, ApiError } from '../api'
import type { Ciudad, Vuelo } from '../types/flight'

export default function HomePage() {
  const [cities, setCities] = useState<Ciudad[]>([])
  const [tipoTrayecto, setTipoTrayecto] = useState<'UNICO' | 'COMPLETO'>('UNICO')
  const [origenId, setOrigenId] = useState<number>(0)
  const [destinoId, setDestinoId] = useState<number>(0)
  const [fechaSalida, setFechaSalida] = useState('')
  const [fechaRegreso, setFechaRegreso] = useState('')
  const [pasajeros, setPasajeros] = useState<number>(1)
  const [clase, setClase] = useState<'ECONOMICA' | 'PRIMERA_CLASE'>('ECONOMICA')

  const [loading, setLoading] = useState(false)
  const [hasSearched, setHasSearched] = useState(false)
  const [searchError, setSearchError] = useState('')
  const [vuelosIda, setVuelosIda] = useState<Vuelo[]>([])
  const [vuelosRegreso, setVuelosRegreso] = useState<Vuelo[]>([])

  useEffect(() => {
    api.get('/flights/cities/').then(setCities).catch(() => {})
  }, [])

  async function handleSearch(e: FormEvent) {
    e.preventDefault()
    setSearchError('')
    setLoading(true)
    setHasSearched(true)

    try {
      const payload: Record<string, unknown> = {
        tipo_trayecto: tipoTrayecto,
        pasajeros,
        clase,
      }
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
              Buscar vuelos <span aria-hidden="true">→</span>
            </Link>
            <Link to="/registro" className="btn btn--secondary">
              Crear cuenta
            </Link>
          </div>
          <div className="home-trust">
            <span className="home-trust__avatars" aria-hidden="true">✦ ✈ ●</span>
            <span>Más de 2.000 viajeros ya vuelan con Alas</span>
          </div>
        </div>

        <div className="home-hero__visual" aria-label="Resumen de un viaje destacado">
          <div className="home-route-card">
            <div className="home-route-card__top">
              <span>Ruta destacada</span>
              <span className="home-route-card__status">● Disponible</span>
            </div>
            <div className="home-route">
              <div>
                <strong>PEI</strong>
                <span>Pereira</span>
              </div>
              <div className="home-route__line"><span>✈</span></div>
              <div className="home-route__destination">
                <strong>MAD</strong>
                <span>Madrid</span>
              </div>
            </div>
            <div className="home-route-card__bottom">
              <span>Vuelo directo · 9h 35min</span>
              <Link to="/vuelos" style={{ color: '#ffe8f0', fontWeight: 700 }}>
                Ver vuelos ↗
              </Link>
            </div>
          </div>
          <div className="home-floating-card home-floating-card--top">
            <span className="home-floating-card__icon">↗</span>
            <span><strong>12</strong> destinos por explorar</span>
          </div>
          <div className="home-floating-card home-floating-card--bottom">
            <span className="home-floating-card__icon">✓</span>
            <span><strong>Reserva fácil</strong><br />en pocos pasos</span>
          </div>
        </div>
      </section>

      {/* MOTOR DE BÚSQUEDA INTERACTIVO (CU-05) */}
      <section className="home-section" style={{ paddingTop: '0.5rem', paddingBottom: '2.5rem' }}>
        <div className="home-section__heading">
          <div>
            <span className="home-eyebrow">Búsqueda rápida en tiempo real</span>
            <h2>Encuentra y cotiza tu vuelo</h2>
          </div>
        </div>

        <div className="flight-search-box" style={{ background: 'white', padding: '1.5rem', borderRadius: '1rem', boxShadow: '0 10px 25px -5px rgba(0,0,0,0.08)', color: '#1e293b' }}>
          <form onSubmit={handleSearch} style={{ display: 'flex', flexDirection: 'column', gap: '1rem' }}>
            <div style={{ display: 'flex', gap: '1rem', alignItems: 'center' }}>
              <label style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', cursor: 'pointer', fontWeight: 600 }}>
                <input
                  type="radio"
                  name="trayecto"
                  checked={tipoTrayecto === 'UNICO'}
                  onChange={() => setTipoTrayecto('UNICO')}
                />
                Solo ida
              </label>
              <label style={{ display: 'flex', alignItems: 'center', gap: '0.4rem', cursor: 'pointer', fontWeight: 600 }}>
                <input
                  type="radio"
                  name="trayecto"
                  checked={tipoTrayecto === 'COMPLETO'}
                  onChange={() => setTipoTrayecto('COMPLETO')}
                />
                Ida y regreso
              </label>
            </div>

            <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))', gap: '0.8rem' }}>
              <div>
                <label style={{ display: 'block', fontSize: '0.85rem', fontWeight: 600, marginBottom: '0.2rem' }}>Origen</label>
                <select
                  className="form-control"
                  value={origenId}
                  onChange={(e) => setOrigenId(Number(e.target.value))}
                  style={{ width: '100%', padding: '0.5rem', borderRadius: '0.4rem', border: '1px solid #cbd5e1' }}
                >
                  <option value={0}>Todos los orígenes</option>
                  {cities.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.nombre} ({c.codigo_pais})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '0.85rem', fontWeight: 600, marginBottom: '0.2rem' }}>Destino</label>
                <select
                  className="form-control"
                  value={destinoId}
                  onChange={(e) => setDestinoId(Number(e.target.value))}
                  style={{ width: '100%', padding: '0.5rem', borderRadius: '0.4rem', border: '1px solid #cbd5e1' }}
                >
                  <option value={0}>Todos los destinos</option>
                  {cities.map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.nombre} ({c.codigo_pais})
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '0.85rem', fontWeight: 600, marginBottom: '0.2rem' }}>Fecha de salida</label>
                <input
                  type="date"
                  className="form-control"
                  value={fechaSalida}
                  onChange={(e) => setFechaSalida(e.target.value)}
                  style={{ width: '100%', padding: '0.5rem', borderRadius: '0.4rem', border: '1px solid #cbd5e1' }}
                />
              </div>

              {tipoTrayecto === 'COMPLETO' && (
                <div>
                  <label style={{ display: 'block', fontSize: '0.85rem', fontWeight: 600, marginBottom: '0.2rem' }}>Fecha de regreso</label>
                  <input
                    type="date"
                    className="form-control"
                    value={fechaRegreso}
                    onChange={(e) => setFechaRegreso(e.target.value)}
                    style={{ width: '100%', padding: '0.5rem', borderRadius: '0.4rem', border: '1px solid #cbd5e1' }}
                  />
                </div>
              )}

              <div>
                <label style={{ display: 'block', fontSize: '0.85rem', fontWeight: 600, marginBottom: '0.2rem' }}>Pasajeros</label>
                <select
                  className="form-control"
                  value={pasajeros}
                  onChange={(e) => setPasajeros(Number(e.target.value))}
                  style={{ width: '100%', padding: '0.5rem', borderRadius: '0.4rem', border: '1px solid #cbd5e1' }}
                >
                  {[1, 2, 3, 4, 5].map((n) => (
                    <option key={n} value={n}>
                      {n} {n === 1 ? 'viajero' : 'viajeros'}
                    </option>
                  ))}
                </select>
              </div>

              <div>
                <label style={{ display: 'block', fontSize: '0.85rem', fontWeight: 600, marginBottom: '0.2rem' }}>Clase</label>
                <select
                  className="form-control"
                  value={clase}
                  onChange={(e) => setClase(e.target.value as 'ECONOMICA' | 'PRIMERA_CLASE')}
                  style={{ width: '100%', padding: '0.5rem', borderRadius: '0.4rem', border: '1px solid #cbd5e1' }}
                >
                  <option value="ECONOMICA">Clase Económica</option>
                  <option value="PRIMERA_CLASE">Primera Clase</option>
                </select>
              </div>
            </div>

            {searchError && (
              <div style={{ color: '#dc2626', fontSize: '0.875rem' }}>{searchError}</div>
            )}

            <button
              type="submit"
              disabled={loading}
              className="btn btn--primary"
              style={{ alignSelf: 'flex-start', padding: '0.6rem 1.8rem', fontSize: '1rem' }}
            >
              {loading ? 'Buscando vuelos...' : '🔍 Buscar vuelos disponibles'}
            </button>
          </form>
        </div>
      </section>

      {/* RESULTADOS DE BÚSQUEDA (CU-05) */}
      {hasSearched && (
        <section className="home-section" style={{ background: '#f8fafc', padding: '2rem 1.5rem', borderRadius: '1rem', margin: '2rem 0' }}>
          <div className="home-section__heading">
            <div>
              <span className="home-eyebrow">Resultados de búsqueda</span>
              <h2>Vuelos disponibles para tu viaje</h2>
            </div>
          </div>

          <div style={{ marginTop: '1.5rem' }}>
            <h3 style={{ fontSize: '1.25rem', marginBottom: '1rem', color: '#0f172a' }}>
              🛫 Vuelos de ida ({vuelosIda.length})
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
                          ${clase === 'PRIMERA_CLASE' ? v.costo_persona_primera : v.costo_persona_economica} COP
                        </div>
                      </div>
                      <Link to="/vuelos" className="btn btn--primary" style={{ padding: '0.4rem 0.8rem', fontSize: '0.85rem' }}>
                        Reservar / Comprar ↗
                      </Link>
                    </div>
                  </div>
                ))}
              </div>
            )}

            {tipoTrayecto === 'COMPLETO' && (
              <div style={{ marginTop: '2.5rem' }}>
                <h3 style={{ fontSize: '1.25rem', marginBottom: '1rem', color: '#0f172a' }}>
                  🛬 Vuelos de regreso ({vuelosRegreso.length})
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
                              ${clase === 'PRIMERA_CLASE' ? v.costo_persona_primera : v.costo_persona_economica} COP
                            </div>
                          </div>
                          <Link to="/vuelos" className="btn btn--primary" style={{ padding: '0.4rem 0.8rem', fontSize: '0.85rem' }}>
                            Reservar / Comprar ↗
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
              <span className="destination-card__arrow">↗</span>
            </article>
          </Link>
          <Link to="/vuelos" style={{ textDecoration: 'none' }}>
            <article className="destination-card destination-card--blue">
              <span className="destination-card__code">BOG</span>
              <div>
                <h3>Bogotá</h3>
                <p>Cultura, gastronomía y negocios</p>
              </div>
              <span className="destination-card__arrow">↗</span>
            </article>
          </Link>
          <Link to="/vuelos" style={{ textDecoration: 'none' }}>
            <article className="destination-card destination-card--purple">
              <span className="destination-card__code">CTG</span>
              <div>
                <h3>Cartagena</h3>
                <p>Sol, playa y arquitectura colonial</p>
              </div>
              <span className="destination-card__arrow">↗</span>
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
          Empezar ahora <span aria-hidden="true">→</span>
        </Link>
      </section>
    </main>
  )
}
