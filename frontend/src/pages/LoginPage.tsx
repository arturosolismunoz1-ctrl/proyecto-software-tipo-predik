import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { apiLogin, setToken } from '../api/client'
import { useAuthStore } from '../store/useAuthStore'

export default function LoginPage() {
  const [email, setEmail]       = useState('admin@predik.local')
  const [password, setPassword] = useState('')
  const [error, setError]       = useState('')
  const [loading, setLoading]   = useState(false)

  const { setAuthenticated } = useAuthStore()
  const navigate = useNavigate()

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError('')
    setLoading(true)
    try {
      const token = await apiLogin(email, password)
      setToken(token)
      setAuthenticated(true)
      navigate('/')
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Error de autenticación')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="min-h-screen flex" style={{ background: 'linear-gradient(135deg, #0a2855 0%, #144d9e 60%, #1a5fc3 100%)' }}>
      {/* Panel izquierdo — branding */}
      <div className="hidden lg:flex lg:w-1/2 flex-col justify-center px-16 text-white">
        <div className="mb-8">
          {/* Logo placeholder */}
          <div className="flex items-center gap-3 mb-6">
            <div className="w-10 h-10 bg-white bg-opacity-20 rounded-xl flex items-center justify-center">
              <svg className="w-6 h-6 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                  d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M15 11a3 3 0 11-6 0 3 3 0 016 0z" />
              </svg>
            </div>
            <span className="text-2xl font-bold tracking-tight">Predik Geo</span>
          </div>
          <h2 className="text-4xl font-bold leading-tight mb-4">
            Inteligencia<br />Geoespacial
          </h2>
          <p className="text-blue-200 text-lg leading-relaxed max-w-md">
            Analiza el potencial comercial de cualquier zona de México con datos reales del INEGI DENUE y Censo 2020.
          </p>
        </div>

        <div className="space-y-4 mt-8">
          {[
            { icon: '📍', text: '5.5M establecimientos DENUE actualizados' },
            { icon: '🗺️', text: 'Polígonos AGEB reales del Marco Geoestadístico Nacional' },
            { icon: '📊', text: 'Demografía del Censo 2020 por zona' },
            { icon: '📥', text: 'Exporta a KMZ (Google Earth) o Excel' },
          ].map((f, i) => (
            <div key={i} className="flex items-center gap-3 text-blue-100">
              <span className="text-xl">{f.icon}</span>
              <span className="text-sm">{f.text}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Panel derecho — login form */}
      <div className="flex-1 flex items-center justify-center px-6 py-12">
        <div className="w-full max-w-sm">
          {/* Mobile logo */}
          <div className="lg:hidden text-center mb-8">
            <div className="inline-flex items-center gap-2 text-white text-xl font-bold">
              <svg className="w-7 h-7" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
                  d="M17.657 16.657L13.414 20.9a1.998 1.998 0 01-2.827 0l-4.244-4.243a8 8 0 1111.314 0z" />
              </svg>
              Predik Geo
            </div>
          </div>

          <div className="bg-white rounded-2xl shadow-2xl p-8">
            <h1 className="text-2xl font-bold text-gray-800 mb-1">Iniciar sesión</h1>
            <p className="text-gray-500 text-sm mb-6">Accede a tu plataforma de análisis</p>

            <form onSubmit={handleSubmit} className="space-y-4">
              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1.5">Email</label>
                <input
                  type="email"
                  value={email}
                  onChange={e => setEmail(e.target.value)}
                  className="w-full border border-gray-300 rounded-lg px-4 py-2.5 text-sm focus:ring-2 focus:ring-brand-copper focus:border-brand-copper outline-none transition-shadow"
                  required
                  autoFocus
                />
              </div>

              <div>
                <label className="block text-sm font-medium text-gray-700 mb-1.5">Contraseña</label>
                <input
                  type="password"
                  value={password}
                  onChange={e => setPassword(e.target.value)}
                  placeholder="••••••••"
                  className="w-full border border-gray-300 rounded-lg px-4 py-2.5 text-sm focus:ring-2 focus:ring-brand-copper focus:border-brand-copper outline-none transition-shadow"
                  required
                />
              </div>

              {error && (
                <div className="bg-red-50 border border-red-200 text-red-700 text-sm rounded-lg px-4 py-3">
                  {error}
                </div>
              )}

              <button
                type="submit"
                disabled={loading}
                className="w-full bg-brand-navy text-white rounded-lg py-3 font-semibold text-sm hover:bg-brand-navy/90 disabled:opacity-60 disabled:cursor-not-allowed transition-colors mt-2 flex items-center justify-center gap-2"
              >
                {loading && (
                  <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
                )}
                {loading ? 'Verificando...' : 'Entrar'}
              </button>
            </form>
          </div>

          <p className="text-center text-blue-200 text-xs mt-6 opacity-70">
            Powered by INEGI DENUE · Censo 2020 · PostGIS
          </p>
        </div>
      </div>
    </div>
  )
}
