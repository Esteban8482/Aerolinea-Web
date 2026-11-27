// Cliente HTTP compartido – HU-007 / HU-008 / HU-009 / CU-01-03.
// Gestiona CSRF y cookies de sesión de forma transparente.

const BASE = '/api/v1'

export class ApiError extends Error {
  code: string
  status: number
  details: Record<string, unknown>

  constructor(
    status: number,
    body: { code?: string; message?: string; details?: Record<string, unknown> },
  ) {
    super(body?.message ?? `Error ${status}`)
    this.status = status
    this.code = body?.code ?? 'unknown'
    this.details = body?.details ?? {}
  }
}

async function parse(response: Response) {
  const text = await response.text()
  let body
  try { body = text ? JSON.parse(text) : {} } catch { throw new ApiError(response.status, { message: 'El servidor no devolvió una respuesta válida. Intenta nuevamente.' }) }
  if (['not_authenticated', 'session_invalidated'].includes(body.code)) window.dispatchEvent(new Event('session-expired'))
  if (!response.ok) throw new ApiError(response.status, body)
  return body
}

async function getCsrfToken(): Promise<string> {
  const data = await fetch(`${BASE}/auth/csrf/`, {
    credentials: 'same-origin',
  }).then(parse)
  return data.csrf_token
}

async function request(
  method: string,
  path: string,
  body?: unknown,
  csrfToken?: string,
  extraHeaders: Record<string, string> = {},
) {
  const headers: Record<string, string> = { ...extraHeaders }
  if (body !== undefined) headers['Content-Type'] = 'application/json'
  if (csrfToken) headers['X-CSRFToken'] = csrfToken
  const response = await fetch(`${BASE}${path}`, {
    method,
    credentials: 'same-origin',
    headers,
    body: body === undefined ? undefined : JSON.stringify(body),
  })
  return parse(response)
}

export function toFormData(
  payload: Record<string, string | boolean>,
  image: File,
): FormData {
  const body = new FormData()
  for (const [key, value] of Object.entries(payload))
    body.append(key, String(value))
  body.append('image', image)
  return body
}

export const api = {
  get: (path: string) => request('GET', path),
  getWithHeaders: (path: string, headers: Record<string, string>) =>
    request('GET', path, undefined, undefined, headers),

  getBlobWithHeaders: async (path: string, headers: Record<string, string> = {}) => {
    const response = await fetch(`${BASE}${path}`, {
      credentials: 'same-origin',
      headers,
    })
    if (!response.ok) return parse(response)
    return response.blob()
  },

  // Todo POST del contrato exige CSRF; se obtiene uno nuevo en cada llamada.
  post: async (path: string, body: unknown) => {
    const csrfToken = await getCsrfToken()
    return request('POST', path, body ?? {}, csrfToken)
  },

  postWithHeaders: async (
    path: string,
    body: unknown,
    headers: Record<string, string>,
  ) => {
    const csrfToken = await getCsrfToken()
    return request('POST', path, body ?? {}, csrfToken, headers)
  },

  delete: async (path: string) => request('DELETE', path, undefined, await getCsrfToken()),

  patch: async (path: string, body: unknown) => {
    const csrfToken = await getCsrfToken()
    return request('PATCH', path, body ?? {}, csrfToken)
  },

  postMultipart: async (path: string, form: FormData) => {
    const csrfToken = await getCsrfToken()
    const response = await fetch(`${BASE}${path}`, {
      method: 'POST',
      credentials: 'same-origin',
      headers: { 'X-CSRFToken': csrfToken },
      body: form,
    })
    return parse(response)
  },
}
