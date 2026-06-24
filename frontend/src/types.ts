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
