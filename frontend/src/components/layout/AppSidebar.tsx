import { useEffect, useState } from 'react'
import { NavLink, useLocation } from 'react-router-dom'

const STORAGE_KEY = 'geodata_sidebar_collapsed'

const Isotipo = ({ size }: { size: number }) => (
  <svg
    viewBox="0 0 100 90"
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
    style={{ width: size, height: size, flexShrink: 0 }}
  >
    <path d="M8 82 L8 44 L33 26 L33 82"   stroke="#DEA36D" strokeWidth="4.5" strokeLinejoin="round" fill="none" />
    <path d="M33 82 L33 12 L54 4 L54 82"  stroke="#DEA36D" strokeWidth="4.5" strokeLinejoin="round" fill="none" />
    <path d="M54 82 L54 34 L82 46 L82 82" stroke="#DEA36D" strokeWidth="4.5" strokeLinejoin="round" fill="none" />
    <rect x="37" y="54" width="14" height="28" stroke="#DEA36D" strokeWidth="3.5" fill="none" />
    <line x1="5" y1="82" x2="85" y2="82" stroke="#DEA36D" strokeWidth="3.5" strokeLinecap="round" />
  </svg>
)

const NAV_ITEMS = [
  { to: '/dashboard', icon: 'ti-layout-dashboard', label: 'Dashboard' },
  { to: '/proyectos', icon: 'ti-folder',            label: 'Proyectos' },
  { to: '/analisis',  icon: 'ti-map-pin',           label: 'Nuevo análisis' },
  { to: '/historial', icon: 'ti-clock',             label: 'Historial' },
  { to: '/consulta',  icon: 'ti-search',            label: 'Consulta unitaria' },
]

const ADMIN_ITEMS = [
  { to: '/config', icon: 'ti-database', label: 'Admin ETL' },
  { to: '/config', icon: 'ti-settings', label: 'Configuración' },
]

interface SidebarItemProps {
  to: string
  icon: string
  label: string
  collapsed: boolean
}

function SidebarItem({ to, icon, label, collapsed }: SidebarItemProps) {
  const location = useLocation()
  const isActive = location.pathname.startsWith(to)

  return (
    <NavLink
      to={to}
      title={collapsed ? label : undefined}
      className={[
        'flex items-center gap-3 px-3 py-2 rounded-lg transition-colors',
        'text-sm font-medium',
        isActive
          ? 'bg-[rgba(222,163,109,0.18)] text-brand-copper'
          : 'text-[rgba(255,255,255,0.65)] hover:bg-[rgba(222,163,109,0.08)] hover:text-white',
        collapsed ? 'justify-center' : '',
      ].join(' ')}
    >
      <i className={`ti ${icon} text-base flex-shrink-0 ${isActive ? 'text-brand-copper' : 'text-[rgba(255,255,255,0.65)]'}`} />
      {!collapsed && <span className="truncate">{label}</span>}
    </NavLink>
  )
}

export function AppSidebar() {
  const [collapsed, setCollapsed] = useState<boolean>(() => {
    try {
      return localStorage.getItem(STORAGE_KEY) === 'true'
    } catch {
      return false
    }
  })

  useEffect(() => {
    try {
      localStorage.setItem(STORAGE_KEY, String(collapsed))
    } catch {
      // ignore
    }
  }, [collapsed])

  return (
    <aside
      className="flex flex-col bg-brand-navy h-full flex-shrink-0 overflow-hidden transition-all duration-200 ease-in-out"
      style={{ width: collapsed ? 56 : 220 }}
    >
      {/* Logo */}
      <div className={`flex items-center gap-3 px-3 py-4 border-b border-[rgba(255,255,255,0.1)] ${collapsed ? 'justify-center' : ''}`}>
        <Isotipo size={collapsed ? 32 : 40} />
        {!collapsed && (
          <div className="leading-tight min-w-0">
            <div className="text-white tracking-[0.15em] font-light" style={{ fontSize: 9 }}>
              TRES DIMENSIONES
            </div>
            <div className="text-brand-copper tracking-[0.1em] font-medium" style={{ fontSize: 9 }}>
              CO.
            </div>
          </div>
        )}
      </div>

      {/* Navegación principal */}
      <nav className="flex-1 overflow-y-auto py-3 px-2 space-y-0.5 sidebar-scroll">
        {NAV_ITEMS.map(item => (
          <SidebarItem key={item.to} {...item} collapsed={collapsed} />
        ))}

        {/* Separador */}
        <div className="my-3 border-t border-[rgba(255,255,255,0.1)]" />

        <div className={`px-1 mb-1 ${collapsed ? 'hidden' : ''}`}>
          <span className="text-[10px] text-[rgba(255,255,255,0.35)] uppercase tracking-widest">
            Admin
          </span>
        </div>

        {ADMIN_ITEMS.map(item => (
          <SidebarItem key={item.to} {...item} collapsed={collapsed} />
        ))}
      </nav>

      {/* Toggle colapsar */}
      <div className="px-2 py-3 border-t border-[rgba(255,255,255,0.1)]">
        <button
          onClick={() => setCollapsed(prev => !prev)}
          title={collapsed ? 'Expandir sidebar' : 'Colapsar sidebar'}
          className={`w-full flex items-center gap-3 px-3 py-2 rounded-lg text-[rgba(255,255,255,0.4)] hover:text-white hover:bg-[rgba(255,255,255,0.08)] transition-colors ${collapsed ? 'justify-center' : ''}`}
        >
          <i className={`ti ${collapsed ? 'ti-chevron-right' : 'ti-chevron-left'} text-base`} />
          {!collapsed && <span className="text-xs">Colapsar</span>}
        </button>
      </div>
    </aside>
  )
}
