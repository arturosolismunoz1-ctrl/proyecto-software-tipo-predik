# PREDIK-GEO — Resumen Técnico Completo
Generado: 2026-06-25

---

## 1. STACK

### Backend
| Categoría | Tecnología |
|---|---|
| Framework | FastAPI 0.111.1 + Uvicorn |
| ORM | SQLAlchemy 2.0 + Alembic (migraciones) |
| Base de datos | PostgreSQL + PostGIS (GeoAlchemy2 0.14.0) |
| Geo | Shapely 2.0.0, PyProj 3.6.0, pyshp 2.3.0 |
| Auth | python-jose (JWT), bcrypt |
| HTTP client | httpx 0.26.0 |
| Scheduler | APScheduler |
| Cache | Redis |

### Frontend
| Categoría | Tecnología |
|---|---|
| Framework | React 18.3.1 + TypeScript |
| Build | Vite 5.3.4 |
| Routing | react-router-dom 6.24.1 |
| State | Zustand 4.5.4 (solo auth) |
| Mapa | Leaflet 1.9.4, react-leaflet 4.2.1, leaflet-draw |
| Estilos | Tailwind CSS 3.4.6 |

---

## 2. ESTRUCTURA DE CARPETAS

```
predik-geo/
├── backend/
│   ├── alembic/
│   │   └── versions/   # 7 migraciones (0001→0007)
│   ├── app/
│   │   ├── api/v1/
│   │   │   ├── admin.py
│   │   │   ├── analisis.py       ← Caso 1: análisis competitivo
│   │   │   ├── auth.py
│   │   │   ├── bie.py            ← Indicadores macroeconómicos INEGI
│   │   │   ├── catalogo.py       ← Estados, municipios, SCIAN
│   │   │   ├── cron.py
│   │   │   ├── etl.py
│   │   │   ├── reporte.py        ← Generación KMZ/Excel
│   │   │   ├── schemas.py        ← Modelos Pydantic
│   │   │   └── zona.py           ← Concentración comercial, densidad
│   │   ├── connectors/
│   │   │   └── inegi/
│   │   │       ├── bie.py
│   │   │       └── denue.py
│   │   ├── etl/
│   │   │   ├── denue.py
│   │   │   └── poblacion.py
│   │   ├── models/
│   │   │   ├── analytics.py
│   │   │   ├── core.py           ← User, Organization, etc.
│   │   │   └── raw_data.py       ← DenueEstablishment, AgebGeometry
│   │   ├── services/
│   │   │   ├── bie.py
│   │   │   ├── densidad_poblacional.py
│   │   │   ├── reporte.py        ← generar_reporte() / preview_reporte()
│   │   │   └── zona_analysis.py
│   │   ├── main.py
│   │   ├── auth.py
│   │   ├── db.py
│   │   └── deps.py
│   ├── scripts/
│   └── requirements.txt
├── frontend/
│   └── src/
│       ├── api/
│       │   └── client.ts         ← Todas las llamadas al backend
│       ├── components/
│       │   ├── AdminPanel.tsx
│       │   ├── EconomicContextWidget.tsx
│       │   ├── KPIPanel.tsx
│       │   ├── ResultsOverlay.tsx
│       │   └── wizard/
│       │       └── WizardAnalisis.tsx  ← Wizard 5 pasos (Caso 1)
│       ├── pages/
│       │   ├── LoginPage.tsx
│       │   └── MapPage.tsx       ← Interfaz principal
│       ├── store/
│       │   └── useAuthStore.ts
│       ├── types.ts
│       └── App.tsx
├── data/                         # MGN, DENUE, Censo 2020
└── infra/
```

---

## 3. BASE DE DATOS Y ESQUEMA

### Schema `raw_data`
| Tabla | Campos clave | Geometría |
|---|---|---|
| `denue_establishments` | clee, nombre, codigo_scian, entidad, municipio, colonia | POINT (GiST index) |
| `ageb_geometries` | cvegeo (PK 16 dígitos), clave_ent, clave_mun, nom_ent | MULTIPOLYGON |
| `ageb_demographics` | cvegeo, pobtot, score_nse, nse_nivel, vivpar_hab | (no geom) |
| `manzana_vivienda` | cvegeo, clave_mun, vivtot, vivpar_hab, servicios | MULTIPOLYGON |
| `bie_indicadores` | indicador_id, estado_clave, periodo, valor | (no geom) |

### Schema `core`
- `organizations` → `users` → `api_credentials`, `query_log`

### Schema `analytics`
- `zona_analysis_results` (id, organization_id, polygon, result_json)

### NSE scoring
Multi-variable: educación (34%) + IMSS (27%) + computadora (24%) + internet (9%) + auto (6%)

---

## 4. ENDPOINTS API (completos)

### Auth `/api/v1/auth/`
| Método | Ruta | Descripción |
|---|---|---|
| POST | `/login` | JWT login |
| POST | `/refresh` | Renovar token |

### Catálogo `/api/v1/catalogo/`
| Método | Ruta | Descripción |
|---|---|---|
| GET | `/estados` | 32 estados |
| GET | `/municipios/{clave_estado}` | Municipios por estado |
| GET | `/scian` | Códigos SCIAN disponibles en BD |
| GET | `/municipio-bbox/{clave_estado}/{clave_mun}` | BBox + centroide de municipio |

### Reporte `/api/v1/reporte/`
| Método | Ruta | Descripción |
|---|---|---|
| POST | `/generar` | Genera KMZ o Excel (polígono + capas + clasificación) |
| POST | `/preview` | Preview GeoJSON para el mapa |

### Zona `/api/v1/zona/`
| Método | Ruta | Descripción |
|---|---|---|
| POST | `/concentracion-comercial` | Concentración comercial en polígono |
| POST | `/densidad-poblacional` | Densidad poblacional (Censo 2020) |
| GET | `/analisis/{analysis_id}` | Recuperar análisis guardado |

### Análisis Competitivo `/api/v1/analisis/` — Caso 1
| Método | Ruta | Descripción |
|---|---|---|
| POST | `/competencia` | Análisis completo: competidores directos/indirectos, hubs, zonas blancas |
| GET | `/` | Listar análisis guardados |
| GET | `/{analysis_id}` | Detalle de análisis |
| GET | `/comparar` | Comparar 2+ análisis |
| DELETE | `/{analysis_id}` | Eliminar análisis |

**Request `/competencia`:**
```
clave_estado, claves_municipios, nse_niveles,
marca_propia, competencia_directa, scian_giros,
incluir_sucursales, incluir_hubs, incluir_zonas_blancas,
radio_hub_metros (50-500), nivel_geografico, formato_salida
```

### BIE `/api/v1/bie/`
| Método | Ruta | Descripción |
|---|---|---|
| GET | `/indicadores` | Catálogo de indicadores (ITAEE, desempleo, etc.) |
| GET | `/estado/{clave_estado}` | Resumen económico de un estado |
| GET | `/estado/{clave_estado}/{indicador_key}` | Serie histórica |
| POST | `/sync/{clave_estado}` | Cargar BIE de un estado |

### Admin & ETL
- `GET /api/v1/admin/bd-status` — Estado de la BD (DENUE, AGEBs)
- `POST /api/v1/etl/etl/{source}/run` — Ejecutar ETL (DENUE)
- `POST /api/v1/etl/etl/maestro/run` — ETL masivo 1-32 estados

---

## 5. SERVICIOS BACKEND CLAVE

### `services/reporte.py`
- `generar_reporte()` — ETL → query DENUE → clasifica AGEBs/manzanas → genera KMZ o Excel
- `preview_reporte()` — Devuelve GeoJSON para visualización en mapa
- `calcular_hubs()` — Agrupa competidores por proximidad (radio configurable)
- `clasificar_por_oportunidad()` — Verde (sin competencia) → Rojo (saturado)
- `generar_kmz_maestro()` — KML con polígonos + puntos + estilos

### `services/zona_analysis.py`
- `calculate_commercial_concentration()` — Conteo SCIAN por zona, negocios ancla
- `calculate_densidad_poblacional()` — Demografía por edad/género, viviendas

### `services/bie.py`
- `cargar_indicadores_estado()` — Fetch desde API INEGI → BD
- `resumen_economico_estado()` — ITAEE, desempleo, PEA, empleo formal

---

## 6. FRONTEND ACTUAL

### Rutas
| Ruta | Componente | Propósito |
|---|---|---|
| `/login` | `LoginPage.tsx` | Login (default: admin@predik.local) |
| `/` | `MapPage.tsx` | App principal (ruta protegida) |
| `*` | → `/` | Redirect al home |

### `MapPage.tsx` — Interfaz principal
- **Sidebar izquierdo (320px):** selector estado/municipio + constructor de capas (1-8) + opciones análisis + botón generar
- **Centro:** Mapa Leaflet (MapTiler) con polígonos coloreados + marcadores de establecimientos
- **Sidebar derecho:** `KPIPanel` (resultados) o `WizardAnalisis` (Caso 1)

### Componentes
| Componente | Propósito |
|---|---|
| `ResultsOverlay.tsx` | Renderiza capas GeoJSON en el mapa (polígonos + puntos) |
| `KPIPanel.tsx` | Dashboard KPI: top zonas, distribución, establecimientos por capa |
| `AdminPanel.tsx` | Panel admin: estado BD, sync conectores, ETL |
| `EconomicContextWidget.tsx` | Widget indicadores BIE (ITAEE, desempleo) |
| `WizardAnalisis.tsx` | Wizard 5 pasos — Caso 1 |

### Conexión al backend
Toda la comunicación pasa por `frontend/src/api/client.ts` con helper `req()` que inyecta el JWT automáticamente.

---

## 7. ESTADO DEL WIZARD (Caso 1)

### Lo que YA ESTÁ implementado
- **Paso 1:** Selector de estado (32 estados desde API)
- **Paso 2:** Multi-selector de municipios con búsqueda
- **Paso 3:** Checkboxes de NSE (AB, C+, C, C-, D+, D, E) con etiquetas AMAI
- **Paso 4:** Nombre de marca + códigos SCIAN + competidores directos + opciones (hubs, sucursales, zonas blancas, radio hub, nivel geográfico)
- **Paso 5:** Llamada a `/api/v1/analisis/competencia` → GeoJSON → `KPIPanel` + `ResultsOverlay`
- **Descarga KMZ** desde el mismo paso 5

### Lo que FALTA o está incompleto
- **Visualización de resultados detallados** en el paso 5 (el panel de resultados puede ser básico)
- **Historial de análisis** (`GET /analisis/` y `GET /analisis/comparar`) no están conectados al UI
- **Comparación de análisis** entre zonas/períodos no tiene UI
- **EconomicContextWidget** puede no estar integrado en el flujo del wizard
- **Validaciones de formulario** y mensajes de error robustos

---

## 8. DEPENDENCIAS

### `requirements.txt` (backend)
```
fastapi==0.111.1
uvicorn[standard]
sqlalchemy==2.0.*
geoalchemy2==0.14.0
shapely==2.0.*
pyproj==3.6.*
psycopg2-binary
alembic==1.11.1
python-jose[cryptography]
bcrypt
passlib
httpx==0.26.0
openpyxl==3.1.0
pyshp==2.3.0
apscheduler
redis
pytest-asyncio
```

### `package.json` (frontend)
```json
{
  "react": "18.3.1",
  "react-router-dom": "6.24.1",
  "zustand": "4.5.4",
  "leaflet": "1.9.4",
  "react-leaflet": "4.2.1",
  "leaflet-draw": "1.0.4",
  "tailwindcss": "3.4.6",
  "vite": "5.3.4",
  "typescript": "5.x"
}
```

---

## 9. MODELOS PYDANTIC (schemas.py)

```python
class CapaBusqueda(BaseModel):
    keyword: str
    label: str
    color: Literal["red", "green", "blue", "yellow", "orange", "purple", "cyan", "pink"]
    estado: str
    icon: Literal["circle", "star"] = "circle"
    scian_prefix: Optional[str] = None

class ReporteRequest(BaseModel):
    nombre: str
    polygon: Geometry
    capas: List[CapaBusqueda]
    formato: Literal["kmz", "excel"]
    clasificacion_hexagonos: Literal["densidad", "oportunidad", "poder_adquisitivo"]
    nivel_geografico: Literal["ageb", "manzana"]

class AnalisisCompetenciaRequest(BaseModel):
    clave_estado: str
    claves_municipios: List[str]
    nse_niveles: Optional[List[str]] = None
    marca_propia: Optional[str] = None
    scian_giros: Optional[List[str]] = None
    competencia_directa: List[str]
    incluir_sucursales: bool = True
    incluir_hubs: bool = True
    incluir_zonas_blancas: bool = True
    radio_hub_metros: int = 150
    nivel_geografico: Literal["ageb", "manzana"] = "ageb"
    formato_salida: Literal["kmz", "geojson"] = "kmz"
```

---

## 10. TIPOS TYPESCRIPT (types.ts)

```typescript
type ColorNombre = 'red' | 'green' | 'blue' | 'yellow' | 'orange' | 'purple' | 'cyan' | 'pink'
type IconTipo = 'circle' | 'star'
type Clasificacion = 'densidad' | 'oportunidad' | 'poder_adquisitivo'
type Formato = 'kmz' | 'excel'
type NivelGeografico = 'ageb' | 'manzana'
type NseNivel = 'AB' | 'Cmas' | 'C' | 'Cmenos' | 'Dmas' | 'D' | 'E'

interface Capa {
  id: string
  keyword: string
  label: string
  color: ColorNombre
  icon: IconTipo
  estado: string
}

interface WizardData {
  estadoClave: string
  estadoNombre: string
  municipios: MunicipioCatalogo[]
  nseNiveles: NseNivel[]
  marcaPropia: string
  scianGiros: string[]
  competenciaDirecta: string[]
  incluirSucursales: boolean
  incluirHubs: boolean
  incluirZonasBlancas: boolean
  radioHub: 100 | 150 | 200 | 300
  nivelGeografico: NivelGeografico
}

interface CompetenciaResultado {
  zonas: GeoJSONFeature[]
  capas: CapaConPuntos[]
  indirecta: { cantidad: number; puntos: any[] }
  hubs: any[]
  resumen: { /* ... */ }
}
```

---

## 11. VARIABLES DE ENTORNO (.env.example)

```
ENVIRONMENT=development
DATABASE_URL=postgresql+psycopg2://admin:password@localhost:5432/geodata_predik_clone
REDIS_URL=redis://localhost:6379/0
JWT_SECRET=dev_secret_change_in_production
ACCESS_TOKEN_EXPIRE_MINUTES=30
REFRESH_TOKEN_EXPIRE_DAYS=7
INEGI_DENUE_TOKEN=<obtener en inegi.org.mx>
INEGI_BIE_API_TOKEN=<obtener en inegi.org.mx>
PLAN_STARTER_MONTHLY_LIMIT=50
PLAN_BASIC_MONTHLY_LIMIT=500
PLAN_PLUS_MONTHLY_LIMIT=5000
RATE_LIMIT_ENABLED=false
CENSO_DATA_DIR=data/censo_2020
MGN_DATA_DIR=data/mgn
SCHEDULER_ENABLED=false
SCHEDULER_SYNC_TIME=08:00
LOG_LEVEL=INFO
```

---

**Estado general del proyecto: ~75-80% completo.**
El backend tiene toda la lógica implementada. El frontend tiene el wizard de 5 pasos funcional
pero los resultados del Caso 1, el historial/comparación de análisis, y la integración del
widget BIE en el flujo del wizard pueden necesitar trabajo adicional.
