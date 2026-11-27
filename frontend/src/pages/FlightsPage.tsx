import CatalogueSelect from '../components/CatalogueSelect'
import { useCallback, useEffect, useMemo, useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { api, ApiError } from '../api'
import CancellationPanel from '../components/CancellationPanel'
import FlightCitySelect from '../components/FlightCitySelect'
import type { Ciudad, FlightSearchResult, Ruta, Vuelo, VueloDetalle } from '../types/flight'
import ColumnFilter from '../components/ColumnFilter'
import BookingModal from '../components/BookingModal'
import CatalogPage from './CatalogPage'

interface FlightsPageProps {
  session: {
    authenticated: boolean
    role: string | null
    is_email_verified: boolean
  }
}

export default function FlightsPage({ session }: FlightsPageProps) {
  const isAdmin = session.authenticated && session.role === 'ADMINISTRADOR'

  // Catálogos y datos
  const [panelFlightId, setPanelFlightId] = useState<number | null>(null)
  const [cities, setCities] = useState<Ciudad[]>([])
  const [routes, setRoutes] = useState<Ruta[]>([])
  const [flights, setFlights] = useState<Vuelo[]>([])
  const [loading, setLoading] = useState(false)
  const [notification, setNotification] = useState<{ type: 'success' | 'error'; message: string } | null>(null)

  // Filtros
  const [filterEstado, setFilterEstado] = useState<string>('')
  const [filterTipo, setFilterTipo] = useState<string>('')
  const [searchTerm, setSearchTerm] = useState<string>('')

  // Búsqueda interactiva (HU-005) y Catálogo por Ciudad (HU-006)
  const [searchTipoTrayecto, setSearchTipoTrayecto] = useState<'UNICO' | 'COMPLETO'>('UNICO')
  const [searchOrigenId, setSearchOrigenId] = useState<number | ''>('')
  const [searchDestinoId, setSearchDestinoId] = useState<number | ''>('')
  const [searchFechaSalida, setSearchFechaSalida] = useState('')
  const [searchFechaRegreso, setSearchFechaRegreso] = useState('')
  const [searchPasajeros, setSearchPasajeros] = useState<number>(1)
  const [searchClase, setSearchClase] = useState<string>('')
  const [searchMaxPrecio, setSearchMaxPrecio] = useState<string>('')
  const [searchCityOriginId, setSearchCityOriginId] = useState<number | ''>('')
  const [searchResults, setSearchResults] = useState<FlightSearchResult | null>(null)
  const [searching, setSearching] = useState(false)
  const [searchError, setSearchError] = useState('')

  // Estado para BookingModal (HU-012, HU-013)
  const [bookingFlight, setBookingFlight] = useState<Vuelo | null>(null)
  const [bookingFlightRegreso, setBookingFlightRegreso] = useState<Vuelo | null>(null)
  const [bookingClase, setBookingClase] = useState<'ECONOMICA' | 'PRIMERA_CLASE'>('ECONOMICA')

  // Modos de vista
  const [view, setView] = useState<'LIST' | 'CREATE' | 'EDIT'>('LIST')
  // Pestañas de la ventana unificada: 'PUBLIC' (lo que ve el cliente) y
  // 'ADMIN' (gestión: programar, editar, cancelar y catálogo de rutas).
  const [tab, setTab] = useState<'PUBLIC' | 'ADMIN'>('PUBLIC')
  const effectiveTab = isAdmin ? tab : 'PUBLIC'
  const [selectedFlight, setSelectedFlight] = useState<VueloDetalle | null>(null)
  const [flightToCancel, setFlightToCancel] = useState<Vuelo | null>(null)

  // Estado formulario creación
  const [createTipo, setCreateTipo] = useState<'NACIONAL' | 'INTERNACIONAL'>('NACIONAL')
  const [createOrigenId, setCreateOrigenId] = useState<number>(0)
  const [createDestinoId, setCreateDestinoId] = useState<number>(0)
  const [createFechaSalida, setCreateFechaSalida] = useState('')
  const [createHoraSalida, setCreateHoraSalida] = useState('')
  const [createCostoEconomica, setCreateCostoEconomica] = useState('180000')
  const [createCostoPrimera, setCreateCostoPrimera] = useState('270000')
  const [createBusy, setCreateBusy] = useState(false)
  const [createError, setCreateError] = useState('')

  // Estado formulario edición
  const [editFechaSalida, setEditFechaSalida] = useState('')
  const [editHoraSalida, setEditHoraSalida] = useState('')
  const [editCostoEconomica, setEditCostoEconomica] = useState('')
  const [editCostoPrimera, setEditCostoPrimera] = useState('')
  const [editMotivo, setEditMotivo] = useState('')
  const [editBusy, setEditBusy] = useState(false)
  const [editError, setEditError] = useState('')

  // Estado modal cancelación
  const [cancelMotivo, setCancelMotivo] = useState('')
  const [cancelBusy, setCancelBusy] = useState(false)
  const [cancelError, setCancelError] = useState('')

  // Estado modal de promoción
  const [promotionFlight, setPromotionFlight] = useState<Vuelo | null>(null)
  const [promotionClase, setPromotionClase] = useState<'ECONOMICA' | 'PRIMERA_CLASE'>('ECONOMICA')
  const [promotionPrice, setPromotionPrice] = useState('')
  const [promotionStartsImmediately, setPromotionStartsImmediately] = useState(true)
  const [promotionStartsAt, setPromotionStartsAt] = useState('')
  const [promotionEndsAt, setPromotionEndsAt] = useState('')
  const [promotionBusy, setPromotionBusy] = useState(false)
  const [promotionError, setPromotionError] = useState('')

  // Cargar catálogos: al montar y cada vez que la ventana recupera el foco,
  // para que las rutas creadas en el Catálogo aparezcan sin recargar a mano.
  const loadCatalogos = useCallback(() => {
    api.get('/flights/cities/').then(setCities).catch(() => {})
    api.get('/flights/routes/').then(setRoutes).catch(() => {})
  }, [])

  useEffect(() => {
    loadCatalogos()
    window.addEventListener('focus', loadCatalogos)
    return () => window.removeEventListener('focus', loadCatalogos)
  }, [loadCatalogos])

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
    window.addEventListener('focus', loadFlights)
    return () => window.removeEventListener('focus', loadFlights)
  }, [loadFlights])

  // Lo que ve el visitante (y el admin en la pestaña "Disponibles"):
  // solo vuelos programados con salida futura (HU-005/HU-006).
  // La pestaña "Gestión" muestra el listado completo para poder administrarlo.
  const displayFlights = useMemo(() => {
    if (effectiveTab === 'ADMIN') return flights
    const now = new Date()
    return flights.filter(
      (v) => v.estado === 'PROGRAMADO' && new Date(v.salida_utc) > now,
    )
  }, [flights, effectiveTab])

  // Catálogo de rutas activas
  const activeRoutes = useMemo(() => routes.filter((r) => r.activa !== false), [routes])

  // Rutas disponibles según el tipo de vuelo seleccionado
  const tipoRoutes = useMemo(() => {
    return activeRoutes.filter((r) => r.tipo_vuelo === createTipo)
  }, [activeRoutes, createTipo])

  // Orígenes disponibles: reactivo a la selección de destino y catálogo de rutas
  const origenesDisponibles = useMemo(() => {
    const candidateRoutes = createDestinoId
      ? tipoRoutes.filter((r) => r.destino.id === createDestinoId)
      : tipoRoutes
    const map = new Map<number, Ciudad>()
    for (const r of candidateRoutes) {
      if (!map.has(r.origen.id)) {
        map.set(r.origen.id, r.origen)
      }
    }
    return Array.from(map.values()).sort((a, b) => a.nombre.localeCompare(b.nombre))
  }, [tipoRoutes, createDestinoId])

  // Destinos disponibles: reactivo a la selección de origen y catálogo de rutas
  const destinosDisponibles = useMemo(() => {
    const candidateRoutes = createOrigenId
      ? tipoRoutes.filter((r) => r.origen.id === createOrigenId)
      : tipoRoutes
    const map = new Map<number, Ciudad>()
    for (const r of candidateRoutes) {
      if (!map.has(r.destino.id)) {
        map.set(r.destino.id, r.destino)
      }
    }
    return Array.from(map.values()).sort((a, b) => a.nombre.localeCompare(b.nombre))
  }, [tipoRoutes, createOrigenId])

  const rutaSeleccionada = useMemo(() => {
    if (!createOrigenId || !createDestinoId) return null
    return activeRoutes.find((r) => r.origen.id === createOrigenId && r.destino.id === createDestinoId)
  }, [activeRoutes, createOrigenId, createDestinoId])

  const capacidad = createTipo === 'NACIONAL' ? 150 : 250
  const sillasPrimera = createTipo === 'NACIONAL' ? 25 : 50
  const sillasEconomica = createTipo === 'NACIONAL' ? 125 : 200

  // Filtrado en memoria por búsqueda libre de origen/destino
  const filteredFlights = useMemo(() => {
    if (!searchTerm.trim()) return displayFlights
    const term = searchTerm.toLowerCase().trim()
    return displayFlights.filter(
      (f) =>
        f.codigo_vuelo.toLowerCase().includes(term) ||
        f.origen.toLowerCase().includes(term) ||
        f.destino.toLowerCase().includes(term),
    )
  }, [displayFlights, searchTerm])

  // Ejecución de búsqueda de vuelos (HU-005)
  const handleExecuteSearch = async (e?: FormEvent) => {
    if (e) e.preventDefault()
    if (searchOrigenId && searchDestinoId && searchOrigenId === searchDestinoId) {
      setSearchError('El origen y el destino no pueden ser la misma ciudad.')
      return
    }

    setSearching(true)
    setSearchError('')
    try {
      const params = new URLSearchParams()
      if (searchOrigenId) params.append('origen_id', String(searchOrigenId))
      if (searchDestinoId) params.append('destino_id', String(searchDestinoId))
      if (searchFechaSalida) params.append('fecha_salida', searchFechaSalida)
      if (searchTipoTrayecto === 'COMPLETO' && searchFechaRegreso) {
        params.append('fecha_regreso', searchFechaRegreso)
      }
      params.append('tipo_trayecto', searchTipoTrayecto)
      params.append('pasajeros', String(searchPasajeros))
      if (searchClase) params.append('clase', searchClase)
      if (searchMaxPrecio) params.append('precio_max', searchMaxPrecio)

      const data = await api.get(`/flights/search/?${params.toString()}`)
      setSearchResults(data)
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : 'Error al buscar vuelos.'
      setSearchError(msg)
    } finally {
      setSearching(false)
    }
  }

  const handleClearSearch = () => {
    setSearchOrigenId('')
    setSearchDestinoId('')
    setSearchFechaSalida('')
    setSearchFechaRegreso('')
    setSearchPasajeros(1)
    setSearchClase('')
    setSearchMaxPrecio('')
    setSearchCityOriginId('')
    setSearchResults(null)
    setSearchError('')
  }

  // Lista visible: según búsqueda activa (HU-005), catálogo por ciudad (HU-006) o tabla general
  const currentList = useMemo(() => {
    if (effectiveTab === 'ADMIN') return filteredFlights

    if (searchResults !== null) {
      return searchResults.vuelos_ida
    }

    if (searchCityOriginId) {
      const city = cities.find((c) => c.id === searchCityOriginId)
      if (!city) return displayFlights
      return displayFlights.filter((f) => f.origen === city.nombre)
    }

    return filteredFlights
  }, [effectiveTab, filteredFlights, searchResults, searchCityOriginId, cities, displayFlights])

  // Manejo de: Programar Vuelo
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
        message: '¡Vuelo programado exitosamente! Código de vuelo y sillas generadas.',
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

  // Manejo de: Editar Vuelo
  const handleOpenEdit = async (flight: Vuelo) => {
    try {
      const detail: VueloDetalle = await api.get(`/flights/${flight.id}/`)
      setSelectedFlight(detail)
      setEditFechaSalida(detail.fecha_salida)
      setEditHoraSalida(detail.hora_salida.slice(0, 5))
      setEditCostoEconomica(detail.costo_persona_economica)
      setEditCostoPrimera(detail.costo_persona_primera)
      setEditMotivo('')
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
    if (!editMotivo.trim()) {
      setEditError('Debes indicar el motivo de la modificación.')
      setEditBusy(false)
      return
    }
    try {
      await api.patch(`/flights/${selectedFlight.id}/`, {
        motivo: editMotivo.trim(),
        fecha_salida: editFechaSalida,
        hora_salida: editHoraSalida.length === 5 ? `${editHoraSalida}:00` : editHoraSalida,
        costo_persona_economica: editCostoEconomica,
        costo_persona_primera: editCostoPrimera,
      })
      setView('LIST')
      setSelectedFlight(null)
      setNotification({
        type: 'success',
        message: '¡Vuelo editado exitosamente! Horarios de llegada recalculados.',
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

  // Manejo de: Cancelar Vuelo
  const handleCancelSubmit = async (e: FormEvent) => {
    e.preventDefault()
    if (!flightToCancel) return
    if (!cancelMotivo.trim()) {
      setCancelError('Debes indicar el motivo de la cancelación.')
      return
    }

    try {
      const impact = await api.get(`/sales/flights/${flightToCancel.id}/cancellation-panel/`)
      if (!window.confirm(`Primera confirmación: cancelar ${flightToCancel.codigo_vuelo}, ${flightToCancel.origen} → ${flightToCancel.destino}, salida ${new Date(flightToCancel.salida_utc).toLocaleString('es-CO')}. Afecta ${impact.passengers} pasajeros, ${impact.purchases} compras y ${impact.reservations} reservas. ¿Continuar?`)) return
      if (!window.confirm('Confirmación final: se liberarán las reservas y se invalidarán los pasabordos. Cada comprador decidirá reubicación o reembolso. ¿Cancelar definitivamente el vuelo?')) return
    } catch { setCancelError('No se pudo consultar el impacto. Reintenta.'); return }
    setCancelBusy(true)
    setCancelError('')
    try {
      await api.post(`/flights/${flightToCancel.id}/cancel/`, {
        motivo: cancelMotivo.trim(),
        confirmed: true,
      })
      setFlightToCancel(null)
      setCancelMotivo('')
      setNotification({
        type: 'success',
        message: 'Vuelo cancelado. Se notificó la gestión pendiente a los compradores; no se realizaron reembolsos automáticos.',
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

  const handlePromotionSubmit = async (e: FormEvent) => {
    e.preventDefault()
    if (!promotionFlight) return

    const basePrice =
      promotionClase === 'ECONOMICA'
        ? Number(promotionFlight.costo_persona_economica)
        : Number(promotionFlight.costo_persona_primera)
    const start = promotionStartsImmediately ? new Date() : new Date(promotionStartsAt)
    const end = new Date(promotionEndsAt)
    const departure = new Date(promotionFlight.salida_utc)

    if (Number(promotionPrice) <= 0 || Number(promotionPrice) >= basePrice) {
      setPromotionError('El precio promocional debe ser positivo y menor que la tarifa base.')
      return
    }
    if (
      Number.isNaN(start.getTime()) ||
      Number.isNaN(end.getTime()) ||
      (!promotionStartsImmediately && start <= new Date()) ||
      end <= start ||
      end > departure
    ) {
      setPromotionError('Indica un periodo futuro válido que finalice antes de la salida del vuelo.')
      return
    }

    setPromotionBusy(true)
    setPromotionError('')
    try {
      await api.post(`/sales/flights/${promotionFlight.id}/promotions/`, {
        clase: promotionClase,
        price: promotionPrice,
        starts_at: start.toISOString(),
        ends_at: end.toISOString(),
      })
      setPromotionFlight(null)
      setNotification({
        type: 'success',
        message: `Promoción creada para el vuelo ${promotionFlight.codigo_vuelo}.`,
      })
      loadFlights()
    } catch (err) {
      setPromotionError(
        err instanceof ApiError ? err.message : 'No fue posible crear la promoción.',
      )
    } finally {
      setPromotionBusy(false)
    }
  }

  return (
    <div className="page-shell">
      <div className="page-card" style={{ maxWidth: '1100px' }}>
        <header className="page-card__header">
          <h1 className="page-card__title">
            {view === 'CREATE'
              ? 'Programar nuevo vuelo'
              : view === 'EDIT'
                ? `Editar vuelo ${selectedFlight?.codigo_vuelo}`
                : 'Vuelos'}
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

        {panelFlightId && isAdmin && <div className="form-container"><button type="button" onClick={() => setPanelFlightId(null)}>Cerrar consulta</button><CancellationPanel flightId={panelFlightId} /></div>}
      {/* ============================================================
            VISTA: CREACIÓN
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
                    onChange={(e) => {
                      const nextOrigenId = Number(e.target.value)
                      setCreateOrigenId(nextOrigenId)
                      if (nextOrigenId) {
                        const availableDests = tipoRoutes.filter((r) => r.origen.id === nextOrigenId)
                        if (availableDests.length === 1) {
                          setCreateDestinoId(availableDests[0].destino.id)
                        } else if (createDestinoId && !availableDests.some((r) => r.destino.id === createDestinoId)) {
                          setCreateDestinoId(0)
                        }
                      }
                    }}
                    required
                  >
                    <option value="">
                      {origenesDisponibles.length === 0
                        ? 'No hay orígenes con rutas activas'
                        : 'Seleccione origen...'}
                    </option>
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
                    onChange={(e) => {
                      const nextDestinoId = Number(e.target.value)
                      setCreateDestinoId(nextDestinoId)
                      if (nextDestinoId) {
                        const availableOrigins = tipoRoutes.filter((r) => r.destino.id === nextDestinoId)
                        if (availableOrigins.length === 1) {
                          setCreateOrigenId(availableOrigins[0].origen.id)
                        } else if (createOrigenId && !availableOrigins.some((r) => r.origen.id === createOrigenId)) {
                          setCreateOrigenId(0)
                        }
                      }
                    }}
                    required
                  >
                    <option value="">
                      {destinosDisponibles.length === 0
                        ? createOrigenId
                          ? 'No hay rutas activas desde este origen'
                          : 'Seleccione origen primero...'
                        : 'Seleccione destino...'}
                    </option>
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
                  <p style={{ margin: 0 }}>Asignado automáticamente por el sistema</p>
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
            VISTA: EDICIÓN
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

            <div className="form-group" style={{ marginTop: '1rem' }}>
              <label className="form-label" htmlFor="edit-motivo">
                Motivo de la modificación<span className="form-label__required">*</span>
              </label>
              <textarea
                id="edit-motivo"
                className="form-input"
                rows={3}
                maxLength={500}
                value={editMotivo}
                onChange={(e) => setEditMotivo(e.target.value)}
                placeholder="Explica el motivo del cambio de horario o tarifa..."
                required
              />
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
        {/* Barra de pestañas: solo la ven los administradores.
            Los clientes y visitantes ven directamente la pestaña pública. */}
        {view === 'LIST' && isAdmin && (
          <div
            role="tablist"
            style={{ display: 'flex', gap: '0.5rem', marginBottom: '1.5rem', borderBottom: '2px solid var(--color-border, #ddd)' }}
          >
            {(
              [
                ['PUBLIC', 'Disponibles'],
                ['ADMIN', 'Gestión'],
              ] as const
            ).map(([key, label]) => (
              <button
                key={key}
                type="button"
                role="tab"
                aria-selected={effectiveTab === key}
                onClick={() => setTab(key)}
                style={{
                  background: 'transparent',
                  border: 'none',
                  borderBottom: effectiveTab === key ? '3px solid var(--color-primary, #4b0082)' : '3px solid transparent',
                  padding: '0.5rem 1rem',
                  fontWeight: 700,
                  cursor: 'pointer',
                  color: effectiveTab === key ? 'var(--color-primary, #4b0082)' : 'inherit',
                  marginBottom: '-2px',
                }}
              >
                {label}
              </button>
            ))}
          </div>
        )}

        {view === 'LIST' && effectiveTab === 'ADMIN' && isAdmin && (
          <div style={{ display: 'flex', justifyContent: 'flex-end', marginBottom: '1rem' }}>
            <button
              type="button"
              className="btn btn--primary"
              onClick={() => setView('CREATE')}
            >
              + Programar nuevo vuelo
            </button>
          </div>
        )}

        {view === 'LIST' && (
          <>
            {/* PANEL DE BÚSQUEDA Y FILTRADO (HU-005) Y CATÁLOGO POR CIUDAD (HU-006) */}
            {effectiveTab === 'PUBLIC' && (
              <div
                className="admin-card-panel"
                style={{
                  marginBottom: '2rem',
                  background: '#fdf9fc',
                  border: '1px solid var(--color-border)',
                }}
              >
                <div
                  style={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    marginBottom: '1rem',
                    flexWrap: 'wrap',
                    gap: '1rem',
                  }}
                >
                  <div>
                    <h2 style={{ fontSize: '1.25rem', margin: 0, color: 'var(--color-primary)' }}>
                      🔍 Encuentra tu próximo vuelo
                    </h2>
                    <p style={{ margin: 0, fontSize: '0.85rem', color: 'var(--color-text-secondary)' }}>
                      Consulta itinerarios, disponibilidad de cupos y tarifas en tiempo real.
                    </p>
                  </div>

                  {/* Selector de trayecto: Solo ida / Ida y regreso */}
                  <div
                    style={{
                      display: 'flex',
                      gap: '1rem',
                      background: '#ffffff',
                      padding: '0.35rem 0.8rem',
                      border: '1px solid var(--color-border)',
                      borderRadius: '0.25rem',
                    }}
                  >
                    <label
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '0.4rem',
                        cursor: 'pointer',
                        fontSize: '0.9rem',
                        fontWeight: 600,
                      }}
                    >
                      <input
                        type="radio"
                        name="trayecto"
                        checked={searchTipoTrayecto === 'UNICO'}
                        onChange={() => setSearchTipoTrayecto('UNICO')}
                      />
                      Solo ida
                    </label>
                    <label
                      style={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: '0.4rem',
                        cursor: 'pointer',
                        fontSize: '0.9rem',
                        fontWeight: 600,
                      }}
                    >
                      <input
                        type="radio"
                        name="trayecto"
                        checked={searchTipoTrayecto === 'COMPLETO'}
                        onChange={() => setSearchTipoTrayecto('COMPLETO')}
                      />
                      Ida y regreso
                    </label>
                  </div>
                </div>

                {searchError && (
                  <div className="alert alert--error" style={{ marginBottom: '1rem' }}>
                    <span className="alert__body">{searchError}</span>
                  </div>
                )}

                <form onSubmit={handleExecuteSearch} noValidate>
                  <div
                    style={{
                      display: 'grid',
                      gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
                      gap: '1rem',
                      marginBottom: '1rem',
                    }}
                  >
                    <div className="form-group" style={{ margin: 0 }}>
                      <label className="form-label" style={{ fontSize: '0.85rem' }}>
                        Ciudad de Origen
                      </label>
                      <FlightCitySelect side="origin" value={searchOrigenId} opposite={searchDestinoId} date={searchFechaSalida} passengers={searchPasajeros} travelClass={searchClase} onChange={setSearchOrigenId} />
                    </div>

                    <div className="form-group" style={{ margin: 0 }}>
                      <label className="form-label" style={{ fontSize: '0.85rem' }}>
                        Ciudad de Destino
                      </label>
                      <FlightCitySelect side="destination" value={searchDestinoId} opposite={searchOrigenId} date={searchFechaSalida} passengers={searchPasajeros} travelClass={searchClase} onChange={setSearchDestinoId} />
                    </div>

                    <div className="form-group" style={{ margin: 0 }}>
                      <label className="form-label" style={{ fontSize: '0.85rem' }}>
                        Fecha de ida
                      </label>
                      <input
                        type="date"
                        className="form-input"
                        value={searchFechaSalida}
                        onChange={(e) => setSearchFechaSalida(e.target.value)}
                      />
                    </div>

                    {searchTipoTrayecto === 'COMPLETO' && (
                      <div className="form-group" style={{ margin: 0 }}>
                        <label className="form-label" style={{ fontSize: '0.85rem' }}>
                          Fecha de regreso
                        </label>
                        <input
                          type="date"
                          className="form-input"
                          value={searchFechaRegreso}
                          min={searchFechaSalida || undefined}
                          onChange={(e) => setSearchFechaRegreso(e.target.value)}
                        />
                      </div>
                    )}

                    <div className="form-group" style={{ margin: 0 }}>
                      <label className="form-label" style={{ fontSize: '0.85rem' }}>
                        Pasajeros (máx. 5)
                      </label>
                      <select
                        className="form-select"
                        value={searchPasajeros}
                        onChange={(e) => setSearchPasajeros(Number(e.target.value))}
                      >
                        <option value={1}>1 pasajero</option>
                        <option value={2}>2 pasajeros</option>
                        <option value={3}>3 pasajeros</option>
                        <option value={4}>4 pasajeros</option>
                        <option value={5}>5 pasajeros</option>
                      </select>
                    </div>

                    <div className="form-group" style={{ margin: 0 }}>
                      <label className="form-label" style={{ fontSize: '0.85rem' }}>
                        Clase
                      </label>
                      <CatalogueSelect category="travel_class" label="Clase de viaje" value={searchClase} onChange={value => setSearchClase(value as string)} />
                    </div>
                  </div>

                  <div
                    style={{
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'center',
                      flexWrap: 'wrap',
                      gap: '1rem',
                      paddingTop: '0.75rem',
                      borderTop: '1px solid #e2e8f0',
                    }}
                  >
                    {/* HU-006: Catálogo rápido por ciudad */}
                    <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                      <span style={{ fontSize: '0.85rem', color: '#64748b' }}>
                        O consultar catálogo por ciudad:
                      </span>
                      <FlightCitySelect side="origin" value={searchCityOriginId} opposite="" date="" passengers={1} travelClass="" onChange={setSearchCityOriginId} />
                    </div>

                    <div style={{ display: 'flex', gap: '0.75rem' }}>
                      {(searchResults !== null ||
                        searchCityOriginId ||
                        searchOrigenId ||
                        searchDestinoId ||
                        searchFechaSalida) && (
                        <button
                          type="button"
                          className="btn btn--secondary"
                          style={{ padding: '0.45rem 0.9rem', fontSize: '0.9rem' }}
                          onClick={handleClearSearch}
                        >
                          Limpiar búsqueda
                        </button>
                      )}
                      <button
                        type="submit"
                        className="btn btn--primary"
                        style={{ padding: '0.45rem 1.25rem', fontSize: '0.9rem' }}
                        disabled={searching}
                      >
                        {searching ? 'Buscando vuelos...' : '🔍 Buscar Vuelos'}
                      </button>
                    </div>
                  </div>
                </form>
              </div>
            )}

            {/* AVISO DE RESULTADOS DE BÚSQUEDA */}
            {searchResults !== null && (
              <div
                style={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  marginBottom: '1rem',
                  padding: '0.75rem 1rem',
                  background: '#f0fdf4',
                  border: '1px solid #bbf7d0',
                  borderRadius: '0.35rem',
                }}
              >
                <span style={{ fontWeight: 600, color: '#166534', fontSize: '0.95rem' }}>
                  ✓ {searchResults.vuelos_ida.length}{' '}
                  {searchResults.vuelos_ida.length === 1 ? 'vuelo encontrado' : 'vuelos encontrados'}{' '}
                  para tu búsqueda de ida
                  {searchResults.tipo_trayecto === 'COMPLETO' &&
                    ` (${searchResults.vuelos_regreso.length} de regreso)`}
                </span>
                <button
                  type="button"
                  onClick={handleClearSearch}
                  style={{
                    background: 'transparent',
                    border: 'none',
                    color: '#166534',
                    textDecoration: 'underline',
                    cursor: 'pointer',
                    fontSize: '0.85rem',
                  }}
                >
                  Ver todos los vuelos
                </button>
              </div>
            )}

            {loading ? (
              <div style={{ padding: '3rem', textAlign: 'center', color: 'var(--color-text-secondary)' }}>
                Cargando itinerarios de vuelos...
              </div>
            ) : currentList.length === 0 ? (
              <div style={{ padding: '3rem', textAlign: 'center', color: 'var(--color-text-secondary)' }}>
                No se encontraron vuelos que coincidan con los criterios seleccionados.
              </div>
            ) : (
              <div className="table-wrap">
                <table className="admin-table">
                  <thead>
                    <tr>
                      <ColumnFilter label="Código" active={Boolean(searchTerm.trim())}>
                        <input
                          type="text"
                          className="form-input"
                          style={{ width: '100%' }}
                          placeholder="Buscar código, origen o destino..."
                          value={searchTerm}
                          onChange={(e) => setSearchTerm(e.target.value)}
                        />
                      </ColumnFilter>
                      <ColumnFilter label="Tipo" active={Boolean(filterTipo)}>
                        <CatalogueSelect category="flight_type" label="Tipo de vuelo" value={filterTipo} onChange={value => setFilterTipo(value as string)} />
                      </ColumnFilter>
                      <th>Ruta</th>
                      <th>Salida</th>
                      <th>Llegada</th>
                      {isAdmin && effectiveTab === 'ADMIN' ? (
                        <ColumnFilter label="Estado" active={Boolean(filterEstado)}>
                          <select
                            className="form-select"
                            style={{ width: '100%' }}
                            value={filterEstado}
                            onChange={(e) => setFilterEstado(e.target.value)}
                          >
                            <option value="">Todos</option>
                            <option value="PROGRAMADO">Programado</option>
                            <option value="REALIZADO">Realizado</option>
                            <option value="CANCELADO">Cancelado</option>
                          </select>
                        </ColumnFilter>
                      ) : (
                        <th>Estado</th>
                      )}
                      <th>Cupos</th>
                      <th>Tarifa Económica</th>
                      <th>Acciones</th>
                    </tr>
                  </thead>
                  <tbody>
                    {currentList.map((f) => {
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
                          <td>${Number(effectiveTab === 'ADMIN' ? f.costo_persona_economica : f.precio_vigente_economica).toLocaleString('es-CO')}</td>
                          <td>
                            {isAdmin && effectiveTab === 'ADMIN' && <button type="button" className="btn btn--secondary btn--small" onClick={() => setPanelFlightId(f.id)}>Pasajeros / resolución</button>}
                            {isAdmin && effectiveTab === 'ADMIN' ? (
                              isProgramado ? (
                                <div style={{ display: 'flex', gap: '0.5rem', flexWrap: 'wrap' }}>
                                  {new Date(f.salida_utc).getTime() <= Date.now() && <button type="button" className="btn btn--secondary" onClick={async () => { if (!window.confirm('¿Confirmas que este vuelo fue realizado?')) return; try { await api.post(`/sales/flights/${f.id}/performed/`, {}); loadFlights() } catch (e) { setNotification({ type: 'error', message: e instanceof ApiError ? e.message : 'No se confirmó la operación.' }) } }}>Confirmar realizado</button>}
                                  
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
                                    className="btn btn--secondary"
                                    style={{ padding: '0.3rem 0.6rem', fontSize: '0.85rem' }}
                                    onClick={() => {
                                      setPromotionFlight(f)
                                      setPromotionClase('ECONOMICA')
                                      setPromotionPrice('')
                                      setPromotionStartsImmediately(true)
                                      setPromotionStartsAt('')
                                      setPromotionEndsAt('')
                                      setPromotionError('')
                                    }}
                                  >
                                    Promoción
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
                              )
                            ) : (
                              <button
                                type="button"
                                className="btn btn--primary"
                                style={{ padding: '0.35rem 0.75rem', fontSize: '0.85rem', whiteSpace: 'nowrap' }}
                                onClick={() => {
                                  setBookingFlight(f)
                                  setBookingClase(searchClase === 'PRIMERA_CLASE' ? 'PRIMERA_CLASE' : 'ECONOMICA')
                                  if (searchResults && searchResults.vuelos_regreso.length > 0) {
                                    setBookingFlightRegreso(searchResults.vuelos_regreso[0])
                                  } else {
                                    setBookingFlightRegreso(null)
                                  }
                                }}
                              >
                                ✈ Reservar / Comprar
                              </button>
                            )}
                          </td>
                        </tr>
                      )
                    })}
                  </tbody>
                </table>
              </div>
            )}

            {/* SECCIÓN DE VUELOS DE REGRESO SI BÚSQUEDA COMPLETA (HU-005) */}
            {searchResults && searchResults.tipo_trayecto === 'COMPLETO' && searchResults.vuelos_regreso.length > 0 && (
              <div style={{ marginTop: '2.5rem' }}>
                <h3 style={{ fontSize: '1.25rem', color: 'var(--color-primary)', marginBottom: '0.75rem' }}>
                  🔄 Vuelos de Regreso Disponibles ({searchResults.vuelos_regreso.length})
                </h3>
                <div className="table-wrap">
                  <table className="admin-table">
                    <thead>
                      <tr>
                        <th>Código</th>
                        <th>Tipo</th>
                        <th>Ruta</th>
                        <th>Salida</th>
                        <th>Llegada</th>
                        <th>Cupos</th>
                        <th>Tarifa Económica</th>
                        <th>Acción</th>
                      </tr>
                    </thead>
                    <tbody>
                      {searchResults.vuelos_regreso.map((rf) => (
                        <tr key={rf.id}>
                          <td><strong>{rf.codigo_vuelo}</strong></td>
                          <td>{rf.tipo_vuelo}</td>
                          <td><strong>{rf.origen}</strong> → <strong>{rf.destino}</strong></td>
                          <td>{rf.fecha_salida} <br /><small style={{ color: 'var(--color-text-secondary)' }}>{rf.hora_salida}</small></td>
                          <td>{rf.fecha_llegada} <br /><small style={{ color: 'var(--color-text-secondary)' }}>{rf.hora_llegada}</small></td>
                          <td>{rf.cupos_disponibles_economica + rf.cupos_disponibles_primera} / {rf.capacidad_total}</td>
                          <td>${Number(rf.precio_vigente_economica).toLocaleString('es-CO')}</td>
                          <td>
                            <button
                              type="button"
                              className="btn btn--secondary"
                              style={{ padding: '0.35rem 0.65rem', fontSize: '0.85rem' }}
                              onClick={() => {
                                setBookingFlightRegreso(rf)
                                setNotification({ type: 'success', message: `Vuelo de regreso ${rf.codigo_vuelo} seleccionado.` })
                              }}
                            >
                              {bookingFlightRegreso?.id === rf.id ? '✓ Seleccionado' : 'Seleccionar regreso'}
                            </button>
                          </td>
                        </tr>
                      ))}
                    </tbody>
                  </table>
                </div>
              </div>
            )}

            {/* Catálogo de rutas: herramienta interna de gestión,
                visible solo en la pestaña Gestión */}
            {effectiveTab === 'ADMIN' && isAdmin && (
              <div style={{ marginTop: '3rem' }}>
                <CatalogPage session={session} />
              </div>
            )}
          </>
        )}
      </div>

      {/* ============================================================
          MODAL: CANCELACIÓN DE VUELO
          ============================================================ */}
      {flightToCancel && (
        <div className="modal-backdrop" role="dialog" aria-modal="true">
          <div className="modal-box">
            <h2 className="modal-box__title">¿Cancelar vuelo {flightToCancel.codigo_vuelo}?</h2>

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
                <p className="journey-inline-note">
                  Al confirmar, se liberan las reservas impagadas. Cada comprador selecciona después reubicación o reembolso para sus tiquetes pagados.
                </p>
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

      {promotionFlight && (
        <div className="modal-backdrop" role="dialog" aria-modal="true" aria-labelledby="promotion-title">
          <div className="modal-box">
            <h2 className="modal-box__title" id="promotion-title">
              Crear promoción · {promotionFlight.codigo_vuelo}
            </h2>
            <p className="form-subtitle">
              Define un precio temporal para una clase. Solo aplica a nuevas reservas y compras
              dentro del periodo indicado.
            </p>
            {promotionError && (
              <div className="alert alert--error" role="alert">
                <span className="alert__body">{promotionError}</span>
              </div>
            )}
            <form onSubmit={handlePromotionSubmit}>
              <div className="journey-form__grid">
                <div className="form-group">
                  <label className="form-label" htmlFor="promotion-class">Clase</label>
                  <CatalogueSelect category="travel_class" label="Clase de promoción" value={promotionClase} onChange={value => setPromotionClase(value as 'ECONOMICA' | 'PRIMERA_CLASE')} />
                </div>
                <div className="form-group">
                  <label className="form-label" htmlFor="promotion-price">Precio promocional (COP)</label>
                  <input
                    id="promotion-price"
                    className="form-input"
                    type="number"
                    min="0.01"
                    step="0.01"
                    value={promotionPrice}
                    onChange={(event) => setPromotionPrice(event.target.value)}
                    required
                  />
                  <span className="form-hint">
                    Tarifa base:{' '}
                    {promotionClase === 'ECONOMICA'
                      ? promotionFlight.costo_persona_economica
                      : promotionFlight.costo_persona_primera}{' '}
                    COP
                  </span>
                </div>
                <div className="form-group">
                  <label className="form-checkbox" style={{ marginTop: '1.8rem' }}>
                    <input
                      type="checkbox"
                      checked={promotionStartsImmediately}
                      onChange={(event) => setPromotionStartsImmediately(event.target.checked)}
                    />
                    <span className="form-checkbox__text">Iniciar inmediatamente</span>
                  </label>
                  {!promotionStartsImmediately && (
                    <div style={{ marginTop: '.75rem' }}>
                      <label className="form-label" htmlFor="promotion-start">Inicio (hora local del dispositivo)</label>
                      <input
                        id="promotion-start"
                        className="form-input"
                        type="datetime-local"
                        value={promotionStartsAt}
                        onChange={(event) => setPromotionStartsAt(event.target.value)}
                        required
                      />
                    </div>
                  )}
                </div>
                <div className="form-group">
                  <label className="form-label" htmlFor="promotion-end">Fin (hora local del dispositivo)</label>
                  <input
                    id="promotion-end"
                    className="form-input"
                    type="datetime-local"
                    value={promotionEndsAt}
                    onChange={(event) => setPromotionEndsAt(event.target.value)}
                    required
                  />
                </div>
              </div>
              <p className="form-hint">
                La promoción puede iniciar ahora o programarse; no puede superar la tarifa base
                y debe terminar antes de la salida. Los periodos de la misma clase no pueden cruzarse.
              </p>
              <div className="modal-actions">
                <button
                  type="button"
                  className="btn btn--secondary"
                  onClick={() => setPromotionFlight(null)}
                  disabled={promotionBusy}
                >
                  Volver
                </button>
                <button type="submit" className="btn btn--primary" disabled={promotionBusy}>
                  {promotionBusy ? 'Guardando…' : 'Crear promoción'}
                </button>
              </div>
            </form>
          </div>
        </div>
      )}

      {/* MODAL DE RESERVA Y COMPRA (HU-012, HU-013) */}
      {bookingFlight && (
        <BookingModal
          vuelo={bookingFlight}
          vueloRegreso={bookingFlightRegreso}
          session={session}
          initialClase={bookingClase}
          initialPasajeros={searchPasajeros}
          onClose={() => {
            setBookingFlight(null)
            setBookingFlightRegreso(null)
          }}
          onSuccess={(msg) => {
            setNotification({ type: 'success', message: msg })
            loadFlights()
          }}
        />
      )}
    </div>
  )
}

