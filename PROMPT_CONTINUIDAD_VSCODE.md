# PROMPT DE CONTINUIDAD — Pegar esto como primer mensaje en Claude Code (VS Code)

Copia y pega TODO el contenido de este archivo como tu primer mensaje a Claude dentro de VS Code. Antes de pegarlo, abre en VS Code la carpeta del proyecto: `predik-geo` (en el Desktop, es el repositorio Git con la historia completa).

---

## CONTEXTO DEL PROYECTO

Estoy construyendo un clon funcional de **GeoData Intelligence** (plataforma de inteligencia geoespacial y geomarketing de PREDIK Data-Driven), para uso propio / comercialización futura como SaaS. Ya trabajé el diseño completo de arquitectura, documentación e implementación con instancias anteriores de Claude. Tú vas a continuar exactamente desde donde se quedó ese trabajo.

**Lee primero estos documentos antes de cualquier cosa:**
- `docs/00-README.md` — índice de toda la documentación técnica
- `docs/10-bitacora-de-avance.md` — registro cronológico exacto de qué se hizo y qué falta (9 sesiones)
- `docs/11-plan-sprints.md` — plan de 13 sprints en 5 fases; **estamos al inicio del Sprint 0.2**
- `docs/12-reporte-avance-pm.md` — reporte PM con avance por etapa, ruta crítica y riesgos

---

## RESUMEN EJECUTIVO (decisiones ya acordadas — no re-discutir)

- **Stack backend:** FastAPI + PostgreSQL 16 + PostGIS 3.4 + H3 v4.2.2 + Redis
- **Stack frontend actual (MVP):** React 18 + Vite 5 + TypeScript + Tailwind + react-leaflet 4
- **Stack frontend próximo (Enterprise — Fase 1):** MapLibre GL + Deck.gl + shadcn/ui + TanStack Query + ECharts + Framer Motion
- **Arquitectura de datos:** `raw_data` (crudo) → `cube` (H3 precalculado) → `analytics` (resultados usuario)
- **Conectores:** toda fuente implementa `BaseConnector` (`fetch()`, `health_check()`), normaliza a `GeoFeature`
- **Multi-tenancy desde día 1:** todas las tablas de negocio llevan `organization_id`
- **Auth:** JWT access token (30 min) + refresh (7 días), HS256, secret en `JWT_SECRET`
- **Granularidad:** Manzanas → AGEBs → H3 (en ese orden de preferencia por granularidad real)

---

## ESTADO ACTUAL DE LA BASE DE DATOS (al 2026-06-24)

| Tabla | Registros | Estado |
|---|---|---|
| `raw_data.denue_establishments` | ~528,808 | ⚠️ Parcial (~6 estados) |
| `raw_data.ageb_geometries` | **82,283** | ✅ CRS corregido, cvegeo_9 poblado |
| `raw_data.ageb_demographics` | **66,750** | ✅ JOIN funcional — 63,876 matches |
| `raw_data.manzana_vivienda` | **352,884+** | ⚠️ 7/32 estados procesados |
| `raw_data.bie_indicadores` | Poblado | ✅ Con fallback a datos demo |
| `cube.commercial_density_h3` | ~294 | Fallback cuando no hay AGEBs |

**Credenciales dev:**
- Usuario: `admin@predik.local` / `dev_password_admin`
- DB: `postgresql+psycopg2://admin:dev_password_local@localhost:5432/geodata_predik_clone`

---

## CÓMO LEVANTAR EL SERVIDOR (Windows — importante)

```bash
# Desde Bash (Git Bash), en la raíz del proyecto:
cd backend
/c/Users/Arturo\ Solis\ Munoz/Desktop/predik-geo/.venv/Scripts/python.exe \
  -m uvicorn app.main:app --host 127.0.0.1 --port 8000

# NO usar --reload (tiene bug de permisos de socket en Windows)
# Para recargar cambios: matar el proceso y reiniciar manualmente
```

**URLs:** Backend http://localhost:8000 | Frontend http://localhost:5173 (npm run dev en /frontend)

---

## BACKEND — ENDPOINTS IMPLEMENTADOS

```
POST /api/v1/auth/login                              JWT login
POST /api/v1/auth/refresh                            Refresh token
GET  /api/v1/catalogo/estados                        32 estados México
GET  /api/v1/catalogo/municipios/{clave}             Municipios por estado
GET  /api/v1/catalogo/municipio-bbox/{ent}/{mun}     Bbox para fly-to en mapa
POST /api/v1/reporte/preview                         GeoJSON + KPIs para visualizar en mapa
POST /api/v1/reporte/generar                         KMZ o Excel descargable
POST /api/v1/zona/concentracion-comercial            Heatmap H3
POST /api/v1/zona/densidad-poblacional               Densidad poblacional por AGEB
POST /api/v1/zona/establecimientos                   Puntos DENUE en polígono
GET  /api/v1/admin/bd-status                         Estado de tablas en BD
POST /api/v1/admin/etl/trigger                       Lanza ETL por fuente
GET  /api/v1/bie/estado/{clave}                      Indicadores macroeconómicos BIE INEGI
GET  /api/v1/analisis                                Historial de análisis
```

**Parámetros clave de `/reporte/preview` y `/reporte/generar`:**
```json
{
  "polygon": { GeoJSON Polygon },
  "capas": [{ "keyword": "farmacia", "label": "Farmacias", "color": "red",
               "estado": "09", "icon": "circle" }],
  "clasificacion_hexagonos": "densidad | oportunidad | poder_adquisitivo",
  "nivel_geografico": "ageb | manzana",
  "ejecutar_etl": false,
  "max_records": 500,
  "h3_resolution": 9
}
```

---

## FRONTEND MVP — FUNCIONALIDADES ACTUALES

Está completo y funcional en `frontend/`. Las páginas y componentes principales:
- `LoginPage.tsx` — login con branding dividido
- `MapPage.tsx` — mapa + sidebar 3 pasos + estado `nivelGeografico`
- `components/ResultsOverlay.tsx` — polígonos + puntos en mapa con toggles de visibilidad
- `components/KPIPanel.tsx` — panel deslizable con KPIs, distribución de zonas, top 5 ← **pendiente hacerlo manzana-aware**
- `components/EconomicContextWidget.tsx` — widget BIE (indicadores macro por estado)
- `components/AdminPanel.tsx` — estado de BD y comandos ETL
- `api/client.ts` — fetch con JWT, interfaces TypeScript completas
- `types.ts` — incluye `NivelGeografico = 'ageb' | 'manzana'`

---

## SCRIPTS DE DATOS (en `backend/scripts/`)

| Script | Uso |
|---|---|
| `etl_mgn_maestro.py` | ETL completo MGN + Censo 2020 (NO re-ejecutar — ya completo) |
| `etl_manzana.py` | ETL manzanas por estado: `python etl_manzana.py --estado 09` |
| `etl_maestro.py` | ETL DENUE por estados: `python etl_maestro.py --solo-denue --estados 09,14,15` |
| `load_marco_geoestadistico.py` | Carga shapefiles MGN (reprojecta EPSG:6372→4326) |
| `etl_bie.py` | Carga indicadores BIE INEGI por estado |

---

## QUIRKS Y BUGS CONOCIDOS (muy importante — no repetir)

1. **CRS EPSG:6372:** Los shapefiles MGN usan Lambert Conformal Conic (metros), no WGS84. Los scripts ya reprojectan al cargar. Si un UPDATE manual llena la tabla, usar: `UPDATE raw_data.ageb_geometries SET geom = ST_Transform(ST_SetSRID(geom, 6372), 4326)`. Síntoma de bug: `usa_agebs=False` aunque la tabla tenga datos.

2. **GROUP BY en columna JSON:** PostgreSQL no tiene operador de igualdad para `json`. Nunca poner una columna `Column(JSON)` en un `GROUP BY`. Usar `func.max(cast(columna, Text))` como agregado.

3. **Transacción abortada en cascada:** Si una query SQLAlchemy falla, el session queda en estado `aborted`. Siempre agregar `db.rollback()` después de cada bloque `except Exception` antes de intentar otra query en la misma sesión.

4. **uvicorn --reload en Windows:** Causa `[WinError 10013]` de permisos de socket. **No usar --reload**. Reiniciar manualmente para recargar código.

5. **INEGI DENUE keyword "mcdonald":** causa abort de conexión. Usar `"mc donalds"` (con espacio).

6. **cvegeo formato manzana (16 chars):** `ent(0:2)+mun(2:5)+loc(5:9)+ageb(9:13)+mza(13:16)`. Para obtener cvegeo_ageb (9 chars): `cvegeo[0:2] + cvegeo[2:5] + cvegeo[9:13]` — **no** `cvegeo[:9]` que da ent+mun+loc.

7. **Puerto 8000 ocupado:** Verificar con PowerShell: `Get-NetTCPConnection -LocalPort 8000`. Matar el proceso: `Stop-Process -Id {PID} -Force`.

---

## ESTADO DEL PLAN DE SPRINTS (al 2026-06-24)

**Avance global del producto:** 38% | **Dentro del plan de sprints:** 9% (1.2/13 sprints)

| Fase | Estado | % |
|---|---|---|
| FASE 0 — Cierre técnico | EN PROGRESO | 60% |
| FASE 1 — Frontend Enterprise | NO INICIADO | 0% |
| FASE 2 — Site Selector | NO INICIADO | 0% |
| FASE 3 — POI Explorer | NO INICIADO | 0% |
| FASE 4 — Reportes PDF | PARCIAL | 20% |
| FASE 5 — Cloud / SaaS | NO INICIADO | 0% |

**Hito demo a clientes:** Cierre Sprint 2.3 (semana 8 desde hoy)
**Hito MVP en producción:** Cierre Sprint 5.2 (semana 13 desde hoy)

---

## TAREA INMEDIATA AL REANUDAR (Sprint 0.2 — pendiente)

### 1. ETL DENUE estados prioritarios (CUELLO DE BOTELLA #1)
Sin datos de CDMX, Jalisco y Edomex el Site Selector no tiene valor de demo:
```bash
cd backend
python scripts/etl_maestro.py --solo-denue --estados 09,14,15
# Si funciona, agregar: 19 (NL), 21 (Puebla), 31 (Yucatán)
```

### 2. ETL manzanas estados restantes (background)
25 estados sin manzanas. Correr en background mientras se trabaja otra cosa:
```bash
python scripts/etl_manzana.py --estado 09
# Después de completar, aplicar CRS fix para registros nuevos:
# UPDATE raw_data.manzana_vivienda SET geom = ST_Transform(ST_SetSRID(geom, 6372), 4326)
# WHERE ST_X(ST_Centroid(geom)) > 1000;  -- coordenadas en metros = EPSG:6372
```

### 3. Cerrar deuda técnica Sprint 0.2
```python
# a) Lazy health check en registry.py — no llamar HTTP al importar el módulo
# b) Tests unitarios para query_agebs_en_poligono con datos semilla
# c) Verificar reporte CDMX Benito Juárez (polígono grande, validar escala)
```

### 4. Iniciar Sprint 1.1 — Frontend Enterprise
Cuando 0.2 esté cerrado, arrancar con el setup del nuevo stack:
- Nuevo proyecto Vite con MapLibre GL, Deck.gl, shadcn/ui, TanStack Query, ECharts, Framer Motion
- Tema dark enterprise, TopBar, LeftNav, routing protegido, Zustand stores
- El MVP actual queda como fallback operativo — no se elimina hasta que Enterprise esté completo

---

## FLUJO DE TRABAJO (no negociable)

1. Todo cambio se guarda localmente en los archivos reales del repositorio
2. Rama por tarea: `git checkout develop && git checkout -b feature/nombre`
3. Al terminar: `git add` → `git commit` (Conventional Commits) → `git push`
4. Cada hito completado → actualizar `docs/10-bitacora-de-avance.md`
5. Cada decisión técnica nueva → ADR en `docs/06-decisiones-tecnicas-adr.md`
6. API-first: los scripts de prueba siempre llaman endpoints HTTP, nunca importan ORM directamente

## INSTRUCCIÓN DE ARRANQUE

Antes de escribir cualquier código:
1. `git log --oneline -10` y `git status` — estado del repo
2. Lee `docs/10-bitacora-de-avance.md` — última sesión registrada
3. Verifica servidor: `curl http://127.0.0.1:8000/health` (si no responde, levantarlo)
4. Confírmame el estado actual y por dónde seguimos
