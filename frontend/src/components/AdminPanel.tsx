import { useEffect, useState } from 'react'
import { apiBdStatus } from '../api/client'

interface BdStatus {
  ageb_geometries:   number
  ageb_demographics: number
  denue_total:       number
}

interface Props {
  onClose: () => void
}

function parseStatus(raw: { tablas?: { tabla: string; registros: number }[] }): BdStatus {
  const t = raw.tablas ?? []
  return {
    ageb_geometries:   t.find(r => r.tabla.includes('geometries'))?.registros   ?? 0,
    ageb_demographics: t.find(r => r.tabla.includes('demographics'))?.registros ?? 0,
    denue_total:       t.find(r => r.tabla.includes('denue'))?.registros        ?? 0,
  }
}

export function AdminPanel({ onClose }: Props) {
  const [status, setStatus] = useState<BdStatus | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError]   = useState<string | null>(null)

  useEffect(() => {
    apiBdStatus()
      .then(d => setStatus(parseStatus(d)))
      .catch(e => setError(String(e)))
      .finally(() => setLoading(false))
  }, [])

  const rows: { label: string; value: number | undefined; meta: string }[] = [
    {
      label: 'AGEBs (geometrías)',
      value: status?.ageb_geometries,
      meta: status?.ageb_geometries
        ? status.ageb_geometries > 50_000
          ? '✓ Nacional (32 estados)'
          : status.ageb_geometries > 1_000
          ? '✓ Cargado'
          : '⚠ Parcial'
        : '✗ Vacío',
    },
    {
      label: 'AGEBs (demografía)',
      value: status?.ageb_demographics,
      meta: status?.ageb_demographics
        ? status.ageb_demographics > 50_000
          ? '✓ Nacional (32 estados)'
          : status.ageb_demographics > 1_000
          ? '✓ Cargado'
          : '⚠ Parcial'
        : '✗ Vacío',
    },
    {
      label: 'Establecimientos DENUE',
      value: status?.denue_total,
      meta: status?.denue_total ? '✓ Cargado' : '✗ Vacío',
    },
  ]

  return (
    <div className="fixed inset-0 z-[9999] flex items-center justify-center bg-black/60 backdrop-blur-sm">
      <div className="bg-[#0d1b2a] border border-white/10 rounded-xl shadow-2xl w-[480px] max-h-[80vh] flex flex-col overflow-hidden">

        {/* Header */}
        <div className="flex items-center justify-between px-5 py-4 border-b border-white/10">
          <div>
            <h2 className="font-bold text-white text-lg">Panel de administración</h2>
            <p className="text-xs text-gray-400">Estado de la base de datos y ETL</p>
          </div>
          <button onClick={onClose} className="text-gray-400 hover:text-white text-2xl leading-none">×</button>
        </div>

        {/* Body */}
        <div className="flex-1 overflow-y-auto px-5 py-4 space-y-5">

          {/* BD Status */}
          <section>
            <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">
              Estado de la base de datos
            </h3>
            {loading ? (
              <p className="text-gray-400 text-sm">Cargando...</p>
            ) : error ? (
              <p className="text-red-400 text-sm">{error}</p>
            ) : (
              <div className="space-y-2">
                {rows.map(row => (
                  <div key={row.label} className="flex items-center justify-between bg-white/5 rounded-lg px-4 py-3">
                    <div>
                      <div className="text-sm font-medium text-white">{row.label}</div>
                      <div className="text-xs text-gray-400">{row.meta}</div>
                    </div>
                    <div className="text-lg font-bold text-blue-400">
                      {row.value !== undefined && row.value !== null
                        ? row.value.toLocaleString()
                        : '—'}
                    </div>
                  </div>
                ))}
              </div>
            )}
          </section>

          {/* ETL Instructions */}
          <section>
            <h3 className="text-xs font-semibold text-gray-400 uppercase tracking-wider mb-3">
              Carga de datos (ETL)
            </h3>
            <div className="space-y-2 text-sm text-gray-300">

              {/* MGN */}
              <div className="bg-white/5 rounded-lg px-4 py-3">
                <div className="flex items-center gap-2 mb-1">
                  <span className={
                    (status?.ageb_geometries ?? 0) > 1_000
                      ? 'text-green-400' : 'text-yellow-400'
                  }>●</span>
                  <span className="font-medium text-white">Geometrías MGN 2025</span>
                </div>
                <p className="text-xs text-gray-400 mb-2">
                  Polígonos de AGEBs del Marco Geoestadístico Nacional (32 estados).
                </p>
                <code className="block bg-black/40 rounded px-3 py-2 text-xs text-green-300 whitespace-pre-wrap">
python backend/scripts/etl_mgn_maestro.py --solo-mgn
                </code>
              </div>

              {/* Censo 2020 */}
              <div className="bg-white/5 rounded-lg px-4 py-3">
                <div className="flex items-center gap-2 mb-1">
                  <span className={
                    (status?.ageb_demographics ?? 0) > 1_000
                      ? 'text-green-400' : 'text-yellow-400'
                  }>●</span>
                  <span className="font-medium text-white">Demografía Censo 2020</span>
                </div>
                <p className="text-xs text-gray-400 mb-2">
                  Población, escolaridad, vivienda por AGEB (32 estados).
                </p>
                <code className="block bg-black/40 rounded px-3 py-2 text-xs text-green-300 whitespace-pre-wrap">
python backend/scripts/etl_mgn_maestro.py --solo-censo
                </code>
              </div>

              {/* DENUE */}
              <div className="bg-white/5 rounded-lg px-4 py-3">
                <div className="flex items-center gap-2 mb-1">
                  <span className={
                    (status?.denue_total ?? 0) > 10_000
                      ? 'text-green-400' : 'text-yellow-400'
                  }>●</span>
                  <span className="font-medium text-white">Establecimientos DENUE</span>
                </div>
                <p className="text-xs text-gray-400 mb-2">
                  Directorio de negocios INEGI. Requiere token DENUE.
                </p>
                <code className="block bg-black/40 rounded px-3 py-2 text-xs text-green-300 whitespace-pre-wrap">
python backend/scripts/etl_maestro.py --solo-denue
                </code>
              </div>

            </div>
          </section>

        </div>

        {/* Footer */}
        <div className="px-5 py-3 border-t border-white/10 flex justify-end">
          <button
            onClick={onClose}
            className="px-4 py-2 rounded-lg bg-white/10 hover:bg-white/20 text-sm text-white transition"
          >
            Cerrar
          </button>
        </div>

      </div>
    </div>
  )
}
