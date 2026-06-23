import { useCallback, useEffect, useRef, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { MapContainer, TileLayer, useMap } from 'react-leaflet'
import L from 'leaflet'
import 'leaflet-draw'
import { useAuthStore } from '../store/useAuthStore'
import { apiEstados, apiGenerarReporte, apiBdStatus } from '../api/client'
import type { Capa, ColorNombre, EstadoCatalogo, GeoJSONGeometry, Clasificacion, Formato } from '../types'

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
        polygon:     { shapeOptions: { color: '#1a5fc3', weight: 2, fillOpacity: 0.12 } },
        rectangle:   { shapeOptions: { color: '#1a5fc3', weight: 2, fillOpacity: 0.12 } },
        polyline:    false,
        circle:      false,
        marker:      false,
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
  const colors = { vacia: 'bg-red-100 text-red-700', parcial: 'bg-yellow-100 text-yellow-700', ok: 'bg-green-100 text-green-700' }
  return (
    <span className={`inline-flex items-center gap-1 text-xs font-medium px-2 py-0.5 rounded-full ${colors[estado]}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${estado === 'ok' ? 'bg-green-500' : estado === 'parcial' ? 'bg-yellow-500' : 'bg-red-400'}`} />
      {label}: {count.toLocaleString()}
    </span>
  )
}

// ── LayerRow ──────────────────────────────────────────────────────────────────

interface LayerRowProps {
  capa: Capa
  estados: EstadoCatalogo[]
  onChange: (c: Capa) => void
  onRemove: () => void
  canRemove: boolean
  index: number
}

function LayerRow({ capa, estados, onChange, onRemove, canRemove, index }: LayerRowProps) {
  const set = (field: keyof Capa, v: string) => onChange({ ...capa, [field]: v })

  return (
    <div className="border border-gray-200 rounded-xl p-3 bg-white shadow-sm space-y-2.5">
      {/* Header de capa */}
      <div className="flex items-center justify-between">
        <span className="text-xs font-semibold text-gray-400 uppercase tracking-wider">
          Capa {index + 1}
        </span>
        {canRemove && (
          <button onClick={onRemove} className="text-gray-300 hover:text-red-400 transition-colors">
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
            </svg>
          </button>
        )}
      </div>

      {/* Keyword */}
      <input
        type="text"
        placeholder="Negocio a buscar (ej: little caesars)"
        value={capa.keyword}
        onChange={e => set('keyword', e.target.value)}
        className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm placeholder-gray-400 focus:ring-2 focus:ring-brand-500 focus:border-brand-500 outline-none"
      />

      {/* Etiqueta */}
      <input
        type="text"
        placeholder="Nombre en el reporte (ej: Little Caesars)"
        value={capa.label}
        onChange={e => set('label', e.target.value)}
        className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm placeholder-gray-400 focus:ring-2 focus:ring-brand-500 focus:border-brand-500 outline-none"
      />

      {/* Estado */}
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

      {/* Color + Icono */}
      <div className="flex items-center justify-between">
        {/* Paleta de colores */}
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

        {/* Tipo de icono */}
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
  const { logout } = useAuthStore()
  const navigate   = useNavigate()

  const [polygon,       setPolygon]       = useState<GeoJSONGeometry | null>(null)
  const [estados,       setEstados]       = useState<EstadoCatalogo[]>([])
  const [capas,         setCapas]         = useState<Capa[]>([mkCapa('blue')])
  const [clasificacion, setClasificacion] = useState<Clasificacion>('densidad')
  const [formato,       setFormato]       = useState<Formato>('kmz')
  const [loading,       setLoading]       = useState(false)
  const [status,        setStatus]        = useState<string>('')
  const [statusType,    setStatusType]    = useState<'idle' | 'ok' | 'error'>('idle')
  const [bdInfo,        setBdInfo]        = useState<{ denue: number; demographics: number } | null>(null)

  const handlePolygon = useCallback((g: GeoJSONGeometry) => {
    setPolygon(g)
    setStatus('Área definida. Configura las capas y genera el reporte.')
    setStatusType('ok')
  }, [])

  // Cargar catálogo de estados y estado de BD al montar
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
    setStatus('Consultando INEGI DENUE y generando reporte... esto puede tardar 3-8 minutos.')
    setStatusType('idle')

    try {
      const payload = {
        nombre: capas.map(c => c.label || c.keyword).join(' vs '),
        polygon,
        capas: capas.map(c => ({
          keyword: c.keyword.trim(),
          label:   c.label.trim() || c.keyword.trim(),
          color:   c.color,
          icon:    c.icon,
          estado:  c.estado,
        })),
        formato,
        clasificacion_hexagonos: clasificacion,
        h3_resolution: 9,
        ejecutar_etl: true,
      }

      const { blob, filename } = await apiGenerarReporte(payload)

      // Disparar descarga del archivo
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

  const handleLogout = () => {
    logout()
    navigate('/login')
  }

  return (
    <div className="h-screen flex overflow-hidden bg-gray-50">

      {/* ══════════════════════ SIDEBAR ══════════════════════ */}
      <aside className="w-80 min-w-[320px] bg-white border-r border-gray-100 flex flex-col shadow-sm z-10">

        {/* ── Header ── */}
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
            <button
              onClick={handleLogout}
              className="text-blue-300 hover:text-white text-xs border border-blue-600 hover:border-blue-300 rounded-md px-2.5 py-1 transition-colors"
            >
              Salir
            </button>
          </div>

          {/* BD Status badges */}
          {bdInfo && (
            <div className="mt-3 flex flex-wrap gap-1.5">
              <BdBadge count={bdInfo.denue}        label="DENUE" />
              <BdBadge count={bdInfo.demographics} label="Censo" />
            </div>
          )}
        </div>

        {/* ── Body scrollable ── */}
        <div className="flex-1 overflow-y-auto sidebar-scroll px-4 py-5 space-y-6">

          {/* PASO 1: Área */}
          <section>
            <div className="flex items-center gap-2 mb-2">
              <span className="w-5 h-5 rounded-full bg-brand-800 text-white text-xs flex items-center justify-center font-bold flex-shrink-0">1</span>
              <h2 className="text-sm font-semibold text-gray-700">Área de análisis</h2>
            </div>
            <div className={`text-xs rounded-lg px-3 py-2.5 border flex items-center gap-2 ${
              polygon
                ? 'bg-green-50 border-green-200 text-green-700'
                : 'bg-amber-50 border-amber-200 text-amber-700'
            }`}>
              {polygon ? (
                <>
                  <svg className="w-4 h-4 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                  </svg>
                  Polígono definido correctamente
                </>
              ) : (
                <>
                  <svg className="w-4 h-4 flex-shrink-0" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 15l-2 5L9 9l11 4-5 2zm0 0l5 5" />
                  </svg>
                  Dibuja un polígono en el mapa
                </>
              )}
            </div>
          </section>

          {/* PASO 2: Capas */}
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

          {/* PASO 3: Opciones */}
          <section>
            <div className="flex items-center gap-2 mb-3">
              <span className="w-5 h-5 rounded-full bg-brand-800 text-white text-xs flex items-center justify-center font-bold flex-shrink-0">3</span>
              <h2 className="text-sm font-semibold text-gray-700">Opciones de análisis</h2>
            </div>

            {/* Clasificación */}
            <div className="mb-4">
              <p className="text-xs text-gray-500 font-medium mb-2">Clasificación de zonas</p>
              <div className="space-y-1.5">
                {[
                  { value: 'densidad',         label: 'Densidad comercial',            desc: 'Intensidad de establecimientos' },
                  { value: 'oportunidad',       label: 'Oportunidad competitiva',       desc: 'Zonas sin presencia de la competencia' },
                  { value: 'poder_adquisitivo', label: 'Poder adquisitivo',             desc: 'Zonas premium según escolaridad INEGI' },
                ].map(opt => (
                  <label key={opt.value} className={`flex items-start gap-2.5 p-2.5 rounded-lg border cursor-pointer transition-colors ${
                    clasificacion === opt.value ? 'bg-brand-50 border-brand-300' : 'border-gray-100 hover:bg-gray-50'
                  }`}>
                    <input
                      type="radio"
                      name="clasificacion"
                      value={opt.value}
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

            {/* Formato */}
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
                      type="radio"
                      name="formato"
                      value={f.value}
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

        {/* ── Footer / CTA ── */}
        <div className="p-4 border-t border-gray-100 flex-shrink-0 space-y-2.5">
          {/* Status message */}
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

          {/* Botón principal */}
          <button
            onClick={handleGenerar}
            disabled={loading || !polygon}
            className="w-full bg-brand-800 text-white rounded-xl py-3 font-semibold text-sm hover:bg-brand-700 active:bg-brand-900 disabled:opacity-50 disabled:cursor-not-allowed transition-colors flex items-center justify-center gap-2 shadow-sm"
          >
            {loading ? (
              <>
                <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                Generando reporte...
              </>
            ) : (
              <>
                <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                    d="M12 10v6m0 0l-3-3m3 3l3-3m2 8H7a2 2 0 01-2-2V5a2 2 0 012-2h5.586a1 1 0 01.707.293l5.414 5.414a1 1 0 01.293.707V19a2 2 0 01-2 2z" />
                </svg>
                Generar Reporte {formato.toUpperCase()}
              </>
            )}
          </button>
        </div>
      </aside>

      {/* ══════════════════════ MAPA ══════════════════════ */}
      <main className="flex-1 relative">
        <MapContainer
          center={[23.6345, -102.5528]}
          zoom={5}
          className="h-full w-full"
          zoomControl
        >
          {/* MapTiler Streets — aspecto Google Maps */}
          <TileLayer
            url={`https://api.maptiler.com/maps/streets-v2/{z}/{x}/{y}.png?key=${import.meta.env.VITE_MAPTILER_KEY}`}
            attribution='&copy; <a href="https://www.maptiler.com/copyright/" target="_blank">MapTiler</a> &copy; <a href="https://www.openstreetmap.org/copyright" target="_blank">OpenStreetMap</a>'
            tileSize={512}
            zoomOffset={-1}
            minZoom={1}
            maxZoom={20}
          />
          <DrawControl onPolygon={handlePolygon} />
        </MapContainer>

        {/* Tooltip de ayuda flotante (desaparece al dibujar) */}
        {!polygon && (
          <div className="absolute bottom-8 left-1/2 -translate-x-1/2 bg-white rounded-full shadow-lg px-5 py-2.5 text-sm text-gray-600 flex items-center gap-2 pointer-events-none z-[1000]">
            <svg className="w-4 h-4 text-brand-700" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                d="M15 15l-2 5L9 9l11 4-5 2zm0 0l5 5" />
            </svg>
            Usa la herramienta de dibujo para definir el área de análisis
          </div>
        )}
      </main>
    </div>
  )
}
