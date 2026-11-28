import { useCallback, useEffect, useState } from 'react'
import { Link } from 'react-router-dom'
import { api, ApiError } from '../api'
import { useOperationKey } from '../operations'
import { Dialog } from './UI'
interface Method {
  id: number
  tipo: string
  alias: string
  titular: string
  cardholder_first_name: string
  cardholder_last_name: string
  marca: string
  numero_enmascarado: string
  activo: boolean
  disponibilidad: 'DISPONIBLE' | 'VENCIDO' | 'INACTIVO'
  mes_vencimiento: number | null
  anio_vencimiento: number | null
}
interface Movement { id: number; tipo: string; valor: string; saldo_resultante: string; referencia: string; creado_en: string }
export default function WalletPanel({ onBalance }: { onBalance?: (balance: string) => void }) {
  const [balance, setBalance] = useState('')
  const [methods, setMethods] = useState<Method[]>([])
  const [movements, setMovements] = useState<Movement[]>([])
  const [next, setNext] = useState<string | null>(null)
  const [selected, setSelected] = useState('')
  const [amount, setAmount] = useState('1000')
  const [busy, setBusy] = useState(false)
  const [notice, setNotice] = useState('')
  const [confirmDeposit, setConfirmDeposit] = useState(false)
  const [removeMethod, setRemoveMethod] = useState<Method | null>(null)
  const key = useOperationKey()
  const load = useCallback(async () => {
    const [wallet, firstMethods, history] = await Promise.all([api.get('/sales/wallet/'), api.get('/sales/wallet/payment-methods/'), api.get('/sales/wallet/movements/')])
    const all = [...firstMethods.results]
    let page = firstMethods.next
    while (page) { const url = new URL(page, location.origin); const data = await api.get(url.pathname.replace('/api/v1', '') + url.search); all.push(...data.results); page = data.next }
    setBalance(wallet.balance); setMethods(all); setMovements(history.results); setNext(history.next)
    onBalance?.(wallet.balance)
  }, [onBalance])
  useEffect(() => { load().catch(() => setNotice('No se pudo cargar la billetera.')) }, [load])
  const errorText = (error: unknown) => error instanceof ApiError ? `${error.message} ${Object.values(error.details).flat().join(' ')}` : 'No se confirmó el resultado. Puedes reintentar la misma operación.'
  async function deposit() {
    if (!selected) return
    const payload = { monto: amount, medio_pago_id: Number(selected) }
    setBusy(true); setNotice('')
    try {
      await api.postWithHeaders('/sales/wallet/deposit/', payload, { 'Idempotency-Key': key.forRequest(payload) })
      key.clear(); setNotice('Depósito confirmado.'); try { await load() } catch { setNotice('Depósito confirmado. No fue posible actualizar el saldo visible; recarga la consulta antes de otra operación.') }
    } catch (e) { setNotice(errorText(e)) } finally { setBusy(false); setConfirmDeposit(false) }
  }
  async function remove(method: Method) {
    setBusy(true)
    try {
      await api.delete(`/sales/wallet/payment-methods/${method.id}/`)
      setNotice('Método de pago eliminado.')
      setRemoveMethod(null)
      await load()
    } catch (e) {
      setNotice(errorText(e))
    } finally {
      setBusy(false)
    }
  }
  async function more() {
    if (!next) return
    try { const url = new URL(next, location.origin); const data = await api.get(url.pathname.replace('/api/v1', '') + url.search); setMovements([...movements, ...data.results]); setNext(data.next) } catch (e) { setNotice(errorText(e)) }
  }
  return (
    <section className="wallet-panel form-container" aria-label="Billetera">
      <header className="wallet-panel__header">
        <div>
          <h2>Billetera</h2>
        </div>
        <p className="wallet-panel__balance">
          Saldo disponible <strong>${balance || '…'} COP</strong>
        </p>
      </header>
      {notice && <p role="status" className="alert">{notice}</p>}

      <div className="wallet-panel__section">
        <h3>Métodos de pago registrados</h3>
        {!methods.length && (
          <div className="empty-state">
            <strong>Aún no tienes métodos de pago.</strong>
            <p>Añade tu primer método para agregar dinero a tu billetera.</p>
            <Link className="btn btn--primary" to="/metodos/nueva">Añadir tarjeta</Link>
          </div>
        )}
        <div className="wallet-panel__methods">
          {methods.map((method) => (
            <div className="wallet-panel__method" key={method.id}>
              <div>
                <strong>{method.marca ? `${method.marca === 'MASTERCARD' ? 'Mastercard' : 'Visa'} ${method.numero_enmascarado}` : method.alias}</strong>
                <div>
                  {method.cardholder_first_name || method.cardholder_last_name
                    ? `${method.cardholder_first_name} ${method.cardholder_last_name}`
                    : method.titular}
                  {method.mes_vencimiento && ` · Vence ${String(method.mes_vencimiento).padStart(2, '0')}/${String(method.anio_vencimiento).slice(-2)}`}
                </div>
                <span className={`tag tag--${method.disponibilidad === 'DISPONIBLE' ? 'success' : 'warning'}`}>
                  {method.disponibilidad === 'DISPONIBLE' ? 'Disponible' : method.disponibilidad === 'VENCIDO' ? 'Vencido' : 'Inactivo'}
                </span>
              </div>
              {method.activo && (
                <div className="wallet-panel__actions">
                  <button type="button" className="btn btn--secondary btn--small" disabled={busy} onClick={() => setRemoveMethod(method)}>
                    Eliminar método de pago
                  </button>
                </div>
              )}
            </div>
          ))}
        </div>
        {methods.length > 0 && (
          <Link className="btn btn--secondary" to="/metodos/nueva" style={{ marginTop: '0.75rem' }}>
            Añadir otra tarjeta
          </Link>
        )}
      </div>

      <div className="wallet-panel__section">
        <h3>Añadir dinero</h3>
        <div className="wallet-panel__deposit-form">
          <label className="form-group">
            Método de pago registrado
            <select className="form-select" value={selected} onChange={event => setSelected(event.target.value)}>
              <option value="">Selecciona un método</option>
              {methods.filter(method => method.activo && method.disponibilidad === 'DISPONIBLE').map(method => (
                <option key={method.id} value={method.id}>{method.marca ? `${method.marca === 'MASTERCARD' ? 'Mastercard' : 'Visa'} ${method.numero_enmascarado}` : method.alias}</option>
              ))}
            </select>
          </label>
          <label className="form-group">
            Monto COP
            <input className="form-input" type="number" min="1000" step="0.01" value={amount} onChange={event => setAmount(event.target.value)} />
          </label>
          <button type="button" className="btn btn--primary" disabled={busy || !selected || Number(amount) < 1000} onClick={() => setConfirmDeposit(true)}>
            Confirmar depósito
          </button>
        </div>
      </div>

      <div className="wallet-panel__section">
        <h3>Actividad reciente</h3>
        {!movements.length && <p>No hay movimientos.</p>}
        <ul className="wallet-panel__movements">
          {movements.map(movement => {
            const descriptions: Record<string, string> = {
              DEPOSITO: 'Dinero añadido',
              COMPRA: 'Compra de tiquetes',
              REEMBOLSO: 'Reembolso',
              RETIRO: 'Retiro',
            }
            const date = new Date(movement.creado_en).toLocaleString('es-CO', {
              dateStyle: 'medium',
              timeStyle: 'short',
            })
            const amount = new Intl.NumberFormat('es-CO', {
              style: 'currency',
              currency: 'COP',
              maximumFractionDigits: 2,
            }).format(Number(movement.valor))
            return (
              <li key={movement.id}>
                <strong>{descriptions[movement.tipo] ?? movement.tipo}</strong>
                <span> · {date} · {movement.referencia}</span>
                <strong className={movement.tipo === 'COMPRA' || movement.tipo === 'RETIRO' ? '' : 'movement-positive'}> · {movement.tipo === 'COMPRA' || movement.tipo === 'RETIRO' ? '−' : '+'}{amount}</strong>
              </li>
            )
          })}
        </ul>
        {next && <button type="button" className="btn btn--secondary btn--small" disabled={busy} onClick={more}>Más movimientos</button>}
      </div>
      {confirmDeposit && (
        <Dialog title="Confirmar depósito" onClose={() => setConfirmDeposit(false)} closeDisabled={busy}>
          <p>Revisa el importe y el método antes de confirmar.</p>
          <div className="movement-summary">
            <span>Importe</span>
            <strong>{new Intl.NumberFormat('es-CO', { style: 'currency', currency: 'COP' }).format(Number(amount))}</strong>
          </div>
          <div className="movement-summary">
            <span>Método de pago</span>
            <strong>
              {(() => {
                const method = methods.find((item) => item.id === Number(selected))
                return method?.marca
                  ? `${method.marca === 'MASTERCARD' ? 'Mastercard' : 'Visa'} ${method.numero_enmascarado}`
                  : method?.alias ?? 'No seleccionado'
              })()}
            </strong>
          </div>
          <div className="form-actions">
            <button type="button" className="btn btn--primary" disabled={busy} onClick={deposit}>
              {busy ? 'Confirmando…' : 'Confirmar depósito'}
            </button>
            <button type="button" className="btn btn--secondary" disabled={busy} onClick={() => setConfirmDeposit(false)}>
              Volver
            </button>
          </div>
        </Dialog>
      )}
      {removeMethod && (
        <Dialog title="Eliminar método de pago" onClose={() => setRemoveMethod(null)} closeDisabled={busy}>
          <p>El método dejará de estar disponible. Los movimientos históricos se conservarán.</p>
          <div className="form-actions">
            <button type="button" className="btn btn--danger" disabled={busy} onClick={() => remove(removeMethod)}>
              {busy ? 'Eliminando…' : 'Eliminar método de pago'}
            </button>
            <button type="button" className="btn btn--secondary" disabled={busy} onClick={() => setRemoveMethod(null)}>
              Cancelar
            </button>
          </div>
        </Dialog>
      )}
    </section>
  )
}
