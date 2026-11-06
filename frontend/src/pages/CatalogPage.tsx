import { useCallback, useEffect, useMemo, useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { api, ApiError } from '../api'
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
  const [searchTerm, setSearchTerm] = useState('')
  const [filterTipo, setFilterTipo] = useState('')
  const [filterEstado, setFilterEstado] = useState('')

  // Formulario creación de ruta
  const [showCreate, setShowCreate] = useState(false)
  const [createOrigenId, setCreateOrigenId] = useState<number>(0)
  const [createDestinoId, setCreateDestinoId] = useState<number>(0)
  const [createTipo, setCreateTipo] = useState<'NACIONAL' | 'INTERNACIONAL'>('NACIONAL')
  const [createDuracion, setCreateDuracion] = useState<number>(60)
  const [createActiva, setCreateActiva] = useState<boolean>(true)
  const [createBusy, setCreateBusy] = useState(false)
  const [createError, setCreateError] = useState('')

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
    if (isAuthorized) {
      loadData()
    }
  }, [isAuthorized, loadData])

  // Filtrado de rutas en tabla
  const filteredRoutes = useMemo(() => {
    return routes.filter((r) => {
      if (filterTipo && r.tipo_vuelo !== filterTipo) return false
      if (filterEstado === 'activa' && !r.activa) return false
      if (filterEstado === 'inactiva' && r.activa) return false
      if (searchTerm.trim()) {
        const term = searchTerm.toLowerCase().trim()
        const matchOrigen = r.origen.nombre.toLowerCase().includes(term)
        const matchDestino = r.destino.nombre.toLowerCase().includes(term)
        return matchOrigen || matchDestino
      }
      return true
    })
  }, [routes, filterTipo, filterEstado, searchTerm])

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
        origen: createOrigenId,
        destino: createDestinoId,
        tipo_vuelo: createTipo,
        duracion_min: createDuracion,
        activa: createActiva,
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

  if (!isAuthorized) {
    return (
      <div className="page-shell">
        <div className="page-card" style={{ maxWidth: '640px', margin: '3rem auto' }}>
          <header className="page-card__header">
            <h1 className="page-card__title">Acceso restringido</h1>
          </header>
          <div className="alert alert--error" style={{ marginBottom: '1.5rem' }}>
            Solo el personal con rol <strong>Administrador</strong> o <strong>ROOT</strong> tiene
            autorización para gestionar el catálogo de rutas. Su rol actual es{' '}
            <strong>{session.role || 'Visitante'}</strong>.
          </div>
          <Link to="/" className="btn btn--secondary">
            Volver al inicio
          </Link>
        </div>
      </div>
    )
  }

  return (
    <div className="page-shell">
      <div className="page-card" style={{ maxWidth: '1100px' }}>
        <header className="page-card__header">
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', flexWrap: 'wrap', gap: '1rem' }}>
            <div>
              <h1 className="page-card__title">Catálogo de Rutas</h1>
              <p className="page-card__subtitle">
                Gestión de rutas activas e itinerarios base para vuelos comerciales.
              </p>
            </div>
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
        {showCreate && (
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
                    onChange={(e) => setCreateTipo(e.target.value as 'NACIONAL' | 'INTERNACIONAL')}
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
                    {cities.map((c) => (
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
                    {cities
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

        {/* Filtros de catálogo */}
        <div className="flight-controls-bar" style={{ alignItems: 'flex-end', marginBottom: '1.5rem' }}>
          <div className="flight-filters" style={{ alignItems: 'flex-end' }}>
            <div className="form-group" style={{ margin: 0 }}>
              <label htmlFor="search-route" className="form-label" style={{ fontSize: '0.85rem', marginBottom: '0.25rem' }}>
                Buscar ciudad
              </label>
              <input
                id="search-route"
                type="text"
                className="form-input"
                style={{ width: '220px', padding: '0.5rem 0.75rem' }}
                placeholder="Origen o destino..."
                value={searchTerm}
                onChange={(e) => setSearchTerm(e.target.value)}
              />
            </div>

            <div className="form-group" style={{ margin: 0 }}>
              <label htmlFor="filter-route-tipo" className="form-label" style={{ fontSize: '0.85rem', marginBottom: '0.25rem' }}>
                Tipo de ruta
              </label>
              <select
                id="filter-route-tipo"
                className="form-select"
                style={{ width: '160px', padding: '0.5rem 0.75rem' }}
                value={filterTipo}
                onChange={(e) => setFilterTipo(e.target.value)}
              >
                <option value="">Todas</option>
                <option value="NACIONAL">Nacional</option>
                <option value="INTERNACIONAL">Internacional</option>
              </select>
            </div>

            <div className="form-group" style={{ margin: 0 }}>
              <label htmlFor="filter-route-estado" className="form-label" style={{ fontSize: '0.85rem', marginBottom: '0.25rem' }}>
                Estado
              </label>
              <select
                id="filter-route-estado"
                className="form-select"
                style={{ width: '160px', padding: '0.5rem 0.75rem' }}
                value={filterEstado}
                onChange={(e) => setFilterEstado(e.target.value)}
              >
                <option value="">Todas</option>
                <option value="activa">Activas</option>
                <option value="inactiva">Inactivas</option>
              </select>
            </div>
          </div>
        </div>

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
                  <th>Tipo</th>
                  <th>Origen</th>
                  <th>Destino</th>
                  <th>Duración estimada</th>
                  <th>Estado</th>
                  <th>Acciones</th>
                </tr>
              </thead>
              <tbody>
                {filteredRoutes.map((r) => {
                  const isEditing = editingRouteId === r.id
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

