import { useCallback, useEffect, useState, type FormEvent } from 'react'
import { Link } from 'react-router-dom'
import { api, ApiError } from '../api'
import SeatManager from '../components/SeatManager'
import CatalogueSelect from '../components/CatalogueSelect'
import type { Tiquete } from '../types/flight'

interface CheckInPageProps {
  session: {
    authenticated: boolean
    role: string | null
    is_email_verified: boolean
  }
}

interface GuestAccessForm {
  locator: string
  document_type: string
  document: string
  email: string
}

function isCheckInOpen(ticket: Tiquete) {
  const departure = new Date(ticket.vuelo.salida_utc).getTime()
  const now = Date.now()
  return ticket.estado === 'ACTIVO' && ticket.vuelo.estado === 'PROGRAMADO' && now >= departure - 24 * 60 * 60 * 1000 && now < departure
}

function formatDeparture(value: string) {
  return new Date(value).toLocaleString('es-CO', {
    dateStyle: 'medium',
    timeStyle: 'short',
  })
}

export default function CheckInPage({ session }: CheckInPageProps) {
  const [group, setGroup] = useState('')
  const [tickets, setTickets] = useState<Tiquete[]>([])
  const [selectedIds, setSelectedIds] = useState<number[]>([])
  const [guestToken, setGuestToken] = useState('')
  const [loading, setLoading] = useState(false)
  const [submitting, setSubmitting] = useState(false)
  const [notification, setNotification] = useState<{
    type: 'success' | 'error' | 'info'
    message: string
  } | null>(null)
  const [guestForm, setGuestForm] = useState<GuestAccessForm>({
    locator: '',
    document_type: 'CC',
    document: '',
    email: '',
  })
  const [requestingLink, setRequestingLink] = useState(false)

  const loadTickets = useCallback(async (token?: string) => {
    setLoading(true)
    try {
      const allTickets: Tiquete[] = []
      let path = '/sales/check-in/'
      let hasNextPage = true
      while (hasNextPage) {
        const data = token
          ? await api.getWithHeaders(path, { 'X-Checkin-Token': token })
          : await api.get(path)
        const results = Array.isArray(data) ? data : data.results
        if (Array.isArray(results)) allTickets.push(...results)

        if (Array.isArray(data) || !data.next) {
          hasNextPage = false
        } else {
          const nextUrl = new URL(data.next, window.location.origin)
          path = `/sales/check-in/${nextUrl.search}`
        }
      }
      setTickets(allTickets)
      setGroup(previous => allTickets.some(t => `${t.purchase_id}:${t.vuelo.id}` === previous) ? previous : allTickets.length ? `${allTickets[0].purchase_id}:${allTickets[0].vuelo.id}` : '')
      setSelectedIds([])
    } catch (error) {
      const message =
        error instanceof ApiError
          ? error.message
          : 'No fue posible consultar los tiquetes habilitados para check-in.'
      setNotification({ type: 'error', message })
      setTickets([])
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    const fragment = new URLSearchParams(window.location.hash.slice(1))
    const token = fragment.get('token')
    if (token) {
      window.history.replaceState(
        null,
        document.title,
        `${window.location.pathname}${window.location.search}`,
      )
      setGuestToken(token)
      void loadTickets(token)
    }
  }, [loadTickets])

  useEffect(() => {
    if (session.authenticated && session.role === 'CLIENTE' && !guestToken) {
      void loadTickets()
    }
  }, [guestToken, loadTickets, session.authenticated, session.role])

  function toggleTicket(ticketId: number) {
    setSelectedIds((ids) =>
      ids.includes(ticketId) ? ids.filter((id) => id !== ticketId) : [...ids, ticketId],
    )
  }

  async function handleCheckIn() {
    if (selectedIds.length === 0) return
    setSubmitting(true)
    setNotification(null)
    try {
      const headers: Record<string, string> = guestToken
        ? { 'X-Checkin-Token': guestToken }
        : {}
      await api.postWithHeaders('/sales/check-in/', { ticket_ids: selectedIds }, headers)
      setNotification({
        type: 'success',
        message: 'Check-in confirmado. Ya puedes descargar el pasabordo de cada tiquete.',
      })
      await loadTickets(guestToken || undefined)
    } catch (error) {
      const message =
        error instanceof ApiError ? error.message : 'No fue posible confirmar el check-in.'
      setNotification({ type: 'error', message })
    } finally {
      setSubmitting(false)
    }
  }

  async function handleDownload(ticket: Tiquete) {
    setNotification(null)
    try {
      const headers: Record<string, string> = guestToken
        ? { 'X-Checkin-Token': guestToken }
        : {}
      const pdf = await api.getBlobWithHeaders(
        `/sales/tickets/${ticket.id}/boarding-pass/`,
        headers,
      )
      const url = URL.createObjectURL(pdf)
      const link = document.createElement('a')
      link.href = url
      link.download = `pasabordo-${ticket.codigo_tiquete}.pdf`
      document.body.appendChild(link)
      link.click()
      link.remove()
      window.setTimeout(() => URL.revokeObjectURL(url), 1000)
    } catch (error) {
      const message =
        error instanceof ApiError ? error.message : 'No fue posible descargar el pasabordo.'
      setNotification({ type: 'error', message })
    }
  }

  async function handleRequestLink(event: FormEvent<HTMLFormElement>) {
    event.preventDefault()
    setRequestingLink(true)
    setNotification(null)
    try {
      const response = await api.post('/sales/check-in/access/', {
        ...guestForm,
        locator: guestForm.locator.trim().toUpperCase(),
        document_type: guestForm.document_type.trim().toUpperCase(),
        document: guestForm.document.trim(),
        email: guestForm.email.trim().toLowerCase(),
      })
      setNotification({
        type: 'success',
        message:
          response.message ??
          'Si los datos corresponden a un tiquete habilitado, recibirás un enlace de acceso.',
      })
    } catch (error) {
      const message =
        error instanceof ApiError
          ? error.message
          : 'No fue posible solicitar el enlace de check-in.'
      setNotification({ type: 'error', message })
    } finally {
      setRequestingLink(false)
    }
  }

  const canLoadSessionTickets =
    session.authenticated && session.role === 'CLIENTE' && !guestToken

  return (
    <main className="journey-page">
      <header className="journey-header">
        <div>
          <span className="journey-eyebrow">Tu viaje, a un paso</span>
          <h1>Check-in y pasabordo</h1>
          <p>
            Confirma tu viaje dentro de las 24 horas previas a la salida y descarga tu
            pasabordo en PDF.
          </p>
        </div>
        {canLoadSessionTickets && (
          <Link className="btn btn--secondary" to="/perfil">
            Mis compras y sillas
          </Link>
        )}
      </header>

      {notification && (
        <div className={`alert alert--${notification.type}`} role="status">
          <span className="alert__body">{notification.message}</span>
        </div>
      )}

      {guestToken || canLoadSessionTickets ? (
        <section className="journey-panel">
          <div className="journey-panel__heading">
            <div>
              <span className="journey-eyebrow">Tiquetes disponibles</span>
              <h2>Prepara tu abordaje</h2>
            </div>
            <button
              type="button"
              className="btn btn--secondary btn--small"
              onClick={() => void loadTickets(guestToken || undefined)}
              disabled={loading}
            >
              {loading ? 'Actualizando…' : 'Actualizar'}
            </button>
          </div>

          {loading ? (
            <p className="journey-empty">Consultando tus tiquetes…</p>
          ) : tickets.length === 0 ? (
            <div className="journey-empty">
              <strong>No hay tiquetes disponibles en este acceso.</strong>
              <span>Verifica la compra o solicita un nuevo enlace seguro.</span>
            </div>
          ) : (
            <div className="journey-ticket-list">
              <label>Compra y vuelo<select className="form-select" value={group} onChange={e => { setGroup(e.target.value); setSelectedIds([]) }}>{[...new Map(tickets.map(t => [`${t.purchase_id}:${t.vuelo.id}`, t])).entries()].map(([key, t]) => <option key={key} value={key}>{t.locator} · {t.vuelo.codigo_vuelo} · {formatDeparture(t.vuelo.salida_utc)}</option>)}</select></label>
              {tickets.filter(t => `${t.purchase_id}:${t.vuelo.id}` === group).map((ticket) => {
                const checkInOpen = isCheckInOpen(ticket)
                const confirmed = ticket.estado === 'ACTIVO' && ticket.vuelo.estado !== 'CANCELADO' && ticket.estado_checkin === 'CONFIRMADO'
                const selectable = ticket.estado === 'ACTIVO' && checkInOpen && !confirmed
                return (
                  <article className="journey-ticket" key={ticket.id}>
                    <div className="journey-ticket__select">
                      <input
                        id={`ticket-${ticket.id}`}
                        type="checkbox"
                        checked={selectedIds.includes(ticket.id)}
                        onChange={() => toggleTicket(ticket.id)}
                        disabled={!selectable || submitting}
                        aria-label={`Seleccionar tiquete ${ticket.codigo_tiquete}`}
                      />
                    </div>
                    <div className="journey-ticket__main">
                      <div className="journey-ticket__top">
                        <div>
                          <span className="journey-ticket__code">{ticket.codigo_tiquete}</span>
                          <h3>
                            {ticket.vuelo.origen} <span aria-hidden="true">→</span>{' '}
                            {ticket.vuelo.destino}
                          </h3>
                        </div>
                        <span
                          className={`journey-status ${
                            confirmed ? 'journey-status--done' : checkInOpen ? 'journey-status--open' : ''
                          }`}
                        >
                          {confirmed
                            ? 'Check-in confirmado'
                            : checkInOpen
                              ? 'Check-in disponible'
                              : 'Aún no disponible'}
                        </span>
                      </div>
                      <div className="journey-ticket__details">
                        <span>Vuelo {ticket.vuelo.codigo_vuelo}</span>
                        <span>Salida {formatDeparture(ticket.vuelo.salida_utc)}</span>
                        <span>
                          {ticket.viajero.nombres} {ticket.viajero.apellidos}
                        </span>
                        <span>
                          Silla {ticket.silla.numero_silla} ·{' '}
                          {ticket.clase === 'PRIMERA_CLASE' ? 'Primera clase' : 'Económica'}
                        </span>
                      </div>
                      {!confirmed && !checkInOpen && (
                        <p className="journey-ticket__hint">
                          El check-in se habilita 24 horas antes de la salida.
                        </p>
                      )}
                      <SeatManager ticket={ticket} token={guestToken || undefined} onChanged={() => { loadTickets(guestToken || undefined) }} />
                      {confirmed && (
                        <button
                          type="button"
                          className="btn btn--primary btn--small journey-ticket__download"
                          onClick={() => void handleDownload(ticket)}
                        >
                          Descargar pasabordo PDF
                        </button>
                      )}
                    </div>
                  </article>
                )
              })}
            </div>
          )}

          {tickets.some(
            (ticket) => ticket.estado === 'ACTIVO' && isCheckInOpen(ticket) && ticket.estado_checkin !== 'CONFIRMADO',
          ) && (
            <div className="journey-actions">
              <p>Selecciona los tiquetes habilitados que deseas confirmar.</p>
              <button
                type="button"
                className="btn btn--primary"
                onClick={() => void handleCheckIn()}
                disabled={selectedIds.length === 0 || submitting}
              >
                {submitting ? 'Confirmando…' : `Confirmar check-in (${selectedIds.length})`}
              </button>
            </div>
          )}
        </section>
      ) : (
        <section className="journey-login-callout">
          <div>
            <span className="journey-eyebrow">¿Ya tienes una cuenta?</span>
            <h2>Consulta tus tiquetes desde tu sesión</h2>
            <p>También puedes acceder de forma segura con el enlace enviado al correo del viajero.</p>
          </div>
          <Link to="/login?next=/check-in" className="btn btn--primary">
            Iniciar sesión
          </Link>
        </section>
      )}

      {!guestToken && (
        <section className="journey-panel journey-guest">
          <div className="journey-panel__heading">
            <div>
              <span className="journey-eyebrow">Acceso para viajeros</span>
              <h2>Solicitar enlace de check-in</h2>
            </div>
          </div>
          <p className="journey-panel__copy">
            Ingresa los datos asociados al tiquete. Enviaremos un enlace privado al correo
            registrado para el viajero.
          </p>
          <form className="journey-form" onSubmit={handleRequestLink}>
            <div className="journey-form__grid">
              <div className="form-group">
                <label className="form-label" htmlFor="guest-locator">Localizador</label>
                <input
                  id="guest-locator"
                  className="form-input"
                  value={guestForm.locator}
                  onChange={(event) =>
                    setGuestForm({ ...guestForm, locator: event.target.value.toUpperCase() })
                  }
                  minLength={6}
                  maxLength={6}
                  required
                  autoComplete="off"
                />
              </div>
              <CatalogueSelect category="document_type" label="Tipo de documento" value={guestForm.document_type} onChange={document_type => setGuestForm({ ...guestForm, document_type })} />
              <div className="form-group">
                <label className="form-label" htmlFor="guest-document">Número de documento</label>
                <input
                  id="guest-document"
                  className="form-input"
                  value={guestForm.document}
                  onChange={(event) => setGuestForm({ ...guestForm, document: event.target.value })}
                  required
                  autoComplete="off"
                />
              </div>
              <div className="form-group">
                <label className="form-label" htmlFor="guest-email">Correo registrado</label>
                <input
                  id="guest-email"
                  type="email"
                  className="form-input"
                  value={guestForm.email}
                  onChange={(event) => setGuestForm({ ...guestForm, email: event.target.value })}
                  required
                  autoComplete="email"
                />
              </div>
            </div>
            <button type="submit" className="btn btn--primary" disabled={requestingLink}>
              {requestingLink ? 'Enviando solicitud…' : 'Enviar enlace seguro'}
            </button>
            <p className="form-hint">
              Por seguridad, la respuesta no confirma si los datos coinciden con un tiquete.
            </p>
          </form>
        </section>
      )}
    </main>
  )
}
