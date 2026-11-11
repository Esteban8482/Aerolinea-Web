import { Link, useLocation } from 'react-router-dom'

interface HeaderProps {
  authenticated: boolean
  role: string | null
  onLogout: () => void
}

export default function Header({ authenticated, role, onLogout }: HeaderProps) {
  const location = useLocation()

  const isActive = (path: string) =>
    location.pathname === path ? 'site-header__link site-header__link--active' : 'site-header__link'

  return (
    <header className="site-header">
      <Link to="/" className="site-header__brand">
        ✈ Alas
      </Link>

      <nav className="site-header__nav">
        <Link to="/vuelos" className={isActive('/vuelos')}>
          ✈ Vuelos
        </Link>
        {authenticated ? (
          <div className="site-header__user">
            {role === 'ROOT' && (
              <Link to="/administradores" className={isActive('/administradores')}>
                🛠️ Crear Administrador
              </Link>
            )}
            <Link to="/perfil" className={isActive('/perfil')}>
              👤 Mi perfil
            </Link>
            <span className="user-role-tag">
              {role === 'ROOT'
                ? 'ROOT'
                : role === 'ADMINISTRADOR'
                  ? 'Admin'
                  : 'Cliente'}
            </span>
            <button className="btn--header" type="button" onClick={onLogout}>
              Cerrar sesión
            </button>
          </div>
        ) : (
          <>
            <Link to="/registro" className={isActive('/registro')}>
              Registro
            </Link>
            <Link to="/login" className={isActive('/login')}>
              Iniciar sesión
            </Link>
          </>
        )}
      </nav>
    </header>
  )
}
