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

export const NSE_NIVELES: { nivel: NseNivel; label: string; graproes_min: number; graproes_max: number | null; color: string }[] = [
  { nivel: 'AB',     label: 'A/B  — Posgrado',       graproes_min: 16, graproes_max: null, color: '#1e3a8a' },
  { nivel: 'Cmas',   label: 'C+   — Licenciatura',   graproes_min: 14, graproes_max: 16,   color: '#1d4ed8' },
  { nivel: 'C',      label: 'C    — Preparatoria',   graproes_min: 12, graproes_max: 14,   color: '#2563eb' },
  { nivel: 'Cmenos', label: 'C−   — Bachillerato',   graproes_min: 10, graproes_max: 12,   color: '#3b82f6' },
  { nivel: 'Dmas',   label: 'D+   — Secundaria',     graproes_min:  9, graproes_max: 10,   color: '#f59e0b' },
  { nivel: 'D',      label: 'D    — Primaria',        graproes_min:  7, graproes_max:  9,   color: '#f97316' },
  { nivel: 'E',      label: 'E    — Sin escolaridad', graproes_min:  0, graproes_max:  7,   color: '#ef4444' },
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
