const BASE = '/api/v1'

const TOKEN_KEY = 'predik_token'

export const getToken = (): string | null => localStorage.getItem(TOKEN_KEY)
export const setToken = (t: string): void => localStorage.setItem(TOKEN_KEY, t)
export const clearToken = (): void => localStorage.removeItem(TOKEN_KEY)

async function req(path: string, opts: RequestInit = {}): Promise<Response> {
  const token = getToken()
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(opts.headers as Record<string, string> ?? {}),
  }
  if (token) headers['Authorization'] = `Bearer ${token}`

  const res = await fetch(`${BASE}${path}`, { ...opts, headers })

  if (res.status === 401) {
    clearToken()
    window.location.href = '/login'
  }

  return res
}

// ── Auth ──────────────────────────────────────────────────────────────────────

export async function apiLogin(email: string, password: string): Promise<string> {
  const res = await fetch(`${BASE}/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ email, password }),
  })
  if (!res.ok) {
    const data = await res.json().catch(() => ({}))
    throw new Error(data?.detail?.error?.message ?? 'Credenciales incorrectas')
  }
  const data = await res.json()
  return data.access_token as string
}

// ── Catálogo ──────────────────────────────────────────────────────────────────

export async function apiEstados() {
  const res = await req('/catalogo/estados')
  if (!res.ok) throw new Error('Error cargando estados')
  return res.json()
}

// ── Reporte ───────────────────────────────────────────────────────────────────

export async function apiGenerarReporte(payload: object): Promise<{ blob: Blob; filename: string }> {
  const res = await req('/reporte/generar', {
    method: 'POST',
    body: JSON.stringify(payload),
  })

  if (!res.ok) {
    const text = await res.text()
    throw new Error(`Error ${res.status}: ${text.slice(0, 300)}`)
  }

  const disposition = res.headers.get('content-disposition') ?? ''
  const match = disposition.match(/filename="?([^"]+)"?/)
  const filename = match?.[1] ?? 'reporte.kmz'

  return { blob: await res.blob(), filename }
}

// ── Admin ─────────────────────────────────────────────────────────────────────

export async function apiBdStatus() {
  const res = await req('/admin/bd-status')
  if (!res.ok) throw new Error('Error consultando BD status')
  return res.json()
}
