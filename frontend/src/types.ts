export type ColorNombre =
  | 'red' | 'green' | 'blue' | 'yellow'
  | 'orange' | 'purple' | 'cyan' | 'pink'

export type IconTipo = 'circle' | 'star'

export type Clasificacion = 'densidad' | 'oportunidad' | 'poder_adquisitivo'

export type Formato = 'kmz' | 'excel'

export type NivelGeografico = 'ageb' | 'manzana'

export interface Capa {
  id: string
  keyword: string
  label: string
  color: ColorNombre
  icon: IconTipo
  estado: string
}

export interface EstadoCatalogo {
  clave: string
  nombre: string
  abreviatura: string
}

export interface MunicipioCatalogo {
  clave: string
  nombre: string
  clave_estado: string
}

export interface MunicipioBbox {
  nombre: string
  clave_estado: string
  clave_mun: string
  minx: number
  miny: number
  maxx: number
  maxy: number
  center_lat: number
  center_lng: number
}

export interface GeoJSONGeometry {
  type: string
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  coordinates: any
}

// ── Wizard Caso 1 ─────────────────────────────────────────────────────────────

export type NseNivel = 'AB' | 'Cmas' | 'C' | 'Cmenos' | 'Dmas' | 'D' | 'E'

/**
 * Clasificación NSE usando score multi-variable inspirado en AMAI.
 * Los umbrales se aplican a un score 0-100 que combina educación (34%),
 * computadora (24%), seguridad social (27%), internet (9%) y automóvil (6%).
 * Porcentajes = distribución AMAI nacional de referencia.
 */
export const NSE_NIVELES: { nivel: NseNivel; label: string; pct_amai: number; score_min: number; color: string }[] = [
  { nivel: 'AB',     label: 'A/B  — Alto',          pct_amai:  7.2, score_min: 67, color: '#1e3a8a' },
  { nivel: 'Cmas',   label: 'C+   — Medio alto',    pct_amai: 14.2, score_min: 57, color: '#1d4ed8' },
  { nivel: 'C',      label: 'C    — Medio',          pct_amai: 17.0, score_min: 50, color: '#2563eb' },
  { nivel: 'Cmenos', label: 'C−   — Medio bajo',    pct_amai: 18.7, score_min: 42, color: '#3b82f6' },
  { nivel: 'Dmas',   label: 'D+   — Popular alto',  pct_amai: 18.4, score_min: 35, color: '#f59e0b' },
  { nivel: 'D',      label: 'D    — Popular',        pct_amai: 18.5, score_min: 25, color: '#f97316' },
  { nivel: 'E',      label: 'E    — Muy bajo',       pct_amai:  6.0, score_min:  0, color: '#ef4444' },
]

export interface WizardData {
  // Paso 1
  estadoClave: string
  estadoNombre: string
  // Paso 2
  municipios: MunicipioCatalogo[]
  // Paso 3
  nseNiveles: NseNivel[]
  // Paso 4
  marcaPropia: string
  scianGiros: string[]
  competenciaDirecta: string[]
  incluirSucursales: boolean
  incluirHubs: boolean
  incluirZonasBlancas: boolean
  radioHub: 100 | 150 | 200 | 300
  nivelGeografico: NivelGeografico
}

export interface CompetenciaResultado {
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  zonas: any[]
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  capas: any[]
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  indirecta: { cantidad: number; puntos: any[] }
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  hubs: any[]
  resumen: {
    total_establecimientos: number
    total_directa: number
    total_indirecta: number
    total_hubs: number
    total_zonas: number
    nivel_geografico: string
    clasificacion: string
  }
}
