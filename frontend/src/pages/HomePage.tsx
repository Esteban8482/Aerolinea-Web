import { Link } from 'react-router-dom'

export default function HomePage() {
  return (
    <main className="home-page">
      <section className="home-hero">
        <div className="home-hero__content">
          <span className="home-eyebrow">Vuela diferente · Viaja más lejos</span>
          <h1 className="home-hero__title">
            Tu próximo destino
            <span> empieza aquí.</span>
          </h1>
          <p className="home-hero__subtitle">
            Encuentra nuevas rutas, guarda tus viajes y disfruta una experiencia
            simple desde la búsqueda hasta el abordaje.
          </p>
          <div className="home-actions">
            <Link to="/registro" className="btn btn--primary">
              Crear cuenta <span aria-hidden="true">→</span>
            </Link>
            <Link to="/login" className="btn btn--secondary">
              Ya tengo una cuenta
            </Link>
          </div>
          <div className="home-trust">
            <span className="home-trust__avatars" aria-hidden="true">✦ ✈ ●</span>
            <span>Más de 2.000 viajeros ya vuelan con Alas</span>
          </div>
        </div>
        <div className="home-hero__visual" aria-label="Resumen de un viaje destacado">
          <div className="home-route-card">
            <div className="home-route-card__top">
              <span>Ruta destacada</span>
              <span className="home-route-card__status">● Disponible</span>
            </div>
            <div className="home-route">
              <div>
                <strong>PEI</strong>
                <span>Pereira</span>
              </div>
              <div className="home-route__line"><span>✈</span></div>
              <div className="home-route__destination">
                <strong>MAD</strong>
                <span>Madrid</span>
              </div>
            </div>
            <div className="home-route-card__bottom">
              <span>Vuelo directo · 9h 35min</span>
              <strong>Desde $1.249.000</strong>
            </div>
          </div>
          <div className="home-floating-card home-floating-card--top">
            <span className="home-floating-card__icon">↗</span>
            <span><strong>12</strong> destinos por explorar</span>
          </div>
          <div className="home-floating-card home-floating-card--bottom">
            <span className="home-floating-card__icon">✓</span>
            <span><strong>Reserva fácil</strong><br />en pocos pasos</span>
          </div>
        </div>
      </section>

      <section className="home-section">
        <div className="home-section__heading">
          <div>
            <span className="home-eyebrow">Inspírate</span>
            <h2>Destinos que te están esperando</h2>
          </div>
          <span className="home-section__hint">Próximamente en Alas</span>
        </div>
        <div className="destination-grid">
          <article className="destination-card destination-card--pink">
            <span className="destination-card__code">MAD</span>
            <div>
              <h3>Madrid</h3>
              <p>Historia, arte y atardeceres</p>
            </div>
            <span className="destination-card__arrow">↗</span>
          </article>
          <article className="destination-card destination-card--blue">
            <span className="destination-card__code">MDE</span>
            <div>
              <h3>Medellín</h3>
              <p>Ciudad de la eterna primavera</p>
            </div>
            <span className="destination-card__arrow">↗</span>
          </article>
          <article className="destination-card destination-card--purple">
            <span className="destination-card__code">NYC</span>
            <div>
              <h3>Nueva York</h3>
              <p>La ciudad que nunca duerme</p>
            </div>
            <span className="destination-card__arrow">↗</span>
          </article>
        </div>
      </section>

      <section className="home-benefits">
        <div>
          <span className="home-eyebrow">Todo en un solo lugar</span>
          <h2>Planea el viaje. Nosotros cuidamos el resto.</h2>
        </div>
        <div className="benefit-list">
          <div className="benefit-item"><span>01</span><div><h3>Busca con libertad</h3><p>Explora rutas y encuentra el vuelo que se adapta a tus planes.</p></div></div>
          <div className="benefit-item"><span>02</span><div><h3>Gestiona tus tiquetes</h3><p>Ten tus reservas y datos de viaje siempre a la mano.</p></div></div>
          <div className="benefit-item"><span>03</span><div><h3>Viaja con tranquilidad</h3><p>Una experiencia clara, segura y pensada para ti.</p></div></div>
        </div>
      </section>

      <section className="home-cta">
        <div>
          <span className="home-eyebrow">Tu aventura comienza hoy</span>
          <h2>¿Listo para despegar?</h2>
        </div>
        <Link to="/registro" className="btn btn--light">Empezar ahora <span aria-hidden="true">→</span></Link>
      </section>
    </main>
  )
}
