import { useLocation, useNavigate } from 'react-router-dom'
import { AppSidebar } from '../components/layout/AppSidebar'
import { AppTopbar }  from '../components/layout/AppTopbar'
import { WizardAnalisis } from '../components/wizard/WizardAnalisis'

export default function WizardCompetenciaPage() {
  const location = useLocation()
  const navigate  = useNavigate()

  return (
    <div className="flex h-screen overflow-hidden bg-brand-bg">
      <AppSidebar />

      <div className="flex flex-col flex-1 overflow-hidden min-w-0">
        <AppTopbar editMode={false} onToggleEdit={() => {}} currentPath={location.pathname} />

        <div className="flex-1 overflow-auto flex justify-center py-6 px-4">
          <div className="w-full max-w-md">
            <WizardAnalisis
              onClose={() => navigate('/analisis')}
              onResultado={() => {}}
            />
          </div>
        </div>
      </div>
    </div>
  )
}
