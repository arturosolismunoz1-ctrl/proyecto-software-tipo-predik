import { useLocation } from 'react-router-dom'
import { AppSidebar } from '../components/layout/AppSidebar'
import { AppTopbar } from '../components/layout/AppTopbar'

export default function HistorialPage() {
  const location = useLocation()
  return (
    <div className="flex h-screen overflow-hidden bg-brand-bg">
      <AppSidebar />
      <div className="flex flex-col flex-1 overflow-hidden min-w-0">
        <AppTopbar editMode={false} onToggleEdit={() => {}} currentPath={location.pathname} />
        <main className="flex-1 overflow-auto p-4 flex items-center justify-center">
          <div className="flex flex-col items-center justify-center h-64 gap-3">
            <i className="ti ti-clock text-4xl text-brand-copper/40" />
            <p className="text-brand-black/40 text-sm">Historial — Próximamente</p>
          </div>
        </main>
      </div>
    </div>
  )
}
