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

export interface ScianGiro {
  codigo: string
  descripcion: string
}

export async function apiScianCatalogo(): Promise<ScianGiro[]> {
  const res = await req('/catalogo/scian')
  if (!res.ok) throw new Error('Error cargando giros SCIAN')
  return res.json()
}

export async function apiEstados() {
  const res = await req('/catalogo/estados')
  if (!res.ok) throw new Error('Error cargando estados')
  return res.json()
}

export async function apiMunicipios(claveEstado: string) {
  const res = await req(`/catalogo/municipios/${claveEstado}`)
  if (!res.ok) throw new Error('Error cargando municipios')
  return res.json()
}

export async function apiMunicipioBbox(claveEstado: string, claveMun: string) {
  const res = await req(`/catalogo/municipio-bbox/${claveEstado}/${claveMun}`)
  if (!res.ok) throw new Error('No se encontró el municipio en la BD')
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

// ── Preview GeoJSON ───────────────────────────────────────────────────────────

export interface PuntoEstablecimiento {
  nombre: string
  clase_actividad: string
  colonia: string
  municipio: string
  lat: number
  lon: number
}

export interface CapaPreview {
  label: string
  keyword: string
  color: string
  icon: 'circle' | 'star'
  estado: string
  cantidad: number
  puntos: PuntoEstablecimiento[]
}

export interface PreviewData {
  zonas: GeoJSONFeature[]
  capas: CapaPreview[]
  resumen: {
    total_establecimientos: number
    total_zonas: number
    usa_agebs: boolean
    usa_manzanas: boolean
    nivel_geografico: 'ageb' | 'manzana'
    clasificacion: string
    poblacion_alcanzada: number
    zonas_premium: number
  }
}

interface GeoJSONFeature {
  type: 'Feature'
  geometry: object
  properties: {
    label: string
    hex_color: string
    cantidad: number
    intensidad: number
    nivel?: string
    tipo_zona?: 'ageb' | 'manzana' | 'h3'
    // AGEB
    cvegeo?: string
    nom_mun?: string
    pobtot?: number
    graproes?: number
    h3_index?: string
    // Manzana
    vivtot?: number
    vivpar_hab?: number
    con_agua?: number
    con_dren?: number
    con_luz?: number
  }
}

export async function apiPreviewReporte(payload: object): Promise<PreviewData> {
  const res = await req('/reporte/preview', {
    method: 'POST',
    body: JSON.stringify(payload),
  })
  if (!res.ok) {
    const text = await res.text()
    throw new Error(`Error ${res.status}: ${text.slice(0, 300)}`)
  }
  return res.json()
}

// ── Admin ─────────────────────────────────────────────────────────────────────

export async function apiBdStatus() {
  const res = await req('/admin/bd-status')
  if (!res.ok) throw new Error('Error consultando BD status')
  return res.json()
}

export async function apiTriggerEtl(payload: object): Promise<{ message: string }> {
  const res = await req('/admin/etl/trigger', { method: 'POST', body: JSON.stringify(payload) })
  if (!res.ok) throw new Error('Error lanzando ETL')
  return res.json()
}

// ── Historial ─────────────────────────────────────────────────────────────────

export async function apiHistorial(): Promise<object[]> {
  const res = await req('/analisis?limit=20')
  if (!res.ok) return []
  return res.json()
}

// ── BIE (indicadores macroeconómicos) ─────────────────────────────────────────

export interface BieIndicadorValor {
  valor: number | null
  nombre: string
  unidad: string
  periodo?: string
  interpretacion: string
}

export interface BieResumen {
  fuente: string
  estado_clave: string
  advertencia?: string
  indicadores: Record<string, BieIndicadorValor>
}

export async function apiBieResumen(claveEstado: string): Promise<BieResumen> {
  const res = await req(`/bie/estado/${claveEstado}`)
  if (!res.ok) throw new Error('Error cargando indicadores BIE')
  return res.json()
}

// ── Wizard Caso 1 — Análisis de competencia ───────────────────────────────────

export interface AnalisisCompetenciaPayload {
  clave_estado: string
  claves_municipios: string[]
  graproes_min?: number | null
  graproes_max?: number | null
  marca_propia?: string
  scian_giro?: string
  competencia_directa: string[]
  incluir_sucursales: boolean
  incluir_hubs: boolean
  incluir_zonas_blancas: boolean
  radio_hub_metros: number
  nivel_geografico: 'ageb' | 'manzana'
  max_records?: number
}

export async function apiAnalisisCompetenciaPreview(
  payload: AnalisisCompetenciaPayload
) {
  const res = await req('/analisis/competencia', {
    method: 'POST',
    body: JSON.stringify({ ...payload, formato_salida: 'geojson' }),
  })
  if (!res.ok) {
    const text = await res.text()
    throw new Error(`Error ${res.status}: ${text.slice(0, 400)}`)
  }
  return res.json()
}

export async function apiAnalisisCompetenciaKmz(
  payload: AnalisisCompetenciaPayload
): Promise<{ blob: Blob; filename: string }> {
  const res = await req('/analisis/competencia', {
    method: 'POST',
    body: JSON.stringify({ ...payload, formato_salida: 'kmz' }),
  })
  if (!res.ok) {
    const text = await res.text()
    throw new Error(`Error ${res.status}: ${text.slice(0, 400)}`)
  }
  const disposition = res.headers.get('content-disposition') ?? ''
  const match = disposition.match(/filename="?([^"]+)"?/)
  const filename = match?.[1] ?? 'analisis_competencia.kmz'
  return { blob: await res.blob(), filename }
}
