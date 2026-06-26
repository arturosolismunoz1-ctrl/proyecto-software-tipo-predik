import { BrowserRouter, Navigate, Route, Routes } from 'react-router-dom'
import { useAuthStore } from './store/useAuthStore'
import LoginPage from './pages/LoginPage'
import WizardCompetenciaPage from './pages/WizardCompetenciaPage'
import DashboardHomePage from './pages/DashboardHomePage'
import AnalisisPage from './pages/AnalisisPage'
import ProyectosPage from './pages/ProyectosPage'
import ConsultaPage from './pages/ConsultaPage'
import HistorialPage from './pages/HistorialPage'
import ConfigPage from './pages/ConfigPage'

function ProtectedRoute({ children }: { children: React.ReactNode }) {
  const { isAuthenticated } = useAuthStore()
  return isAuthenticated ? <>{children}</> : <Navigate to="/login" replace />
}

export default function App() {
  return (
    <BrowserRouter>
      <Routes>
        <Route path="/login" element={<LoginPage />} />
        <Route path="/" element={<Navigate to="/dashboard" replace />} />
        <Route path="/dashboard" element={<ProtectedRoute><DashboardHomePage /></ProtectedRoute>} />
        <Route path="/analisis"  element={<ProtectedRoute><AnalisisPage /></ProtectedRoute>} />
        <Route path="/proyectos" element={<ProtectedRoute><ProyectosPage /></ProtectedRoute>} />
        <Route path="/consulta"  element={<ProtectedRoute><ConsultaPage /></ProtectedRoute>} />
        <Route path="/historial" element={<ProtectedRoute><HistorialPage /></ProtectedRoute>} />
        <Route path="/config"    element={<ProtectedRoute><ConfigPage /></ProtectedRoute>} />
        <Route path="/analisis/competencia" element={<ProtectedRoute><WizardCompetenciaPage /></ProtectedRoute>} />
        <Route path="*"          element={<Navigate to="/dashboard" replace />} />
      </Routes>
    </BrowserRouter>
  )
}
