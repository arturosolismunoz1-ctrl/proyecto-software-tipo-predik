import { useState } from 'react'
import { useLocation } from 'react-router-dom'
import { AppSidebar } from '../components/layout/AppSidebar'
import { AppTopbar } from '../components/layout/AppTopbar'
import { DashboardPage } from '../components/dashboard/DashboardPage'

export default function DashboardHomePage() {
  const [editMode, setEditMode] = useState(false)
  const location = useLocation()

  return (
    <div className="flex h-screen overflow-hidden bg-brand-bg">
      <AppSidebar />
      <div className="flex flex-col flex-1 overflow-hidden min-w-0">
        <AppTopbar
          editMode={editMode}
          onToggleEdit={() => setEditMode(prev => !prev)}
          currentPath={location.pathname}
        />
        <main className="flex-1 overflow-auto p-4">
          <DashboardPage editMode={editMode} />
        </main>
      </div>
    </div>
  )
}
