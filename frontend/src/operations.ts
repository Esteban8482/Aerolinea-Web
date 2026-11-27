import { useRef } from 'react'
// Keep one key for the same request, including retries after an interrupted response.
export function useOperationKey() {
  const operation = useRef<{ fingerprint: string; key: string } | null>(null)
  return {
    forRequest: (payload: unknown) => {
      const fingerprint = JSON.stringify(payload)
      if (operation.current?.fingerprint !== fingerprint) operation.current = { fingerprint, key: crypto.randomUUID() }
      return operation.current!.key
    },
    clear: () => { operation.current = null },
  }
}

import { api, ApiError } from './api'
export function useConfirmedPurchase() {
  const pending = useRef<{ input: string; payload: Record<string, unknown>; key: string } | null>(null)
  return async (input: Record<string, unknown>, quoteInput: Record<string, unknown>) => {
    const fingerprint = JSON.stringify(input)
    if (!pending.current || pending.current.input !== fingerprint) {
      const quote = await api.post('/sales/quote/', quoteInput)
      const wallet = await api.get('/sales/wallet/')
      if (Number(wallet.balance) < Number(quote.total)) throw new ApiError(400, { code: 'insufficient_wallet_balance', message: `Saldo insuficiente. Total cotizado: $${quote.total} COP; saldo $${wallet.balance} COP. Registra un medio y deposita fondos para continuar.` })
      if (!window.confirm(`Total cotizado: $${quote.total} COP. Saldo disponible: $${wallet.balance} COP. ¿Aceptas pagar este total?`)) return null
      pending.current = { input: fingerprint, payload: { ...input, accepted_total: quote.total }, key: crypto.randomUUID() }
    }
    try {
      const result = await api.postWithHeaders('/sales/purchases/', pending.current.payload, { 'Idempotency-Key': pending.current.key })
      pending.current = null
      return result
    } catch (error) {
      // A transport/5xx/session-finalization failure may follow a committed purchase.
      // Retrying it must send exactly the previously accepted payload and key, without requoting.
      if (error instanceof ApiError && error.status < 500 && error.code !== 'session_invalidated' && error.code !== 'not_authenticated') pending.current = null
      throw error
    }
  }
}
