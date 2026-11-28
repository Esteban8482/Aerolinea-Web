import { Link, useLocation } from 'react-router-dom'
import {
  ClipboardCheck,
  LogIn,
  LogOut,
  Plane,
  UserRound,
  UserRoundPlus,
} from 'lucide-react'

interface HeaderProps {
  authenticated: boolean
  role: string | null
  logoutBusy: boolean
  onLogout: () => void
}

export default function Header({
  authenticated,
  role,
  logoutBusy,
  onLogout,
}: HeaderProps) {
  const location = useLocation()

  const isActive = (path: string) => location.pathname === path
  const linkClassName = (path: string) =>
    `site-header__link${isActive(path) ? ' site-header__link--active' : ''}`

  return (
    <header className="site-header"><div className="site-header__inner">
      <Link to="/" className="site-header__brand">
        <Plane aria-hidden="true" size={24} />
        <span>Alas</span>
      </Link>

      <nav className="site-header__nav" aria-label="Navegación principal">
        <Link
          to="/vuelos"
          className={linkClassName('/vuelos')}
          aria-current={isActive('/vuelos') ? 'page' : undefined}
        >
          <Plane aria-hidden="true" size={16} />
          <span>Vuelos</span>
        </Link>
        {(!authenticated || role === 'CLIENTE') && (
          <Link
            to="/check-in"
            className={linkClassName('/check-in')}
            aria-current={isActive('/check-in') ? 'page' : undefined}
          >
            <ClipboardCheck aria-hidden="true" size={16} />
            <span>Check-in</span>
          </Link>
        )}
        {authenticated ? (
          <div className="site-header__user">
            {role === 'ROOT' && (
              <Link
                to="/administradores"
                className={linkClassName('/administradores')}
                aria-current={isActive('/administradores') ? 'page' : undefined}
              >
                <UserRoundPlus aria-hidden="true" size={16} />
                <span>Crear administrador</span>
              </Link>
            )}
            <Link
              to="/perfil"
              className={linkClassName('/perfil')}
              aria-current={isActive('/perfil') ? 'page' : undefined}
            >
              <UserRound aria-hidden="true" size={16} />
              <span>Mi perfil</span>
            </Link>
            <span className="user-role-tag">
              {role === 'ROOT'
                ? 'ROOT'
                : role === 'ADMINISTRADOR'
                  ? 'Administrador'
                  : 'Cliente'}
            </span>
            <button
              className="btn--header"
              type="button"
              onClick={onLogout}
              disabled={logoutBusy}
              aria-busy={logoutBusy}
            >
              <LogOut aria-hidden="true" size={16} />
              {logoutBusy ? 'Cerrando sesión…' : 'Cerrar sesión'}
            </button>
          </div>
        ) : (
          <>
            <Link
              to="/registro"
              className={linkClassName('/registro')}
              aria-current={isActive('/registro') ? 'page' : undefined}
            >
              <UserRoundPlus aria-hidden="true" size={16} />
              Registro
            </Link>
            <Link
              to="/login"
              className={`${linkClassName('/login')} site-header__link--account`}
              aria-current={isActive('/login') ? 'page' : undefined}
            >
              <LogIn aria-hidden="true" size={16} />
              Iniciar sesión
            </Link>
          </>
        )}
      </nav>
    </div></header>
  )
}
