import { useEffect, useState } from 'react'
import { apiBieResumen, type BieResumen } from '../api/client'

interface Props {
  claveEstado: string
  nombreEstado: string
}

interface Tile {
  key: string
  label: string
  value: string | null
  sub?: string
  colorClass: string
  tooltip?: string
}

function buildTiles(ind: BieResumen['indicadores']): Tile[] {
  const itaee = ind['itaee']
  const desoc  = ind['desocupacion']
  const emp    = ind['empleo_formal']
  const pea    = ind['pea']

  return [
    {
      key: 'itaee',
      label: 'Crec. económico',
      value: itaee?.valor != null
        ? `${itaee.valor > 0 ? '+' : ''}${itaee.valor.toFixed(1)}%`
        : null,
      sub: itaee?.periodo,
      colorClass:
        itaee?.valor == null ? 'text-gray-400'
        : itaee.valor > 2    ? 'text-green-600'
        : itaee.valor > 0    ? 'text-emerald-500'
        : 'text-red-500',
      tooltip: itaee?.interpretacion,
    },
    {
      key: 'desocupacion',
      label: 'Desocupación',
      value: desoc?.valor != null ? `${desoc.valor.toFixed(1)}%` : null,
      sub: desoc?.periodo,
      colorClass:
        desoc?.valor == null ? 'text-gray-400'
        : desoc.valor < 4   ? 'text-green-600'
        : desoc.valor < 6   ? 'text-yellow-600'
        : 'text-red-500',
      tooltip: desoc?.interpretacion,
    },
    {
      key: 'empleo_formal',
      label: 'Empleo formal',
      value: emp?.valor != null
        ? emp.valor >= 1_000_000
          ? `${(emp.valor / 1_000_000).toFixed(1)}M`
          : `${(emp.valor / 1_000).toFixed(0)}k`
        : null,
      sub: emp?.periodo,
      colorClass: 'text-brand-700',
      tooltip: emp?.interpretacion,
    },
    {
      key: 'pea',
      label: 'PEA',
      value: pea?.valor != null ? `${pea.valor.toLocaleString()}k` : null,
      sub: pea?.periodo,
      colorClass: 'text-indigo-600',
      tooltip: pea?.interpretacion,
    },
  ]
}

export function EconomicContextWidget({ claveEstado, nombreEstado }: Props) {
  const [data,    setData]    = useState<BieResumen | null>(null)
  const [loading, setLoading] = useState(false)
  const [open,    setOpen]    = useState(true)

  useEffect(() => {
    if (!claveEstado) return
    setLoading(true)
    setData(null)
    apiBieResumen(claveEstado)
      .then(setData)
      .catch(console.error)
      .finally(() => setLoading(false))
  }, [claveEstado])

  const isDemo = data?.fuente === 'demo'
  const tiles  = data ? buildTiles(data.indicadores) : []

  return (
    <div className="border border-gray-200 rounded-xl bg-white shadow-sm overflow-hidden">
      {/* Header colapsable */}
      <button
        onClick={() => setOpen(o => !o)}
        className="w-full flex items-center justify-between px-3 py-2.5 text-left hover:bg-gray-50 transition-colors"
      >
        <div className="flex items-center gap-2">
          <svg className="w-3.5 h-3.5 text-brand-700" fill="none" viewBox="0 0 24 24" stroke="currentColor">
            <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
              d="M9 19v-6a2 2 0 00-2-2H5a2 2 0 00-2 2v6a2 2 0 002 2h2a2 2 0 002-2zm0 0V9a2 2 0 012-2h2a2 2 0 012 2v10m-6 0a2 2 0 002 2h2a2 2 0 002-2m0 0V5a2 2 0 012-2h2a2 2 0 012 2v14a2 2 0 01-2 2h-2a2 2 0 01-2-2z" />
          </svg>
          <span className="text-xs font-semibold text-gray-600">Contexto económico</span>
          {isDemo && (
            <span className="text-[10px] bg-amber-100 text-amber-700 px-1.5 py-0.5 rounded-full font-medium">
              Demo
            </span>
          )}
          {!isDemo && data && (
            <span className="text-[10px] bg-green-100 text-green-700 px-1.5 py-0.5 rounded-full font-medium">
              BIE INEGI
            </span>
          )}
        </div>
        <svg
          className={`w-3.5 h-3.5 text-gray-400 transition-transform ${open ? 'rotate-180' : ''}`}
          fill="none" viewBox="0 0 24 24" stroke="currentColor"
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </svg>
      </button>

      {open && (
        <div className="px-3 pb-3">
          <p className="text-[11px] text-gray-400 mb-2 truncate">{nombreEstado}</p>

          {loading ? (
            <div className="flex items-center gap-2 text-xs text-gray-400 py-2">
              <span className="w-3 h-3 border-2 border-brand-700 border-t-transparent rounded-full animate-spin flex-shrink-0" />
              Cargando indicadores...
            </div>
          ) : data ? (
            <>
              <div className="grid grid-cols-2 gap-1.5">
                {tiles.map(t => (
                  <div
                    key={t.key}
                    title={t.tooltip}
                    className="bg-gray-50 rounded-lg px-2.5 py-2 cursor-default"
                  >
                    <div className={`text-base font-bold leading-none ${t.colorClass}`}>
                      {t.value ?? '—'}
                    </div>
                    <div className="text-[11px] text-gray-500 mt-0.5 leading-tight">{t.label}</div>
                    {t.sub && (
                      <div className="text-[10px] text-gray-400 mt-0.5">{t.sub}</div>
                    )}
                  </div>
                ))}
              </div>
              {data.advertencia && (
                <p className="text-[10px] text-amber-600 mt-2 leading-tight">{data.advertencia}</p>
              )}
              <p className="text-[10px] text-gray-300 mt-1.5">Fuente: INEGI BIE</p>
            </>
          ) : (
            <p className="text-xs text-gray-400 py-1">No se pudo cargar el contexto económico.</p>
          )}
        </div>
      )}
    </div>
  )
}
