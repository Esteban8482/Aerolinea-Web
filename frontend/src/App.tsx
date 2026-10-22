import { useMemo, useState, type FormEvent } from 'react'
import {
  ArrowUpRight,
  Bell,
  CalendarDays,
  Check,
  ChevronRight,
  CircleHelp,
  Clock3,
  FileText,
  Filter,
  LayoutDashboard,
  LockKeyhole,
  Mail,
  Menu,
  Plane,
  Plus,
  Search,
  Settings2,
  Sparkles,
  Ticket,
  UserRound,
  X,
} from 'lucide-react'

type Activity = {
  date: string
  title: string
  detail: string
  status: 'Completado' | 'Pendiente'
  icon: 'ticket' | 'file'
}

type AuthMode = 'login' | 'register' | 'recover' | 'verify'

const activities: Activity[] = [
  { date: '16 OCT 2026', title: 'Perfil actualizado', detail: 'Datos personales y preferencias', status: 'Completado', icon: 'file' },
  { date: '02 OCT 2026', title: 'Documento cargado', detail: 'Cédula de ciudadanía · terminada en 42', status: 'Completado', icon: 'file' },
  { date: 'Próximamente', title: 'Tu itinerario aparecerá aquí', detail: 'Cuando conectemos tus viajes', status: 'Pendiente', icon: 'ticket' },
]

const navItems = [
  { label: 'Resumen', icon: LayoutDashboard },
  { label: 'Mis datos', icon: UserRound },
  { label: 'Documentos', icon: FileText },
]

function App() {
  const [activeNav, setActiveNav] = useState('Resumen')
  const [isSidebarOpen, setIsSidebarOpen] = useState(false)
  const [isDialogOpen, setIsDialogOpen] = useState(false)
  const [query, setQuery] = useState('')
  const [showOnlyPending, setShowOnlyPending] = useState(false)
  const [toast, setToast] = useState('')
  const [screen, setScreen] = useState<'dashboard' | 'auth'>('dashboard')
  const [authMode, setAuthMode] = useState<AuthMode>('login')

  const filteredActivities = useMemo(() => {
    const normalizedQuery = query.toLowerCase().trim()
    return activities.filter((activity) => {
      const matchesQuery = `${activity.title} ${activity.detail} ${activity.status}`.toLowerCase().includes(normalizedQuery)
      return matchesQuery && (!showOnlyPending || activity.status === 'Pendiente')
    })
  }, [query, showOnlyPending])

  const showToast = (message: string) => {
    setToast(message)
    window.setTimeout(() => setToast(''), 3200)
  }

  if (screen === 'auth') {
    return <AuthScreen mode={authMode} onModeChange={setAuthMode} onBack={() => setScreen('dashboard')} />
  }

  return (
    <div className="app-shell">
      <aside className={`sidebar ${isSidebarOpen ? 'sidebar--open' : ''}`}>
        <div className="brand-lockup">
          <div className="brand-mark"><Plane size={20} strokeWidth={2.5} /></div>
          <span>alas<span className="brand-dot">.</span></span>
        </div>

        <div className="sidebar-section-label">Tu espacio</div>
        <nav className="main-nav" aria-label="Navegación principal">
          {navItems.map(({ label, icon: Icon }) => (
            <button
              key={label}
              className={`nav-item ${activeNav === label ? 'nav-item--active' : ''}`}
              onClick={() => { setActiveNav(label); setIsSidebarOpen(false) }}
            >
              <Icon size={18} />
              <span>{label}</span>
              {activeNav === label && <span className="nav-indicator" />}
            </button>
          ))}
        </nav>

        <div className="sidebar-bottom">
          <button className="nav-item" onClick={() => showToast('La configuración estará disponible pronto.')}>
            <Settings2 size={18} /><span>Preferencias</span>
          </button>
          <div className="support-card">
            <div className="support-icon"><CircleHelp size={18} /></div>
            <strong>¿Necesitas ayuda?</strong>
            <span>Estamos para acompañarte.</span>
            <button onClick={() => showToast('Un asesor se pondrá en contacto contigo.')}>Contactar <ArrowUpRight size={14} /></button>
          </div>
          <button className="user-mini user-mini--button" onClick={() => { setAuthMode('login'); setScreen('auth') }}>
            <div className="avatar avatar--small">MR</div>
            <div><strong>Mariana Ríos</strong><span>Cliente</span></div>
            <ChevronRight size={16} className="muted-icon" />
          </button>
        </div>
      </aside>

      {isSidebarOpen && <button className="sidebar-scrim" aria-label="Cerrar menú" onClick={() => setIsSidebarOpen(false)} />}

      <main className="main-content">
        <header className="topbar">
          <button className="icon-button mobile-menu" aria-label="Abrir menú" onClick={() => setIsSidebarOpen(true)}><Menu size={21} /></button>
          <div className="breadcrumb"><span>Mi espacio</span><ChevronRight size={15} /><strong>{activeNav}</strong></div>
          <div className="topbar-actions">
            <button className="icon-button notification-button" aria-label="Notificaciones" onClick={() => showToast('No tienes notificaciones nuevas.')}><Bell size={19} /><span /></button>
            <div className="avatar">MR</div>
          </div>
        </header>

        <div className="page-content">
          <section className="welcome-row fade-in">
            <div>
              <p className="eyebrow"><Sparkles size={14} /> EXPERIENCIA ALAS</p>
              <h1>Hola, Mariana<span className="accent-dot">.</span></h1>
              <p className="intro">Todo listo para que tu próximo viaje empiece sin complicaciones.</p>
            </div>
            <div className="date-chip"><CalendarDays size={17} /><span>Miércoles, 21 de octubre</span></div>
          </section>

          <section className="journey-banner fade-in delay-1">
            <div className="banner-copy">
              <p className="eyebrow eyebrow--light">PREPARA TU PRÓXIMO VUELO</p>
              <h2>Tu viaje comienza<br /><em>mucho antes de despegar.</em></h2>
              <p>Estamos preparando nuevas herramientas para acompañarte en cada etapa.</p>
              <button className="light-button" onClick={() => showToast('Te avisaremos cuando esta experiencia esté lista.')}>Conocer más <ArrowUpRight size={16} /></button>
            </div>
            <div className="banner-visual" aria-hidden="true">
              <div className="sun-disc" />
              <div className="route-line route-line--one" />
              <div className="route-line route-line--two" />
              <Plane className="banner-plane" size={92} strokeWidth={1.1} />
              <span className="city-label city-label--one">PEI</span><span className="city-label city-label--two">BOG</span>
            </div>
          </section>

          <section className="overview-grid fade-in delay-2">
            <article className="summary-card">
              <div className="summary-icon summary-icon--coral"><Ticket size={20} /></div>
              <div><span className="card-label">Próximos viajes</span><strong className="summary-value">0</strong><span className="summary-note">Aún no tienes itinerarios</span></div>
              <button className="round-arrow" aria-label="Ver próximos viajes" onClick={() => showToast('La gestión de viajes estará disponible pronto.')}><ArrowUpRight size={17} /></button>
            </article>
            <article className="summary-card">
              <div className="summary-icon summary-icon--yellow"><Clock3 size={20} /></div>
              <div><span className="card-label">Estado del perfil</span><strong className="summary-value summary-value--text">En orden</strong><span className="summary-note">Última revisión hoy</span></div>
              <button className="round-arrow" aria-label="Editar perfil" onClick={() => setActiveNav('Mis datos')}><ArrowUpRight size={17} /></button>
            </article>
            <article className="summary-card summary-card--accent">
              <div className="summary-icon summary-icon--navy"><Plus size={20} /></div>
              <div><span className="card-label">Acceso rápido</span><strong className="summary-value summary-value--text">Completa tu perfil</strong><span className="summary-note">Solo te tomará un minuto</span></div>
              <button className="round-arrow round-arrow--dark" aria-label="Completar perfil" onClick={() => setIsDialogOpen(true)}><ArrowUpRight size={17} /></button>
            </article>
          </section>

          <section className="workspace-grid fade-in delay-3">
            <div className="activity-panel">
              <div className="panel-heading">
                <div><p className="eyebrow">ACTIVIDAD</p><h2>Lo más reciente</h2></div>
                <div className="panel-tools">
                  <div className="search-field"><Search size={16} /><input value={query} onChange={(event) => setQuery(event.target.value)} placeholder="Buscar" aria-label="Buscar actividad" /></div>
                  <button className={`filter-button ${showOnlyPending ? 'filter-button--active' : ''}`} onClick={() => setShowOnlyPending(!showOnlyPending)}><Filter size={15} /> {showOnlyPending ? 'Pendientes' : 'Filtrar'}</button>
                </div>
              </div>
              <div className="table-wrap">
                <table>
                  <thead><tr><th>FECHA</th><th>ACTIVIDAD</th><th>ESTADO</th><th><span className="sr-only">Acciones</span></th></tr></thead>
                  <tbody>
                    {filteredActivities.map((activity) => <tr key={activity.title}>
                      <td className="date-cell">{activity.date}</td>
                      <td><div className="activity-name"><span className={`activity-icon activity-icon--${activity.icon}`}>{activity.icon === 'ticket' ? <Ticket size={16} /> : <FileText size={16} />}</span><span><strong>{activity.title}</strong><small>{activity.detail}</small></span></div></td>
                      <td><span className={`status-pill status-pill--${activity.status === 'Completado' ? 'done' : 'pending'}`}>{activity.status === 'Completado' && <Check size={13} />}{activity.status}</span></td>
                      <td><button className="row-action" aria-label={`Ver ${activity.title}`} onClick={() => showToast(`Abriendo: ${activity.title}`)}><ChevronRight size={17} /></button></td>
                    </tr>)}
                  </tbody>
                </table>
                {filteredActivities.length === 0 && <div className="empty-state"><Search size={20} /><span>No encontramos actividades con esos filtros.</span><button onClick={() => { setQuery(''); setShowOnlyPending(false) }}>Limpiar filtros</button></div>}
              </div>
              <button className="view-all" onClick={() => showToast('Mostrando el historial completo próximamente.')}>Ver historial completo <ArrowUpRight size={16} /></button>
            </div>

            <aside className="profile-panel">
              <div className="profile-panel-top"><p className="eyebrow eyebrow--light">TU PERFIL</p><button className="dots-button" aria-label="Más opciones"><span /><span /><span /></button></div>
              <div className="avatar avatar--large">MR</div><h2>Mariana Ríos</h2><p>Viajera frecuente</p>
              <div className="profile-rule" />
              <div className="profile-data"><span>Correo electrónico</span><strong>mariana.rios@mail.com</strong></div>
              <div className="profile-data"><span>Miembro desde</span><strong>Octubre de 2026</strong></div>
              <button className="profile-button" onClick={() => setIsDialogOpen(true)}>Editar información <ArrowUpRight size={16} /></button>
            </aside>
          </section>
        </div>
      </main>

      {isDialogOpen && <div className="dialog-backdrop" role="presentation" onMouseDown={(event) => { if (event.target === event.currentTarget) setIsDialogOpen(false) }}>
        <section className="dialog" role="dialog" aria-modal="true" aria-labelledby="dialog-title">
          <div className="dialog-heading"><div><p className="eyebrow">DATOS PERSONALES</p><h2 id="dialog-title">Completa tu perfil</h2></div><button className="icon-button" aria-label="Cerrar diálogo" onClick={() => setIsDialogOpen(false)}><X size={19} /></button></div>
          <p className="dialog-copy">Tus datos quedarán listos para cuando actives tus próximos servicios.</p>
          <form onSubmit={(event) => { event.preventDefault(); setIsDialogOpen(false); showToast('Cambios guardados correctamente.') }}>
            <label>Nombre completo<input defaultValue="Mariana Ríos" /></label>
            <div className="form-row"><label>Tipo de documento<select defaultValue="Cédula de ciudadanía"><option>Cédula de ciudadanía</option><option>Pasaporte</option></select></label><label>Número<input defaultValue="1.088.***.742" /></label></div>
            <label>Correo electrónico<input type="email" defaultValue="mariana.rios@mail.com" /></label>
            <div className="dialog-actions"><button type="button" className="text-button" onClick={() => setIsDialogOpen(false)}>Cancelar</button><button type="submit" className="primary-button">Guardar cambios <Check size={16} /></button></div>
          </form>
        </section>
      </div>}

      {toast && <div className="toast" role="status"><Check size={16} />{toast}</div>}
    </div>
  )
}

type AuthScreenProps = {
  mode: AuthMode
  onModeChange: (mode: AuthMode) => void
  onBack: () => void
}

function AuthScreen({ mode, onModeChange, onBack }: AuthScreenProps) {
  const isLogin = mode === 'login'
  const isRegister = mode === 'register'
  const isRecover = mode === 'recover'
  const isVerify = mode === 'verify'

  const handleSubmit = (event: FormEvent<HTMLFormElement>) => {
    event.preventDefault()
    if (isVerify) {
      onBack()
      return
    }
    onModeChange('verify')
  }

  return (
    <main className="auth-shell">
      <section className="auth-brand-panel">
        <button className="auth-back-link" onClick={onBack}><ChevronRight size={15} className="auth-back-icon" /> Volver al resumen</button>
        <div className="auth-brand-lockup"><div className="brand-mark"><Plane size={20} strokeWidth={2.5} /></div><strong>alas<span className="brand-dot">.</span></strong></div>
        <div className="auth-brand-copy"><p className="eyebrow eyebrow--light"><Sparkles size={14} /> VIAJAR EMPIEZA AQUÍ</p><h1>Un espacio pensado para <em>volar tranquilo.</em></h1><p>Guarda tus datos, recibe novedades y ten cada detalle de tu viaje a la mano.</p></div>
        <div className="auth-route-art" aria-hidden="true"><span className="route-badge route-badge--origin">PEI</span><div className="auth-route-line" /><Plane size={64} /><span className="route-badge route-badge--destination">MAD</span></div>
      </section>

      <section className="auth-form-panel">
        <div className="auth-form-card">
          {!isVerify && <div className="auth-tabs"><button className={isLogin ? 'auth-tab auth-tab--active' : 'auth-tab'} onClick={() => onModeChange('login')}>Ingresar</button><button className={isRegister ? 'auth-tab auth-tab--active' : 'auth-tab'} onClick={() => onModeChange('register')}>Crear cuenta</button></div>}
          <div className="auth-heading"><div className="auth-heading-icon">{isRecover ? <Mail size={19} /> : isVerify ? <Check size={19} /> : <LockKeyhole size={19} />}</div><p className="eyebrow">CUENTA ALAS</p><h2>{isLogin ? 'Qué bueno verte.' : isRegister ? 'Empieza tu viaje.' : isRecover ? 'Recupera tu acceso.' : 'Revisa tu correo.'}</h2><p>{isLogin ? 'Ingresa tus datos para continuar.' : isRegister ? 'Crea tu cuenta de cliente en pocos pasos.' : isRecover ? 'Te enviaremos un enlace para crear una nueva contraseña.' : 'Enviamos un código de verificación a tu correo.'}</p></div>
          {isVerify ? <form className="auth-form" onSubmit={handleSubmit}><label>Código de verificación<input autoFocus inputMode="numeric" placeholder="000 000" required /></label><button className="primary-button auth-submit" type="submit">Verificar correo <Check size={16} /></button><button className="auth-text-link" type="button">Reenviar código</button></form> : <form className="auth-form" onSubmit={handleSubmit}>
            {isRegister && <div className="auth-form-row"><label>Nombres<input placeholder="Mariana" required /></label><label>Apellidos<input placeholder="Ríos" required /></label></div>}
            <label>{isRecover ? 'Correo electrónico registrado' : 'Correo electrónico'}<input type="email" placeholder="tu@correo.com" required /></label>
            {!isRecover && <label>Contraseña<input type="password" placeholder="Mínimo 12 caracteres" minLength={12} required /></label>}
            {isRegister && <label className="auth-check"><input type="checkbox" required /><span>Acepto la política de tratamiento de datos.</span></label>}
            <button className="primary-button auth-submit" type="submit">{isLogin ? 'Iniciar sesión' : isRegister ? 'Crear mi cuenta' : 'Enviar enlace'} <ArrowUpRight size={16} /></button>
          </form>}
          <div className="auth-footer">{isLogin && <button className="auth-text-link" onClick={() => onModeChange('recover')}>¿Olvidaste tu contraseña?</button>}{isRecover && <button className="auth-text-link" onClick={() => onModeChange('login')}>Volver a iniciar sesión</button>}{isVerify && <button className="auth-text-link" onClick={() => onModeChange('login')}>Usar otro correo</button>}</div>
        </div>
        <p className="auth-legal">Al continuar aceptas nuestros términos de uso y política de privacidad.</p>
      </section>
    </main>
  )
}

export default App