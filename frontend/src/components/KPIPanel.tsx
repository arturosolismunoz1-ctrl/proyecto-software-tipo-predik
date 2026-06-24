import type { PreviewData } from '../api/client'

const COLOR_MAP: Record<string, string> = {
  red:    '#ef4444',
  green:  '#22c55e',
  blue:   '#3b82f6',
  yellow: '#eab308',
  orange: '#f97316',
  purple: '#a855f7',
  cyan:   '#06b6d4',
  pink:   '#ec4899',
}

const NIVEL_BADGE: Record<string, { bg: string; text: string }> = {
  PREMIUM:    { bg: '#005500', text: '#ffffff' },
  MEDIO_ALTO: { bg: '#22AA22', text: '#ffffff' },
  MEDIO:      { bg: '#FFAA00', text: '#000000' },
  BAJO:       { bg: '#888888', text: '#ffffff' },
  ALTA:       { bg: '#006400', text: '#ffffff' },
  MEDIA_ALTA: { bg: '#44CC44', text: '#000000' },
  MEDIA:      { bg: '#DDCC00', text: '#000000' },
  BAJA:       { bg: '#AAAAAA', text: '#ffffff' },
  SATURADA:   { bg: '#CC0000', text: '#ffffff' },
}

interface Props {
  data: PreviewData | null
  onClose: () => void
  visibleCapas?: Record<string, boolean>
  onToggleCapa?: (keyword: string) => void
}

export function KPIPanel({ data, onClose, visibleCapas, onToggleCapa }: Props) {
  if (!data) return null

  const { resumen, capas, zonas } = data

  // Top 5 zonas por cantidad
  const topZonas = [...zonas]
    .filter(z => z.properties.cantidad > 0)
    .sort((a, b) => b.properties.cantidad - a.properties.cantidad)
    .slice(0, 5)

  // Distribución por nivel
  const nivelesCount: Record<string, number> = {}
  zonas.forEach(z => {
    const nivel = z.properties.nivel || 'Sin clasificar'
    nivelesCount[nivel] = (nivelesCount[nivel] || 0) + 1
  })

  const clasificacionLabel: Record<string, string> = {
    densidad:          'Densidad comercial',
    oportunidad:       'Oportunidad de negocio',
    poder_adquisitivo: 'Poder adquisitivo',
  }

  return (
    <div className="flex flex-col h-full bg-[#0d1b2a] text-white overflow-hidden">
      {/* Header */}
      <div className="flex items-center justify-between px-4 py-3 border-b border-white/10 bg-[#0a1520]">
        <div>
          <h2 className="font-bold text-base text-white">Resultados del análisis</h2>
          <p className="text-xs text-gray-400">
            {clasificacionLabel[resumen.clasificacion] || resumen.clasificacion}
            {resumen.usa_agebs ? ' · AGEBs reales' : ' · Hexágonos H3'}
          </p>
        </div>
        <button
          onClick={onClose}
          className="text-gray-400 hover:text-white text-xl leading-none"
          title="Cerrar"
        >
          ×
        </button>
      </div>

      {/* Scroll area */}
      <div className="flex-1 overflow-y-auto px-4 py-3 space-y-5">

        {/* KPIs principales */}
        <div className="grid grid-cols-2 gap-3">
          <KPICard
            value={resumen.total_establecimientos.toLocaleString()}
            label="Establecimientos encontrados"
            color="#3b82f6"
          />
          <KPICard
            value={resumen.total_zonas.toLocaleString()}
            label="Zonas analizadas"
            color="#22c55e"
          />
          {resumen.poblacion_alcanzada > 0 && (
            <KPICard
              value={(resumen.poblacion_alcanzada / 1000).toFixed(1) + 'k'}
              label="Población en zona"
              color="#a855f7"
            />
          )}
          {resumen.zonas_premium > 0 && (
            <KPICard
              value={resumen.zonas_premium.toLocaleString()}
              label="Zonas PREMIUM / ALTA"
              color="#eab308"
            />
          )}
        </div>

        {/* Por capa */}
        <Section title="Establecimientos por capa">
          <div className="space-y-2">
            {capas.map(capa => {
              const max     = Math.max(...capas.map(c => c.cantidad), 1)
              const pct     = (capa.cantidad / max) * 100
              const visible = visibleCapas ? (visibleCapas[capa.keyword] !== false) : true
              return (
                <div key={capa.keyword} className={visible ? '' : 'opacity-40'}>
                  <div className="flex justify-between text-sm mb-1">
                    <span className="flex items-center gap-2 min-w-0">
                      <span
                        className="inline-block w-3 h-3 rounded-full flex-shrink-0"
                        style={{ background: COLOR_MAP[capa.color] || '#888' }}
                      />
                      <span className="truncate">{capa.label}</span>
                    </span>
                    <span className="flex items-center gap-2 flex-shrink-0 ml-2">
                      <span className="font-bold">{capa.cantidad}</span>
                      {onToggleCapa && (
                        <button
                          onClick={() => onToggleCapa(capa.keyword)}
                          title={visible ? 'Ocultar en mapa' : 'Mostrar en mapa'}
                          className="text-gray-400 hover:text-white transition-colors"
                        >
                          {visible ? (
                            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                                d="M15 12a3 3 0 11-6 0 3 3 0 016 0z" />
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                                d="M2.458 12C3.732 7.943 7.523 5 12 5c4.478 0 8.268 2.943 9.542 7-1.274 4.057-5.064 7-9.542 7-4.477 0-8.268-2.943-9.542-7z" />
                            </svg>
                          ) : (
                            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                                d="M13.875 18.825A10.05 10.05 0 0112 19c-4.478 0-8.268-2.943-9.543-7a9.97 9.97 0 011.563-3.029m5.858.908a3 3 0 114.243 4.243M9.878 9.878l4.242 4.242M9.88 9.88l-3.29-3.29m7.532 7.532l3.29 3.29M3 3l3.59 3.59m0 0A9.953 9.953 0 0112 5c4.478 0 8.268 2.943 9.543 7a10.025 10.025 0 01-4.132 5.411m0 0L21 21" />
                            </svg>
                          )}
                        </button>
                      )}
                    </span>
                  </div>
                  <div className="h-1.5 bg-white/10 rounded-full overflow-hidden">
                    <div
                      className="h-full rounded-full transition-all"
                      style={{
                        width: `${pct}%`,
                        background: visible ? (COLOR_MAP[capa.color] || '#3b82f6') : '#444',
                      }}
                    />
                  </div>
                </div>
              )
            })}
          </div>
        </Section>

        {/* Distribución por nivel */}
        {Object.keys(nivelesCount).length > 0 && (
          <Section title="Distribución de zonas">
            <div className="space-y-1.5">
              {Object.entries(nivelesCount)
                .sort((a, b) => b[1] - a[1])
                .map(([nivel, count]) => {
                  const badge = NIVEL_BADGE[nivel]
                  const pct = (count / resumen.total_zonas) * 100
                  return (
                    <div key={nivel} className="flex items-center gap-2 text-sm">
                      <span
                        className="px-1.5 py-0.5 rounded text-xs font-bold whitespace-nowrap"
                        style={badge
                          ? { background: badge.bg, color: badge.text }
                          : { background: '#444', color: '#fff' }}
                      >
                        {nivel}
                      </span>
                      <div className="flex-1 h-1.5 bg-white/10 rounded-full overflow-hidden">
                        <div
                          className="h-full rounded-full"
                          style={{
                            width: `${pct}%`,
                            background: badge?.bg || '#666',
                          }}
                        />
                      </div>
                      <span className="text-gray-400 w-6 text-right">{count}</span>
                    </div>
                  )
                })}
            </div>
          </Section>
        )}

        {/* Top zonas */}
        {topZonas.length > 0 && (
          <Section title="Top zonas por concentración">
            <div className="space-y-1.5">
              {topZonas.map((zona, i) => {
                const p = zona.properties
                return (
                  <div key={p.cvegeo || p.h3_index || i}
                    className="flex items-center gap-2 bg-white/5 rounded px-3 py-2 text-sm">
                    <span className="text-gray-400 w-4">{i + 1}.</span>
                    <div className="flex-1 min-w-0">
                      <div className="font-medium truncate">{p.label}</div>
                      {p.nom_mun && (
                        <div className="text-xs text-gray-400 truncate">{p.nom_mun}</div>
                      )}
                    </div>
                    <span className="font-bold text-blue-400">{p.cantidad}</span>
                  </div>
                )
              })}
            </div>
          </Section>
        )}

      </div>
    </div>
  )
}

function KPICard({ value, label, color }: { value: string; label: string; color: string }) {
  return (
    <div className="bg-white/5 rounded-lg px-3 py-3">
      <div className="text-2xl font-bold" style={{ color }}>{value}</div>
      <div className="text-xs text-gray-400 mt-0.5 leading-snug">{label}</div>
    </div>
  )
}

function Section({ title, children }: { title: string; children: React.ReactNode }) {
  return (
    <div>
      <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-2">
        {title}
      </h3>
      {children}
    </div>
  )
}
