import { useEffect, useMemo, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import {
  BarChart, Bar, XAxis, YAxis, Tooltip, ResponsiveContainer,
  PieChart, Pie, Cell, Legend,
} from 'recharts'
import { MapContainer, TileLayer } from 'react-leaflet'
import { apiHistorial } from '../../api/client'

import 'react-grid-layout/css/styles.css'
import 'react-resizable/css/styles.css'

// react-grid-layout is CJS — Rollup may wrap it in { default: module.exports }
// eslint-disable-next-line @typescript-eslint/no-explicit-any
import _rglImport from 'react-grid-layout'
// eslint-disable-next-line @typescript-eslint/no-explicit-any
const _rglMod = ((_rglImport as any).default ?? _rglImport) as any
// eslint-disable-next-line @typescript-eslint/no-explicit-any
type AnyComponent = React.ComponentType<any>
const RglResponsive  = _rglMod.Responsive  as AnyComponent
const RglWidthProvider = _rglMod.WidthProvider as (c: AnyComponent) => AnyComponent
const ResponsiveGridLayout = RglWidthProvider(RglResponsive)

// ── Layouts ───────────────────────────────────────────────────────────────────

const LAYOUT_STORAGE_KEY = 'geodata_dashboard_layout_v1'

const defaultLayouts = {
  lg: [
    { i: 'mapa',      x: 0, y: 0, w: 7, h: 4, minW: 4, minH: 3 },
    { i: 'grafica',   x: 7, y: 0, w: 5, h: 4, minW: 3, minH: 3 },
    { i: 'proyectos', x: 0, y: 4, w: 6, h: 3, minW: 3, minH: 2 },
    { i: 'nse',       x: 6, y: 4, w: 6, h: 3, minW: 3, minH: 2 },
  ],
}

function loadLayouts() {
  try {
    const saved = localStorage.getItem(LAYOUT_STORAGE_KEY)
    return saved ? JSON.parse(saved) : defaultLayouts
  } catch {
    return defaultLayouts
  }
}

// ── WidgetShell ───────────────────────────────────────────────────────────────

interface WidgetShellProps {
  id: string
  title: string
  icon: string
  editMode: boolean
  children: React.ReactNode
}

function WidgetShell({ id, title, icon, editMode, children }: WidgetShellProps) {
  return (
    <div
      key={id}
      className={`bg-white rounded-xl overflow-hidden border ${
        editMode ? 'border-dashed border-brand-copper' : 'border-brand-beige'
      } h-full flex flex-col`}
    >
      <div className="flex items-center gap-2 px-3 py-2 border-b border-brand-beige bg-brand-navy/5 flex-shrink-0">
        {editMode && (
          <span className="drag-handle cursor-grab text-brand-copper active:cursor-grabbing">
            <i className="ti ti-grip-vertical text-base" />
          </span>
        )}
        <i className={`ti ti-${icon} text-brand-copper text-sm`} />
        <span className="text-xs font-medium text-brand-black">{title}</span>
      </div>
      <div className="flex-1 overflow-hidden">
        {children}
      </div>
    </div>
  )
}

// ── Widget: Mapa ──────────────────────────────────────────────────────────────

function WidgetMapa() {
  return (
    <MapContainer
      center={[20.9674, -89.5926]}
      zoom={11}
      style={{ height: '100%', width: '100%' }}
      scrollWheelZoom={false}
      zoomControl={false}
    >
      <TileLayer
        url="https://{s}.tile.openstreetmap.org/{z}/{x}/{y}.png"
        attribution='&copy; <a href="https://www.openstreetmap.org/copyright">OpenStreetMap</a> contributors'
      />
    </MapContainer>
  )
}

// ── Widget: Gráfica ───────────────────────────────────────────────────────────

const MESES = ['Ene', 'Feb', 'Mar', 'Abr', 'May', 'Jun', 'Jul', 'Ago', 'Sep', 'Oct', 'Nov', 'Dic']

const defaultChartData = [
  { mes: 'Ene', analisis: 2 },
  { mes: 'Feb', analisis: 4 },
  { mes: 'Mar', analisis: 3 },
  { mes: 'Abr', analisis: 7 },
  { mes: 'May', analisis: 5 },
  { mes: 'Jun', analisis: 9 },
]

function WidgetGrafica({ analisisList }: { analisisList: AnalisisItem[] }) {
  const chartData = useMemo(() => {
    if (!analisisList.length) return defaultChartData
    const counts: Record<string, number> = {}
    analisisList.forEach(a => {
      try {
        const d = new Date(a.created_at)
        const key = MESES[d.getMonth()]
        counts[key] = (counts[key] ?? 0) + 1
      } catch { /* ignore */ }
    })
    const result = Object.entries(counts).map(([mes, analisis]) => ({ mes, analisis }))
    return result.length ? result : defaultChartData
  }, [analisisList])

  return (
    <div className="h-full p-2">
      <p className="text-[10px] text-brand-black/50 mb-1 px-1">Análisis por mes</p>
      <ResponsiveContainer width="100%" height="90%">
        <BarChart data={chartData} margin={{ top: 4, right: 12, left: -20, bottom: 4 }}>
          <XAxis dataKey="mes" tick={{ fontSize: 10, fill: '#222222' }} />
          <YAxis tick={{ fontSize: 10, fill: '#222222' }} allowDecimals={false} />
          <Tooltip
            contentStyle={{ background: '#051C2C', border: 'none', borderRadius: 6 }}
            labelStyle={{ color: '#DEA36D', fontSize: 11 }}
            itemStyle={{ color: '#ffffff', fontSize: 11 }}
          />
          <Bar dataKey="analisis" fill="#DEA36D" radius={[3, 3, 0, 0]} />
        </BarChart>
      </ResponsiveContainer>
    </div>
  )
}

// ── Widget: Proyectos recientes ───────────────────────────────────────────────

interface AnalisisItem {
  id?: string
  marca_propia?: string
  claves_municipios?: string[]
  created_at: string
  status?: string
}

function formatFecha(iso: string): string {
  try {
    return new Date(iso).toLocaleDateString('es-MX', { day: '2-digit', month: 'short', year: 'numeric' })
  } catch {
    return iso
  }
}

function WidgetProyectos({ analisisList }: { analisisList: AnalisisItem[] }) {
  const navigate = useNavigate()
  const items = analisisList.slice(0, 6)

  return (
    <div className="h-full flex flex-col p-2">
      <div className="flex-1 overflow-y-auto">
        {items.length === 0 ? (
          <div className="flex flex-col items-center justify-center h-full gap-2 text-brand-black/30">
            <i className="ti ti-folder text-2xl" />
            <p className="text-xs">No hay análisis recientes</p>
          </div>
        ) : (
          items.map((a, idx) => (
            <div key={a.id ?? idx} className="flex items-center gap-2 p-2 border-b border-brand-beige/50 last:border-0">
              <div className="flex-1 min-w-0">
                <p className="text-xs font-medium text-brand-black truncate">
                  {a.marca_propia || `Análisis #${(a.id ?? '').slice(0, 8)}`}
                </p>
                <p className="text-[10px] text-brand-black/50">
                  {a.claves_municipios?.length ?? 0} municipios · {formatFecha(a.created_at)}
                </p>
              </div>
              <span className={`text-[9px] px-2 py-0.5 rounded font-medium flex-shrink-0 ${
                (a.status ?? 'completado') === 'completado'
                  ? 'bg-brand-green text-white'
                  : 'border border-brand-copper text-brand-copper'
              }`}>
                {a.status ?? 'completado'}
              </span>
            </div>
          ))
        )}
      </div>
      <button
        onClick={() => navigate('/analisis')}
        className="mt-2 py-1.5 text-xs border border-brand-copper text-brand-copper rounded hover:bg-brand-copper hover:text-brand-navy transition-colors w-full"
      >
        + Nuevo análisis
      </button>
    </div>
  )
}

// ── Widget: NSE Donut ─────────────────────────────────────────────────────────

const NSE_DATA = [
  { name: 'AB',  value: 15 },
  { name: 'C+',  value: 20 },
  { name: 'C',   value: 25 },
  { name: 'C-',  value: 18 },
  { name: 'D+',  value: 12 },
  { name: 'D',   value: 7  },
  { name: 'E',   value: 3  },
]

const NSE_COLORS = ['#DEA36D', '#051C2C', '#19322F', '#D0D0AA', '#4A6FA5', '#8B7355', '#222222']

function WidgetNSE() {
  return (
    <div className="h-full p-2">
      <p className="text-[10px] text-brand-black/50 mb-1 px-1">Distribución NSE — referencia AMAI</p>
      <ResponsiveContainer width="100%" height="90%">
        <PieChart>
          <Pie
            data={NSE_DATA}
            cx="40%"
            cy="50%"
            innerRadius="40%"
            outerRadius="65%"
            dataKey="value"
          >
            {NSE_DATA.map((_, index) => (
              <Cell key={index} fill={NSE_COLORS[index % NSE_COLORS.length]} />
            ))}
          </Pie>
          <Tooltip
            formatter={(value) => [`${value}%`, 'NSE']}
            contentStyle={{ background: '#051C2C', border: 'none', borderRadius: 6, fontSize: 11 }}
            itemStyle={{ color: '#ffffff' }}
          />
          <Legend
            layout="vertical"
            align="right"
            verticalAlign="middle"
            iconSize={8}
            iconType="circle"
            formatter={(value) => (
              <span style={{ fontSize: 10, color: '#222222' }}>{value}</span>
            )}
          />
        </PieChart>
      </ResponsiveContainer>
    </div>
  )
}

// ── KPI Cards ─────────────────────────────────────────────────────────────────

interface KpiCardProps {
  label: string
  valor: string | number
  subtexto: string
}

function KpiCard({ label, valor, subtexto }: KpiCardProps) {
  return (
    <div className="bg-white rounded-lg p-4 border-l-4 border-brand-copper">
      <p className="text-xs text-brand-black/60 uppercase tracking-wide mb-1">{label}</p>
      <p className="text-3xl font-semibold text-brand-navy">{valor}</p>
      <p className="text-xs text-brand-black/40 mt-1">{subtexto}</p>
    </div>
  )
}

// ── DashboardPage ─────────────────────────────────────────────────────────────

interface Props {
  editMode: boolean
}

export function DashboardPage({ editMode }: Props) {
  const [analisisList, setAnalisisList] = useState<AnalisisItem[]>([])
  const [layouts, setLayouts] = useState(loadLayouts)

  useEffect(() => {
    apiHistorial()
      .then(data => setAnalisisList(data as AnalisisItem[]))
      .catch(() => { /* silent */ })
  }, [])

  // KPI derivados
  const now = new Date()
  const esteMes = analisisList.filter(a => {
    try { return new Date(a.created_at).getMonth() === now.getMonth() && new Date(a.created_at).getFullYear() === now.getFullYear() }
    catch { return false }
  })
  const mesPasado = analisisList.filter(a => {
    try {
      const d = new Date(a.created_at)
      const prev = new Date(now.getFullYear(), now.getMonth() - 1, 1)
      return d.getMonth() === prev.getMonth() && d.getFullYear() === prev.getFullYear()
    }
    catch { return false }
  })
  const delta = esteMes.length - mesPasado.length
  const totalMunicipios = analisisList.reduce((sum, a) => sum + (a.claves_municipios?.length ?? 0), 0)
  const estadosSet = new Set(analisisList.flatMap(a => a.claves_municipios?.map(m => m.slice(0, 2)) ?? []))
  const ultimoAnalisis = analisisList[0]

  const kpis: KpiCardProps[] = [
    {
      label: 'Análisis este mes',
      valor: esteMes.length,
      subtexto: delta !== 0 ? `${delta > 0 ? '+' : ''}${delta} vs mes anterior` : 'sin cambio vs mes anterior',
    },
    {
      label: 'Zonas evaluadas',
      valor: totalMunicipios,
      subtexto: estadosSet.size > 0 ? `en ${estadosSet.size} estado${estadosSet.size > 1 ? 's' : ''}` : '—',
    },
    {
      label: 'KMZ generados',
      valor: analisisList.length,
      subtexto: ultimoAnalisis ? `último: ${formatFecha(ultimoAnalisis.created_at)}` : 'sin registros',
    },
    {
      label: 'Total análisis',
      valor: analisisList.length,
      subtexto: 'plan activo',
    },
  ]

  return (
    <div className="h-full flex flex-col gap-3">
      {/* KPI fijos */}
      <div className="grid grid-cols-4 gap-3 flex-shrink-0">
        {kpis.map(k => <KpiCard key={k.label} {...k} />)}
      </div>

      {/* Widget grid */}
      <div className="flex-1 min-h-0">
        <ResponsiveGridLayout
          className="layout"
          layouts={layouts}
          breakpoints={{ lg: 1200, md: 996, sm: 768, xs: 480 }}
          cols={{ lg: 12, md: 10, sm: 6, xs: 4 }}
          rowHeight={80}
          margin={[10, 10]}
          isDraggable={editMode}
          isResizable={editMode}
          draggableHandle=".drag-handle"
          onLayoutChange={(_layout: unknown, allLayouts: unknown) => {
            setLayouts(allLayouts)
            try {
              localStorage.setItem(LAYOUT_STORAGE_KEY, JSON.stringify(allLayouts))
            } catch { /* ignore */ }
          }}
        >
          <div key="mapa">
            <WidgetShell id="mapa" title="Mapa" icon="map" editMode={editMode}>
              <WidgetMapa />
            </WidgetShell>
          </div>

          <div key="grafica">
            <WidgetShell id="grafica" title="Actividad mensual" icon="chart-bar" editMode={editMode}>
              <WidgetGrafica analisisList={analisisList} />
            </WidgetShell>
          </div>

          <div key="proyectos">
            <WidgetShell id="proyectos" title="Análisis recientes" icon="clock" editMode={editMode}>
              <WidgetProyectos analisisList={analisisList} />
            </WidgetShell>
          </div>

          <div key="nse">
            <WidgetShell id="nse" title="Distribución NSE" icon="chart-pie" editMode={editMode}>
              <WidgetNSE />
            </WidgetShell>
          </div>
        </ResponsiveGridLayout>
      </div>
    </div>
  )
}
