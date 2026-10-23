// Cliente HTTP mínimo para el home temporal del Product Owner (HU-007/008/009).

const BASE = '/api/v1'

export class ApiError extends Error {
  code: string
  status: number
  details: Record<string, unknown>

  constructor(status: number, body: { code?: string; message?: string; details?: Record<string, unknown> }) {
    super(body?.message ?? `Error ${status}`)
    this.status = status
    this.code = body?.code ?? 'unknown'
    this.details = body?.details ?? {}
  }
}

async function parse(response: Response) {
  const text = await response.text()
  const body = text ? JSON.parse(text) : {}
  if (!response.ok) throw new ApiError(response.status, body)
  return body
}

async function getCsrfToken(): Promise<string> {
  const data = await fetch(`${BASE}/auth/csrf/`, { credentials: 'same-origin' }).then(parse)
  return data.csrf_token
}

async function request(method: string, path: string, body?: unknown, csrfToken?: string) {
  const headers: Record<string, string> = {}
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

export function toFormData(payload: Record<string, string | boolean>, image: File): FormData {
  const body = new FormData()
  for (const [key, value] of Object.entries(payload)) body.append(key, String(value))
  body.append('image', image)
  return body
}

export const api = {
  get: (path: string) => request('GET', path),
  // Todo POST del contrato exige CSRF; se obtiene uno nuevo en cada llamada.
  post: async (path: string, body: unknown) => {
    const csrfToken = await getCsrfToken()
    return request('POST', path, body ?? {}, csrfToken)
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