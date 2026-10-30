import { useCallback, useEffect, useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { api, ApiError } from '../api'

interface Admin {
  id: number
  email: string
  first_name: string
  last_name: string
  document_number?: string
  role: string
}

interface AdminPage {
  count: number
  next: string | null
  previous: string | null
  results: Admin[]
}

interface AdministratorsPageProps {
  session: {
    authenticated: boolean
    role: string | null
    is_email_verified: boolean
  }
}

export default function AdministratorsPage({ session }: AdministratorsPageProps) {
  /* -------- Estado del Formulario de Creación (Columna Izquierda) -------- */
  const [form, setForm] = useState({
    document_number: '',
    first_name: '',
    last_name: '',
    phone: '',
    email: '',
    password: '',
  })
  const [showPassword, setShowPassword] = useState(false)
  const [formError, setFormError] = useState('')
  const [formSuccess, setFormSuccess] = useState('')
  const [busy, setBusy] = useState(false)

  /* -------- Estado del Formulario de Cambio de Contraseña (Columna Derecha) -------- */
  const [pwTargetAdminId, setPwTargetAdminId] = useState<number | ''>('')
  const [pwPassword, setPwPassword] = useState('')
  const [pwConfirmPassword, setPwConfirmPassword] = useState('')
  const [showPwPassword, setShowPwPassword] = useState(false)
  const [showPwConfirmPassword, setShowPwConfirmPassword] = useState(false)
  const [pwFormError, setPwFormError] = useState('')
  const [pwFormSuccess, setPwFormSuccess] = useState('')
  const [pwBusy, setPwBusy] = useState(false)

  /* -------- Estado de la Lista Paginada -------- */
  const [list, setList] = useState<AdminPage | null>(null)
  const [page, setPage] = useState(1)
  const [listLoading, setListLoading] = useState(false)
  const [listError, setListError] = useState('')

  const loadAdministrators = useCallback(async (targetPage: number) => {
    setListLoading(true)
    setListError('')
    try {
      const data = await api.get(`/users/administrators/?page=${targetPage}`)
      setList(data as AdminPage)
      setPage(targetPage)
    } catch (err) {
      if (err instanceof ApiError) {
        setListError(err.message)
      } else {
        setListError('No fue posible cargar el listado de administradores.')
      }
    } finally {
      setListLoading(false)
    }
  }, [])

  useEffect(() => {
    if (session.authenticated && session.role === 'ROOT') {
      void loadAdministrators(1)
    }
  }, [session.authenticated, session.role, loadAdministrators])

  const update = (key: string, value: string) => {
    setForm((prev) => ({ ...prev, [key]: value }))
    setFormError('')
  }

  /* -------- Enviar Alta de Administrador -------- */
  async function handleCreateAdmin(e: FormEvent) {
    e.preventDefault()
    setFormError('')
    setFormSuccess('')

    if (!form.document_number.trim()) {
      setFormError('El número de documento o cédula es obligatorio.')
      return
    }
    if (!form.first_name.trim()) {
      setFormError('Los nombres son obligatorios.')
      return
    }
    if (!form.last_name.trim()) {
      setFormError('Los apellidos son obligatorios.')
      return
    }
    if (!form.phone.trim()) {
      setFormError('El número de teléfono es obligatorio.')
      return
    }
    if (!form.email.trim()) {
      setFormError('El correo electrónico es obligatorio.')
      return
    }
    if (!form.password) {
      setFormError('La contraseña inicial es obligatoria.')
      return
    }
    if (form.password.length < 8) {
      setFormError('La contraseña inicial debe tener al menos 8 caracteres.')
      return
    }
    if (!/\d/.test(form.password)) {
      setFormError('La contraseña inicial debe contener al menos un número.')
      return
    }

    setBusy(true)
    try {
      const payload: Record<string, string> = {
        document_number: form.document_number.trim(),
        first_name: form.first_name.trim(),
        last_name: form.last_name.trim(),
        phone: form.phone.trim(),
        email: form.email.trim().toLowerCase(),
        password: form.password,
      }

      const data = await api.post('/users/administrators/', payload)

      setFormSuccess(
        `Administrador creado exitosamente con ID #${data.id} (${data.email}). Se ha registrado la cuenta y su aviso en auditoría.`,
      )
      setForm({
        document_number: '',
        first_name: '',
        last_name: '',
        phone: '',
        email: '',
        password: '',
      })
      await loadAdministrators(1)
    } catch (err) {
      if (err instanceof ApiError) {
        if (err.status === 409) {
          setFormError('Ya existe un usuario registrado con ese correo electrónico.')
        } else if (err.status === 400 && err.details) {
          const msgs = Object.values(err.details)
            .flat()
            .map(String)
            .join(' ')
          setFormError(msgs || err.message)
        } else if (err.status === 429) {
          setFormError('Se ha excedido el límite de solicitudes. Espere unos minutos.')
        } else {
          setFormError(err.message)
        }
      } else {
        setFormError('No fue posible contactar el servidor.')
      }
    } finally {
      setBusy(false)
    }
  }

  /* -------- Enviar Cambio de Contraseña de Administrador -------- */
  async function handleChangeAdminPassword(e: FormEvent) {
    e.preventDefault()
    setPwFormError('')
    setPwFormSuccess('')

    if (!pwTargetAdminId) {
      setPwFormError('Debe seleccionar un administrador existente de la lista.')
      return
    }
    if (!pwPassword) {
      setPwFormError('La nueva contraseña es obligatoria.')
      return
    }
    if (pwPassword.length < 8) {
      setPwFormError('La nueva contraseña debe tener al menos 8 caracteres.')
      return
    }
    if (!/\d/.test(pwPassword)) {
      setPwFormError('La nueva contraseña debe contener al menos un número.')
      return
    }
    if (!pwConfirmPassword) {
      setPwFormError('Debe confirmar la nueva contraseña.')
      return
    }
    if (pwPassword !== pwConfirmPassword) {
      setPwFormError('Las contraseñas no coinciden.')
      return
    }

    setPwBusy(true)
    try {
      await api.post('/users/administrators/password/', {
        admin_id: Number(pwTargetAdminId),
        password: pwPassword,
        password_confirmation: pwConfirmPassword,
      })

      const targetAdmin = list?.results.find((a) => a.id === Number(pwTargetAdminId))
      const adminLabel = targetAdmin
        ? `${targetAdmin.first_name} ${targetAdmin.last_name} (${targetAdmin.email})`
        : `#${pwTargetAdminId}`

      setPwFormSuccess(`Contraseña actualizada con éxito para el administrador ${adminLabel}.`)
      setPwPassword('')
      setPwConfirmPassword('')
      setPwTargetAdminId('')
    } catch (err) {
      if (err instanceof ApiError) {
        if (err.status === 400 && err.details) {
          const msgs = Object.values(err.details).flat().map(String).join(' ')
          setPwFormError(msgs || err.message)
        } else if (err.status === 503) {
          setPwFormError(
            err.code === 'password_check_unavailable'
              ? 'No fue posible verificar la seguridad de la contraseña en este momento. Intente de nuevo en unos segundos.'
              : 'Servicio no disponible temporalmente.',
          )
        } else {
          setPwFormError(err.message)
        }
      } else {
        setPwFormError('No fue posible contactar el servidor.')
      }
    } finally {
      setPwBusy(false)
    }
  }

  /* -------- Validación de Sesión y Rol -------- */
  if (!session.authenticated) {
    return (
      <div className="page page--narrow">
        <div className="form-container">
          <h1 className="form-title">Sesión requerida</h1>
          <p className="form-subtitle">
            Debe iniciar sesión para acceder al panel de administración.
          </p>
          <Link to="/login" className="btn btn--primary btn--full">
            Iniciar sesión
          </Link>
        </div>
      </div>
    )
  }

  if (session.role !== 'ROOT') {
    return (
      <div className="page page--narrow">
        <div className="form-container">
          <h1 className="form-title">Acceso restringido</h1>
          <div className="alert alert--error">
            <span className="alert__title">Permisos insuficientes (HU-009)</span>
            <span className="alert__body">
              Solo el usuario con rol <strong>ROOT</strong> tiene autorización para crear y gestionar cuentas de administrador. Su rol actual es <strong>{session.role || 'Visitante'}</strong>.
            </span>
          </div>
          <Link to="/" className="btn btn--secondary btn--full">
            Volver al inicio
          </Link>
        </div>
      </div>
    )
  }

  /* -------- Render Principal para ROOT -------- */
  return (
    <div className="page page--wide">
      <div className="form-container">
        <h1 className="form-title">Gestión de Administradores y Credenciales</h1>
        <p className="form-subtitle">
          Panel exclusivo de ROOT (HU-009). Registre nuevos administradores, modifique contraseñas de administradores existentes e inspeccione el equipo activo.
        </p>

        {/* --- Grilla de dos columnas (Izquierda: Crear, Derecha: Cambiar Contraseña) --- */}
        <div className="admin-forms-grid">
          {/* Columna Izquierda: Formulario Crear Administrador */}
          <div className="admin-card-panel">
            <h2 className="form-section__title">Crear administrador</h2>
            <p className="form-hint" style={{ marginBottom: '1.25rem' }}>
              Todos los campos marcados con asterisco (*) son obligatorios.
            </p>

            {formSuccess && (
              <div className="alert alert--success" style={{ marginBottom: '1rem' }}>
                <span className="alert__title">Operación completada</span>
                <span className="alert__body">{formSuccess}</span>
              </div>
            )}

            {formError && (
              <div className="alert alert--error" style={{ marginBottom: '1rem' }}>
                <span className="alert__body">{formError}</span>
              </div>
            )}

            <form onSubmit={handleCreateAdmin} noValidate>
              <div className="form-group" style={{ marginBottom: '0.85rem' }}>
                <label className="form-label" htmlFor="admin-doc">
                  Cédula / Documento de identidad<span className="form-label__required">*</span>
                </label>
                <input
                  id="admin-doc"
                  type="text"
                  className="form-input"
                  value={form.document_number}
                  onChange={(e) => update('document_number', e.target.value)}
                  placeholder="Ej. 1098765432"
                  maxLength={20}
                  required
                />
              </div>

              <div className="form-group" style={{ marginBottom: '0.85rem' }}>
                <label className="form-label" htmlFor="admin-fname">
                  Nombres<span className="form-label__required">*</span>
                </label>
                <input
                  id="admin-fname"
                  type="text"
                  className="form-input"
                  value={form.first_name}
                  onChange={(e) => update('first_name', e.target.value)}
                  placeholder="Ej. Laura María"
                  maxLength={150}
                  required
                />
              </div>

              <div className="form-group" style={{ marginBottom: '0.85rem' }}>
                <label className="form-label" htmlFor="admin-lname">
                  Apellidos<span className="form-label__required">*</span>
                </label>
                <input
                  id="admin-lname"
                  type="text"
                  className="form-input"
                  value={form.last_name}
                  onChange={(e) => update('last_name', e.target.value)}
                  placeholder="Ej. Gómez Pérez"
                  maxLength={150}
                  required
                />
              </div>

              <div className="form-group" style={{ marginBottom: '0.85rem' }}>
                <label className="form-label" htmlFor="admin-phone">
                  Teléfono<span className="form-label__required">*</span>
                </label>
                <input
                  id="admin-phone"
                  type="tel"
                  className="form-input"
                  value={form.phone}
                  onChange={(e) => update('phone', e.target.value)}
                  placeholder="Ej. +57 300 1234567"
                  maxLength={30}
                  required
                />
              </div>

              <div className="form-group" style={{ marginBottom: '0.85rem' }}>
                <label className="form-label" htmlFor="admin-email">
                  Correo electrónico<span className="form-label__required">*</span>
                </label>
                <input
                  id="admin-email"
                  type="email"
                  className="form-input"
                  value={form.email}
                  onChange={(e) => update('email', e.target.value)}
                  placeholder="admin@alas.com"
                  maxLength={254}
                  required
                />
              </div>

              <div className="form-group" style={{ marginBottom: '1.25rem' }}>
                <label className="form-label" htmlFor="admin-pass">
                  Contraseña inicial<span className="form-label__required">*</span>
                </label>
                <div className="password-wrapper">
                  <input
                    id="admin-pass"
                    type={showPassword ? 'text' : 'password'}
                    className="form-input"
                    value={form.password}
                    onChange={(e) => update('password', e.target.value)}
                    autoComplete="new-password"
                    placeholder="Mínimo 8 caracteres y 1 número"
                    required
                  />
                  <button
                    type="button"
                    className="password-toggle"
                    onClick={() => setShowPassword(!showPassword)}
                    aria-label={showPassword ? 'Ocultar contraseña' : 'Mostrar contraseña'}
                  >
                    {showPassword ? 'Ocultar' : 'Ver'}
                  </button>
                </div>
                <span className="form-hint">Mínimo 8 caracteres e incluir al menos un número.</span>
              </div>

              <button type="submit" className="btn btn--primary btn--full" disabled={busy}>
                {busy ? 'Creando administrador...' : 'Crear Administrador'}
              </button>
            </form>
          </div>

          {/* Columna Derecha: Formulario Cambiar Contraseña de Administrador Existente */}
          <div className="admin-card-panel">
            <h2 className="form-section__title">Cambiar contraseña de administrador</h2>
            <p className="form-hint" style={{ marginBottom: '1.25rem' }}>
              Seleccione un administrador existente de la lista para actualizar sus credenciales de acceso.
            </p>

            {pwFormSuccess && (
              <div className="alert alert--success" style={{ marginBottom: '1rem' }}>
                <span className="alert__title">Contraseña actualizada</span>
                <span className="alert__body">{pwFormSuccess}</span>
              </div>
            )}

            {pwFormError && (
              <div className="alert alert--error" style={{ marginBottom: '1rem' }}>
                <span className="alert__body">{pwFormError}</span>
              </div>
            )}

            <form onSubmit={handleChangeAdminPassword} noValidate>
              <div className="form-group" style={{ marginBottom: '0.85rem' }}>
                <label className="form-label" htmlFor="pw-target-admin">
                  Seleccionar administrador<span className="form-label__required">*</span>
                </label>
                <select
                  id="pw-target-admin"
                  className="form-select"
                  value={pwTargetAdminId}
                  onChange={(e) => {
                    setPwTargetAdminId(e.target.value ? Number(e.target.value) : '')
                    setPwFormError('')
                  }}
                  required
                >
                  <option value="">-- Seleccione un administrador --</option>
                  {(list?.results ?? []).map((adm) => (
                    <option key={adm.id} value={adm.id}>
                      #{adm.id} - {adm.first_name} {adm.last_name} ({adm.email})
                    </option>
                  ))}
                </select>
                {list && list.results.length === 0 && (
                  <span className="form-hint" style={{ color: 'var(--color-error)' }}>
                    No hay administradores registrados para modificar.
                  </span>
                )}
              </div>

              <div className="form-group" style={{ marginBottom: '0.85rem' }}>
                <label className="form-label" htmlFor="pw-new-pass">
                  Nueva contraseña<span className="form-label__required">*</span>
                </label>
                <div className="password-wrapper">
                  <input
                    id="pw-new-pass"
                    type={showPwPassword ? 'text' : 'password'}
                    className="form-input"
                    value={pwPassword}
                    onChange={(e) => {
                      setPwPassword(e.target.value)
                      setPwFormError('')
                    }}
                    autoComplete="new-password"
                    placeholder="Mínimo 8 caracteres y 1 número"
                    required
                  />
                  <button
                    type="button"
                    className="password-toggle"
                    onClick={() => setShowPwPassword(!showPwPassword)}
                    aria-label={showPwPassword ? 'Ocultar contraseña' : 'Mostrar contraseña'}
                  >
                    {showPwPassword ? 'Ocultar' : 'Ver'}
                  </button>
                </div>
                <span className="form-hint">Mínimo 8 caracteres e incluir al menos un número.</span>
              </div>

              <div className="form-group" style={{ marginBottom: '1.25rem' }}>
                <label className="form-label" htmlFor="pw-confirm-pass">
                  Confirmar nueva contraseña<span className="form-label__required">*</span>
                </label>
                <div className="password-wrapper">
                  <input
                    id="pw-confirm-pass"
                    type={showPwConfirmPassword ? 'text' : 'password'}
                    className="form-input"
                    value={pwConfirmPassword}
                    onChange={(e) => {
                      setPwConfirmPassword(e.target.value)
                      setPwFormError('')
                    }}
                    autoComplete="new-password"
                    placeholder="Repita la nueva contraseña"
                    required
                  />
                  <button
                    type="button"
                    className="password-toggle"
                    onClick={() => setShowPwConfirmPassword(!showPwConfirmPassword)}
                    aria-label={showPwConfirmPassword ? 'Ocultar contraseña' : 'Mostrar contraseña'}
                  >
                    {showPwConfirmPassword ? 'Ocultar' : 'Ver'}
                  </button>
                </div>
                <span className="form-hint">Vuelva a escribir la misma contraseña.</span>
              </div>

              <button
                type="submit"
                className="btn btn--primary btn--full"
                disabled={pwBusy || !pwTargetAdminId}
              >
                {pwBusy ? 'Actualizando contraseña...' : 'Actualizar Contraseña'}
              </button>
            </form>
          </div>
        </div>

        {/* --- Listado Paginado de Administradores (Ancho completo) --- */}
        <div className="form-section mt-3">
          <h2 className="form-section__title">
            Administradores registrados {list ? `(${list.count} en total)` : ''}
          </h2>

          {listError && (
            <div className="alert alert--error">
              <span className="alert__body">{listError}</span>
            </div>
          )}

          {listLoading ? (
            <p>Cargando administradores...</p>
          ) : (
            <>
              <div className="table-wrap">
                <table className="admin-table">
                  <thead>
                    <tr>
                      <th style={{ width: '70px' }}>ID</th>
                      <th style={{ width: '130px' }}>Documento</th>
                      <th>Nombres</th>
                      <th>Apellidos</th>
                      <th>Correo electrónico</th>
                      <th style={{ width: '120px' }}>Rol</th>
                    </tr>
                  </thead>
                  <tbody>
                    {(list?.results ?? []).map((admin) => (
                      <tr key={admin.id}>
                        <td>#{admin.id}</td>
                        <td><strong>{admin.document_number || '—'}</strong></td>
                        <td>{admin.first_name || '—'}</td>
                        <td>{admin.last_name || '—'}</td>
                        <td>{admin.email}</td>
                        <td>
                          <span className="badge badge--success" style={{ fontSize: '0.85rem' }}>
                            {admin.role}
                          </span>
                        </td>
                      </tr>
                    ))}
                    {list && list.results.length === 0 && (
                      <tr>
                        <td colSpan={6} style={{ textAlign: 'center', padding: '2rem' }}>
                          No hay administradores registrados aún.
                        </td>
                      </tr>
                    )}
                  </tbody>
                </table>
              </div>

              {list && (list.next || list.previous || list.count > 0) && (
                <div className="pager">
                  <button
                    className="btn btn--secondary btn--small"
                    type="button"
                    onClick={() => void loadAdministrators(page - 1)}
                    disabled={!list.previous || listLoading}
                  >
                    ← Anterior
                  </button>
                  <span>
                    Página {page} de {Math.max(1, Math.ceil(list.count / 20))}
                  </span>
                  <button
                    className="btn btn--secondary btn--small"
                    type="button"
                    onClick={() => void loadAdministrators(page + 1)}
                    disabled={!list.next || listLoading}
                  >
                    Siguiente →
                  </button>
                </div>
              )}
            </>
          )}
        </div>
      </div>
    </div>
  )
}
