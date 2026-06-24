import { useCallback, useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { MapContainer, TileLayer, useMap } from 'react-leaflet'
import L from 'leaflet'
import 'leaflet-draw'
import { useAuthStore } from '../store/useAuthStore'
import {
  apiEstados, apiMunicipios, apiMunicipioBbox,
  apiGenerarReporte, apiBdStatus,
  apiPreviewReporte,
} from '../api/client'
import type { PreviewData } from '../api/client'
import type { Capa, ColorNombre, EstadoCatalogo, MunicipioCatalogo, MunicipioBbox, GeoJSONGeometry, Clasificacion, Formato, NivelGeografico } from '../types'
import { ResultsOverlay }          from '../components/ResultsOverlay'
import { KPIPanel }                from '../components/KPIPanel'
import { AdminPanel }              from '../components/AdminPanel'
import { EconomicContextWidget }   from '../components/EconomicContextWidget'

// ── Constantes ────────────────────────────────────────────────────────────────

const COLORES: { value: ColorNombre; hex: string; label: string }[] = [
  { value: 'blue',   hex: '#3b82f6', label: 'Azul' },
  { value: 'red',    hex: '#ef4444', label: 'Rojo' },
  { value: 'green',  hex: '#22c55e', label: 'Verde' },
  { value: 'yellow', hex: '#eab308', label: 'Amarillo' },
  { value: 'orange', hex: '#f97316', label: 'Naranja' },
  { value: 'purple', hex: '#a855f7', label: 'Morado' },
  { value: 'cyan',   hex: '#06b6d4', label: 'Cyan' },
  { value: 'pink',   hex: '#ec4899', label: 'Rosa' },
]

const COLOR_CYCLE: ColorNombre[] = ['blue', 'red', 'green', 'yellow', 'orange', 'purple', 'cyan', 'pink']

let _uid = 0
const mkCapa = (color: ColorNombre): Capa => ({
  id:      `capa_${++_uid}`,
  keyword: '',
  label:   '',
  color,
  icon:    'circle',
  estado:  '09',
})

// ── MapFlyTo ──────────────────────────────────────────────────────────────────

interface FlyTarget { lat: number; lng: number; zoom: number }

function MapFlyTo({ target }: { target: FlyTarget | null }) {
  const map = useMap()
  const prev = useRef<FlyTarget | null>(null)

  useEffect(() => {
    if (target && target !== prev.current) {
      prev.current = target
      map.flyTo([target.lat, target.lng], target.zoom, { duration: 1.2 })
    }
  }, [map, target])

  return null
}

// ── DrawControl ───────────────────────────────────────────────────────────────

function DrawControl({ onPolygon }: { onPolygon: (g: GeoJSONGeometry) => void }) {
  const map = useMap()

  useEffect(() => {
    const group = new L.FeatureGroup()
    map.addLayer(group)

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const DC = (L.Control as any).Draw
    const control = new DC({
      draw: {
        polygon:      { shapeOptions: { color: '#1a5fc3', weight: 2, fillOpacity: 0.12 } },
        rectangle:    { shapeOptions: { color: '#1a5fc3', weight: 2, fillOpacity: 0.12 } },
        polyline:     false,
        circle:       false,
        marker:       false,
        circlemarker: false,
      },
      edit: { featureGroup: group },
    })
    map.addControl(control)

    // eslint-disable-next-line @typescript-eslint/no-explicit-any
    const onCreate = (e: any) => {
      group.clearLayers()
      group.addLayer(e.layer)
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      onPolygon((e.layer as any).toGeoJSON().geometry as GeoJSONGeometry)
    }

    map.on('draw:created', onCreate)
    return () => {
      map.off('draw:created', onCreate)
      map.removeControl(control)
      map.removeLayer(group)
    }
  }, [map, onPolygon])

  return null
}

// ── BdBadge ───────────────────────────────────────────────────────────────────

function BdBadge({ count, label }: { count: number; label: string }) {
  const estado = count === 0 ? 'vacia' : count < 10_000 ? 'parcial' : 'ok'
  const colors = {
    vacia:   'bg-red-100 text-red-700',
    parcial: 'bg-yellow-100 text-yellow-700',
    ok:      'bg-green-100 text-green-700',
  }
  return (
    <span className={`inline-flex items-center gap-1 text-xs font-medium px-2 py-0.5 rounded-full ${colors[estado]}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${
        estado === 'ok' ? 'bg-green-500' : estado === 'parcial' ? 'bg-yellow-500' : 'bg-red-400'
      }`} />
      {label}: {count.toLocaleString()}
    </span>
  )
}

// ── LayerRow ──────────────────────────────────────────────────────────────────

interface LayerRowProps {
  capa:     Capa
  estados:  EstadoCatalogo[]
  onChange: (c: Capa) => void
  onRemove: () => void
  canRemove: boolean
  index:    number
}

function LayerRow({ capa, estados, onChange, onRemove, canRemove, index }: LayerRowProps) {
  const set = (field: keyof Capa, v: string) => onChange({ ...capa, [field]: v })

  return (
    <div className="border border-gray-200 rounded-xl p-3 bg-white shadow-sm space-y-2.5">
      <div className="flex items-center justify-between">
        <span className="text-xs font-semibold text-gray-400 uppercase tracking-wider">Capa {index + 1}</span>
        {canRemove && (
          <button onClick={onRemove} className="text-gray-300 hover:text-red-400 transition-colors">
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        )}
      </div>

      <input
        type="text"
        placeholder="Negocio a buscar (ej: little caesars)"
        value={capa.keyword}
        onChange={e => set('keyword', e.target.value)}
        className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm placeholder-gray-400 focus:ring-2 focus:ring-brand-500 focus:border-brand-500 outline-none"
      />

      <input
        type="text"
        placeholder="Nombre en el reporte (ej: Little Caesars)"
        value={capa.label}
        onChange={e => set('label', e.target.value)}
        className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm placeholder-gray-400 focus:ring-2 focus:ring-brand-500 focus:border-brand-500 outline-none"
      />

      <select
        value={capa.estado}
        onChange={e => set('estado', e.target.value)}
        className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-brand-500 focus:border-brand-500 outline-none bg-white"
      >
        {estados.map(est => (
          <option key={est.clave} value={est.clave}>
            {est.clave} · {est.nombre}
          </option>
        ))}
      </select>

      <div className="flex items-center justify-between">
        <div className="flex gap-1">
          {COLORES.map(c => (
            <button
              key={c.value}
              title={c.label}
              onClick={() => set('color', c.value)}
              style={{ backgroundColor: c.hex }}
              className={`w-5 h-5 rounded-full transition-transform border-2 ${
                capa.color === c.value ? 'scale-125 border-gray-700' : 'border-transparent hover:scale-110'
              }`}
            />
          ))}
        </div>
        <div className="flex gap-3 text-xs">
          {(['circle', 'star'] as const).map(ico => (
            <label key={ico} className="flex items-center gap-1 cursor-pointer select-none">
              <input
                type="radio"
                name={`icon_${capa.id}`}
                value={ico}
                checked={capa.icon === ico}
                onChange={() => set('icon', ico)}
                className="accent-brand-700"
              />
              <span className="text-gray-600">{ico === 'circle' ? '● Punto' : '★ Estrella'}</span>
            </label>
          ))}
        </div>
      </div>
    </div>
  )
}

// ── MapPage ───────────────────────────────────────────────────────────────────

export default function MapPage() {
  const { logout }  = useAuthStore()
  const navigate    = useNavigate()

  const [polygon,       setPolygon]       = useState<GeoJSONGeometry | null>(null)
  const [estados,       setEstados]       = useState<EstadoCatalogo[]>([])
  const [municipios,    setMunicipios]    = useState<MunicipioCatalogo[]>([])
  const [selectedEnt,   setSelectedEnt]   = useState<string>('')
  const [selectedMun,   setSelectedMun]   = useState<string>('')
  const [munLoading,    setMunLoading]    = useState(false)
  const [flyTarget,     setFlyTarget]     = useState<FlyTarget | null>(null)
  const [capas,         setCapas]         = useState<Capa[]>([mkCapa('blue')])
  const [clasificacion,    setClasificacion]    = useState<Clasificacion>('densidad')
  const [formato,          setFormato]          = useState<Formato>('kmz')
  const [nivelGeografico,  setNivelGeografico]  = useState<NivelGeografico>('ageb')
  const [loading,       setLoading]       = useState(false)
  const [status,        setStatus]        = useState<string>('')
  const [statusType,    setStatusType]    = useState<'idle' | 'ok' | 'error'>('idle')
  const [bdInfo,        setBdInfo]        = useState<{ denue: number; demographics: number } | null>(null)
  const [previewData,   setPreviewData]   = useState<PreviewData | null>(null)
  const [showKPI,       setShowKPI]       = useState(false)
  const [showAdmin,     setShowAdmin]     = useState(false)
  const [visibleCapas,  setVisibleCapas]  = useState<Record<string, boolean>>({})

  const handlePolygon = useCallback((g: GeoJSONGeometry) => {
    setPolygon(g)
    setStatus('Área definida. Configura las capas y genera el reporte.')
    setStatusType('ok')
  }, [])

  const toggleCapa = useCallback((keyword: string) => {
    setVisibleCapas(prev => ({ ...prev, [keyword]: !(prev[keyword] !== false) }))
  }, [])

  const handleEstadoChange = async (clave: string) => {
    setSelectedEnt(clave)
    setSelectedMun('')
    setMunicipios([])
    if (!clave) return
    try {
      const data: MunicipioCatalogo[] = await apiMunicipios(clave)
      setMunicipios(data)
    } catch {
      setMunicipios([])
    }
  }

  const handleMunicipioChange = async (clave: string) => {
    setSelectedMun(clave)
    if (!clave || !selectedEnt) return
    setMunLoading(true)
    try {
      const bbox: MunicipioBbox = await apiMunicipioBbox(selectedEnt, clave)
      const polygon: GeoJSONGeometry = {
        type: 'Polygon',
        coordinates: [[
          [bbox.minx, bbox.miny],
          [bbox.maxx, bbox.miny],
          [bbox.maxx, bbox.maxy],
          [bbox.minx, bbox.maxy],
          [bbox.minx, bbox.miny],
        ]],
      }
      setPolygon(polygon)
      setFlyTarget({ lat: bbox.center_lat, lng: bbox.center_lng, zoom: 12 })
      setStatus(`Municipio: ${bbox.nombre}. Ajusta el polígono o genera el reporte.`)
      setStatusType('ok')
    } catch (err) {
      setStatus(err instanceof Error ? err.message : 'No se encontró el municipio en la BD (AGEBs no cargadas para esta zona)')
      setStatusType('error')
    } finally {
      setMunLoading(false)
    }
  }

  useEffect(() => {
    apiEstados()
      .then((data: EstadoCatalogo[]) => setEstados(data))
      .catch(console.error)

    apiBdStatus()
      .then((data: { tablas: { tabla: string; registros: number }[] }) => {
        const denue = data.tablas.find((t: { tabla: string }) => t.tabla.includes('denue'))?.registros ?? 0
        const demo  = data.tablas.find((t: { tabla: string }) => t.tabla.includes('demographics'))?.registros ?? 0
        setBdInfo({ denue, demographics: demo })
      })
      .catch(console.error)
  }, [])

  const addCapa = () => {
    if (capas.length >= 8) return
    setCapas(prev => [...prev, mkCapa(COLOR_CYCLE[prev.length % COLOR_CYCLE.length])])
  }

  const updateCapa = (id: string, updated: Capa) =>
    setCapas(prev => prev.map(c => c.id === id ? updated : c))

  const removeCapa = (id: string) =>
    setCapas(prev => prev.filter(c => c.id !== id))

  const buildPayload = (etl: boolean) => ({
    nombre:                  capas.map(c => c.label || c.keyword).join(' vs '),
    polygon,
    capas:                   capas.map(c => ({
      keyword: c.keyword.trim(),
      label:   c.label.trim() || c.keyword.trim(),
      color:   c.color,
      icon:    c.icon,
      estado:  c.estado,
    })),
    formato,
    clasificacion_hexagonos: clasificacion,
    h3_resolution:           9,
    ejecutar_etl:            etl,
    nivel_geografico:        nivelGeografico,
  })

  const handleGenerar = async () => {
    if (!polygon) {
      setStatus('Primero dibuja un polígono en el mapa.')
      setStatusType('error')
      return
    }
    const invalidas = capas.filter(c => !c.keyword.trim())
    if (invalidas.length) {
      setStatus('Todas las capas deben tener un keyword.')
      setStatusType('error')
      return
    }

    setLoading(true)
    setPreviewData(null)
    setShowKPI(false)
    setStatus('Consultando INEGI DENUE... esto puede tardar 3–8 minutos.')
    setStatusType('idle')

    try {
      // 1. Preview (ETL + datos para mapa) — genera los datos y los devuelve en JSON
      const preview = await apiPreviewReporte(buildPayload(true))
      setPreviewData(preview)
      const initVis: Record<string, boolean> = {}
      preview.capas.forEach(c => { initVis[c.keyword] = true })
      setVisibleCapas(initVis)
      setShowKPI(true)

      const total = preview.resumen.total_establecimientos
      setStatus(
        `${total} establecimiento${total !== 1 ? 's' : ''} encontrado${total !== 1 ? 's' : ''}. ` +
        `${preview.resumen.total_zonas} zonas analizadas. Generando archivo...`
      )
      setStatusType('ok')

      // 2. Generar archivo (sin re-correr ETL — usa datos ya cargados)
      const { blob, filename } = await apiGenerarReporte(buildPayload(false))

      const url = URL.createObjectURL(blob)
      const a   = document.createElement('a')
      a.href     = url
      a.download = filename
      document.body.appendChild(a)
      a.click()
      a.remove()
      URL.revokeObjectURL(url)

      setStatus(`Reporte descargado: ${filename}`)
      setStatusType('ok')
    } catch (err) {
      setStatus(err instanceof Error ? err.message : 'Error desconocido al generar reporte')
      setStatusType('error')
    } finally {
      setLoading(false)
    }
  }

  const handleLogout = () => { logout(); navigate('/login') }

  return (
    <div className="h-screen flex overflow-hidden bg-gray-50">

      {/* ══ SIDEBAR ══════════════════════════════════════════════════════ */}
      <aside className="w-80 min-w-[320px] bg-white border-r border-gray-100 flex flex-col shadow-sm z-10">

        {/* Header */}
        <div className="bg-brand-800 px-5 py-4 flex-shrink-0">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2.5">
              <div className="w-8 h-8 bg-white bg-opacity-15 rounded-lg flex items-center justify-center flex-shrink-0">
                <svg className="w-5 h-5 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                    d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
                </svg>
              </div>
              <div>
                <p className="text-white font-bold text-base leading-none">Predik Geo</p>
                <p className="text-blue-300 text-xs mt-0.5">Inteligencia Geoespacial</p>
              </div>
            </div>
            <div className="flex items-center gap-2">
              {/* Admin */}
              <button
                onClick={() => setShowAdmin(true)}
                className="text-blue-300 hover:text-white text-xs border border-blue-600 hover:border-blue-300 rounded-md px-2.5 py-1 transition-colors"
                title="Panel de administración"
              >
                Admin
              </button>
              {/* Logout */}
              <button
                onClick={handleLogout}
                className="text-blue-300 hover:text-white text-xs border border-blue-600 hover:border-blue-300 rounded-md px-2.5 py-1 transition-colors"
              >
                Salir
              </button>
            </div>
          </div>

          {bdInfo && (
            <div className="mt-3 flex flex-wrap gap-1.5">
              <BdBadge count={bdInfo.denue}        label="DENUE" />
              <BdBadge count={bdInfo.demographics} label="Censo" />
            </div>
          )}
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto sidebar-scroll px-4 py-5 space-y-6">

          {/* PASO 1 */}
          <section>
            <div className="flex items-center gap-2 mb-2">
              <span className="w-5 h-5 rounded-full bg-brand-800 text-white text-xs flex items-center justify-center font-bold flex-shrink-0">1</span>
              <h2 className="text-sm font-semibold text-gray-700">Área de análisis</h2>
            </div>

            {/* Selección por estado/municipio */}
            <div className="space-y-2 mb-2">
              <select
                value={selectedEnt}
                onChange={e => handleEstadoChange(e.target.value)}
                className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-brand-500 focus:border-brand-500 outline-none bg-white"
              >
                <option value="">— Selecciona un estado —</option>
                {estados.map(est => (
                  <option key={est.clave} value={est.clave}>
                    {est.clave} · {est.nombre}
                  </option>
                ))}
              </select>

              {selectedEnt && (
                <div className="relative">
                  <select
                    value={selectedMun}
                    onChange={e => handleMunicipioChange(e.target.value)}
                    disabled={munLoading}
                    className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-brand-500 focus:border-brand-500 outline-none bg-white disabled:opacity-60"
                  >
                    <option value="">— Selecciona un municipio —</option>
                    {municipios.map(m => (
                      <option key={m.clave} value={m.clave}>
                        {m.nombre}
                      </option>
                    ))}
                  </select>
                  {munLoading && (
                    <span className="absolute right-3 top-2.5 w-4 h-4 border-2 border-brand-700 border-t-transparent rounded-full animate-spin" />
                  )}
                </div>
              )}

              {selectedEnt && municipios.length === 0 && !munLoading && (
                <p className="text-xs text-gray-400 px-1">
                  No hay municipios cargados para este estado. Dibuja el polígono manualmente.
                </p>
              )}
            </div>

            {/* Contexto económico BIE */}
            {selectedEnt && (
              <EconomicContextWidget
                claveEstado={selectedEnt}
                nombreEstado={estados.find(e => e.clave === selectedEnt)?.nombre ?? selectedEnt}
              />
            )}

            <div className="relative flex items-center gap-2 mb-2">
              <div className="flex-1 h-px bg-gray-100" />
              <span className="text-xs text-gray-400 flex-shrink-0">o dibuja en el mapa</span>
              <div className="flex-1 h-px bg-gray-100" />
            </div>

            <div className={`text-xs rounded-lg px-3 py-2.5 border flex items-center gap-2 ${
              polygon
                ? 'bg-green-50 border-green-200 text-green-700'
                : 'bg-amber-50 border-amber-200 text-amber-700'
            }`}>
              {polygon ? (
                <><svg className="w-4 h-4 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>Área definida correctamente</>
              ) : (
                <><svg className="w-4 h-4 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 15l-2 5L9 9l11 4-5 2zm0 0l5 5" />
                </svg>Dibuja un polígono en el mapa</>
              )}
            </div>
          </section>

          {/* PASO 2 */}
          <section>
            <div className="flex items-center justify-between mb-2">
              <div className="flex items-center gap-2">
                <span className="w-5 h-5 rounded-full bg-brand-800 text-white text-xs flex items-center justify-center font-bold flex-shrink-0">2</span>
                <h2 className="text-sm font-semibold text-gray-700">Capas de búsqueda</h2>
              </div>
              <button
                onClick={addCapa}
                disabled={capas.length >= 8}
                className="text-xs text-brand-700 hover:text-brand-900 font-medium disabled:opacity-40 disabled:cursor-not-allowed flex items-center gap-1"
              >
                <svg className="w-3.5 h-3.5" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M12 4v16m8-8H4" />
                </svg>
                Agregar
              </button>
            </div>
            <div className="space-y-2">
              {capas.map((capa, i) => (
                <LayerRow
                  key={capa.id}
                  capa={capa}
                  estados={estados}
                  onChange={updated => updateCapa(capa.id, updated)}
                  onRemove={() => removeCapa(capa.id)}
                  canRemove={capas.length > 1}
                  index={i}
                />
              ))}
            </div>
          </section>

          {/* PASO 3 */}
          <section>
            <div className="flex items-center gap-2 mb-3">
              <span className="w-5 h-5 rounded-full bg-brand-800 text-white text-xs flex items-center justify-center font-bold flex-shrink-0">3</span>
              <h2 className="text-sm font-semibold text-gray-700">Opciones de análisis</h2>
            </div>

            {/* Nivel geográfico */}
            <div className="mb-4">
              <p className="text-xs text-gray-500 font-medium mb-2">Nivel de detalle geográfico</p>
              <div className="grid grid-cols-2 gap-2">
                {([
                  { value: 'ageb',    label: 'AGEB',     desc: '~1 km² · Censo 2020' },
                  { value: 'manzana', label: 'Manzana',  desc: '~100 m² · Vivienda' },
                ] as const).map(n => (
                  <label key={n.value} className={`flex flex-col gap-0.5 p-2.5 rounded-lg border cursor-pointer transition-colors ${
                    nivelGeografico === n.value ? 'bg-brand-50 border-brand-400' : 'border-gray-100 hover:bg-gray-50'
                  }`}>
                    <div className="flex items-center gap-2">
                      <input
                        type="radio" name="nivel" value={n.value}
                        checked={nivelGeografico === n.value}
                        onChange={() => setNivelGeografico(n.value)}
                        className="accent-brand-700"
                      />
                      <span className="text-sm font-semibold text-gray-700">{n.label}</span>
                    </div>
                    <span className="text-xs text-gray-400 pl-5">{n.desc}</span>
                  </label>
                ))}
              </div>
              {nivelGeografico === 'manzana' && (
                <p className="text-xs text-amber-600 bg-amber-50 border border-amber-200 rounded-lg px-2.5 py-1.5 mt-2">
                  Requiere ETL de manzanas cargado. Disponible para estados ya procesados.
                </p>
              )}
            </div>

            <div className="mb-4">
              <p className="text-xs text-gray-500 font-medium mb-2">Clasificación de zonas</p>
              <div className="space-y-1.5">
                {[
                  { value: 'densidad',         label: 'Densidad comercial',       desc: 'Intensidad de establecimientos' },
                  { value: 'oportunidad',       label: 'Oportunidad competitiva',  desc: 'Zonas sin presencia de la competencia' },
                  { value: 'poder_adquisitivo', label: 'Poder adquisitivo',        desc: 'Zonas premium según escolaridad INEGI' },
                ].map(opt => (
                  <label key={opt.value} className={`flex items-start gap-2.5 p-2.5 rounded-lg border cursor-pointer transition-colors ${
                    clasificacion === opt.value ? 'bg-brand-50 border-brand-300' : 'border-gray-100 hover:bg-gray-50'
                  }`}>
                    <input
                      type="radio" name="clasificacion" value={opt.value}
                      checked={clasificacion === opt.value}
                      onChange={() => setClasificacion(opt.value as Clasificacion)}
                      className="accent-brand-700 mt-0.5 flex-shrink-0"
                    />
                    <div>
                      <p className="text-sm font-medium text-gray-700">{opt.label}</p>
                      <p className="text-xs text-gray-400">{opt.desc}</p>
                    </div>
                  </label>
                ))}
              </div>
            </div>

            <div>
              <p className="text-xs text-gray-500 font-medium mb-2">Formato de descarga</p>
              <div className="flex gap-3">
                {([
                  { value: 'kmz',   label: 'KMZ',   desc: 'Google Earth' },
                  { value: 'excel', label: 'Excel',  desc: '.xlsx' },
                ] as const).map(f => (
                  <label key={f.value} className={`flex-1 flex items-center gap-2 p-2.5 rounded-lg border cursor-pointer transition-colors ${
                    formato === f.value ? 'bg-brand-50 border-brand-300' : 'border-gray-100 hover:bg-gray-50'
                  }`}>
                    <input
                      type="radio" name="formato" value={f.value}
                      checked={formato === f.value}
                      onChange={() => setFormato(f.value)}
                      className="accent-brand-700"
                    />
                    <div>
                      <p className="text-sm font-semibold text-gray-700">{f.label}</p>
                      <p className="text-xs text-gray-400">{f.desc}</p>
                    </div>
                  </label>
                ))}
              </div>
            </div>
          </section>
        </div>

        {/* Footer CTA */}
        <div className="p-4 border-t border-gray-100 flex-shrink-0 space-y-2.5">
          {status && (
            <div className={`text-xs rounded-lg px-3 py-2.5 border ${
              statusType === 'ok'    ? 'bg-green-50  border-green-200  text-green-700'  :
              statusType === 'error' ? 'bg-red-50    border-red-200    text-red-700'    :
                                       'bg-blue-50   border-blue-200   text-blue-700'
            }`}>
              {loading && (
                <span className="inline-block w-3 h-3 border-2 border-current border-t-transparent rounded-full animate-spin mr-2 align-middle" />
              )}
              {status}
            </div>
          )}

          <div className="flex gap-2">
            {/* Ver KPIs (si hay datos) */}
            {previewData && (
              <button
                onClick={() => setShowKPI(v => !v)}
                className="flex-shrink-0 border border-brand-300 text-brand-700 rounded-xl py-3 px-3 text-sm font-semibold hover:bg-brand-50 transition-colors"
                title="Ver KPIs"
              >
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                    d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
                </svg>
              </button>
            )}

            <button
              onClick={handleGenerar}
              disabled={loading || !polygon}
              className="flex-1 bg-brand-800 text-white rounded-xl py-3 font-semibold text-sm hover:bg-brand-700 active:bg-brand-900 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center justify-center gap-2 shadow-sm"
            >
              {loading ? (
                <>
                  <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                  Analizando...
                </>
              ) : (
                <>
                  <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                      d="M9 20l-5.447-2.724A1 1 0 013 16.382V5.618a1 1 0 011.447-.894L9 7m0 13l6-3m-6 3V7m6 10l4.553 2.276A1 1 0 0021 18.382V7.618a1 1 0 00-.553-.894L15 4m0 13V4m0 0L9 7" />
                  </svg>
                  Analizar y Descargar
                </>
              )}
            </button>
          </div>
        </div>
      </aside>

      {/* ══ MAPA ════════════════════════════════════════════════════════ */}
      <main className="flex-1 relative overflow-hidden">
        <MapContainer
          center={[23.6345, -102.5528]}
          zoom={5}
          className="h-full w-full"
          zoomControl
        >
          <TileLayer
            url={`https://api.maptiler.com/maps/streets-v2/{z}/{x}/{y}.png?key=${import.meta.env.VITE_MAPTILER_KEY}`}
            attribution='&copy; <a href="https://www.maptiler.com/copyright/" target="_blank">MapTiler</a> &copy; <a href="https://www.openstreetmap.org/copyright" target="_blank">OpenStreetMap</a>'
            tileSize={512}
            zoomOffset={-1}
            minZoom={1}
            maxZoom={20}
          />
          <DrawControl onPolygon={handlePolygon} />
          <MapFlyTo target={flyTarget} />
          <ResultsOverlay data={previewData} visibleCapas={visibleCapas} />
        </MapContainer>

        {/* Tooltip de ayuda */}
        {!polygon && (
          <div className="absolute bottom-8 left-1/2 -translate-x-1/2 bg-white rounded-full shadow-lg px-5 py-2.5 text-sm text-gray-600 flex items-center gap-2 pointer-events-none z-[1000]">
            <svg className="w-4 h-4 text-brand-700" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                d="M15 15l-2 5L9 9l11 4-5 2zm0 0l5 5" />
            </svg>
            Usa la herramienta de dibujo para definir el área de análisis
          </div>
        )}

        {/* Spinner overlay mientras analiza */}
        {loading && (
          <div className="absolute inset-0 bg-black/20 flex items-center justify-center z-[999] pointer-events-none">
            <div className="bg-white rounded-2xl shadow-xl px-8 py-6 flex flex-col items-center gap-3">
              <span className="w-10 h-10 border-4 border-brand-800 border-t-transparent rounded-full animate-spin" />
              <p className="text-sm font-semibold text-gray-700">Consultando INEGI DENUE...</p>
              <p className="text-xs text-gray-400">Puede tardar 3–8 minutos</p>
            </div>
          </div>
        )}
      </main>

      {/* ══ PANEL KPIs (deslizable derecho) ═════════════════════════════ */}
      <div className={`
        flex-shrink-0 border-l border-gray-200 bg-[#0d1b2a] transition-all duration-300 overflow-hidden
        ${showKPI && previewData ? 'w-80' : 'w-0'}
      `}>
        {showKPI && previewData && (
          <div className="w-80 h-full">
            <KPIPanel
              data={previewData}
              onClose={() => setShowKPI(false)}
              visibleCapas={visibleCapas}
              onToggleCapa={toggleCapa}
            />
          </div>
        )}
      </div>

      {/* ══ ADMIN MODAL ══════════════════════════════════════════════════ */}
      {showAdmin && <AdminPanel onClose={() => setShowAdmin(false)} />}

    </div>
  )
}
