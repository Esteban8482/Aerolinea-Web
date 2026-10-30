import { useCallback, useEffect, useMemo, useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { api, ApiError } from '../api'
import type { Ciudad, Ruta, Vuelo, VueloDetalle } from '../types/flight'

interface FlightsPageProps {
  session: {
    authenticated: boolean
    role: string | null
    is_email_verified: boolean
  }
}

export default function FlightsPage({ session }: FlightsPageProps) {
  const isAdmin = session.authenticated && (session.role === 'ADMINISTRADOR' || session.role === 'ROOT')

  // Catálogos y datos
  const [cities, setCities] = useState<Ciudad[]>([])
  const [routes, setRoutes] = useState<Ruta[]>([])
  const [flights, setFlights] = useState<Vuelo[]>([])
  const [loading, setLoading] = useState(false)
  const [notification, setNotification] = useState<{ type: 'success' | 'error'; message: string } | null>(null)

  // Filtros
  const [filterEstado, setFilterEstado] = useState<string>('')
  const [filterTipo, setFilterTipo] = useState<string>('')
  const [searchTerm, setSearchTerm] = useState<string>('')

  // Modos de vista
  const [view, setView] = useState<'LIST' | 'CREATE' | 'EDIT'>('LIST')
  const [selectedFlight, setSelectedFlight] = useState<VueloDetalle | null>(null)
  const [flightToCancel, setFlightToCancel] = useState<Vuelo | null>(null)

  // Estado formulario creación (CU-01)
  const [createTipo, setCreateTipo] = useState<'NACIONAL' | 'INTERNACIONAL'>('NACIONAL')
  const [createOrigenId, setCreateOrigenId] = useState<number>(0)
  const [createDestinoId, setCreateDestinoId] = useState<number>(0)
  const [createFechaSalida, setCreateFechaSalida] = useState('')
  const [createHoraSalida, setCreateHoraSalida] = useState('')
  const [createCostoEconomica, setCreateCostoEconomica] = useState('180000')
  const [createCostoPrimera, setCreateCostoPrimera] = useState('270000')
  const [createBusy, setCreateBusy] = useState(false)
  const [createError, setCreateError] = useState('')

  // Estado formulario edición (CU-02)
  const [editFechaSalida, setEditFechaSalida] = useState('')
  const [editHoraSalida, setEditHoraSalida] = useState('')
  const [editCostoEconomica, setEditCostoEconomica] = useState('')
  const [editCostoPrimera, setEditCostoPrimera] = useState('')
  const [editBusy, setEditBusy] = useState(false)
  const [editError, setEditError] = useState('')

  // Estado modal cancelación (CU-03)
  const [cancelMotivo, setCancelMotivo] = useState('')
  const [cancelAlternativa, setCancelAlternativa] = useState<'REINTEGRO' | 'REUBICACION'>('REINTEGRO')
  const [cancelBusy, setCancelBusy] = useState(false)
  const [cancelError, setCancelError] = useState('')

  // Cargar catálogos
  useEffect(() => {
    api.get('/flights/cities/').then(setCities).catch(() => {})
    api.get('/flights/routes/').then(setRoutes).catch(() => {})
  }, [])

  // Cargar vuelos
  const loadFlights = useCallback(async () => {
    setLoading(true)
    try {
      const params = new URLSearchParams()
      if (filterEstado) params.append('estado', filterEstado)
      if (filterTipo) params.append('tipo_vuelo', filterTipo)
      const query = params.toString() ? `?${params.toString()}` : ''
      const data = await api.get(`/flights/${query}`)
      setFlights(data)
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : 'Error al cargar vuelos.'
      setNotification({ type: 'error', message: msg })
    } finally {
      setLoading(false)
    }
  }, [filterEstado, filterTipo])

  useEffect(() => {
    loadFlights()
  }, [loadFlights])

  // Filtrado reactivo de ciudades para creación
  const origenesDisponibles = useMemo(() => {
    if (createTipo === 'NACIONAL') {
      return cities.filter((c) => c.es_capital_principal)
    }
    return cities.filter((c) => c.origen_internacional)
  }, [cities, createTipo])

  const destinosDisponibles = useMemo(() => {
    if (createTipo === 'NACIONAL') {
      return cities.filter((c) => c.es_capital_principal && c.id !== createOrigenId)
    }
    return cities.filter((c) => c.destino_internacional)
  }, [cities, createTipo, createOrigenId])

  const rutaSeleccionada = useMemo(() => {
    if (!createOrigenId || !createDestinoId) return null
    return routes.find((r) => r.origen.id === createOrigenId && r.destino.id === createDestinoId)
  }, [routes, createOrigenId, createDestinoId])

  const capacidad = createTipo === 'NACIONAL' ? 150 : 250
  const sillasPrimera = createTipo === 'NACIONAL' ? 25 : 50
  const sillasEconomica = createTipo === 'NACIONAL' ? 125 : 200

  // Filtrado en memoria por búsqueda libre de origen/destino
  const filteredFlights = useMemo(() => {
    if (!searchTerm.trim()) return flights
    const term = searchTerm.toLowerCase().trim()
    return flights.filter(
      (f) =>
        f.codigo_vuelo.toLowerCase().includes(term) ||
        f.origen.toLowerCase().includes(term) ||
        f.destino.toLowerCase().includes(term),
    )
  }, [flights, searchTerm])

  // Manejo de CU-01: Programar Vuelo
  const handleCreateSubmit = async (e: FormEvent) => {
    e.preventDefault()
    if (!createOrigenId || !createDestinoId) {
      setCreateError('Debes seleccionar una ciudad de origen y una de destino.')
      return
    }
    if (!rutaSeleccionada) {
      setCreateError('Ruta no autorizada en el catálogo de rutas activas.')
      return
    }

    setCreateBusy(true)
    setCreateError('')
    try {
      await api.post('/flights/', {
        origen_id: createOrigenId,
        destino_id: createDestinoId,
        fecha_salida: createFechaSalida,
        hora_salida: createHoraSalida.length === 5 ? `${createHoraSalida}:00` : createHoraSalida,
        costo_persona_economica: createCostoEconomica,
        costo_persona_primera: createCostoPrimera || undefined,
      })
      setView('LIST')
      setNotification({
        type: 'success',
        message: '¡Vuelo programado exitosamente (CU-01)! Código de vuelo y sillas generadas.',
      })
      loadFlights()
    } catch (err) {
      if (err instanceof ApiError) {
        setCreateError(err.message)
      } else {
        setCreateError('Error al programar el vuelo.')
      }
    } finally {
      setCreateBusy(false)
    }
  }

  // Manejo de CU-02: Editar Vuelo
  const handleOpenEdit = async (flight: Vuelo) => {
    try {
      const detail: VueloDetalle = await api.get(`/flights/${flight.id}/`)
      setSelectedFlight(detail)
      setEditFechaSalida(detail.fecha_salida)
      setEditHoraSalida(detail.hora_salida.slice(0, 5))
      setEditCostoEconomica(detail.costo_persona_economica)
      setEditCostoPrimera(detail.costo_persona_primera)
      setEditError('')
      setView('EDIT')
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : 'Error al cargar detalle del vuelo.'
      setNotification({ type: 'error', message: msg })
    }
  }

  const handleEditSubmit = async (e: FormEvent) => {
    e.preventDefault()
    if (!selectedFlight) return

    setEditBusy(true)
    setEditError('')
    try {
      await api.patch(`/flights/${selectedFlight.id}/`, {
        fecha_salida: editFechaSalida,
        hora_salida: editHoraSalida.length === 5 ? `${editHoraSalida}:00` : editHoraSalida,
        costo_persona_economica: editCostoEconomica,
        costo_persona_primera: editCostoPrimera,
      })
      setView('LIST')
      setSelectedFlight(null)
      setNotification({
        type: 'success',
        message: '¡Vuelo editado exitosamente (CU-02)! Horarios de llegada recalculados.',
      })
      loadFlights()
    } catch (err) {
      if (err instanceof ApiError) {
        setEditError(err.message)
      } else {
        setEditError('Error al editar el vuelo.')
      }
    } finally {
      setEditBusy(false)
    }
  }

  // Manejo de CU-03: Cancelar Vuelo
  const handleCancelSubmit = async (e: FormEvent) => {
    e.preventDefault()
    if (!flightToCancel) return
    if (!cancelMotivo.trim()) {
      setCancelError('Debes indicar el motivo de la cancelación.')
      return
    }

    setCancelBusy(true)
    setCancelError('')
    try {
      await api.post(`/flights/${flightToCancel.id}/cancel/`, {
        motivo: cancelMotivo.trim(),
        alternativa: cancelAlternativa,
      })
      setFlightToCancel(null)
      setCancelMotivo('')
      setNotification({
        type: 'success',
        message: '¡Vuelo cancelado exitosamente (CU-03)! Notificación oficial y reintegros procesados.',
      })
      loadFlights()
    } catch (err) {
      if (err instanceof ApiError) {
        setCancelError(err.message)
      } else {
        setCancelError('Error al cancelar el vuelo.')
      }
    } finally {
      setCancelBusy(false)
    }
  }

  return (
    <div className="page-shell">
      <div className="page-card" style={{ maxWidth: '1100px' }}>
        <header className="page-card__header">
          <h1 className="page-card__title">
            {view === 'CREATE'
              ? 'Programar nuevo vuelo (CU-01)'
              : view === 'EDIT'
                ? `Editar vuelo ${selectedFlight?.codigo_vuelo} (CU-02)`
                : 'Vuelos y Rutas'}
          </h1>
          <p className="page-card__subtitle">
            {view === 'CREATE'
              ? 'Configure los parámetros de la ruta, salida y tarifas para habilitar la venta de cupos.'
              : view === 'EDIT'
                ? 'Ajuste fechas, horarios y costos con recálculo automático de arribos.'
                : 'Consulta de disponibilidad e itinerarios de vuelos comerciales.'}
          </p>
        </header>

        {notification && (
          <div
            className={`alert ${notification.type === 'success' ? 'alert--success' : 'alert--error'}`}
            style={{ marginBottom: '1.5rem', display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}
          >
            <span>{notification.message}</span>
            <button
              type="button"
              onClick={() => setNotification(null)}
              style={{ background: 'transparent', border: 'none', cursor: 'pointer', fontWeight: 700 }}
            >
              ✕
            </button>
          </div>
        )}

        {/* ============================================================
            VISTA: CREACIÓN (CU-01)
            ============================================================ */}
        {view === 'CREATE' && (
          <form onSubmit={handleCreateSubmit} noValidate>
            {createError && (
              <div className="alert alert--error" style={{ marginBottom: '1.25rem' }}>
                <span className="alert__body">{createError}</span>
              </div>
            )}

            <div className="admin-forms-grid">
              <div className="admin-card-panel">
                <div className="form-group" style={{ marginBottom: '1rem' }}>
                  <label className="form-label" htmlFor="create-tipo">
                    Tipo de vuelo<span className="form-label__required">*</span>
                  </label>
                  <select
                    id="create-tipo"
                    className="form-select"
                    value={createTipo}
                    onChange={(e) => {
                      setCreateTipo(e.target.value as 'NACIONAL' | 'INTERNACIONAL')
                      setCreateOrigenId(0)
                      setCreateDestinoId(0)
                    }}
                  >
                    <option value="NACIONAL">Nacional (Capitales principales)</option>
                    <option value="INTERNACIONAL">Internacional (Rutas directas autorizadas)</option>
                  </select>
                </div>

                <div className="form-group" style={{ marginBottom: '1rem' }}>
                  <label className="form-label" htmlFor="create-origen">
                    Ciudad de origen<span className="form-label__required">*</span>
                  </label>
                  <select
                    id="create-origen"
                    className="form-select"
                    value={createOrigenId || ''}
                    onChange={(e) => setCreateOrigenId(Number(e.target.value))}
                    required
                  >
                    <option value="">Seleccione origen...</option>
                    {origenesDisponibles.map((c) => (
                      <option key={c.id} value={c.id}>
                        {c.nombre} ({c.codigo_pais})
                      </option>
                    ))}
                  </select>
                </div>

                <div className="form-group" style={{ marginBottom: '1rem' }}>
                  <label className="form-label" htmlFor="create-destino">
                    Ciudad de destino<span className="form-label__required">*</span>
                  </label>
                  <select
                    id="create-destino"
                    className="form-select"
                    value={createDestinoId || ''}
                    onChange={(e) => setCreateDestinoId(Number(e.target.value))}
                    required
                  >
                    <option value="">Seleccione destino...</option>
                    {destinosDisponibles.map((c) => (
                      <option key={c.id} value={c.id}>
                        {c.nombre} ({c.codigo_pais})
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="admin-card-panel">
                <div className="form-group" style={{ marginBottom: '1rem' }}>
                  <label className="form-label" htmlFor="create-fecha">
                    Fecha de salida (hora local de origen)<span className="form-label__required">*</span>
                  </label>
                  <input
                    id="create-fecha"
                    type="date"
                    className="form-input"
                    value={createFechaSalida}
                    onChange={(e) => setCreateFechaSalida(e.target.value)}
                    required
                  />
                </div>

                <div className="form-group" style={{ marginBottom: '1rem' }}>
                  <label className="form-label" htmlFor="create-hora">
                    Hora de salida (hora local de origen)<span className="form-label__required">*</span>
                  </label>
                  <input
                    id="create-hora"
                    type="time"
                    className="form-input"
                    value={createHoraSalida}
                    onChange={(e) => setCreateHoraSalida(e.target.value)}
                    required
                  />
                </div>

                <div className="form-group" style={{ marginBottom: '1rem' }}>
                  <label className="form-label" htmlFor="create-costo-eco">
                    Tarifa clase económica (COP)<span className="form-label__required">*</span>
                  </label>
                  <input
                    id="create-costo-eco"
                    type="number"
                    min="1000"
                    step="1000"
                    className="form-input"
                    value={createCostoEconomica}
                    onChange={(e) => {
                      const val = e.target.value
                      setCreateCostoEconomica(val)
                      if (val && !isNaN(Number(val))) {
                        setCreateCostoPrimera((Number(val) * 1.5).toFixed(2))
                      }
                    }}
                    required
                  />
                </div>

                <div className="form-group" style={{ marginBottom: '1rem' }}>
                  <label className="form-label" htmlFor="create-costo-prim">
                    Tarifa primera clase (COP)<span className="form-label__required">*</span>
                  </label>
                  <input
                    id="create-costo-prim"
                    type="number"
                    min="1000"
                    step="1000"
                    className="form-input"
                    value={createCostoPrimera}
                    onChange={(e) => setCreateCostoPrimera(e.target.value)}
                    required
                  />
                </div>
              </div>
            </div>

            <div className="flight-calc-box">
              <div className="flight-calc-box__title">⚙️ Calculado automáticamente por el sistema</div>
              <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(220px, 1fr))', gap: '1rem' }}>
                <div>
                  <strong>Código de vuelo:</strong>
                  <p style={{ margin: 0 }}>Autogenerado (XX0001 - XX9999)</p>
                </div>
                <div>
                  <strong>Duración estimada:</strong>
                  <p style={{ margin: 0 }}>
                    {rutaSeleccionada ? `${rutaSeleccionada.duracion_min} minutos` : 'Ruta no seleccionada'}
                  </p>
                </div>
                <div>
                  <strong>Capacidad total:</strong>
                  <p style={{ margin: 0 }}>{capacidad} pasajeros</p>
                </div>
                <div>
                  <strong>Sillas primera clase:</strong>
                  <p style={{ margin: 0 }}>Sillas 1 a {sillasPrimera}</p>
                </div>
                <div>
                  <strong>Sillas económica:</strong>
                  <p style={{ margin: 0 }}>
                    Sillas {sillasPrimera + 1} a {capacidad} ({sillasEconomica} cupos)
                  </p>
                </div>
                <div>
                  <strong>Noticia oficial:</strong>
                  <p style={{ margin: 0 }}>Publicación automática alusiva al vuelo</p>
                </div>
              </div>
            </div>

            <div style={{ display: 'flex', gap: '1rem', marginTop: '1.5rem' }}>
              <button type="submit" className="btn btn--primary" disabled={createBusy}>
                {createBusy ? 'Guardando vuelo...' : 'Guardar y programar vuelo'}
              </button>
              <button
                type="button"
                className="btn btn--secondary"
                onClick={() => setView('LIST')}
                disabled={createBusy}
              >
                Cancelar
              </button>
            </div>
          </form>
        )}

        {/* ============================================================
            VISTA: EDICIÓN (CU-02)
            ============================================================ */}
        {view === 'EDIT' && selectedFlight && (
          <form onSubmit={handleEditSubmit} noValidate>
            {editError && (
              <div className="alert alert--error" style={{ marginBottom: '1.25rem' }}>
                <span className="alert__body">{editError}</span>
              </div>
            )}

            <div className="admin-forms-grid">
              <div className="admin-card-panel">
                <div className="form-group" style={{ marginBottom: '1rem' }}>
                  <label className="form-label">Código de vuelo (inmutable)</label>
                  <input className="form-input" disabled value={selectedFlight.codigo_vuelo} />
                </div>
                <div className="form-group" style={{ marginBottom: '1rem' }}>
                  <label className="form-label">Ruta (inmutable)</label>
                  <input
                    className="form-input"
                    disabled
                    value={`${selectedFlight.ruta.origen.nombre} → ${selectedFlight.ruta.destino.nombre} (${selectedFlight.tipo_vuelo})`}
                  />
                </div>
                <div className="form-group" style={{ marginBottom: '1rem' }}>
                  <label className="form-label">Estado actual</label>
                  <input className="form-input" disabled value={selectedFlight.estado} />
                </div>
              </div>

              <div className="admin-card-panel">
                <div className="form-group" style={{ marginBottom: '1rem' }}>
                  <label className="form-label" htmlFor="edit-fecha">
                    Fecha de salida (hora local de origen)<span className="form-label__required">*</span>
                  </label>
                  <input
                    id="edit-fecha"
                    type="date"
                    className="form-input"
                    value={editFechaSalida}
                    onChange={(e) => setEditFechaSalida(e.target.value)}
                    required
                  />
                </div>

                <div className="form-group" style={{ marginBottom: '1rem' }}>
                  <label className="form-label" htmlFor="edit-hora">
                    Hora de salida (hora local de origen)<span className="form-label__required">*</span>
                  </label>
                  <input
                    id="edit-hora"
                    type="time"
                    className="form-input"
                    value={editHoraSalida}
                    onChange={(e) => setEditHoraSalida(e.target.value)}
                    required
                  />
                </div>

                <div className="form-group" style={{ marginBottom: '1rem' }}>
                  <label className="form-label" htmlFor="edit-costo-eco">
                    Tarifa económica (COP)<span className="form-label__required">*</span>
                  </label>
                  <input
                    id="edit-costo-eco"
                    type="number"
                    min="1000"
                    step="1000"
                    className="form-input"
                    value={editCostoEconomica}
                    onChange={(e) => setEditCostoEconomica(e.target.value)}
                    required
                  />
                </div>

                <div className="form-group" style={{ marginBottom: '1rem' }}>
                  <label className="form-label" htmlFor="edit-costo-prim">
                    Tarifa primera clase (COP)<span className="form-label__required">*</span>
                  </label>
                  <input
                    id="edit-costo-prim"
                    type="number"
                    min="1000"
                    step="1000"
                    className="form-input"
                    value={editCostoPrimera}
                    onChange={(e) => setEditCostoPrimera(e.target.value)}
                    required
                  />
                </div>
              </div>
            </div>

            <p className="form-hint" style={{ margin: '1rem 0' }}>
              ℹ️ La fecha y hora de llegada se recalcularán automáticamente en la hora local del destino al confirmar los cambios.
            </p>

            <div style={{ display: 'flex', gap: '1rem', marginTop: '1.5rem' }}>
              <button type="submit" className="btn btn--primary" disabled={editBusy}>
                {editBusy ? 'Guardando cambios...' : 'Guardar cambios'}
              </button>
              <button
                type="button"
                className="btn btn--secondary"
                onClick={() => {
                  setView('LIST')
                  setSelectedFlight(null)
                }}
                disabled={editBusy}
              >
                Cancelar
              </button>
            </div>
          </form>
        )}

        {/* ============================================================
            VISTA: LISTA DE VUELOS (PÚBLICO + ACCIONES ADMIN)
            ============================================================ */}
        {view === 'LIST' && (
          <>
            <div className="flight-controls-bar" style={{ alignItems: 'flex-end' }}>
              <div className="flight-filters" style={{ alignItems: 'flex-end' }}>
                <div className="form-group" style={{ margin: 0 }}>
                  <label htmlFor="flight-search" className="form-label" style={{ fontSize: '0.85rem', marginBottom: '0.25rem' }}>
                    Buscar ruta o código
                  </label>
                  <input
                    id="flight-search"
                    type="text"
                    className="form-input"
                    style={{ width: '220px', padding: '0.5rem 0.75rem' }}
                    placeholder="Buscar origen o destino..."
                    value={searchTerm}
                    onChange={(e) => setSearchTerm(e.target.value)}
                  />
                </div>

                <div className="form-group" style={{ margin: 0 }}>
                  <label htmlFor="filter-estado" className="form-label" style={{ fontSize: '0.85rem', marginBottom: '0.25rem' }}>
                    Estado
                  </label>
                  <select
                    id="filter-estado"
                    className="form-select"
                    style={{ width: '160px', padding: '0.5rem 0.75rem' }}
                    value={filterEstado}
                    onChange={(e) => setFilterEstado(e.target.value)}
                  >
                    <option value="">Todos</option>
                    <option value="PROGRAMADO">Programado</option>
                    <option value="REALIZADO">Realizado</option>
                    <option value="CANCELADO">Cancelado</option>
                  </select>
                </div>

                <div className="form-group" style={{ margin: 0 }}>
                  <label htmlFor="filter-tipo" className="form-label" style={{ fontSize: '0.85rem', marginBottom: '0.25rem' }}>
                    Tipo de vuelo
                  </label>
                  <select
                    id="filter-tipo"
                    className="form-select"
                    style={{ width: '160px', padding: '0.5rem 0.75rem' }}
                    value={filterTipo}
                    onChange={(e) => setFilterTipo(e.target.value)}
                  >
                    <option value="">Todos</option>
                    <option value="NACIONAL">Nacional</option>
                    <option value="INTERNACIONAL">Internacional</option>
                  </select>
                </div>
              </div>

              {isAdmin && (
                <button type="button" className="btn btn--primary" onClick={() => setView('CREATE')}>
                  + Programar nuevo vuelo (CU-01)
                </button>
              )}
            </div>

            {loading ? (
              <div style={{ padding: '3rem', textAlign: 'center', color: 'var(--color-text-secondary)' }}>
                Cargando itinerarios de vuelos...
              </div>
            ) : filteredFlights.length === 0 ? (
              <div style={{ padding: '3rem', textAlign: 'center', color: 'var(--color-text-secondary)' }}>
                No se encontraron vuelos que coincidan con los criterios seleccionados.
              </div>
            ) : (
              <div className="table-wrap">
                <table className="admin-table">
                  <thead>
                    <tr>
                      <th>Código</th>
                      <th>Tipo</th>
                      <th>Ruta</th>
                      <th>Salida</th>
                      <th>Llegada</th>
                      <th>Estado</th>
                      <th>Cupos</th>
                      <th>Tarifa Económica</th>
                      {isAdmin && <th>Acciones</th>}
                    </tr>
                  </thead>
                  <tbody>
                    {filteredFlights.map((f) => {
                      const isProgramado = f.estado === 'PROGRAMADO'
                      const badgeClass =
                        f.estado === 'PROGRAMADO'
                          ? 'badge--info'
                          : f.estado === 'REALIZADO'
                            ? 'badge--success'
                            : 'badge--error'

                      return (
                        <tr key={f.id}>
                          <td>
                            <strong>{f.codigo_vuelo}</strong>
                          </td>
                          <td>{f.tipo_vuelo}</td>
                          <td>
                            <strong>{f.origen}</strong> → <strong>{f.destino}</strong>
                          </td>
                          <td>
                            {f.fecha_salida} <br />
                            <small style={{ color: 'var(--color-text-secondary)' }}>{f.hora_salida}</small>
                          </td>
                          <td>
                            {f.fecha_llegada} <br />
                            <small style={{ color: 'var(--color-text-secondary)' }}>{f.hora_llegada}</small>
                          </td>
                          <td>
                            <span className={`badge ${badgeClass}`}>{f.estado}</span>
                          </td>
                          <td>
                            {f.cupos_disponibles_economica + f.cupos_disponibles_primera} / {f.capacidad_total}
                          </td>
                          <td>${Number(f.costo_persona_economica).toLocaleString('es-CO')}</td>
                          {isAdmin && (
                            <td>
                              {isProgramado ? (
                                <div style={{ display: 'flex', gap: '0.5rem' }}>
                                  <button
                                    type="button"
                                    className="btn btn--secondary"
                                    style={{ padding: '0.3rem 0.6rem', fontSize: '0.85rem' }}
                                    onClick={() => handleOpenEdit(f)}
                                  >
                                    Editar
                                  </button>
                                  <button
                                    type="button"
                                    className="btn btn--danger"
                                    style={{ padding: '0.3rem 0.6rem', fontSize: '0.85rem' }}
                                    onClick={() => {
                                      setFlightToCancel(f)
                                      setCancelMotivo('')
                                      setCancelError('')
                                    }}
                                  >
                                    Cancelar
                                  </button>
                                </div>
                              ) : (
                                <span style={{ color: 'var(--color-text-secondary)', fontSize: '0.85rem' }}>—</span>
                              )}
                            </td>
                          )}
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
            )}
          </>
        )}
      </div>

      {/* ============================================================
          MODAL: CANCELACIÓN DE VUELO (CU-03)
          ============================================================ */}
      {flightToCancel && (
        <div className="modal-backdrop" role="dialog" aria-modal="true">
          <div className="modal-box">
            <h2 className="modal-box__title">¿Cancelar vuelo {flightToCancel.codigo_vuelo}? (CU-03)</h2>

            <div className="flight-details-summary">
              <p>
                <strong>Ruta:</strong> {flightToCancel.origen} → {flightToCancel.destino} ({flightToCancel.tipo_vuelo})
              </p>
              <p>
                <strong>Salida programada:</strong> {flightToCancel.fecha_salida} a las {flightToCancel.hora_salida}
              </p>
              <p>
                <strong>Cupos ocupados a proteger:</strong>{' '}
                {flightToCancel.capacidad_total -
                  (flightToCancel.cupos_disponibles_economica + flightToCancel.cupos_disponibles_primera)}
              </p>
            </div>

            {cancelError && (
              <div className="alert alert--error" style={{ marginBottom: '1.25rem' }}>
                <span className="alert__body">{cancelError}</span>
              </div>
            )}

            <form onSubmit={handleCancelSubmit} noValidate>
              <div className="form-group" style={{ marginBottom: '1.25rem' }}>
                <label className="form-label" htmlFor="cancel-motivo">
                  Motivo de la cancelación<span className="form-label__required">*</span>
                </label>
                <textarea
                  id="cancel-motivo"
                  className="form-input"
                  rows={3}
                  placeholder="Detalle el motivo técnico, meteorológico u operacional que justifica la cancelación..."
                  value={cancelMotivo}
                  onChange={(e) => setCancelMotivo(e.target.value)}
                  required
                />
              </div>

              <div className="form-group" style={{ marginBottom: '1.5rem' }}>
                <label className="form-label">Alternativa aplicable para los pasajeros afectados:</label>
                <div style={{ display: 'flex', flexDirection: 'column', gap: '0.5rem', marginTop: '0.5rem' }}>
                  <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer' }}>
                    <input
                      type="radio"
                      name="cancel-alternativa"
                      value="REINTEGRO"
                      checked={cancelAlternativa === 'REINTEGRO'}
                      onChange={() => setCancelAlternativa('REINTEGRO')}
                    />
                    <span>
                      <strong>Reintegro directo</strong> a la billetera virtual del comprador (Recomendado)
                    </span>
                  </label>
                  <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer' }}>
                    <input
                      type="radio"
                      name="cancel-alternativa"
                      value="REUBICACION"
                      checked={cancelAlternativa === 'REUBICACION'}
                      onChange={() => setCancelAlternativa('REUBICACION')}
                    />
                    <span>
                      <strong>Reubicación</strong> en el próximo vuelo disponible de la misma ruta (o reintegro si no hay cupos)
                    </span>
                  </label>
                </div>
              </div>

              <div style={{ display: 'flex', gap: '1rem', justifyContent: 'flex-end' }}>
                <button
                  type="button"
                  className="btn btn--secondary"
                  onClick={() => setFlightToCancel(null)}
                  disabled={cancelBusy}
                >
                  Volver
                </button>
                <button type="submit" className="btn btn--danger" disabled={cancelBusy}>
                  {cancelBusy ? 'Cancelando vuelo...' : 'Confirmar cancelación'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}
    </div>
  )
}

