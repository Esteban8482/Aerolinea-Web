import { Link } from 'react-router-dom'

export default function HomePage() {
  return (
    <div className="page page--wide">
      <div className="home-hero">
        <h1 className="home-hero__title">Bienvenido a Alas</h1>
        <p className="home-hero__subtitle">
          Tu aerolínea de confianza. Regístrate para reservar vuelos, gestionar
          tus tiquetes y disfrutar de la mejor experiencia de viaje.
        </p>
        <div className="home-actions">
          <Link to="/registro" className="btn btn--primary">
            Crear cuenta
          </Link>
          <Link to="/login" className="btn btn--secondary">
            Iniciar sesión
          </Link>
        </div>
      </div>
    </div>
  )
}

