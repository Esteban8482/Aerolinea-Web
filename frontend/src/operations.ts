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
  return async (
    input: Record<string, unknown>,
    quoteInput: Record<string, unknown>,
    confirm?: (info: { total: string; balance: string }) => Promise<boolean>,
  ) => {
    const fingerprint = JSON.stringify(input)
    if (!pending.current || pending.current.input !== fingerprint) {
      const quote = await api.post('/sales/quote/', quoteInput)
      const wallet = await api.get('/sales/wallet/')
      if (Number(wallet.balance) < Number(quote.total)) {
        const total = Number(quote.total)
        const balance = Number(wallet.balance)
        throw new ApiError(400, {
          code: 'insufficient_wallet_balance',
          message: `Saldo insuficiente. Total cotizado: $${total} COP; saldo $${balance} COP.`,
          details: {
            total: String(total),
            balance: String(balance),
            difference: String(total - balance),
          },
        })
      }
      if (confirm) {
        const accepted = await confirm({ total: String(quote.total), balance: String(wallet.balance) })
        if (!accepted) return null
      }
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
