import {
  useCallback,
  useEffect,
  useState,
  type FormEvent,
  type InputHTMLAttributes,
  type ReactNode,
  type SelectHTMLAttributes,
} from 'react'
import { api, ApiError, toFormData } from './api'
import './home.css'

type SessionState = {
  authenticated: boolean
  role: string | null
  is_email_verified: boolean
} | null

type Result = { ok: boolean; title: string; body: string } | null

function toErrorResult(err: unknown): Result {
  if (err instanceof ApiError) {
    const fields = Object.entries(err.details)
      .map(([key, value]) => `${key}: ${Array.isArray(value) ? value.join(' · ') : String(value)}`)
      .join('\n')
    return { ok: false, title: `Error ${err.status} · ${err.code}`, body: fields || err.message }
  }
  return { ok: false, title: 'Error de red', body: 'No fue posible contactar el backend.' }
}

function Field({ label, ...props }: InputHTMLAttributes<HTMLInputElement> & { label: string }) {
  return (
    <label className="fld">
      <span>{label}</span>
      <input {...props} />
    </label>
  )
}

function Select({
  label,
  options,
  ...props
}: SelectHTMLAttributes<HTMLSelectElement> & { label: string; options: { value: string; label: string }[] }) {
  return (
    <label className="fld">
      <span>{label}</span>
      <select {...props}>
        <option value="">Seleccione</option>
        {options.map((option) => (
          <option key={option.value} value={option.value}>{option.label}</option>
        ))}
      </select>
    </label>
  )
}

function Section({
  code,
  title,
  subtitle,
  children,
  hidden,
}: {
  code: string
  title: string
  subtitle?: string
  children: ReactNode
  hidden?: boolean
}) {
  if (hidden) return null
  return (
    <section className="card">
      <div className="card-head">
        <span className="chip">{code}</span>
        <div>
          <h2>{title}</h2>
          {subtitle && <p>{subtitle}</p>}
        </div>
      </div>
      {children}
    </section>
  )
}

function ResultView({ result }: { result: Result }) {
  if (!result) return null
  return (
    <div className={`result ${result.ok ? 'result--ok' : 'result--error'}`} role="status">
      <strong>{result.title}</strong>
      <pre>{result.body}</pre>
    </div>
  )
}

/* ------------------------------- HU-007 ------------------------------- */

function Hu007Register() {
  const [policy, setPolicy] = useState<{ reference: string; version: string; is_test_document: boolean } | null>(null)
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
    accepts: false,
  })
  const [image, setImage] = useState<File | null>(null)
  const [result, setResult] = useState<Result>(null)
  const [busy, setBusy] = useState(false)

  useEffect(() => {
    api.get('/auth/registration-policy/')
      .then(setPolicy)
      .catch((err) => setResult(toErrorResult(err)))
  }, [])

  const update = (key: string, value: string | boolean) =>
    setForm((prev) => ({ ...prev, [key]: value }))

  async function onSubmit(event: FormEvent) {
    event.preventDefault()
    if (!policy) return
    setBusy(true)
    setResult(null)
    const payload: Record<string, string | boolean> = {
      email: form.email,
      username: form.username,
      first_name: form.first_name,
      last_name: form.last_name,
      document_number: form.document_number,
      document_type: 'DNI',
      birth_date: form.birth_date,
      birth_place: form.birth_place,
      billing_address: form.billing_address,
      gender: form.gender,
      password: form.password,
      accepts_data_policy: form.accepts,
      policy_reference: policy.reference,
      policy_version: policy.version,
    }
    try {
      const data = image
        ? await api.postMultipart('/auth/register/', toFormData(payload, image))
        : await api.post('/auth/register/', payload)
      setResult({
        ok: true,
        title: 'Cliente registrado',
        body: `Estado: ${data.status} · Envío del correo de verificación: ${data.delivery}\nRevisa el outbox de desarrollo y usa la sección «Verificación y reenvío de correo».`,
      })
    } catch (err) {
      setResult(toErrorResult(err))
    } finally {
      setBusy(false)
    }
  }

  return (
    <Section
      code="HU-007"
      title="Registro de cliente"
      subtitle={
        policy
          ? `Política vigente: ${policy.reference} · ${policy.version}${policy.is_test_document ? ' (documento de prueba)' : ''}`
          : 'Consultando política vigente…'
      }
    >
      <form className="grid-2" onSubmit={onSubmit}>
        <Field label="DNI" required value={form.document_number} onChange={(e) => update('document_number', e.target.value)} />
        <Field label="Nombres" required value={form.first_name} onChange={(e) => update('first_name', e.target.value)} />
        <Field label="Apellidos" required value={form.last_name} onChange={(e) => update('last_name', e.target.value)} />
        <Field label="Fecha de nacimiento" type="date" required value={form.birth_date} onChange={(e) => update('birth_date', e.target.value)} />
        <Field label="Lugar de nacimiento" required value={form.birth_place} onChange={(e) => update('birth_place', e.target.value)} />
        <Field label="Dirección de facturación" required value={form.billing_address} onChange={(e) => update('billing_address', e.target.value)} />
        <Select
          label="Género"
          required
          value={form.gender}
          onChange={(e) => update('gender', e.target.value)}
          options={[
            { value: 'MASCULINO', label: 'Masculino' },
            { value: 'FEMENINO', label: 'Femenino' },
            { value: 'OTRO', label: 'Otro' },
          ]}
        />
        <Field label="Correo electrónico" type="email" required value={form.email} onChange={(e) => update('email', e.target.value)} />
        <Field label="Nombre de usuario" required value={form.username} onChange={(e) => update('username', e.target.value)} />
        <Field label="Contraseña" type="password" required value={form.password} onChange={(e) => update('password', e.target.value)} />
        <label className="fld fld--wide">
          <span>Imagen de usuario (opcional)</span>
          <input
            type="file"
            accept="image/png,image/jpeg,image/webp"
            onChange={(e) => setImage(e.target.files?.[0] ?? null)}
          />
        </label>
        <label className="check fld--wide">
          <input type="checkbox" required checked={form.accepts} onChange={(e) => update('accepts', e.target.checked)} />
          Acepto la política de tratamiento de datos
        </label>
        <div className="fld--wide">
          <button className="btn" type="submit" disabled={busy || !policy}>
            {busy ? 'Registrando…' : 'Registrarse'}
          </button>
        </div>
      </form>
      <ResultView result={result} />
    </Section>
  )
}

function Hu007Verify() {
  const [token, setToken] = useState('')
  const [email, setEmail] = useState('')
  const [result, setResult] = useState<Result>(null)
  const [busy, setBusy] = useState(false)

  async function verify(event: FormEvent) {
    event.preventDefault()
    setBusy(true)
    setResult(null)
    try {
      const data = await api.post('/auth/verify-email/', { token })
      setResult({ ok: true, title: 'Correo verificado', body: `Estado: ${data.status}` })
    } catch (err) {
      setResult(toErrorResult(err))
    } finally {
      setBusy(false)
    }
  }

  async function resend(event: FormEvent) {
    event.preventDefault()
    setBusy(true)
    setResult(null)
    try {
      const data = await api.post('/auth/resend-verification/', { email })
      setResult({ ok: true, title: 'Reenvío solicitado', body: `Estado: ${data.status}` })
    } catch (err) {
      setResult(toErrorResult(err))
    } finally {
      setBusy(false)
    }
  }

  return (
    <Section code="HU-007" title="Verificación y reenvío de correo" subtitle="Consume el token del correo enviado al outbox de desarrollo">
      <div className="grid-2">
        <form className="stack" onSubmit={verify}>
          <Field label="Token de verificación" required value={token} onChange={(e) => setToken(e.target.value)} />
          <button className="btn" type="submit" disabled={busy || !token}>Verificar correo</button>
        </form>
        <form className="stack" onSubmit={resend}>
          <Field label="Correo para reenvío" type="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
          <button className="btn" type="submit" disabled={busy || !email}>Reenviar verificación</button>
        </form>
      </div>
      <ResultView result={result} />
    </Section>
  )
}

/* ------------------------------- HU-008 ------------------------------- */

function SessionPanel({ session, onSessionChange }: { session: SessionState; onSessionChange: () => void }) {
  const [result, setResult] = useState<Result>(null)

  async function activity() {
    setResult(null)
    try {
      await api.post('/auth/session/activity/', {})
      setResult({ ok: true, title: 'Actividad registrada', body: 'Se renovó la ventana de inactividad (30 min).' })
    } catch (err) {
      setResult(toErrorResult(err))
    }
  }

  async function logout() {
    setResult(null)
    try {
      await api.post('/auth/logout/', {})
      setResult({ ok: true, title: 'Sesión cerrada', body: 'La sesión actual fue revocada en el servidor.' })
    } catch (err) {
      setResult(toErrorResult(err))
    } finally {
      onSessionChange()
    }
  }

  const label = !session
    ? 'Consultando sesión…'
    : session.authenticated
      ? `Autenticado · Rol: ${session.role ?? '—'} · Correo ${session.is_email_verified ? 'verificado' : 'sin verificar'}`
      : 'Visitante (sin sesión)'

  return (
    <div className="session-zone">
      <div className="session-bar">
        <span className="session-badge">{label}</span>
        <button className="btn--ghost" type="button" onClick={activity}>Registrar actividad</button>
        <button className="btn--ghost" type="button" onClick={logout} disabled={!session?.authenticated}>Cerrar sesión</button>
      </div>
      <ResultView result={result} />
    </div>
  )
}

function Hu008Login({ onSessionChange }: { onSessionChange: () => void }) {
  const [identifier, setIdentifier] = useState('')
  const [password, setPassword] = useState('')
  const [result, setResult] = useState<Result>(null)
  const [busy, setBusy] = useState(false)

  async function login(event: FormEvent) {
    event.preventDefault()
    setBusy(true)
    setResult(null)
    const credentials = identifier.includes('@')
      ? { email: identifier, password }
      : { root_id: identifier, password }
    try {
      await api.post('/auth/login/', credentials)
      setResult({ ok: true, title: 'Sesión iniciada', body: 'El estado de sesión se actualizó en la barra superior.' })
      onSessionChange()
    } catch (err) {
      setResult(toErrorResult(err))
    } finally {
      setBusy(false)
    }
  }

  return (
    <Section
      code="HU-008"
      title="Inicio de sesión"
      subtitle="Cliente por correo · ROOT por root_id · 5 fallos consecutivos bloquean el identificador 15 min"
    >
      <form className="grid-2" onSubmit={login}>
        <Field label="Correo o root_id" required autoComplete="username" value={identifier} onChange={(e) => setIdentifier(e.target.value)} />
        <Field label="Contraseña" type="password" required autoComplete="current-password" value={password} onChange={(e) => setPassword(e.target.value)} />
        <div className="fld--wide">
          <button className="btn" type="submit" disabled={busy || !identifier || !password}>Iniciar sesión</button>
        </div>
      </form>
      <ResultView result={result} />
    </Section>
  )
}

function Hu008Recovery() {
  const [email, setEmail] = useState('')
  const [token, setToken] = useState('')
  const [password, setPassword] = useState('')
  const [confirmation, setConfirmation] = useState('')
  const [result, setResult] = useState<Result>(null)
  const [busy, setBusy] = useState(false)

  // HU-008: el token llega en el fragmento #token=…; se retira de la URL de inmediato.
  useEffect(() => {
    const match = window.location.hash.match(/token=([^&]+)/)
    if (match) {
      setToken(decodeURIComponent(match[1]))
      window.history.replaceState(null, '', window.location.pathname + window.location.search)
    }
  }, [])

  async function requestRecovery(event: FormEvent) {
    event.preventDefault()
    setBusy(true)
    setResult(null)
    try {
      await api.post('/auth/password-recovery/', { email })
      setResult({
        ok: true,
        title: 'Solicitud recibida',
        body: 'Si la cuenta es elegible, se enviará un enlace de restablecimiento (vigencia 30 min) al correo. Respuesta uniforme por seguridad.',
      })
    } catch (err) {
      setResult(toErrorResult(err))
    } finally {
      setBusy(false)
    }
  }

  async function reset(event: FormEvent) {
    event.preventDefault()
    setBusy(true)
    setResult(null)
    try {
      await api.post('/auth/password-reset/', { token, password, password_confirmation: confirmation })
      setResult({ ok: true, title: 'Contraseña restablecida', body: 'Todas las sesiones de la cuenta dejaron de autenticar. Inicia sesión de nuevo.' })
    } catch (err) {
      setResult(toErrorResult(err))
    } finally {
      setBusy(false)
    }
  }

  return (
    <Section code="HU-008" title="Recuperación de acceso" subtitle="Solicitud por correo + restablecimiento con token de uso único (se precarga desde #token=… de la URL)">
      <div className="grid-2">
        <form className="stack" onSubmit={requestRecovery}>
          <Field label="Correo de la cuenta" type="email" required value={email} onChange={(e) => setEmail(e.target.value)} />
          <button className="btn" type="submit" disabled={busy || !email}>Solicitar recuperación</button>
        </form>
        <form className="stack" onSubmit={reset}>
          <Field label="Token del correo" required value={token} onChange={(e) => setToken(e.target.value)} />
          <Field label="Nueva contraseña" type="password" required autoComplete="new-password" value={password} onChange={(e) => setPassword(e.target.value)} />
          <Field label="Confirmar contraseña" type="password" required autoComplete="new-password" value={confirmation} onChange={(e) => setConfirmation(e.target.value)} />
          <button className="btn" type="submit" disabled={busy || !token || !password}>Restablecer contraseña</button>
        </form>
      </div>
      <ResultView result={result} />
    </Section>
  )
}

/* ------------------------------- HU-009 ------------------------------- */

type Admin = { id: number; email: string; first_name: string; last_name: string; role: string }
type AdminPage = { count: number; next: string | null; previous: string | null; results: Admin[] }

function Hu009Administrators() {
  const [form, setForm] = useState({ email: '', password: '', first_name: '', last_name: '', document_number: '' })
  const [list, setList] = useState<AdminPage | null>(null)
  const [page, setPage] = useState(1)
  const [result, setResult] = useState<Result>(null)
  const [busy, setBusy] = useState(false)

  const load = useCallback(async (targetPage: number) => {
    try {
      const data = await api.get(`/users/administrators/?page=${targetPage}`)
      setList(data)
      setPage(targetPage)
    } catch (err) {
      setResult(toErrorResult(err))
    }
  }, [])

  useEffect(() => {
    void load(1)
  }, [load])

  const update = (key: string, value: string) => setForm((prev) => ({ ...prev, [key]: value }))

  async function createAdmin(event: FormEvent) {
    event.preventDefault()
    setBusy(true)
    setResult(null)
    try {
      const data = await api.post('/users/administrators/', form)
      setResult({
        ok: true,
        title: 'Administrador creado',
        body: `ID: ${data.id} · Correo: ${data.email} · Rol: ${data.role} · Aviso pendiente: ${data.delivery}`,
      })
      await load(1)
    } catch (err) {
      setResult(toErrorResult(err))
    } finally {
      setBusy(false)
    }
  }

  return (
    <>
      <h3 className="subsection-title">Crear administrador</h3>
      <form className="grid-2" onSubmit={createAdmin}>
        <Field label="Correo electrónico" type="email" required value={form.email} onChange={(e) => update('email', e.target.value)} />
        <Field label="Contraseña inicial" type="password" required autoComplete="new-password" value={form.password} onChange={(e) => update('password', e.target.value)} />
        <Field label="Nombres (opcional)" value={form.first_name} onChange={(e) => update('first_name', e.target.value)} />
        <Field label="Apellidos (opcional)" value={form.last_name} onChange={(e) => update('last_name', e.target.value)} />
        <Field label="Documento (opcional)" value={form.document_number} onChange={(e) => update('document_number', e.target.value)} />
        <div className="fld--wide">
          <button className="btn" type="submit" disabled={busy || !form.email || !form.password}>Crear administrador</button>
        </div>
      </form>

      <h3 className="subsection-title">Administradores registrados (20 por página)</h3>
      <div className="table-wrap">
        <table className="admin-table">
          <thead>
            <tr><th>ID</th><th>Correo</th><th>Nombres</th><th>Apellidos</th><th>Rol</th></tr>
          </thead>
          <tbody>
            {(list?.results ?? []).map((admin) => (
              <tr key={admin.id}>
                <td>{admin.id}</td>
                <td>{admin.email}</td>
                <td>{admin.first_name}</td>
                <td>{admin.last_name}</td>
                <td>{admin.role}</td>
              </tr>
            ))}
            {list && list.results.length === 0 && (
              <tr><td colSpan={5}>No hay administradores registrados.</td></tr>
            )}
          </tbody>
        </table>
      </div>
      <div className="pager">
        <button className="btn btn--small" type="button" onClick={() => void load(page - 1)} disabled={!list?.previous}>Anterior</button>
        <span>{list ? `${list.count} resultado(s) · página ${page}` : 'Cargando…'}</span>
        <button className="btn btn--small" type="button" onClick={() => void load(page + 1)} disabled={!list?.next}>Siguiente</button>
      </div>
      <ResultView result={result} />
    </>
  )
}

function Hu009RootPassword({ onSessionChange }: { onSessionChange: () => void }) {
  const [form, setForm] = useState({ current_password: '', password: '', password_confirmation: '' })
  const [result, setResult] = useState<Result>(null)
  const [busy, setBusy] = useState(false)

  const update = (key: string, value: string) => setForm((prev) => ({ ...prev, [key]: value }))

  async function changePassword(event: FormEvent) {
    event.preventDefault()
    setBusy(true)
    setResult(null)
    try {
      await api.post('/users/root/password/', form)
      setResult({
        ok: true,
        title: 'Contraseña de ROOT actualizada',
        body: 'Todas las sesiones de ROOT (incluida la actual) dejan de autenticar en su próxima petición. Vuelve a iniciar sesión.',
      })
      onSessionChange()
    } catch (err) {
      setResult(toErrorResult(err))
    } finally {
      setBusy(false)
    }
  }

  return (
    <>
      <h3 className="subsection-title">Cambiar contraseña propia de ROOT</h3>
      <form className="grid-2" onSubmit={changePassword}>
        <Field label="Contraseña actual" type="password" required autoComplete="current-password" value={form.current_password} onChange={(e) => update('current_password', e.target.value)} />
        <Field label="Nueva contraseña" type="password" required autoComplete="new-password" value={form.password} onChange={(e) => update('password', e.target.value)} />
        <Field label="Confirmar nueva contraseña" type="password" required autoComplete="new-password" value={form.password_confirmation} onChange={(e) => update('password_confirmation', e.target.value)} />
        <div className="fld--wide">
          <button className="btn" type="submit" disabled={busy || !form.current_password || !form.password}>Cambiar contraseña</button>
        </div>
      </form>
      <ResultView result={result} />
    </>
  )
}

/* -------------------------------- Home -------------------------------- */

export default function HomeDemo() {
  const [session, setSession] = useState<SessionState>(null)

  const refreshSession = useCallback(async () => {
    try {
      const data = await api.get('/auth/session/')
      setSession({
        authenticated: data.authenticated,
        role: data.role ?? null,
        is_email_verified: Boolean(data.is_email_verified),
      })
    } catch {
      setSession({ authenticated: false, role: null, is_email_verified: false })
    }
  }, [])

  useEffect(() => {
    void refreshSession()
  }, [refreshSession])

  return (
    <div className="demo">
      <header className="demo-header">
        <h1>Home temporal · Demo para Product Owner</h1>
        <p>HU-007 Registro y verificación · HU-008 Sesión y recuperación · HU-009 Administración ROOT</p>
        <SessionPanel session={session} onSessionChange={refreshSession} />
      </header>

      <main className="demo-body">
        <Hu007Register />
        <Hu007Verify />
        <Hu008Login onSessionChange={refreshSession} />
        <Hu008Recovery />

        <Section
          code="HU-009"
          title="Administración ROOT"
          subtitle="Visible solo con sesión de ROOT: alta de administradores, lista paginada y cambio de contraseña propia"
          hidden={session?.role !== 'ROOT'}
        >
          <Hu009Administrators />
          <Hu009RootPassword onSessionChange={refreshSession} />
        </Section>
      </main>
    </div>
  )
}