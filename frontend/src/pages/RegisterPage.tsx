import { useEffect, useRef, useState, type FormEvent } from 'react'
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
  const [confirmPassword, setConfirmPassword] = useState('')
  const [birthDateDisplay, setBirthDateDisplay] = useState('')
  const nativeDatePickerRef = useRef<HTMLInputElement>(null)

  const [image, setImage] = useState<File | null>(null)
  const [accepts, setAccepts] = useState(false)
  const [showPassword, setShowPassword] = useState(false)
  const [showConfirmPassword, setShowConfirmPassword] = useState(false)
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

  /* -------- helpers de fecha de nacimiento -------- */
  function parseDisplayDateToIso(display: string): string | null {
    const trimmed = display.trim()
    const parts = trimmed.split('/')
    if (parts.length === 3) {
      const day = parseInt(parts[0], 10)
      const month = parseInt(parts[1], 10)
      const year = parseInt(parts[2], 10)
      const currentYear = new Date().getFullYear()

      if (
        day >= 1 &&
        day <= 31 &&
        month >= 1 &&
        month <= 12 &&
        year >= 1900 &&
        year <= currentYear
      ) {
        const d = new Date(year, month - 1, day)
        if (
          d.getFullYear() === year &&
          d.getMonth() === month - 1 &&
          d.getDate() === day
        ) {
          if (d < new Date()) {
            const mm = String(month).padStart(2, '0')
            const dd = String(day).padStart(2, '0')
            return `${year}-${mm}-${dd}`
          }
        }
      }
    }
    // Formato alternativo YYYY-MM-DD
    if (/^\d{4}-\d{2}-\d{2}$/.test(trimmed)) {
      const d = new Date(trimmed)
      if (!isNaN(d.getTime()) && d < new Date()) {
        return trimmed
      }
    }
    return null
  }

  function formatIsoToDisplay(iso: string): string {
    const parts = iso.split('-')
    if (parts.length === 3) {
      return `${parts[2]}/${parts[1]}/${parts[0]}`
    }
    return iso
  }

  function handleBirthDateTyping(rawValue: string) {
    const digits = rawValue.replace(/\D/g, '')
    let formatted = digits
    if (digits.length > 2 && digits.length <= 4) {
      formatted = `${digits.slice(0, 2)}/${digits.slice(2)}`
    } else if (digits.length > 4) {
      formatted = `${digits.slice(0, 2)}/${digits.slice(2, 4)}/${digits.slice(4, 8)}`
    }

    setBirthDateDisplay(formatted)
    const iso = parseDisplayDateToIso(formatted)
    update('birth_date', iso || '')
  }

  function handleNativeDatePickerChange(isoValue: string) {
    if (!isoValue) return
    const display = formatIsoToDisplay(isoValue)
    setBirthDateDisplay(display)
    update('birth_date', isoValue)
  }

  function openNativeDatePicker() {
    if (nativeDatePickerRef.current) {
      if ('showPicker' in HTMLInputElement.prototype) {
        try {
          nativeDatePickerRef.current.showPicker()
        } catch {
          nativeDatePickerRef.current.focus()
        }
      } else {
        nativeDatePickerRef.current.focus()
      }
    }
  }

  /* -------- helpers de formulario -------- */
  const update = (key: string, value: string) => {
    setForm((prev) => ({ ...prev, [key]: value }))
    setFieldErrors((prev) => {
      const next = { ...prev }
      delete next[key]
      return next
    })
  }

  /** Validación antes de enviar al backend. */
  function validate(): boolean {
    const errors: FieldErrors = {}

    if (!form.document_number.trim())
      errors.document_number = ['Este campo es obligatorio.']
    if (!form.first_name.trim())
      errors.first_name = ['Este campo es obligatorio.']
    if (!form.last_name.trim())
      errors.last_name = ['Este campo es obligatorio.']

    // Validación de fecha de nacimiento
    if (!birthDateDisplay.trim()) {
      errors.birth_date = ['Este campo es obligatorio.']
    } else {
      const parsedIso = parseDisplayDateToIso(birthDateDisplay)
      if (!parsedIso) {
        errors.birth_date = [
          'Fecha inválida. Escriba en formato Día/Mes/Año (ejemplo: 15/06/1980) o selecciónela con el calendario.',
        ]
      }
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

    // Validación de contraseña (mínimo 8 caracteres y al menos un número)
    if (!form.password) {
      errors.password = ['Este campo es obligatorio.']
    } else if (form.password.length < 8) {
      errors.password = ['La contraseña debe tener al menos 8 caracteres.']
    } else if (!/\d/.test(form.password)) {
      errors.password = ['La contraseña debe contener al menos un número.']
    }

    // Confirmación de contraseña
    if (!confirmPassword) {
      errors.password_confirmation = ['Debe confirmar su contraseña.']
    } else if (form.password !== confirmPassword) {
      errors.password_confirmation = ['Las contraseñas no coinciden.']
    }

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

    const isoDate = parseDisplayDateToIso(birthDateDisplay) || form.birth_date

    const payload: Record<string, string | boolean> = {
      email: form.email,
      username: form.username,
      first_name: form.first_name,
      last_name: form.last_name,
      document_number: form.document_number,
      birth_date: isoDate,
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
        if (err.status === 400 && err.details) {
          const mapped: FieldErrors = {}
          for (const [key, value] of Object.entries(err.details)) {
            mapped[key] = Array.isArray(value)
              ? value.map(String)
              : [String(value)]
          }
          setFieldErrors(mapped)
        }
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
              electrónico. Revise su bandeja de entrada y haga clic en el enlace
              para activar su cuenta.
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
    <div className="page page--narrow" style={{ maxWidth: 680 }}>
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
                  placeholder="Ej. 1020304050"
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
                  placeholder="Ej. Carlos Arturo"
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
                  placeholder="Ej. Gómez Pérez"
                />
                {fieldError('last_name')}
              </div>

              {/* Input mejorado de fecha de nacimiento */}
              <div className="form-group">
                <label className="form-label" htmlFor="reg-bdate">
                  Fecha de nacimiento
                  <span className="form-label__required">*</span>
                </label>
                <div className="date-input-group">
                  <input
                    id="reg-bdate"
                    type="text"
                    inputMode="numeric"
                    className={`form-input ${fieldErrors.birth_date ? 'form-input--error' : ''}`}
                    value={birthDateDisplay}
                    onChange={(e) => handleBirthDateTyping(e.target.value)}
                    placeholder="DD/MM/AAAA (ej. 15/06/1980)"
                    maxLength={10}
                  />
                  <button
                    type="button"
                    className="date-picker-btn"
                    onClick={openNativeDatePicker}
                    title="Seleccionar fecha en el calendario"
                    aria-label="Abrir calendario"
                  >
                    📅
                  </button>
                  <input
                    ref={nativeDatePickerRef}
                    type="date"
                    tabIndex={-1}
                    className="date-native-hidden"
                    onChange={(e) => handleNativeDatePickerChange(e.target.value)}
                    max={new Date().toISOString().split('T')[0]}
                  />
                </div>
                <span className="form-hint">
                  Escriba Día/Mes/Año o pulse el calendario 📅.
                </span>
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
                  placeholder="Ej. Bogotá"
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
                  <option value="">Seleccione su género</option>
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
                  placeholder="correo@ejemplo.com"
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
                  placeholder="Ej. cgomez80"
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
                  placeholder="Ej. Calle 100 # 15-20, Bogotá"
                />
                {fieldError('billing_address')}
              </div>
            </div>
          </div>

          {/* --- Seguridad --- */}
          <div className="form-section">
            <h2 className="form-section__title">Seguridad y contraseña</h2>
            <div className="form-grid">
              <div className="form-group">
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
                <span className="form-hint">
                  Mínimo 8 caracteres e incluir al menos un número.
                </span>
                {fieldError('password')}
              </div>

              <div className="form-group">
                <label className="form-label" htmlFor="reg-pass-confirm">
                  Confirmar contraseña<span className="form-label__required">*</span>
                </label>
                <div className="password-wrapper">
                  <input
                    id="reg-pass-confirm"
                    type={showConfirmPassword ? 'text' : 'password'}
                    className={`form-input ${fieldErrors.password_confirmation ? 'form-input--error' : ''}`}
                    value={confirmPassword}
                    onChange={(e) => {
                      setConfirmPassword(e.target.value)
                      setFieldErrors((prev) => {
                        const next = { ...prev }
                        delete next.password_confirmation
                        return next
                      })
                    }}
                    autoComplete="new-password"
                  />
                  <button
                    type="button"
                    className="password-toggle"
                    onClick={() => setShowConfirmPassword(!showConfirmPassword)}
                    aria-label={
                      showConfirmPassword
                        ? 'Ocultar contraseña'
                        : 'Mostrar contraseña'
                    }
                  >
                    {showConfirmPassword ? 'Ocultar' : 'Ver'}
                  </button>
                </div>
                <span className="form-hint">
                  Vuelva a escribir la misma contraseña.
                </span>
                {fieldError('password_confirmation')}
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
                  Formatos permitidos: PNG, JPEG o WebP. Máximo 2 MB.
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
            {busy ? 'Registrando cuenta...' : 'Crear mi cuenta'}
          </button>
        </form>

        <div className="login-footer">
          ¿Ya tiene una cuenta creada?{' '}
          <Link to="/login">Iniciar sesión aquí</Link>
        </div>
      </div>
    </div>
  )
}
