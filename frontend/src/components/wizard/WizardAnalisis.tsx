import { useState, useCallback, useEffect } from 'react'
import type { EstadoCatalogo, MunicipioCatalogo, NseNivel, WizardData, CompetenciaResultado, NivelGeografico } from '../../types'
import { NSE_NIVELES } from '../../types'
import {
  apiEstados, apiMunicipios,
  apiAnalisisCompetenciaPreview, apiAnalisisCompetenciaKmz,
  apiScianCatalogo,
} from '../../api/client'
import type { ScianGiro } from '../../api/client'

const PASOS = ['Estado', 'Municipio(s)', 'NSE', 'Análisis', 'Resultado']

const WIZARD_DEFAULT: WizardData = {
  estadoClave: '',
  estadoNombre: '',
  municipios: [],
  nseNiveles: [],
  marcaPropia: '',
  scianGiros: [],
  competenciaDirecta: [''],
  incluirSucursales: true,
  incluirHubs: true,
  incluirZonasBlancas: true,
  radioHub: 150,
  nivelGeografico: 'ageb',
}

// ── Helper ────────────────────────────────────────────────────────────────────

function nseToGraproes(niveles: NseNivel[]): { min: number | null; max: number | null } {
  if (niveles.length === 0) return { min: null, max: null }
  const seleccionados = NSE_NIVELES.filter(n => niveles.includes(n.nivel))
  const min = Math.min(...seleccionados.map(n => n.graproes_min))
  const maxVals = seleccionados.map(n => n.graproes_max).filter((v): v is number => v !== null)
  const max = maxVals.length < seleccionados.length ? null : Math.max(...maxVals)
  return { min, max }
}

// ── Subcomponentes de pasos ───────────────────────────────────────────────────

function StepHeader({ paso, label }: { paso: number; label: string }) {
  return (
    <div className="flex items-center gap-2 mb-4">
      <span className="w-6 h-6 rounded-full bg-brand-800 text-white text-xs flex items-center justify-center font-bold flex-shrink-0">
        {paso}
      </span>
      <h3 className="text-sm font-semibold text-gray-700">{label}</h3>
    </div>
  )
}

// Paso 1
function Step1Estado({
  data, estados, onNext,
}: {
  data: WizardData
  estados: EstadoCatalogo[]
  onNext: (patch: Partial<WizardData>) => void
}) {
  const [clave, setClave] = useState(data.estadoClave)

  const handleNext = () => {
    if (!clave) return
    const est = estados.find(e => e.clave === clave)
    onNext({ estadoClave: clave, estadoNombre: est?.nombre ?? clave, municipios: [] })
  }

  return (
    <div className="space-y-4">
      <StepHeader paso={1} label="Selecciona el estado" />
      <select
        value={clave}
        onChange={e => setClave(e.target.value)}
        className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm bg-white focus:ring-2 focus:ring-brand-500 outline-none"
      >
        <option value="">— Selecciona un estado —</option>
        {estados.map(est => (
          <option key={est.clave} value={est.clave}>
            {est.clave} · {est.nombre}
          </option>
        ))}
      </select>
      <button
        onClick={handleNext}
        disabled={!clave}
        className="w-full bg-brand-800 text-white rounded-xl py-2.5 font-semibold text-sm disabled:opacity-40"
      >
        Continuar →
      </button>
    </div>
  )
}

// Paso 2
function Step2Municipios({
  data, onNext, onBack,
}: {
  data: WizardData
  onNext: (patch: Partial<WizardData>) => void
  onBack: () => void
}) {
  const [municipios, setMunicipios] = useState<MunicipioCatalogo[]>([])
  const [loading, setLoading] = useState(false)
  const [busqueda, setBusqueda] = useState('')
  const [seleccionados, setSeleccionados] = useState<MunicipioCatalogo[]>(data.municipios)
  const [cargados, setCargados] = useState(false)

  const cargar = useCallback(async () => {
    if (cargados) return
    setLoading(true)
    try {
      const data2 = await apiMunicipios(data.estadoClave)
      setMunicipios(data2)
      setCargados(true)
    } finally {
      setLoading(false)
    }
  }, [data.estadoClave, cargados])

  if (!cargados && !loading) cargar()

  const toggle = (mun: MunicipioCatalogo) => {
    setSeleccionados(prev =>
      prev.find(m => m.clave === mun.clave)
        ? prev.filter(m => m.clave !== mun.clave)
        : [...prev, mun]
    )
  }

  const filtrados = municipios.filter(m =>
    m.nombre.toLowerCase().includes(busqueda.toLowerCase())
  )

  return (
    <div className="space-y-3">
      <StepHeader paso={2} label="Selecciona municipio(s)" />
      <p className="text-xs text-gray-500">
        Estado: <span className="font-medium text-gray-700">{data.estadoNombre}</span>
      </p>

      <input
        type="text"
        placeholder="Buscar municipio..."
        value={busqueda}
        onChange={e => setBusqueda(e.target.value)}
        className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-brand-500 outline-none"
      />

      {loading ? (
        <div className="flex justify-center py-4">
          <span className="w-6 h-6 border-2 border-brand-700 border-t-transparent rounded-full animate-spin" />
        </div>
      ) : (
        <div className="max-h-56 overflow-y-auto border border-gray-100 rounded-lg divide-y divide-gray-50">
          {filtrados.length === 0 && (
            <p className="text-xs text-gray-400 px-3 py-3 text-center">
              No hay municipios cargados para este estado.
            </p>
          )}
          {filtrados.map(m => (
            <label key={m.clave} className="flex items-center gap-2.5 px-3 py-2 hover:bg-gray-50 cursor-pointer">
              <input
                type="checkbox"
                checked={!!seleccionados.find(s => s.clave === m.clave)}
                onChange={() => toggle(m)}
                className="accent-brand-700"
              />
              <span className="text-sm text-gray-700">{m.nombre}</span>
              <span className="text-xs text-gray-400 ml-auto">{m.clave}</span>
            </label>
          ))}
        </div>
      )}

      {seleccionados.length > 0 && (
        <p className="text-xs text-brand-700 font-medium">
          {seleccionados.length} municipio(s) seleccionado(s): {seleccionados.map(m => m.nombre).join(', ')}
        </p>
      )}

      <div className="flex gap-2">
        <button onClick={onBack} className="flex-1 border border-gray-200 text-gray-600 rounded-xl py-2.5 text-sm font-medium">
          ← Atrás
        </button>
        <button
          onClick={() => onNext({ municipios: seleccionados })}
          disabled={seleccionados.length === 0}
          className="flex-1 bg-brand-800 text-white rounded-xl py-2.5 font-semibold text-sm disabled:opacity-40"
        >
          Continuar →
        </button>
      </div>
    </div>
  )
}

// Paso 3
function Step3NSE({
  data, onNext, onBack,
}: {
  data: WizardData
  onNext: (patch: Partial<WizardData>) => void
  onBack: () => void
}) {
  const [seleccionados, setSeleccionados] = useState<NseNivel[]>(data.nseNiveles)
  const [abierto, setAbierto] = useState(true)

  const toggle = (nivel: NseNivel) => {
    setSeleccionados(prev =>
      prev.includes(nivel) ? prev.filter(n => n !== nivel) : [...prev, nivel]
    )
  }

  const toggleTodos = () => {
    setSeleccionados(prev =>
      prev.length === NSE_NIVELES.length ? [] : NSE_NIVELES.map(n => n.nivel)
    )
  }

  const resumen = seleccionados.length === 0
    ? 'Todos los niveles'
    : seleccionados.length === NSE_NIVELES.length
      ? 'Todos los niveles'
      : seleccionados.join(', ')

  return (
    <div className="space-y-3">
      <StepHeader paso={3} label="Nivel Socioeconómico (NSE)" />
      <p className="text-xs text-gray-500 leading-relaxed">
        Filtra zonas por grado promedio de escolaridad (INEGI Censo 2020). Sin selección = todas las zonas.
      </p>

      {/* Dropdown colapsable */}
      <div className="border border-gray-200 rounded-xl overflow-hidden">
        <button
          type="button"
          onClick={() => setAbierto(o => !o)}
          className="w-full flex items-center justify-between px-3 py-2.5 bg-gray-50 hover:bg-gray-100 transition-colors text-left"
        >
          <span className="text-sm text-gray-700 font-medium truncate">{resumen}</span>
          <span className="text-gray-400 ml-2 flex-shrink-0">{abierto ? '▲' : '▼'}</span>
        </button>

        {abierto && (
          <div className="border-t border-gray-100 divide-y divide-gray-50">
            {/* Opción "Todos" */}
            <label className="flex items-center gap-2.5 px-3 py-2 cursor-pointer hover:bg-gray-50">
              <input
                type="checkbox"
                checked={seleccionados.length === NSE_NIVELES.length}
                onChange={toggleTodos}
                className="accent-brand-700"
              />
              <span className="text-sm text-gray-600 font-medium">Todos los niveles</span>
            </label>
            {NSE_NIVELES.map(n => (
              <label key={n.nivel} className={`flex items-center gap-2.5 px-3 py-2 cursor-pointer transition-colors ${
                seleccionados.includes(n.nivel) ? 'bg-brand-50' : 'hover:bg-gray-50'
              }`}>
                <input
                  type="checkbox"
                  checked={seleccionados.includes(n.nivel)}
                  onChange={() => toggle(n.nivel)}
                  className="accent-brand-700"
                />
                <span className="w-2.5 h-2.5 rounded-full flex-shrink-0" style={{ backgroundColor: n.color }} />
                <span className="text-sm text-gray-700">{n.label}</span>
                <span className="text-xs text-gray-400 ml-auto">≥{n.graproes_min} años</span>
              </label>
            ))}
          </div>
        )}
      </div>

      {seleccionados.length === 0 && (
        <p className="text-xs text-amber-600 bg-amber-50 border border-amber-200 rounded-lg px-2.5 py-1.5">
          Sin filtro NSE — se analizarán todas las zonas del municipio.
        </p>
      )}

      <div className="flex gap-2">
        <button onClick={onBack} className="flex-1 border border-gray-200 text-gray-600 rounded-xl py-2.5 text-sm font-medium">
          ← Atrás
        </button>
        <button
          onClick={() => onNext({ nseNiveles: seleccionados })}
          className="flex-1 bg-brand-800 text-white rounded-xl py-2.5 font-semibold text-sm"
        >
          Continuar →
        </button>
      </div>
    </div>
  )
}

// Paso 4
function Step4Analisis({
  data, onNext, onBack, scianCatalogo,
}: {
  data: WizardData
  onNext: (patch: Partial<WizardData>) => void
  onBack: () => void
  scianCatalogo: ScianGiro[]
}) {
  const [marcaPropia, setMarcaPropia] = useState(data.marcaPropia)
  const [scianGiros, setScianGiros] = useState<string[]>(data.scianGiros)
  const [scianSearch, setScianSearch] = useState('')
  const [scianAbierto, setScianAbierto] = useState(false)
  const [competencia, setCompetencia] = useState<string[]>(
    data.competenciaDirecta.length ? data.competenciaDirecta : ['']
  )
  const [incluirSucursales, setIncluirSucursales] = useState(data.incluirSucursales)
  const [incluirHubs, setIncluirHubs] = useState(data.incluirHubs)
  const [incluirZonasBlancas, setIncluirZonasBlancas] = useState(data.incluirZonasBlancas)
  const [radioHub, setRadioHub] = useState<100 | 150 | 200 | 300>(data.radioHub)
  const [nivelGeografico, setNivelGeografico] = useState<NivelGeografico>(data.nivelGeografico)

  const addCompetidor = () => setCompetencia(prev => [...prev, ''])
  const updateCompetidor = (i: number, val: string) =>
    setCompetencia(prev => prev.map((c, idx) => idx === i ? val : c))
  const removeCompetidor = (i: number) =>
    setCompetencia(prev => prev.filter((_, idx) => idx !== i))

  const toggleScian = (codigo: string) => {
    setScianGiros(prev =>
      prev.includes(codigo) ? prev.filter(c => c !== codigo) : [...prev, codigo]
    )
  }

  const handleNext = () => {
    onNext({
      marcaPropia: marcaPropia.trim(),
      scianGiros,
      competenciaDirecta: competencia.map(c => c.trim()).filter(Boolean),
      incluirSucursales,
      incluirHubs,
      incluirZonasBlancas,
      radioHub,
      nivelGeografico,
    })
  }

  const canContinue = marcaPropia.trim() || competencia.some(c => c.trim())

  return (
    <div className="space-y-4">
      <StepHeader paso={4} label="Configuración del análisis" />

      {/* Marca propia */}
      <div className={`border rounded-xl p-3 space-y-2.5 transition-colors ${incluirSucursales ? 'border-green-300 bg-green-50' : 'border-gray-100'}`}>
        <label className="flex items-center gap-2 cursor-pointer">
          <input type="checkbox" checked={incluirSucursales} onChange={e => setIncluirSucursales(e.target.checked)} className="accent-brand-700" />
          <span className="text-sm font-semibold text-gray-700">Mis sucursales</span>
        </label>
        {incluirSucursales && (
          <input
            type="text"
            placeholder="Nombre de tu marca (ej: Fix Trupper)"
            value={marcaPropia}
            onChange={e => setMarcaPropia(e.target.value)}
            className="w-full border border-gray-200 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-brand-500 outline-none bg-white"
          />
        )}
      </div>

      {/* Competencia directa */}
      <div className="border border-gray-100 rounded-xl p-3 space-y-2">
        <p className="text-sm font-semibold text-gray-700">Competencia directa</p>
        {competencia.map((c, i) => (
          <div key={i} className="flex gap-2">
            <input
              type="text"
              placeholder={`Competidor ${i + 1} (ej: Boxito)`}
              value={c}
              onChange={e => updateCompetidor(i, e.target.value)}
              className="flex-1 border border-gray-200 rounded-lg px-3 py-2 text-sm focus:ring-2 focus:ring-brand-500 outline-none"
            />
            {competencia.length > 1 && (
              <button onClick={() => removeCompetidor(i)} className="text-gray-300 hover:text-red-400 px-1">✕</button>
            )}
          </div>
        ))}
        <button onClick={addCompetidor} className="text-xs text-brand-700 hover:text-brand-900 font-medium">
          + Agregar competidor
        </button>
      </div>

      {/* Giro SCIAN multi-select */}
      <div className="space-y-1.5">
        <p className="text-xs text-gray-500 font-medium">Giro(s) SCIAN (competencia indirecta)</p>
        <div className="border border-gray-200 rounded-xl overflow-hidden">
          {/* Cabecera colapsable */}
          <button
            type="button"
            onClick={() => setScianAbierto(o => !o)}
            className="w-full flex items-center justify-between px-3 py-2.5 bg-gray-50 hover:bg-gray-100 transition-colors text-left"
          >
            <span className="text-sm text-gray-700 truncate">
              {scianGiros.length === 0
                ? 'Sin filtro SCIAN'
                : `${scianGiros.length} giro${scianGiros.length > 1 ? 's' : ''} seleccionado${scianGiros.length > 1 ? 's' : ''}`}
            </span>
            <span className="text-gray-400 ml-2 flex-shrink-0">{scianAbierto ? '▲' : '▼'}</span>
          </button>

          {scianAbierto && (
            <div className="border-t border-gray-100">
              {/* Buscador */}
              <div className="px-3 py-2 border-b border-gray-100">
                <input
                  type="text"
                  placeholder="Buscar giro... (ej: farmacia, restaurante)"
                  value={scianSearch}
                  onChange={e => setScianSearch(e.target.value)}
                  className="w-full border border-gray-200 rounded-lg px-3 py-1.5 text-sm focus:ring-2 focus:ring-brand-500 outline-none"
                />
              </div>
              {/* Lista con scroll */}
              <div className="max-h-48 overflow-y-auto divide-y divide-gray-50">
                {scianGiros.length > 0 && (
                  <button
                    type="button"
                    onClick={() => setScianGiros([])}
                    className="w-full text-left px-3 py-1.5 text-xs text-red-500 hover:bg-red-50"
                  >
                    Limpiar selección ({scianGiros.length})
                  </button>
                )}
                {scianCatalogo
                  .filter(s => {
                    const q = scianSearch.toLowerCase()
                    return !q || s.descripcion.toLowerCase().includes(q) || s.codigo.includes(q)
                  })
                  .map(s => (
                    <label key={s.codigo} className={`flex items-center gap-2 px-3 py-2 cursor-pointer transition-colors ${
                      scianGiros.includes(s.codigo) ? 'bg-brand-50' : 'hover:bg-gray-50'
                    }`}>
                      <input
                        type="checkbox"
                        checked={scianGiros.includes(s.codigo)}
                        onChange={() => toggleScian(s.codigo)}
                        className="accent-brand-700 flex-shrink-0"
                      />
                      <span className="text-xs text-gray-700 leading-tight">
                        <span className="font-mono text-gray-400">{s.codigo}</span> — {s.descripcion}
                      </span>
                    </label>
                  ))}
              </div>
            </div>
          )}
        </div>

        {/* Chips de seleccionados */}
        {scianGiros.length > 0 && (
          <div className="flex flex-wrap gap-1.5">
            {scianGiros.map(codigo => {
              const desc = scianCatalogo.find(s => s.codigo === codigo)?.descripcion
              return (
                <span key={codigo} className="inline-flex items-center gap-1 bg-brand-100 text-brand-800 text-xs rounded-full px-2 py-0.5">
                  <span title={desc}>{codigo}</span>
                  <button type="button" onClick={() => toggleScian(codigo)} className="hover:text-red-500">✕</button>
                </span>
              )
            })}
          </div>
        )}
      </div>

      {/* Hubs */}
      <div className={`border rounded-xl p-3 space-y-2 transition-colors ${incluirHubs ? 'border-blue-200 bg-blue-50' : 'border-gray-100'}`}>
        <label className="flex items-center gap-2 cursor-pointer">
          <input type="checkbox" checked={incluirHubs} onChange={e => setIncluirHubs(e.target.checked)} className="accent-brand-700" />
          <span className="text-sm font-semibold text-gray-700">Hubs de competencia directa</span>
        </label>
        {incluirHubs && (
          <div className="flex gap-2">
            {([100, 150, 200, 300] as const).map(r => (
              <button
                key={r}
                onClick={() => setRadioHub(r)}
                className={`flex-1 text-xs py-1.5 rounded-lg border font-medium transition-colors ${
                  radioHub === r ? 'bg-brand-800 text-white border-brand-800' : 'border-gray-200 text-gray-600 hover:bg-gray-50'
                }`}
              >
                {r}m
              </button>
            ))}
          </div>
        )}
      </div>

      {/* Zonas blancas */}
      <label className={`flex items-start gap-2.5 p-3 rounded-xl border cursor-pointer transition-colors ${incluirZonasBlancas ? 'border-amber-300 bg-amber-50' : 'border-gray-100'}`}>
        <input type="checkbox" checked={incluirZonasBlancas} onChange={e => setIncluirZonasBlancas(e.target.checked)} className="accent-brand-700 mt-0.5" />
        <div>
          <p className="text-sm font-semibold text-gray-700">Zonas blancas de oportunidad</p>
          <p className="text-xs text-gray-400">AGEBs sin tu marca ni competencia directa, con perfil NSE match</p>
        </div>
      </label>

      {/* Nivel geográfico */}
      <div className="flex gap-2">
        {(['ageb', 'manzana'] as const).map(n => (
          <label key={n} className={`flex-1 flex items-center gap-2 p-2.5 rounded-lg border cursor-pointer transition-colors ${nivelGeografico === n ? 'bg-brand-50 border-brand-400' : 'border-gray-100'}`}>
            <input type="radio" name="nivel_wiz" value={n} checked={nivelGeografico === n} onChange={() => setNivelGeografico(n)} className="accent-brand-700" />
            <div>
              <p className="text-xs font-semibold text-gray-700">{n === 'ageb' ? 'AGEB' : 'Manzana'}</p>
              <p className="text-xs text-gray-400">{n === 'ageb' ? '~1 km²' : '~100 m²'}</p>
            </div>
          </label>
        ))}
      </div>

      <div className="flex gap-2">
        <button onClick={onBack} className="flex-1 border border-gray-200 text-gray-600 rounded-xl py-2.5 text-sm font-medium">
          ← Atrás
        </button>
        <button
          onClick={handleNext}
          disabled={!canContinue}
          className="flex-1 bg-brand-800 text-white rounded-xl py-2.5 font-semibold text-sm disabled:opacity-40"
        >
          Ejecutar análisis →
        </button>
      </div>
    </div>
  )
}

// Paso 5
function Step5Resultado({
  data,
  resultado,
  loading,
  error,
  kmzListo,
  kmzLoading,
  onDescargarKmz,
  onNuevoAnalisis,
}: {
  data: WizardData
  resultado: CompetenciaResultado | null
  loading: boolean
  error: string | null
  kmzListo: boolean
  kmzLoading: boolean
  onDescargarKmz: () => void
  onNuevoAnalisis: () => void
}) {
  const PROGRESO_PASOS = [
    'Construyendo área de análisis...',
    'Consultando DENUE...',
    'Procesando AGEBs y NSE...',
    'Calculando hubs...',
    'Identificando zonas blancas...',
    'Generando resultados...',
  ]

  if (loading) {
    return (
      <div className="space-y-4">
        <StepHeader paso={5} label="Ejecutando análisis" />
        <div className="space-y-2.5">
          {PROGRESO_PASOS.map((paso, i) => (
            <div key={i} className="flex items-center gap-2.5 text-sm text-gray-500">
              <span className="w-4 h-4 border-2 border-brand-700 border-t-transparent rounded-full animate-spin flex-shrink-0" />
              {paso}
            </div>
          ))}
        </div>
        <p className="text-xs text-gray-400 text-center">Puede tardar 3–8 minutos según el municipio</p>
      </div>
    )
  }

  if (error) {
    return (
      <div className="space-y-4">
        <StepHeader paso={5} label="Error en el análisis" />
        <div className="bg-red-50 border border-red-200 rounded-xl p-3 text-xs text-red-700">{error}</div>
        <button onClick={onNuevoAnalisis} className="w-full border border-gray-200 text-gray-600 rounded-xl py-2.5 text-sm font-medium">
          ↺ Nuevo análisis
        </button>
      </div>
    )
  }

  if (!resultado) return null

  const r = resultado.resumen

  return (
    <div className="space-y-4">
      <StepHeader paso={5} label="Resultados" />

      {/* KPIs */}
      <div className="grid grid-cols-2 gap-2">
        {[
          { label: 'Sucursales propias', value: resultado.capas.find(c => c.icon === 'star')?.cantidad ?? 0, color: 'text-green-700' },
          { label: 'Competencia directa', value: r.total_directa - (resultado.capas.find(c => c.icon === 'star')?.cantidad ?? 0), color: 'text-red-600' },
          { label: 'Indirecta', value: r.total_indirecta, color: 'text-amber-600' },
          { label: 'Zonas analizadas', value: r.total_zonas, color: 'text-brand-700' },
          { label: 'Hubs detectados', value: r.total_hubs, color: 'text-blue-600' },
          { label: 'Nivel', value: r.nivel_geografico.toUpperCase(), color: 'text-gray-500' },
        ].map(kpi => (
          <div key={kpi.label} className="bg-gray-50 rounded-xl p-2.5 text-center border border-gray-100">
            <p className={`text-lg font-bold ${kpi.color}`}>{kpi.value}</p>
            <p className="text-xs text-gray-400 mt-0.5 leading-tight">{kpi.label}</p>
          </div>
        ))}
      </div>

      <div className="text-xs text-gray-500 text-center">
        {data.municipios.map(m => m.nombre).join(', ')} · {data.estadoNombre}
      </div>

      {/* Acciones */}
      <button
        onClick={onDescargarKmz}
        disabled={kmzLoading}
        className="w-full bg-brand-800 text-white rounded-xl py-3 font-semibold text-sm flex items-center justify-center gap-2 disabled:opacity-60"
      >
        {kmzLoading ? (
          <>
            <span className="w-4 h-4 border-2 border-white border-t-transparent rounded-full animate-spin" />
            Generando KMZ...
          </>
        ) : (
          <>
            <svg className="w-4 h-4" fill="none" viewBox="0 0 24 24" stroke="currentColor">
              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M4 16v1a3 3 0 003 3h10a3 3 0 003-3v-1m-4-4l-4 4m0 0l-4-4m4 4V4" />
            </svg>
            {kmzListo ? 'Descargar KMZ' : 'Descargar KMZ (regenerando...)'}
          </>
        )}
      </button>

      <button
        onClick={onNuevoAnalisis}
        className="w-full border border-gray-200 text-gray-600 rounded-xl py-2.5 text-sm font-medium"
      >
        ↺ Nuevo análisis
      </button>
    </div>
  )
}

// ── WizardAnalisis (contenedor principal) ─────────────────────────────────────

interface Props {
  onClose: () => void
  onResultado: (res: CompetenciaResultado) => void
}

export function WizardAnalisis({ onClose, onResultado }: Props) {
  const [paso, setPaso] = useState(1)
  const [data, setData] = useState<WizardData>(WIZARD_DEFAULT)
  const [estados, setEstados] = useState<EstadoCatalogo[]>([])
  const [scianGiros, setScianGiros] = useState<ScianGiro[]>([])
  const [resultado, setResultado] = useState<CompetenciaResultado | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [kmzBlob, setKmzBlob] = useState<{ blob: Blob; filename: string } | null>(null)
  const [kmzLoading, setKmzLoading] = useState(false)

  useEffect(() => {
    apiEstados().then(e => setEstados(e)).catch(() => {})
    apiScianCatalogo().then(g => setScianGiros(g)).catch(() => {})
  }, [])

  const patch = (updates: Partial<WizardData>) => {
    setData(prev => ({ ...prev, ...updates }))
  }

  const buildPayload = (d: WizardData) => {
    const { min, max } = nseToGraproes(d.nseNiveles)
    return {
      clave_estado:        d.estadoClave,
      claves_municipios:   d.municipios.map(m => m.clave),
      graproes_min:        min,
      graproes_max:        max,
      marca_propia:        d.marcaPropia || undefined,
      scian_giros:         d.scianGiros.length > 0 ? d.scianGiros : undefined,
      competencia_directa: d.competenciaDirecta.filter(Boolean),
      incluir_sucursales:  d.incluirSucursales,
      incluir_hubs:        d.incluirHubs,
      incluir_zonas_blancas: d.incluirZonasBlancas,
      radio_hub_metros:    d.radioHub,
      nivel_geografico:    d.nivelGeografico,
    }
  }

  const ejecutar = async (d: WizardData) => {
    setLoading(true)
    setKmzBlob(null)
    setError(null)
    setPaso(5)
    try {
      // Corre GeoJSON y KMZ en paralelo — la espera es la misma
      const [res, kmz] = await Promise.all([
        apiAnalisisCompetenciaPreview(buildPayload(d)),
        apiAnalisisCompetenciaKmz(buildPayload(d)).catch(() => null),
      ])
      setResultado(res)
      onResultado(res)
      if (kmz) setKmzBlob(kmz)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Error desconocido')
    } finally {
      setLoading(false)
      setKmzLoading(false)
    }
  }

  const descargarKmz = async () => {
    // Si ya tenemos el blob listo, descarga instantánea
    if (kmzBlob) {
      const url = URL.createObjectURL(kmzBlob.blob)
      const a = document.createElement('a')
      a.href = url; a.download = kmzBlob.filename
      document.body.appendChild(a); a.click(); a.remove()
      URL.revokeObjectURL(url)
      return
    }
    // Fallback: re-pide el KMZ si por alguna razón no se generó en paralelo
    setKmzLoading(true)
    try {
      const { blob, filename } = await apiAnalisisCompetenciaKmz(buildPayload(data))
      const url = URL.createObjectURL(blob)
      const a = document.createElement('a')
      a.href = url; a.download = filename
      document.body.appendChild(a); a.click(); a.remove()
      URL.revokeObjectURL(url)
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Error al descargar KMZ')
    } finally {
      setKmzLoading(false)
    }
  }

  const irPaso = (n: number, updates?: Partial<WizardData>) => {
    if (updates) patch(updates)
    setPaso(n)
  }

  const siguientePasoConData = (updates: Partial<WizardData>) => {
    const nuevo = { ...data, ...updates }
    patch(updates)
    if (paso === 4) {
      ejecutar(nuevo)
    } else {
      setPaso(p => p + 1)
    }
  }

  return (
    <div className="flex flex-col h-full bg-white">
      {/* Header */}
      <div className="bg-brand-800 px-5 py-4 flex-shrink-0">
        <div className="flex items-center justify-between mb-3">
          <div>
            <p className="text-white font-bold text-sm">Wizard — Análisis de Competencia</p>
            <p className="text-blue-300 text-xs mt-0.5">Caso de uso 1</p>
          </div>
          <button onClick={onClose} className="text-blue-300 hover:text-white text-lg leading-none">✕</button>
        </div>

        {/* Stepper */}
        <div className="flex items-center gap-1">
          {PASOS.map((label, i) => {
            const n = i + 1
            const activo = n === paso
            const completado = n < paso
            return (
              <div key={n} className="flex items-center gap-1 min-w-0">
                <div className={`w-5 h-5 rounded-full text-xs flex items-center justify-center font-bold flex-shrink-0 ${
                  completado ? 'bg-green-400 text-white' :
                  activo     ? 'bg-white text-brand-800' :
                               'bg-brand-700 text-blue-300'
                }`}>
                  {completado ? '✓' : n}
                </div>
                <span className={`text-xs truncate hidden sm:block ${activo ? 'text-white' : 'text-blue-300'}`}>
                  {label}
                </span>
                {i < PASOS.length - 1 && <span className="text-blue-600 flex-shrink-0">›</span>}
              </div>
            )
          })}
        </div>
      </div>

      {/* Body */}
      <div className="flex-1 overflow-y-auto px-4 py-5">
        {paso === 1 && (
          <Step1Estado
            data={data}
            estados={estados}
            onNext={u => siguientePasoConData(u)}
          />
        )}
        {paso === 2 && (
          <Step2Municipios
            data={data}
            onNext={u => siguientePasoConData(u)}
            onBack={() => irPaso(1)}
          />
        )}
        {paso === 3 && (
          <Step3NSE
            data={data}
            onNext={u => siguientePasoConData(u)}
            onBack={() => irPaso(2)}
          />
        )}
        {paso === 4 && (
          <Step4Analisis
            data={data}
            onNext={u => siguientePasoConData(u)}
            onBack={() => irPaso(3)}
            scianCatalogo={scianGiros}
          />
        )}
        {paso === 5 && (
          <Step5Resultado
            data={data}
            resultado={resultado}
            loading={loading}
            error={error}
            kmzListo={!!kmzBlob}
            kmzLoading={kmzLoading}
            onDescargarKmz={descargarKmz}
            onNuevoAnalisis={() => { setResultado(null); setError(null); setKmzBlob(null); setPaso(1); setData(WIZARD_DEFAULT) }}
          />
        )}
      </div>
    </div>
  )
}
