import { useCallback, useEffect, useMemo, useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { api, ApiError } from '../api'
import ColumnFilter from '../components/ColumnFilter'
import type { Ciudad, Ruta } from '../types/flight'

interface CatalogPageProps {
  session: {
    authenticated: boolean
    role: string | null
    is_email_verified: boolean
  }
}

export default function CatalogPage({ session }: CatalogPageProps) {
  const isAuthorized =
    session.authenticated && (session.role === 'ADMINISTRADOR' || session.role === 'ROOT')


    
  const [cities, setCities] = useState<Ciudad[]>([])
  const [routes, setRoutes] = useState<Ruta[]>([])
  const [loading, setLoading] = useState(false)
  const [notification, setNotification] = useState<{ type: 'success' | 'error'; message: string } | null>(null)

  // Filtros
  const [filterTipo, setFilterTipo] = useState('')
  const [filterEstado, setFilterEstado] = useState('')
  const [filterOrigenId, setFilterOrigenId] = useState<number>(0)
  const [filterDestinoId, setFilterDestinoId] = useState<number>(0)

  // Formulario creación de ruta
  const [showCreate, setShowCreate] = useState(false)
  const [createOrigenId, setCreateOrigenId] = useState<number>(0)
  const [createDestinoId, setCreateDestinoId] = useState<number>(0)
  const [createTipo, setCreateTipo] = useState<'NACIONAL' | 'INTERNACIONAL'>('NACIONAL')
  const [createDuracion, setCreateDuracion] = useState<number>(60)
  const [createActiva, setCreateActiva] = useState<boolean>(true)
  const [createBusy, setCreateBusy] = useState(false)
  const [createError, setCreateError] = useState('')

  // Ciudades elegibles según el tipo de vuelo (regla del catálogo)
  const ciudadesOrigen = useMemo(
    () =>
      cities.filter((c) =>
        createTipo === 'NACIONAL'
          ? c.codigo_pais === 'CO' && c.es_capital_principal
          : c.origen_internacional,
      ),
    [cities, createTipo],
  )
  const ciudadesDestino = useMemo(
    () =>
      cities.filter((c) =>
        createTipo === 'NACIONAL'
          ? c.codigo_pais === 'CO' && c.es_capital_principal
          : c.destino_internacional,
      ),
    [cities, createTipo],
  )

  // Edición rápida de duración
  const [editingRouteId, setEditingRouteId] = useState<number | null>(null)
  const [editDuracion, setEditDuracion] = useState<number>(60)
  const [actionBusy, setActionBusy] = useState(false)

  const loadData = useCallback(async () => {
    setLoading(true)
    try {
      const [citiesData, routesData] = await Promise.all([
        api.get('/flights/cities/'),
        api.get('/flights/routes/?todos=1'),
      ])
      setCities(citiesData)
      setRoutes(routesData)
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : 'Error al cargar el catálogo de rutas.'
      setNotification({ type: 'error', message: msg })
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    loadData()
  }, [loadData])

  // Filtrado de rutas en tabla
  const filteredRoutes = useMemo(() => {
    return routes.filter((r) => {
      if (filterTipo && r.tipo_vuelo !== filterTipo) return false
      if (filterEstado === 'activa' && !r.activa) return false
      if (filterEstado === 'inactiva' && r.activa) return false
      if (filterOrigenId && r.origen.id !== filterOrigenId) return false
      if (filterDestinoId && r.destino.id !== filterDestinoId) return false
      return true
    })
  }, [routes, filterTipo, filterEstado, filterOrigenId, filterDestinoId])

  // Alternar estado activo / inactivo
  const handleToggleActive = async (route: Ruta) => {
    setActionBusy(true)
    try {
      const updated: Ruta = await api.patch(`/flights/routes/${route.id}/`, {
        activa: !route.activa,
      })
      setRoutes((prev) => prev.map((r) => (r.id === updated.id ? updated : r)))
      setNotification({
        type: 'success',
        message: `Ruta ${route.origen.nombre} → ${route.destino.nombre} ${
          updated.activa ? 'habilitada' : 'deshabilitada'
        } exitosamente.`,
      })
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : 'No fue posible actualizar la ruta.'
      setNotification({ type: 'error', message: msg })
    } finally {
      setActionBusy(false)
    }
  }

  // Guardar nueva duración
  const handleSaveDuration = async (routeId: number) => {
    if (editDuracion <= 0) {
      setNotification({ type: 'error', message: 'La duración debe ser mayor a 0 minutos.' })
      return
    }
    setActionBusy(true)
    try {
      const updated: Ruta = await api.patch(`/flights/routes/${routeId}/`, {
        duracion_min: editDuracion,
      })
      setRoutes((prev) => prev.map((r) => (r.id === updated.id ? updated : r)))
      setEditingRouteId(null)
      setNotification({
        type: 'success',
        message: 'Duración estimada actualizada con éxito.',
      })
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : 'No fue posible actualizar la duración.'
      setNotification({ type: 'error', message: msg })
    } finally {
      setActionBusy(false)
    }
  }

  // Crear nueva ruta
  const handleCreateRoute = async (e: FormEvent) => {
    e.preventDefault()
    if (!createOrigenId || !createDestinoId) {
      setCreateError('Seleccione una ciudad de origen y una de destino.')
      return
    }
    if (createOrigenId === createDestinoId) {
      setCreateError('El origen y el destino no pueden ser la misma ciudad.')
      return
    }
    if (createDuracion <= 0) {
      setCreateError('La duración estimada debe ser mayor a 0 minutos.')
      return
    }

    setCreateBusy(true)
    setCreateError('')
    try {
      const created: Ruta = await api.post('/flights/routes/', {
        origen_id: createOrigenId,
        destino_id: createDestinoId,
        tipo_vuelo: createTipo,
        duracion_min: createDuracion,
      })
      setRoutes((prev) => [...prev, created])
      setShowCreate(false)
      setCreateOrigenId(0)
      setCreateDestinoId(0)
      setCreateDuracion(60)
      setNotification({
        type: 'success',
        message: `Ruta ${created.origen.nombre} → ${created.destino.nombre} incorporada exitosamente al catálogo.`,
      })
    } catch (err) {
      const msg = err instanceof ApiError ? err.message : 'No fue posible crear la ruta.'
      setCreateError(msg)
    } finally {
      setCreateBusy(false)
    }
  }

  return (
    <div className="page-shell">
      <div className="page-card" style={{ maxWidth: '1100px' }}>
        <header className="page-card__header">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem' }}>
            <div>
              <h1 className="page-card__title">Catálogo de Rutas</h1>
              <p className="page-card__subtitle">
                {isAuthorized
                  ? 'Gestión de rutas activas e itinerarios base para vuelos comerciales.'
                  : 'Rutas e itinerarios base disponibles para vuelos comerciales.'}
              </p>
            </div>
            {isAuthorized && (
              <button
                type="button"
                className="btn btn--primary"
                onClick={() => {
                  setShowCreate(!showCreate)
                  setCreateError('')
                }}
              >
                {showCreate ? 'Cerrar formulario' : '+ Nueva ruta'}
              </button>
            )}
          </div>
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

        {/* Formulario desplegable para agregar nueva ruta */}
        {showCreate && isAuthorized && (
          <div className="admin-card-panel" style={{ marginBottom: '2rem', border: '2px solid var(--color-primary)' }}>
            <h2 className="form-section__title" style={{ fontSize: '1.25rem', marginBottom: '1rem' }}>
              Registrar nueva ruta en el catálogo
            </h2>
            {createError && (
              <div className="alert alert--error" style={{ marginBottom: '1rem' }}>
                {createError}
              </div>
            )}
            <form onSubmit={handleCreateRoute} noValidate>
              <div className="admin-forms-grid" style={{ marginBottom: '1rem' }}>
                <div className="form-group">
                  <label className="form-label" htmlFor="new-route-tipo">
                    Tipo de vuelo<span className="form-label__required">*</span>
                  </label>
                  <select
                    id="new-route-tipo"
                    className="form-select"
                    value={createTipo}
                    onChange={(e) => {
                      setCreateTipo(e.target.value as 'NACIONAL' | 'INTERNACIONAL')
                      setCreateOrigenId(0)
                      setCreateDestinoId(0)
                    }}
                  >
                    <option value="NACIONAL">Nacional</option>
                    <option value="INTERNACIONAL">Internacional</option>
                  </select>
                </div>

                <div className="form-group">
                  <label className="form-label" htmlFor="new-route-duracion">
                    Duración estimada (minutos)<span className="form-label__required">*</span>
                  </label>
                  <input
                    id="new-route-duracion"
                    type="number"
                    min="10"
                    step="5"
                    className="form-input"
                    value={createDuracion}
                    onChange={(e) => setCreateDuracion(Number(e.target.value))}
                    required
                  />
                </div>

                <div className="form-group">
                  <label className="form-label" htmlFor="new-route-origen">
                    Ciudad de origen<span className="form-label__required">*</span>
                  </label>
                  <select
                    id="new-route-origen"
                    className="form-select"
                    value={createOrigenId || ''}
                    onChange={(e) => setCreateOrigenId(Number(e.target.value))}
                    required
                  >
                    <option value="">Seleccione ciudad de origen...</option>
                    {ciudadesOrigen.map((c) => (
                      <option key={c.id} value={c.id}>
                        {c.nombre} ({c.codigo_pais})
                      </option>
                    ))}
                  </select>
                </div>

                <div className="form-group">
                  <label className="form-label" htmlFor="new-route-destino">
                    Ciudad de destino<span className="form-label__required">*</span>
                  </label>
                  <select
                    id="new-route-destino"
                    className="form-select"
                    value={createDestinoId || ''}
                    onChange={(e) => setCreateDestinoId(Number(e.target.value))}
                    required
                  >
                    <option value="">Seleccione ciudad de destino...</option>
                    {ciudadesDestino
                      .filter((c) => c.id !== createOrigenId)
                      .map((c) => (
                        <option key={c.id} value={c.id}>
                          {c.nombre} ({c.codigo_pais})
                        </option>
                      ))}
                  </select>
                </div>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: '1.5rem', marginTop: '1rem' }}>
                <label style={{ display: 'flex', alignItems: 'center', gap: '0.5rem', cursor: 'pointer' }}>
                  <input
                    type="checkbox"
                    checked={createActiva}
                    onChange={(e) => setCreateActiva(e.target.checked)}
                  />
                  <span>Habilitar inmediatamente para programación de vuelos</span>
                </label>
                <button type="submit" className="btn btn--primary" disabled={createBusy}>
                  {createBusy ? 'Guardando ruta...' : 'Guardar ruta en catálogo'}
                </button>
                <button
                  type="button"
                  className="btn btn--secondary"
                  onClick={() => setShowCreate(false)}
                  disabled={createBusy}
                >
                  Cancelar
                </button>
              </div>
            </form>
          </div>
        )}

        {/* Tabla de rutas */}
        {loading ? (
          <div style={{ padding: '3rem', textAlign: 'center', color: 'var(--color-text-secondary)' }}>
            Cargando catálogo de rutas...
          </div>
        ) : filteredRoutes.length === 0 ? (
          <div style={{ padding: '3rem', textAlign: 'center', color: 'var(--color-text-secondary)' }}>
            No se encontraron rutas con los filtros aplicados.
          </div>
        ) : (
          <div className="table-wrap">
            <table className="admin-table">
              <thead>
                <tr>
                  <th>ID</th>
                  <ColumnFilter label="Tipo" active={Boolean(filterTipo)}>
                    <select
                      className="form-select"
                      style={{ width: '100%' }}
                      value={filterTipo}
                      onChange={(e) => setFilterTipo(e.target.value)}
                    >
                      <option value="">Todas</option>
                      <option value="NACIONAL">Nacional</option>
                      <option value="INTERNACIONAL">Internacional</option>
                    </select>
                  </ColumnFilter>
                  <ColumnFilter label="Origen" active={Boolean(filterOrigenId)}>
                    <select
                      className="form-select"
                      style={{ width: '100%' }}
                      value={filterOrigenId || ''}
                      onChange={(e) => setFilterOrigenId(Number(e.target.value))}
                    >
                      <option value="">Todas</option>
                      {cities.map((c) => (
                        <option key={c.id} value={c.id}>
                          {c.nombre} ({c.codigo_pais})
                        </option>
                      ))}
                    </select>
                  </ColumnFilter>
                  <ColumnFilter label="Destino" active={Boolean(filterDestinoId)}>
                    <select
                      className="form-select"
                      style={{ width: '100%' }}
                      value={filterDestinoId || ''}
                      onChange={(e) => setFilterDestinoId(Number(e.target.value))}
                    >
                      <option value="">Todas</option>
                      {cities.map((c) => (
                        <option key={c.id} value={c.id}>
                          {c.nombre} ({c.codigo_pais})
                        </option>
                      ))}
                    </select>
                  </ColumnFilter>
                  <th>Duración estimada</th>
                  <ColumnFilter label="Estado" active={Boolean(filterEstado)}>
                    <select
                      className="form-select"
                      style={{ width: '100%' }}
                      value={filterEstado}
                      onChange={(e) => setFilterEstado(e.target.value)}
                    >
                      <option value="">Todas</option>
                      <option value="activa">Activas</option>
                      <option value="inactiva">Inactivas</option>
                    </select>
                  </ColumnFilter>
                  {isAuthorized && <th>Acciones</th>}
                </tr>
              </thead>
              <tbody>
                {filteredRoutes.map((r) => {
                  const isEditing = isAuthorized && editingRouteId === r.id
                  return (
                    <tr key={r.id}>
                      <td>#{r.id}</td>
                      <td>
                        <span className="badge badge--info">{r.tipo_vuelo}</span>
                      </td>
                      <td>
                        <strong>{r.origen.nombre}</strong> ({r.origen.codigo_pais})
                      </td>
                      <td>
                        <strong>{r.destino.nombre}</strong> ({r.destino.codigo_pais})
                      </td>
                      <td>
                        {isEditing ? (
                          <div style={{ display: 'flex', alignItems: 'center', gap: '0.5rem' }}>
                            <input
                              type="number"
                              min="10"
                              step="5"
                              value={editDuracion}
                              onChange={(e) => setEditDuracion(Number(e.target.value))}
                              style={{ width: '80px', padding: '0.25rem' }}
                            />
                            <button
                              type="button"
                              className="btn btn--primary"
                              style={{ padding: '0.2rem 0.5rem', fontSize: '0.8rem' }}
                              onClick={() => handleSaveDuration(r.id)}
                              disabled={actionBusy}
                            >
                              Guardar
                            </button>
                            <button
                              type="button"
                              className="btn btn--secondary"
                              style={{ padding: '0.2rem 0.5rem', fontSize: '0.8rem' }}
                              onClick={() => setEditingRouteId(null)}
                              disabled={actionBusy}
                            >
                              ✕
                            </button>
                          </div>
                        ) : (
                          <span>{r.duracion_min} minutos</span>
                        )}
                      </td>
                      <td>
                        <span className={`badge ${r.activa ? 'badge--success' : 'badge--error'}`}>
                          {r.activa ? 'Activa' : 'Inactiva'}
                        </span>
                      </td>
                      {isAuthorized && (
                        <td>
                          <div style={{ display: 'flex', gap: '0.5rem' }}>
                            <button
                              type="button"
                              className={`btn ${r.activa ? 'btn--secondary' : 'btn--primary'}`}
                              style={{ padding: '0.3rem 0.6rem', fontSize: '0.85rem' }}
                              onClick={() => handleToggleActive(r)}
                              disabled={actionBusy}
                            >
                              {r.activa ? 'Desactivar' : 'Activar'}
                            </button>
                            {!isEditing && (
                              <button
                                type="button"
                                className="btn btn--secondary"
                                style={{ padding: '0.3rem 0.6rem', fontSize: '0.85rem' }}
                                onClick={() => {
                                  setEditingRouteId(r.id)
                                  setEditDuracion(r.duracion_min)
                                }}
                                disabled={actionBusy}
                              >
                                Editar duración
                              </button>
                            )}
                          </div>
                        </td>
                      )}
                    </tr>
                  )
                })}
              </tbody>
            </table>
          </div>
        )}
      </div>
    </div>
  )
}

