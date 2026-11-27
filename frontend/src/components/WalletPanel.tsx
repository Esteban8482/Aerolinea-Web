import { useCallback, useEffect, useState, type FormEvent } from 'react'
import { api, ApiError } from '../api'
import { useOperationKey } from '../operations'
import CatalogueSelect from './CatalogueSelect'
interface Method { id: number; tipo: string; alias: string; numero_enmascarado: string; activo: boolean; mes_vencimiento: number | null; anio_vencimiento: number | null }
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
  const [form, setForm] = useState({ tipo: 'TARJETA', alias: '', titular: '', entidad: '', numero: '', mes_vencimiento: '1', anio_vencimiento: String(new Date().getFullYear()) })
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
  async function register(e: FormEvent) {
    e.preventDefault(); setBusy(true); setNotice('')
    try {
      const { mes_vencimiento, anio_vencimiento, ...rest } = form
      await api.post('/sales/wallet/payment-methods/', { ...rest, ...(form.tipo === 'TARJETA' ? { mes_vencimiento: Number(mes_vencimiento), anio_vencimiento: Number(anio_vencimiento) } : {}) })
      setForm({ ...form, numero: '', alias: '' }); setNotice('Medio simulado registrado.'); await load()
    } catch (e) { setNotice(errorText(e)) } finally { setBusy(false) }
  }
  async function deposit() {
    if (!selected || !window.confirm(`¿Confirmas el depósito simulado de $${amount} COP con el medio seleccionado?`)) return
    const payload = { monto: amount, medio_pago_id: Number(selected) }
    setBusy(true); setNotice('')
    try {
      await api.postWithHeaders('/sales/wallet/deposit/', payload, { 'Idempotency-Key': key.forRequest(payload) })
      key.clear(); setNotice('Depósito confirmado.'); try { await load() } catch { setNotice('Depósito confirmado. No fue posible actualizar el saldo visible; recarga la consulta antes de otra operación.') }
    } catch (e) { setNotice(errorText(e)) } finally { setBusy(false) }
  }
  async function manage(method: Method, deactivate = false) {
    const alias = deactivate ? null : window.prompt('Nuevo alias', method.alias)
    if (deactivate ? !window.confirm('¿Desactivar este medio de pago? Se conservará el historial.') : !alias) return
    setBusy(true)
    try { if (deactivate) await api.delete(`/sales/wallet/payment-methods/${method.id}/`); else await api.patch(`/sales/wallet/payment-methods/${method.id}/`, { alias }); await load() } catch (e) { setNotice(errorText(e)) } finally { setBusy(false) }
  }
  async function more() {
    if (!next) return
    try { const url = new URL(next, location.origin); const data = await api.get(url.pathname.replace('/api/v1', '') + url.search); setMovements([...movements, ...data.results]); setNext(data.next) } catch (e) { setNotice(errorText(e)) }
  }
  return <section className="form-container" aria-label="Billetera">
    <h2>Billetera virtual</h2><p>Simulación académica. No introduzcas datos bancarios reales ni CVV.</p><p>Saldo disponible: <strong>${balance || '…'} COP</strong></p>
    {notice && <p role="status" className="alert">{notice}</p>}
    <h3>Medios registrados</h3>
    {!methods.length && <p>No tienes medios registrados.</p>}
    {methods.map(m => <div key={m.id}><span>{m.alias} — {m.numero_enmascarado} — {m.activo ? 'Activo' : 'Inactivo'} {m.mes_vencimiento && `(vence ${m.mes_vencimiento}/${m.anio_vencimiento})`}</span>{m.activo && <><button type="button" disabled={busy} onClick={() => manage(m)}>Modificar alias</button><button type="button" disabled={busy} onClick={() => manage(m, true)}>Desactivar</button></>}</div>)}
    <details><summary>Registrar medio simulado</summary><form onSubmit={register}>
      <CatalogueSelect category="payment_method_type" label="Tipo de medio" value={form.tipo} onChange={tipo => setForm({ ...form, tipo })} />
      {(['alias', 'titular', 'entidad', 'numero'] as const).map(field => <label className="form-group" key={field}>{({alias:'Alias',titular:'Titular',entidad:'Entidad',numero:'Número simulado'})[field]}<input className="form-input" required autoComplete="off" value={form[field]} onChange={e => setForm({ ...form, [field]: e.target.value })} /></label>)}
      {form.tipo === 'TARJETA' && <><label>Mes de vencimiento<select value={form.mes_vencimiento} onChange={e => setForm({ ...form, mes_vencimiento: e.target.value })}>{Array.from({length:12}, (_, i) => <option key={i} value={i+1}>{i+1}</option>)}</select></label><label>Año de vencimiento<input type="number" min={new Date().getFullYear()} value={form.anio_vencimiento} onChange={e => setForm({ ...form, anio_vencimiento: e.target.value })} /></label></>}
      <button className="btn btn--primary" disabled={busy}>Registrar</button>
    </form></details>
    <h3>Depositar fondos simulados</h3>
    <label>Medio registrado<select className="form-select" value={selected} onChange={e => setSelected(e.target.value)}><option value="">Selecciona un medio</option>{methods.filter(m => m.activo).map(m => <option key={m.id} value={m.id}>{m.alias} {m.numero_enmascarado}</option>)}</select></label>
    <label>Monto COP<input className="form-input" type="number" min="1000" step="0.01" value={amount} onChange={e => setAmount(e.target.value)} /></label>
    <button type="button" className="btn btn--primary" disabled={busy || !selected || Number(amount) < 1000} onClick={deposit}>Confirmar depósito</button>
    <h3>Movimientos</h3>{!movements.length && <p>No hay movimientos.</p>}
    <ul>{movements.map(m => <li key={m.id}>{new Date(m.creado_en).toLocaleString('es-CO')} — {m.tipo}: ${m.valor} COP · Saldo ${m.saldo_resultante} · {m.referencia}</li>)}</ul>
    {next && <button type="button" onClick={more}>Más movimientos</button>}
  </section>
}
