import { useEffect, useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { api, ApiError, toFormData } from '../api'

interface Policy {
  reference: string
  version: string
  url: string
  is_test_document: boolean
}

type FieldErrors = Record<string, string[]>

export default function RegisterPage() {
  /* -------- estado -------- */
  const [policy, setPolicy] = useState<Policy | null>(null)
  const [policyError, setPolicyError] = useState('')
  const [form, setForm] = useState({
    document_number: '',
    first_name: '',
    last_name: '',
    birth_date: '',
    birth_place: '',
    billing_address: '',
    gender: '',
    email: '',
    username: '',
    password: '',
  })
  const [image, setImage] = useState<File | null>(null)
  const [accepts, setAccepts] = useState(false)
  const [showPassword, setShowPassword] = useState(false)
  const [fieldErrors, setFieldErrors] = useState<FieldErrors>({})
  const [globalError, setGlobalError] = useState('')
  const [busy, setBusy] = useState(false)
  const [success, setSuccess] = useState(false)

  /* -------- cargar política vigente -------- */
  useEffect(() => {
    api
      .get('/auth/registration-policy/')
      .then((data) => setPolicy(data))
      .catch((err) => {
        if (err instanceof ApiError) {
          setPolicyError(err.message)
        } else {
          setPolicyError(
            'No fue posible obtener la política de registro. Intente recargar la página.',
          )
        }
      })
  }, [])

  /* -------- helpers -------- */
  const update = (key: string, value: string) => {
    setForm((prev) => ({ ...prev, [key]: value }))
    // Limpiar error del campo al editar
    setFieldErrors((prev) => {
      const next = { ...prev }
      delete next[key]
      return next
    })
  }

  /** Validación básica antes de enviar al backend. */
  function validate(): boolean {
    const errors: FieldErrors = {}

    if (!form.document_number.trim())
      errors.document_number = ['Este campo es obligatorio.']
    if (!form.first_name.trim())
      errors.first_name = ['Este campo es obligatorio.']
    if (!form.last_name.trim())
      errors.last_name = ['Este campo es obligatorio.']
    if (!form.birth_date) errors.birth_date = ['Este campo es obligatorio.']
    else {
      const d = new Date(form.birth_date)
      if (isNaN(d.getTime()) || d >= new Date())
        errors.birth_date = ['Ingrese una fecha de nacimiento válida.']
    }
    if (!form.birth_place.trim())
      errors.birth_place = ['Este campo es obligatorio.']
    if (!form.billing_address.trim())
      errors.billing_address = ['Este campo es obligatorio.']
    if (!form.gender) errors.gender = ['Seleccione una opción.']
    if (!form.email.trim()) errors.email = ['Este campo es obligatorio.']
    else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(form.email))
      errors.email = ['Ingrese un correo electrónico válido.']
    if (!form.username.trim())
      errors.username = ['Este campo es obligatorio.']
    if (!form.password) errors.password = ['Este campo es obligatorio.']
    else if (form.password.length < 12)
      errors.password = ['La contraseña debe tener al menos 12 caracteres.']
    if (!accepts)
      errors.accepts_data_policy = [
        'Debe aceptar la política de tratamiento de datos.',
      ]

    setFieldErrors(errors)
    return Object.keys(errors).length === 0
  }

  /* -------- envío -------- */
  async function onSubmit(e: FormEvent) {
    e.preventDefault()
    if (!policy) return
    if (!validate()) return

    setBusy(true)
    setGlobalError('')

    const payload: Record<string, string | boolean> = {
      email: form.email,
      username: form.username,
      first_name: form.first_name,
      last_name: form.last_name,
      document_number: form.document_number,
      birth_date: form.birth_date,
      birth_place: form.birth_place,
      billing_address: form.billing_address,
      gender: form.gender,
      password: form.password,
      accepts_data_policy: true,
      policy_reference: policy.reference,
      policy_version: policy.version,
    }

    try {
      if (image) {
        await api.postMultipart('/auth/register/', toFormData(payload, image))
      } else {
        await api.post('/auth/register/', payload)
      }
      setSuccess(true)
    } catch (err) {
      if (err instanceof ApiError) {
        // Errores de validación por campo
        if (err.status === 400 && err.details) {
          const mapped: FieldErrors = {}
          for (const [key, value] of Object.entries(err.details)) {
            mapped[key] = Array.isArray(value)
              ? value.map(String)
              : [String(value)]
          }
          setFieldErrors(mapped)
        }
        // Error global
        if (err.status === 409) {
          setGlobalError(
            'Ya existe una cuenta registrada con ese correo electrónico. Puede iniciar sesión o recuperar su contraseña.',
          )
        } else if (err.status === 429) {
          setGlobalError(
            'Se ha excedido el límite de solicitudes. Por favor espere unos minutos antes de intentar de nuevo.',
          )
        } else if (err.status === 503) {
          setGlobalError(
            err.code === 'password_check_unavailable'
              ? 'No fue posible verificar la seguridad de la contraseña en este momento. Intente de nuevo en unos segundos.'
              : 'El servicio de registro no está disponible en este momento.',
          )
        } else if (!err.details || Object.keys(err.details).length === 0) {
          setGlobalError(err.message)
        }
      } else {
        setGlobalError(
          'No fue posible contactar el servidor. Verifique su conexión a internet.',
        )
      }
    } finally {
      setBusy(false)
    }
  }

  /* -------- render: éxito -------- */
  if (success) {
    return (
      <div className="page page--narrow">
        <div className="form-container">
          <h1 className="form-title">Registro exitoso</h1>
          <div className="alert alert--success">
            <span className="alert__title">¡Su cuenta ha sido creada!</span>
            <span className="alert__body">
              Hemos enviado un correo de verificación a su dirección de correo
              electrónico. Revise su bandeja de entrada (y la carpeta de spam) y
              haga clic en el enlace para activar su cuenta.
            </span>
          </div>
          <div className="mt-2">
            <Link to="/login" className="btn btn--primary btn--full">
              Ir a iniciar sesión
            </Link>
          </div>
        </div>
      </div>
    )
  }

  /* -------- render: formulario -------- */
  const fieldError = (name: string) =>
    fieldErrors[name] ? (
      <span className="form-error">{fieldErrors[name].join(' ')}</span>
    ) : null

  return (
    <div className="page page--narrow" style={{ maxWidth: 640 }}>
      <div className="form-container">
        <h1 className="form-title">Crear cuenta</h1>
        <p className="form-subtitle">
          Complete los datos a continuación para registrarse como cliente.
        </p>

        {policyError && (
          <div className="alert alert--error">
            <span className="alert__title">Servicio no disponible</span>
            <span className="alert__body">{policyError}</span>
          </div>
        )}

        {globalError && (
          <div className="alert alert--error">
            <span className="alert__body">{globalError}</span>
          </div>
        )}

        {policy?.is_test_document && (
          <div className="alert alert--info">
            <span className="alert__body">
              Entorno de desarrollo: la política de datos es un documento de
              prueba.
            </span>
          </div>
        )}

        <form onSubmit={onSubmit} noValidate>
          {/* --- Datos personales --- */}
          <div className="form-section">
            <h2 className="form-section__title">Datos personales</h2>
            <div className="form-grid">
              <div className="form-group">
                <label className="form-label" htmlFor="reg-doc">
                  Número de documento
                  <span className="form-label__required">*</span>
                </label>
                <input
                  id="reg-doc"
                  className={`form-input ${fieldErrors.document_number ? 'form-input--error' : ''}`}
                  value={form.document_number}
                  onChange={(e) => update('document_number', e.target.value)}
                  maxLength={20}
                />
                {fieldError('document_number')}
              </div>

              <div className="form-group">
                <label className="form-label" htmlFor="reg-fname">
                  Nombres<span className="form-label__required">*</span>
                </label>
                <input
                  id="reg-fname"
                  className={`form-input ${fieldErrors.first_name ? 'form-input--error' : ''}`}
                  value={form.first_name}
                  onChange={(e) => update('first_name', e.target.value)}
                  maxLength={150}
                />
                {fieldError('first_name')}
              </div>

              <div className="form-group">
                <label className="form-label" htmlFor="reg-lname">
                  Apellidos<span className="form-label__required">*</span>
                </label>
                <input
                  id="reg-lname"
                  className={`form-input ${fieldErrors.last_name ? 'form-input--error' : ''}`}
                  value={form.last_name}
                  onChange={(e) => update('last_name', e.target.value)}
                  maxLength={150}
                />
                {fieldError('last_name')}
              </div>

              <div className="form-group">
                <label className="form-label" htmlFor="reg-bdate">
                  Fecha de nacimiento
                  <span className="form-label__required">*</span>
                </label>
                <input
                  id="reg-bdate"
                  type="date"
                  className={`form-input ${fieldErrors.birth_date ? 'form-input--error' : ''}`}
                  value={form.birth_date}
                  onChange={(e) => update('birth_date', e.target.value)}
                />
                {fieldError('birth_date')}
              </div>

              <div className="form-group">
                <label className="form-label" htmlFor="reg-bplace">
                  Lugar de nacimiento
                  <span className="form-label__required">*</span>
                </label>
                <input
                  id="reg-bplace"
                  className={`form-input ${fieldErrors.birth_place ? 'form-input--error' : ''}`}
                  value={form.birth_place}
                  onChange={(e) => update('birth_place', e.target.value)}
                />
                {fieldError('birth_place')}
              </div>

              <div className="form-group">
                <label className="form-label" htmlFor="reg-gender">
                  Género<span className="form-label__required">*</span>
                </label>
                <select
                  id="reg-gender"
                  className={`form-select ${fieldErrors.gender ? 'form-input--error' : ''}`}
                  value={form.gender}
                  onChange={(e) => update('gender', e.target.value)}
                >
                  <option value="">Seleccione</option>
                  <option value="MASCULINO">Masculino</option>
                  <option value="FEMENINO">Femenino</option>
                  <option value="OTRO">Otro</option>
                </select>
                {fieldError('gender')}
              </div>
            </div>
          </div>

          {/* --- Contacto y cuenta --- */}
          <div className="form-section">
            <h2 className="form-section__title">Datos de contacto y cuenta</h2>
            <div className="form-grid">
              <div className="form-group">
                <label className="form-label" htmlFor="reg-email">
                  Correo electrónico
                  <span className="form-label__required">*</span>
                </label>
                <input
                  id="reg-email"
                  type="email"
                  className={`form-input ${fieldErrors.email ? 'form-input--error' : ''}`}
                  value={form.email}
                  onChange={(e) => update('email', e.target.value)}
                  maxLength={254}
                  autoComplete="email"
                />
                {fieldError('email')}
              </div>

              <div className="form-group">
                <label className="form-label" htmlFor="reg-username">
                  Nombre de usuario
                  <span className="form-label__required">*</span>
                </label>
                <input
                  id="reg-username"
                  className={`form-input ${fieldErrors.username ? 'form-input--error' : ''}`}
                  value={form.username}
                  onChange={(e) => update('username', e.target.value)}
                  maxLength={150}
                  autoComplete="username"
                />
                {fieldError('username')}
              </div>

              <div className="form-group form-group--full">
                <label className="form-label" htmlFor="reg-addr">
                  Dirección de facturación
                  <span className="form-label__required">*</span>
                </label>
                <input
                  id="reg-addr"
                  className={`form-input ${fieldErrors.billing_address ? 'form-input--error' : ''}`}
                  value={form.billing_address}
                  onChange={(e) => update('billing_address', e.target.value)}
                />
                {fieldError('billing_address')}
              </div>
            </div>
          </div>

          {/* --- Seguridad --- */}
          <div className="form-section">
            <h2 className="form-section__title">Seguridad</h2>
            <div className="form-grid">
              <div className="form-group form-group--full">
                <label className="form-label" htmlFor="reg-pass">
                  Contraseña<span className="form-label__required">*</span>
                </label>
                <div className="password-wrapper">
                  <input
                    id="reg-pass"
                    type={showPassword ? 'text' : 'password'}
                    className={`form-input ${fieldErrors.password ? 'form-input--error' : ''}`}
                    value={form.password}
                    onChange={(e) => update('password', e.target.value)}
                    autoComplete="new-password"
                  />
                  <button
                    type="button"
                    className="password-toggle"
                    onClick={() => setShowPassword(!showPassword)}
                    aria-label={
                      showPassword ? 'Ocultar contraseña' : 'Mostrar contraseña'
                    }
                  >
                    {showPassword ? 'Ocultar' : 'Ver'}
                  </button>
                </div>
                <span className="form-hint">Mínimo 12 caracteres.</span>
                {fieldError('password')}
              </div>

              <div className="form-group form-group--full">
                <label className="form-label" htmlFor="reg-image">
                  Imagen de perfil (opcional)
                </label>
                <input
                  id="reg-image"
                  type="file"
                  className="form-input"
                  accept="image/png,image/jpeg,image/webp"
                  onChange={(e) => setImage(e.target.files?.[0] ?? null)}
                />
                <span className="form-hint">
                  Formatos: PNG, JPEG o WebP. Máximo 2 MB.
                </span>
                {fieldError('image')}
              </div>
            </div>
          </div>

          {/* --- Aceptación --- */}
          <div className="form-section">
            <label className="form-checkbox">
              <input
                type="checkbox"
                checked={accepts}
                onChange={(e) => {
                  setAccepts(e.target.checked)
                  setFieldErrors((prev) => {
                    const next = { ...prev }
                    delete next.accepts_data_policy
                    return next
                  })
                }}
              />
              <span className="form-checkbox__text">
                He leído y acepto la{' '}
                {policy?.url ? (
                  <a href={policy.url} target="_blank" rel="noopener noreferrer">
                    política de tratamiento de datos
                  </a>
                ) : (
                  'política de tratamiento de datos'
                )}
                .
              </span>
            </label>
            {fieldError('accepts_data_policy')}
          </div>

          <button
            type="submit"
            className="btn btn--primary btn--full"
            disabled={busy || !policy}
          >
            {busy ? 'Registrando...' : 'Registrarse'}
          </button>
        </form>

        <div className="login-footer">
          ¿Ya tiene una cuenta?{' '}
          <Link to="/login">Iniciar sesión</Link>
        </div>
      </div>
    </div>
  )
}

