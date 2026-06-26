import { getToken } from '../../api/client'

interface Props {
  editMode: boolean
  onToggleEdit: () => void
  currentPath: string
}

const PAGE_TITLES: Record<string, string> = {
  '/dashboard': 'Dashboard',
  '/analisis':  'Nuevo análisis',
  '/proyectos': 'Proyectos',
  '/historial': 'Historial',
  '/consulta':  'Consulta unitaria',
  '/config':    'Configuración',
  '/analisis/competencia': 'Análisis de competencia',
}

function getInitialsFromJwt(): string {
  try {
    const token = getToken()
    if (!token) return 'AD'
    const payload = JSON.parse(atob(token.split('.')[1]))
    const email: string = payload.sub ?? payload.email ?? ''
    const parts = email.split('@')[0].split(/[._-]/)
    if (parts.length >= 2) return (parts[0][0] + parts[1][0]).toUpperCase()
    if (email.length >= 2) return email.slice(0, 2).toUpperCase()
  } catch {
    // ignore
  }
  return 'AD'
}

export function AppTopbar({ editMode, onToggleEdit, currentPath }: Props) {
  const title = PAGE_TITLES[currentPath] ?? 'GeoData Intelligence'
  const isDashboard = currentPath === '/dashboard'
  const initials = getInitialsFromJwt()

  return (
    <header className="flex items-center justify-between px-5 h-12 border-b border-brand-beige bg-white flex-shrink-0">
      {/* Izquierda: título */}
      <h1 className="text-sm font-semibold text-brand-navy truncate">
        {title}
      </h1>

      {/* Centro: hint edición (solo dashboard en modo edit) */}
      <div className="flex-1 flex justify-center">
        {isDashboard && editMode && (
          <span className="text-[11px] text-brand-beige select-none">
            Arrastra los widgets para reorganizar
          </span>
        )}
      </div>

      {/* Derecha: acciones */}
      <div className="flex items-center gap-3">
        {isDashboard && (
          <button
            onClick={onToggleEdit}
            className={[
              'flex items-center gap-1.5 text-xs font-medium px-3 py-1.5 rounded-lg transition-colors',
              editMode
                ? 'bg-brand-copper text-brand-navy'
                : 'border border-brand-copper text-brand-copper hover:bg-brand-copper hover:text-brand-navy',
            ].join(' ')}
          >
            <i className={`ti ${editMode ? 'ti-check' : 'ti-layout-grid'} text-sm`} />
            {editMode ? 'Guardar layout' : 'Editar layout'}
          </button>
        )}

        <button
          title="Notificaciones"
          className="text-brand-black hover:text-brand-navy transition-colors"
        >
          <i className="ti ti-bell text-lg" />
        </button>

        <div
          className="w-8 h-8 rounded-full bg-brand-navy flex items-center justify-center flex-shrink-0 cursor-default"
        >
          <span className="text-brand-copper text-xs font-semibold">{initials}</span>
        </div>
      </div>
    </header>
  )
}
