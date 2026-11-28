import { useRef, useState, type FormEvent } from 'react'
import { useNavigate } from 'react-router-dom'
import { api, ApiError } from '../api'
import LocationFields from '../components/LocationFields'
import { Field, Feedback } from '../components/UI'

type FieldErrors = Record<string, string[]>

export default function AddCardPage({ session }: {
  session: { authenticated: boolean; role: string | null; is_email_verified: boolean }
}) {
  const navigate = useNavigate()
  const submission = useRef(false)
  const [firstName, setFirstName] = useState('')
  const [lastName, setLastName] = useState('')
  const [number, setNumber] = useState('')
  const [expiry, setExpiry] = useState('')
  const [cvv, setCvv] = useState('')
  const [address, setAddress] = useState('')
  const [postalCode, setPostalCode] = useState('')
  const [location, setLocation] = useState({ country: '', subdivision: '', city: '' })
  const [errors, setErrors] = useState<FieldErrors>({})
  const [notice, setNotice] = useState('')
  const [busy, setBusy] = useState(false)

  if (!session.authenticated || session.role !== 'CLIENTE' || !session.is_email_verified) {
    return (
      <main className="auth-page">
        <section className="card auth-card">
          <h1>Añadir tarjeta</h1>
          <p>Solo clientes con correo verificado pueden registrar métodos de pago.</p>
        </section>
      </main>
    )
  }

  const digits = number.replace(/\D/g, '').slice(0, 16)
  const brand = digits === '4111' + '1111' + '1111' + '1111'
    ? 'VISA'
    : digits === '5555' + '5555' + '5555' + '4444'
      ? 'MASTERCARD'
      : ''

  function formatCard(raw: string) {
    const clean = raw.replace(/\D/g, '').slice(0, 16)
    setNumber(clean.replace(/(.{4})(?=.)/g, '$1 '))
  }

  function formatExpiry(raw: string) {
    const clean = raw.replace(/\D/g, '').slice(0, 4)
    setExpiry(clean.length > 2 ? `${clean.slice(0, 2)}/${clean.slice(2)}` : clean)
  }

  function validate() {
    const next: FieldErrors = {}
    if (!firstName.trim()) next.cardholder_first_name = ['Ingresa los nombres del titular.']
    if (!lastName.trim()) next.cardholder_last_name = ['Ingresa los apellidos del titular.']
    if (!digits) next.numero = ['Ingresa el número de tarjeta.']
    else if (digits.length !== 16) next.numero = ['La tarjeta debe tener 16 dígitos.']
    else if (!brand) next.numero = ['Usa una tarjeta sintética Visa o Mastercard documentada.']
    if (!/^(0[1-9]|1[0-2])\/\d{2}$/.test(expiry)) {
      next.mes_vencimiento = ['Ingresa una fecha de vencimiento válida en formato MM/AA.']
    } else {
      const month = Number(expiry.slice(0, 2))
      const year = 2000 + Number(expiry.slice(3))
      const now = new Date()
      if (year < now.getFullYear() || (year === now.getFullYear() && month < now.getMonth() + 1)) {
        next.mes_vencimiento = ['La tarjeta está vencida.']
      }
    }
    if (!/^\d{3}$/.test(cvv)) next.cvv = ['El código de seguridad debe tener 3 dígitos.']
    if (!location.country) next.billing_country_id = ['Selecciona el país de facturación.']
    if (!location.city) next.billing_city_id = ['Selecciona la ciudad de facturación.']
    if (!address.trim()) next.billing_address = ['Ingresa la dirección de facturación.']
    setErrors(next)
    return Object.keys(next).length === 0
  }

  async function submit(event: FormEvent) {
    event.preventDefault()
    if (submission.current || !validate()) return
    submission.current = true
    setBusy(true)
    setNotice('')
    const month = Number(expiry.slice(0, 2))
    const year = 2000 + Number(expiry.slice(3))
    try {
      await api.post('/sales/wallet/payment-methods/', {
        tipo: 'TARJETA',
        titular: `${firstName.trim()} ${lastName.trim()}`,
        cardholder_first_name: firstName.trim(),
        cardholder_last_name: lastName.trim(),
        numero: digits,
        mes_vencimiento: month,
        anio_vencimiento: year,
        billing_country_id: Number(location.country),
        billing_subdivision_id: location.subdivision ? Number(location.subdivision) : undefined,
        billing_city_id: Number(location.city),
        billing_address: address.trim(),
        postal_code: postalCode.trim(),
      })
      navigate('/perfil', { replace: true })
    } catch (error) {
      if (error instanceof ApiError) {
        const mapped: FieldErrors = {}
        for (const [key, value] of Object.entries(error.details)) {
          mapped[key] = Array.isArray(value) ? value.map(String) : [String(value)]
        }
        setErrors(mapped)
        if (!Object.keys(mapped).length) setNotice(error.message)
      } else {
        setNotice('No fue posible confirmar el registro de la tarjeta.')
      }
    } finally {
      submission.current = false
      setBusy(false)
    }
  }

  const error = (key: string) =>
    errors[key]?.length ? <span className="form-error">{errors[key].join(' ')}</span> : null

  return (
    <main className="page page--narrow">
      <div className="page-head">
        <div>
          <h1>Añadir tarjeta</h1>
          <p>Guarda un método de pago para tus próximos viajes.</p>
        </div>
      </div>
      <section className="card">
        <form onSubmit={submit} noValidate>
          {notice && <Feedback>{notice}</Feedback>}
          <div className="section-header">
            <h2>Información de la tarjeta</h2>
            <div className="card-brands" aria-label="Marcas admitidas">
              <span className={brand === 'VISA' ? 'card-brand card-brand--active' : 'card-brand'}>VISA</span>
              <span className={brand === 'MASTERCARD' ? 'card-brand card-brand--active' : 'card-brand'}>Mastercard</span>
            </div>
          </div>
          <div className="notice notice--info">
            Entorno de demostración. Usa únicamente datos sintéticos: Visa 4111 1111 1111 1111 o Mastercard 5555 5555 5555 4444.
          </div>
          <div className="form-grid">
            <Field
              label="Nombres del titular"
              value={firstName}
              onChange={(event) => setFirstName(event.target.value)}
              maxLength={80}
              autoComplete="cc-name"
              error={errors.cardholder_first_name?.join(' ')}
            />
            <Field
              label="Apellidos del titular"
              value={lastName}
              onChange={(event) => setLastName(event.target.value)}
              maxLength={80}
              autoComplete="cc-family-name"
              error={errors.cardholder_last_name?.join(' ')}
            />
            <div className="form-group">
              <label className="form-label" htmlFor="card-number">Número de tarjeta</label>
              <input
                id="card-number"
                className="form-input"
                inputMode="numeric"
                autoComplete="off"
                maxLength={19}
                placeholder="0000 0000 0000 0000"
                value={number}
                onChange={(event) => formatCard(event.target.value)}
              />
              {error('numero')}
            </div>
            <div className="form-grid form-grid--two">
              <div className="form-group">
                <label className="form-label" htmlFor="card-expiry">Fecha de vencimiento</label>
                <input
                  id="card-expiry"
                  className="form-input"
                  inputMode="numeric"
                  autoComplete="off"
                  maxLength={5}
                  placeholder="MM/AA"
                  value={expiry}
                  onChange={(event) => formatExpiry(event.target.value)}
                />
                {error('mes_vencimiento')}
              </div>
              <div className="form-group">
                <label className="form-label" htmlFor="card-cvv">Código de seguridad (CVV)</label>
                <input
                  id="card-cvv"
                  className="form-input"
                  type="password"
                  inputMode="numeric"
                  autoComplete="off"
                  maxLength={3}
                  placeholder="•••"
                  value={cvv}
                  onChange={(event) => setCvv(event.target.value.replace(/\D/g, '').slice(0, 3))}
                />
                {error('cvv')}
              </div>
            </div>
          </div>

          <LocationFields
            label="Dirección de facturación"
            onChange={() => undefined}
            onDetails={(details) => {
              setLocation(details)
              setErrors((current) => {
                const next = { ...current }
                delete next.billing_country_id
                delete next.billing_subdivision_id
                delete next.billing_city_id
                return next
              })
            }}
          />
          {error('billing_country_id')}
          {error('billing_subdivision_id')}
          {error('billing_city_id')}

          <div className="form-grid">
            <Field
              label="Dirección"
              value={address}
              onChange={(event) => setAddress(event.target.value)}
              maxLength={200}
              autoComplete="street-address"
              error={errors.billing_address?.join(' ')}
            />
            <Field
              label="Código postal (opcional)"
              value={postalCode}
              onChange={(event) => setPostalCode(event.target.value)}
              maxLength={20}
              autoComplete="postal-code"
            />
          </div>

          <div className="form-actions">
            <button type="submit" className="btn btn--primary" disabled={busy} aria-busy={busy}>
              {busy ? 'Guardando tarjeta…' : 'Añadir tarjeta'}
            </button>
            <button type="button" className="btn btn--secondary" disabled={busy} onClick={() => navigate('/perfil')}>
              Cancelar
            </button>
          </div>
        </form>
      </section>
    </main>
  )
}
