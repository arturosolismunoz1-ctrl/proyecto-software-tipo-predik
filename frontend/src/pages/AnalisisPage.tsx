import { useLocation, useNavigate } from 'react-router-dom'
import { AppSidebar } from '../components/layout/AppSidebar'
import { AppTopbar } from '../components/layout/AppTopbar'

export default function AnalisisPage() {
  const navigate = useNavigate()
  const location = useLocation()

  return (
    <div className="flex h-screen overflow-hidden bg-brand-bg">
      <AppSidebar />
      <div className="flex flex-col flex-1 overflow-hidden min-w-0">
        <AppTopbar editMode={false} onToggleEdit={() => {}} currentPath={location.pathname} />
        <main className="flex-1 overflow-auto p-4">
          <div className="max-w-2xl mx-auto mt-8">
            <h2 className="text-lg font-medium text-brand-navy mb-6">
              Selecciona el tipo de análisis
            </h2>

            <div
              className="bg-white rounded-xl border-l-4 border-brand-copper p-5 cursor-pointer hover:shadow-md transition-shadow"
              onClick={() => navigate('/analisis/competencia')}
            >
              <div className="flex items-start gap-4">
                <div className="w-10 h-10 rounded-lg bg-brand-navy flex items-center justify-center flex-shrink-0">
                  <i className="ti ti-map-search text-brand-copper text-xl" />
                </div>
                <div className="flex-1">
                  <h3 className="font-medium text-brand-navy text-sm mb-1">
                    Análisis geoespacial de competencia y zonas de oportunidad
                  </h3>
                  <p className="text-xs text-brand-black/60 leading-relaxed">
                    Identifica zonas con alto potencial, evalúa competidores directos e indirectos,
                    genera hubs de concentración y zonas blancas de oportunidad.
                    Exporta resultados en KMZ o Excel.
                  </p>
                  <div className="flex gap-2 mt-3 flex-wrap">
                    <span className="text-[10px] bg-brand-navy/10 text-brand-navy px-2 py-0.5 rounded">
                      DENUE + Censo 2020
                    </span>
                    <span className="text-[10px] bg-brand-copper/10 text-brand-copper px-2 py-0.5 rounded">
                      Exporta KMZ
                    </span>
                    <span className="text-[10px] bg-brand-green text-white px-2 py-0.5 rounded">
                      NSE por AGEB
                    </span>
                  </div>
                </div>
                <i className="ti ti-arrow-right text-brand-copper text-lg flex-shrink-0 mt-1" />
              </div>
            </div>

            <p className="text-xs text-brand-black/40 text-center mt-6">
              Más tipos de análisis disponibles próximamente
            </p>
          </div>
        </main>
      </div>
    </div>
  )
}
