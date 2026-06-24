# Backend — Arquitectura Técnica

**Proyecto:** predik-geo (clon SaaS de PREDIK GeoData Intelligence)
**Fecha:** 2026-06-24
**Alembic head:** `0006_drop_cube_h3`

---

## 1. Visión general

predik-geo es una plataforma de inteligencia geoespacial comercial para México. El backend expone una API REST sobre datos del INEGI (DENUE, MGN, Censo 2020, BIE) almacenados en PostgreSQL con PostGIS. Las unidades geográficas de análisis son **AGEBs** y **manzanas** del Marco Geoestadístico Nacional — no celdas hexagonales artificiales.

### Stack

| Capa | Tecnología |
|------|-----------|
| API | FastAPI 0.x + Python 3.12 |
| Base de datos | PostgreSQL 16 + PostGIS 3.4 |
| ORM | SQLAlchemy 2.x (síncrono) |
| Migraciones | Alembic |
| Cache/rate-limit | Redis |
| Auth | JWT (python-jose) + bcrypt |
| ETL geoespacial | pyshp, shapely, pyproj |
| Exportación | openpyxl (Excel), zipfile/KML (KMZ) |

---

## 2. Estructura de carpetas del backend

```
backend/
├── alembic/
│   ├── env.py
│   └── versions/
│       ├── 0001_initial_schemas.py
│       ├── 0002_ageb_tables.py
│       ├── 0003_cube_population.py
│       ├── 0004_bie_indicadores.py
│       ├── 0005_add_cvegeo9_index.py
│       └── 0006_drop_cube_h3.py
├── app/
│   ├── main.py              # FastAPI app, CORS, lifespan, scheduler
│   ├── db.py                # SessionLocal, Base
│   ├── auth.py              # JWT: create_access_token, create_refresh_token, decode_token
│   ├── deps.py              # get_db, get_current_user
│   ├── middleware.py        # QueryLogMiddleware
│   ├── rate_limit.py        # check_rate_limit (Redis)
│   ├── scheduler.py         # APScheduler (ETL DENUE nocturno)
│   ├── api/
│   │   └── v1/
│   │       ├── __init__.py  # Router raíz /api/v1
│   │       ├── auth.py
│   │       ├── zona.py
│   │       ├── analisis.py
│   │       ├── admin.py
│   │       ├── etl.py
│   │       ├── reporte.py
│   │       ├── catalogo.py
│   │       ├── bie.py
│   │       └── schemas.py
│   ├── models/
│   │   ├── base.py
│   │   ├── core.py
│   │   ├── raw_data.py
│   │   ├── analytics.py
│   │   └── cube.py          # Vacío — modelos H3 eliminados en 0006
│   ├── connectors/
│   │   ├── base.py          # BaseConnector, GeoFeature
│   │   ├── registry.py
│   │   └── inegi/
│   │       ├── denue.py
│   │       └── bie.py
│   ├── etl/
│   │   ├── base.py          # BaseETL: extract → transform → load_raw
│   │   ├── denue.py         # DenueETL: load_raw()
│   │   └── poblacion.py     # No-op — reemplazado por consultas directas a AGEBs
│   └── services/
│       ├── zona_analysis.py
│       ├── densidad_poblacional.py
│       ├── reporte.py
│       └── bie.py
└── scripts/
    ├── etl_maestro.py
    ├── etl_mgn_maestro.py
    ├── etl_manzana.py
    ├── etl_bie.py
    ├── load_marco_geoestadistico.py
    ├── load_censo_2020.py
    ├── descargar_censo_2020.py
    ├── run_etl.py
    └── seed_dev.py
```

---

## 3. Esquemas de la base de datos

| Esquema | Propósito |
|---------|-----------|
| `core` | Multi-tenancy: organizaciones, usuarios, credenciales, auditoría |
| `raw_data` | Datos brutos de fuentes externas (DENUE, MGN, Censo, BIE) |
| `cube` | Esquema vacío — tablas H3 eliminadas en migración 0006 |
| `analytics` | Resultados de análisis guardados por organización |

---

## 4. Migraciones Alembic

### 0001 — initial_schemas
Crea extensiones PostgreSQL (`pgcrypto`, `postgis`) y los cuatro esquemas. Tablas:
- `core.organizations`, `core.users`, `core.api_credentials`, `core.query_log`
- `raw_data.denue_establishments`: POINT SRID 4326, índices GIST en `geom` y B-tree en `codigo_scian`
- `analytics.zona_analysis_results`: resultados de análisis con índice GIST en `polygon`

### 0002 — ageb_tables
Agrega tablas del Marco Geoestadístico y Censo 2020:
- `raw_data.ageb_geometries`: MULTIPOLYGON SRID 4326, PK `cvegeo`, índice GIST en `geom`
- `raw_data.ageb_demographics`: indicadores Censo 2020 por AGEB
- `raw_data.manzana_vivienda`: geometría + vivienda a nivel manzana, cvegeo de 16 chars

### 0003 — cube_population
Crea `cube.population_density_h3` (eliminada en 0006).

### 0004 — bie_indicadores
Agrega `raw_data.bie_indicadores`: series de tiempo del BIE INEGI, constraint único en `(indicador_id, area_clave, periodo)`.

### 0005 — add_cvegeo9_index
Agrega columna `cvegeo_9 VARCHAR(9)` a `raw_data.ageb_geometries` y la puebla con `ent(2)+mun(3)+ageb(4)`. Normaliza el JOIN entre AGEBs y demografía del Censo (que siempre usa 9 chars).

### 0006 — drop_cube_h3
Elimina `cube.commercial_density_h3` y `cube.population_density_h3`. Los cubos H3 fueron reemplazados por consultas directas a `ageb_geometries`, `ageb_demographics` y `manzana_vivienda`. La extensión h3 y el paquete Python `h3` fueron removidos del stack.

---

## 5. Modelos de datos

### 5.1 Esquema `core`

**`core.organizations`**

| Columna | Tipo | Notas |
|---------|------|-------|
| id | UUID PK | `gen_random_uuid()` |
| name | VARCHAR(255) | |
| plan | VARCHAR(50) | default: `starter` |
| created_at | TIMESTAMPTZ | |
| is_active | BOOLEAN | |

**`core.users`**

| Columna | Tipo | Notas |
|---------|------|-------|
| id | UUID PK | |
| organization_id | UUID FK | → `core.organizations` |
| email | VARCHAR(255) | UNIQUE |
| hashed_password | VARCHAR(255) | bcrypt |
| role | VARCHAR(50) | default: `analyst` |
| created_at | TIMESTAMPTZ | |

**`core.api_credentials`**

| Columna | Tipo | Notas |
|---------|------|-------|
| id | UUID PK | |
| organization_id | UUID FK | |
| connector_name | VARCHAR(100) | ej. `inegi_denue` |
| encrypted_value | TEXT | |
| created_at | TIMESTAMPTZ | |

**`core.query_log`**

| Columna | Tipo | Notas |
|---------|------|-------|
| id | BIGINT PK | autoincrement |
| organization_id | UUID FK | |
| user_id | UUID FK | nullable |
| endpoint | VARCHAR(255) | |
| request_summary | JSON | |
| duration_ms | INTEGER | |
| status_code | INTEGER | |
| created_at | TIMESTAMPTZ | |

### 5.2 Esquema `raw_data`

**`raw_data.denue_establishments`**

| Columna | Tipo | Notas |
|---------|------|-------|
| id | BIGINT PK | |
| clee | VARCHAR(50) | UNIQUE — clave de establecimiento INEGI |
| nombre | VARCHAR(255) | |
| razon_social | VARCHAR(255) | |
| clase_actividad | VARCHAR(255) | |
| codigo_scian | VARCHAR(10) | índice B-tree |
| estrato_personal | VARCHAR(50) | rangos de empleados |
| entidad / municipio / localidad / colonia / cp | VARCHAR | |
| geom | POINT SRID 4326 | índice GIST |
| fuente_actualizacion | DATE | |
| fetched_at | TIMESTAMPTZ | |
| raw_response | JSON | respuesta cruda de la API |

**`raw_data.ageb_geometries`**

| Columna | Tipo | Notas |
|---------|------|-------|
| cvegeo | VARCHAR(16) PK | 9–13 chars según formato MGN |
| clave_ent | VARCHAR(2) | código de entidad federativa |
| clave_mun | VARCHAR(3) | |
| cve_loc | VARCHAR(4) | |
| cve_ageb | VARCHAR(4) | |
| cvegeo_9 | VARCHAR(9) | normalizado ent+mun+ageb; índice B-tree |
| nom_ent / nom_mun / nom_loc | VARCHAR | |
| ambito | VARCHAR(10) | `Urbana` o `Rural` |
| geom | MULTIPOLYGON SRID 4326 | índice GIST |
| loaded_at | TIMESTAMPTZ | |

**`raw_data.ageb_demographics`**

| Columna | Tipo | Notas |
|---------|------|-------|
| cvegeo | VARCHAR(16) PK | |
| fuente | VARCHAR(50) | `Censo 2020` |
| pobtot / pobmas / pobfem | INTEGER | población total, masculina, femenina |
| p_0a14 / p_15a64 / p_65ymas | INTEGER | grupos de edad |
| vivpar_hab | INTEGER | viviendas particulares habitadas |
| prom_ocup | FLOAT | promedio de ocupantes |
| graproes | FLOAT | grado promedio de escolaridad |
| pcon_disc / psinder / pder_ss | INTEGER | salud y derechohabiencia |
| indicadores | JSON | todos los campos crudos del CSV |
| loaded_at | TIMESTAMPTZ | |

**`raw_data.manzana_vivienda`**

| Columna | Tipo | Notas |
|---------|------|-------|
| cvegeo | VARCHAR(16) PK | ent(2)+mun(3)+loc(4)+ageb(4)+mza(3) |
| clave_ent / clave_mun / cve_loc / cve_ageb / cve_mza | VARCHAR | |
| cvegeo_ageb | VARCHAR(16) | FK lógica → ageb_geometries |
| vivtot / vivpar / vivpar_hab | INTEGER | vivienda |
| con_agua / con_dren / con_luz | INTEGER | infraestructura básica |
| geom | MULTIPOLYGON SRID 4326 | índice GIST |
| indicadores | JSONB | campos adicionales del Censo |
| fuente | VARCHAR(50) | `MGN2025+CENSO2020` |
| loaded_at | TIMESTAMPTZ | |

**`raw_data.bie_indicadores`**

| Columna | Tipo | Notas |
|---------|------|-------|
| id | INTEGER PK | autoincrement |
| indicador_id | VARCHAR(20) | ID del BIE (ej. `452001`) |
| nombre / descripcion | VARCHAR/TEXT | |
| unidad / frecuencia | VARCHAR | |
| area_clave | VARCHAR(10) | `00` = nacional |
| estado_clave | VARCHAR(2) | clave INEGI de entidad |
| periodo | VARCHAR(10) | ej. `2024/01` |
| periodo_fecha | DATE | |
| valor | FLOAT | |
| fuente | VARCHAR(50) | default `BIE_INEGI` |
| loaded_at | TIMESTAMPTZ | |

### 5.3 Esquema `analytics`

**`analytics.zona_analysis_results`**

| Columna | Tipo | Notas |
|---------|------|-------|
| id | UUID PK | |
| organization_id | UUID FK | |
| user_id | UUID FK | nullable |
| polygon | POLYGON SRID 4326 | índice GIST |
| analysis_type | VARCHAR(50) | `concentracion_comercial` o `densidad_poblacional` |
| result_json | JSON | resultado completo del análisis |
| created_at | TIMESTAMPTZ | |

---

## 6. APIs disponibles

Base path: `/api/v1`

### 6.1 Autenticación — `/auth`

| Método | Ruta | Descripción |
|--------|------|-------------|
| POST | `/auth/login` | Login con email/password; devuelve `access_token` + `refresh_token` |
| POST | `/auth/refresh` | Renueva el `access_token` usando un `refresh_token` válido |

### 6.2 Análisis de zona — `/zona`

Todos requieren autenticación JWT.

| Método | Ruta | Descripción |
|--------|------|-------------|
| POST | `/zona/concentracion-comercial` | Analiza concentración comercial en un polígono. Devuelve totales, categorías SCIAN, negocios ancla y heatmap por AGEB o manzana |
| POST | `/zona/densidad-poblacional` | Analiza densidad poblacional; devuelve datos Censo 2020 por AGEB con ponderación de área |
| POST | `/zona/establecimientos` | Lista establecimientos individuales DENUE; filtro por `keyword` y `scian_prefix` |
| GET | `/zona/analisis/{analysis_id}` | Recupera un análisis guardado por UUID |

**Parámetro `nivel_geografico`:** `/concentracion-comercial` acepta `"ageb"` (default) o `"manzana"`. Con `"manzana"` usa `manzana_vivienda` como unidad de análisis; si no hay cobertura para esa zona, hace fallback automático a AGEBs.

### 6.3 Análisis guardados — `/analisis`

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/analisis/` | Lista todos los análisis de la organización |
| GET | `/analisis/{analysis_id}` | Obtiene un análisis guardado |
| GET | `/analisis/comparar?ids=uuid1,uuid2` | Compara 2 o más análisis en paralelo |
| DELETE | `/analisis/{analysis_id}` | Elimina un análisis |

### 6.4 Reportes geoespaciales — `/reporte`

| Método | Ruta | Descripción |
|--------|------|-------------|
| POST | `/reporte/generar` | Genera reporte KMZ o Excel con 1–8 capas de búsqueda |
| POST | `/reporte/preview` | Preview en GeoJSON para visualización en mapa |

Parámetros clave de `ReporteRequest`:
- `polygon`: GeoJSON Polygon
- `capas`: lista de `CapaBusqueda` (keyword, label, color, estado, icon, scian_prefix)
- `formato`: `kmz` o `excel`
- `clasificacion_hexagonos`: `densidad` | `oportunidad` | `poder_adquisitivo`
- `nivel_geografico`: `ageb` o `manzana`
- `ejecutar_etl`: `true` para consultar INEGI en tiempo real

> `h3_resolution` fue eliminado — ya no aplica.

### 6.5 Catálogo geográfico — `/catalogo`

No requiere autenticación.

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/catalogo/estados` | Lista los 32 estados con clave INEGI |
| GET | `/catalogo/municipios/{clave_estado}` | Municipios de un estado |
| GET | `/catalogo/municipio-bbox/{clave_estado}/{clave_mun}` | Bounding box de un municipio |

### 6.6 BIE — Indicadores económicos — `/bie`

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/bie/indicadores` | Catálogo de indicadores BIE disponibles |
| GET | `/bie/estado/{clave_estado}` | Resumen económico de un estado |
| GET | `/bie/estado/{clave_estado}/{indicador_key}` | Serie histórica de un indicador; parámetro `limit` (default 12, máx 60) |
| GET | `/bie/stats` | Estadísticas de cobertura BIE en la BD |
| POST | `/bie/sync/{clave_estado}` | Carga BIE en background para un estado |
| POST | `/bie/sync` | Carga BIE en background para los 32 estados |

### 6.7 Administración — `/admin`

Requieren rol `admin`.

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/admin/bd-status` | Estado de tablas clave: `denue_establishments`, `ageb_geometries`, `ageb_demographics`, `manzana_vivienda` |
| GET | `/admin/conectores` | Lista conectores y su estado |
| GET | `/admin/conectores/{nombre}/health` | Health check de un conector |
| POST | `/admin/conectores/{nombre}/sync` | Sincronización de un conector |
| POST | `/admin/etl/{source}/run` | Ejecuta ETL (`inegi_denue`) |
| POST | `/admin/etl/maestro/run` | ETL maestro DENUE paginado |

### 6.8 Health check

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/health` | Retorna `{"status": "ok"}` |

---

## 7. Conectores de datos

### 7.1 DENUE (INEGI)

**Archivo:** `backend/app/connectors/inegi/denue.py`

| Campo | Valor |
|-------|-------|
| Clase | `DenueConnector` (hereda `BaseConnector`) |
| Nombre | `inegi_denue` |
| URL base | `https://www.inegi.org.mx/app/api/denue/v1/consulta` |
| Endpoint | `GET /BuscarEntidad/{keyword}/{estado}/{inicio}/{fin}/{token}` |
| Máximo por llamada | 2,500 registros |
| Token env var | `INEGI_DENUE_TOKEN` |

Normaliza la respuesta al dataclass `GeoFeature`. Sin token devuelve 3 features de demostración.

### 7.2 BIE (INEGI)

**Archivo:** `backend/app/connectors/inegi/bie.py`

| Campo | Valor |
|-------|-------|
| Clase | `BIEConnector` (hereda `BaseConnector`) |
| Nombre | `inegi_bie` |
| URL base | `https://www.inegi.org.mx/app/api/indicadores/desarrolladores/jsonxml` |
| Endpoint | `GET /INDICATOR/{ids}/es/{area}/false/BIE-BISE/2.0/{token}?type=json` |
| Área | `00` (nacional) |
| Token env var | `INEGI_BIE_API_TOKEN` (mismo token que DENUE) |

**Indicadores configurados:**

| Key | ID BIE | Nombre | Frecuencia |
|-----|--------|--------|-----------|
| `itaee` | 452001 | Actividad Económica (ITAEE) | Mensual |
| `desocupacion` | 444612 | Tasa de Desocupación (ENOE) | Trimestral |
| `empleo_formal` | 935 | Trabajadores asegurados IMSS | Mensual |

---

## 8. Lógica de análisis geoespacial

### 8.1 Unidades geográficas

| Nivel | Tabla | Tamaño típico | Fuente |
|-------|-------|--------------|--------|
| AGEB | `ageb_geometries` + `ageb_demographics` | ~1 km² | MGN 2025 + Censo 2020 |
| Manzana | `manzana_vivienda` | ~100 m² | MGN 2025 + Censo 2020 |

La API elige la unidad según `nivel_geografico`. Con `"manzana"` hace fallback automático a AGEBs si no hay cobertura.

### 8.2 Análisis de concentración comercial

**Archivo:** `backend/app/services/zona_analysis.py`

1. Cuenta establecimientos DENUE dentro del polígono, agrupados por `clase_actividad`
2. Identifica negocios ancla (categorías con cantidad ≥ 2× el promedio)
3. Consulta AGEBs o manzanas que intersectan el polígono con `ST_Intersects`
4. Hace JOIN espacial de establecimientos a cada unidad con `ST_Within`
5. Normaliza intensidad de 0 a 1 relativa al máximo de establecimientos por unidad

### 8.3 Clasificación de zonas en reportes

**Archivo:** `backend/app/services/reporte.py`

| Clasificación | Lógica |
|--------------|--------|
| `densidad` | Gradiente de color según cantidad de establecimientos por zona (verde → naranja → rojo) |
| `oportunidad` | Usa `shapely.Point.within(Polygon)` para verificar presencia de cadenas en cada zona: SATURADA → MEDIA → ALTA / MEDIA_ALTA / BAJA según densidad |
| `poder_adquisitivo` | Por `graproes` (años escolaridad Censo 2020): ≥12 PREMIUM / ≥9 MEDIO_ALTO / ≥6 MEDIO / <6 BAJO |

La clasificación `oportunidad` reemplazó el mapeo H3 por Point-in-Polygon con shapely sobre las geometrías reales de cada AGEB o manzana.

### 8.4 Densidad poblacional

**Archivo:** `backend/app/services/densidad_poblacional.py`

Promedio ponderado por fracción de área intersectada:
- `fraccion = ST_Area(ST_Intersection(ageb, polígono)) / ST_Area(ageb)`
- Pondera población, vivienda y grupos de edad por esa fracción
- Devuelve densidad en hab/km²

---

## 9. Scripts ETL

Todos los scripts se ejecutan desde el directorio raíz del repositorio.

### 9.1 `etl_maestro.py` — Orquestador DENUE

```bash
python backend/scripts/etl_maestro.py --solo-denue
python backend/scripts/etl_maestro.py --solo-denue --estados 09,14,15
python backend/scripts/etl_maestro.py --solo-geo
python backend/scripts/etl_maestro.py --solo-censo
```

Itera 20 sectores SCIAN. Usa `ON CONFLICT DO UPDATE` por `clee`.

### 9.2 `etl_mgn_maestro.py` — MGN + Censo 2020 (AGEBs)

```bash
python backend/scripts/etl_mgn_maestro.py
python backend/scripts/etl_mgn_maestro.py --solo-mgn
python backend/scripts/etl_mgn_maestro.py --solo-censo
python backend/scripts/etl_mgn_maestro.py --entidad 31
```

### 9.3 `etl_manzana.py` — Vivienda a nivel manzana

Combina `*m.shp` del MGN con filas de manzana del Censo 2020 (`MZA != "000"`). Reproyecta EPSG:6372 → EPSG:4326 con pyproj.

```bash
python backend/scripts/etl_manzana.py
python backend/scripts/etl_manzana.py --estado 14
```

Requiere ZIPs en `data/mgn/{NN}_{nombre}.zip` y CSVs en `data/censo_2020/RESAGEBURB_{NN}CSV20.csv`.

### 9.4 `etl_bie.py` — Indicadores económicos BIE

```bash
python backend/scripts/etl_bie.py
python backend/scripts/etl_bie.py --estado 14
python backend/scripts/etl_bie.py --dry-run
```

Requiere `INEGI_BIE_API_TOKEN` en `.env`.

---

## 10. Estado actual de la base de datos

*Actualizado: 2026-06-24 ~12:00*

| Tabla | Registros aprox. | Cobertura |
|-------|-----------------|-----------|
| `raw_data.ageb_geometries` | 82,283 | 32 estados (completo) |
| `raw_data.ageb_demographics` | 66,750 | 32 estados (completo) |
| `raw_data.denue_establishments` | ~1,500,000+ | 17/32 estados (01–17); ETL 18–32 en curso |
| `raw_data.manzana_vivienda` | ~1,041,975+ | 14/32 estados (01–14); ETL 15–32 en curso |
| `raw_data.bie_indicadores` | 38,752 | ITAEE, desocupación, empleo formal (32 estados) |
| `cube.commercial_density_h3` | — | Tabla eliminada (migración 0006) |
| `cube.population_density_h3` | — | Tabla eliminada (migración 0006) |
| `analytics.zona_analysis_results` | 7 | Análisis guardados |

### Manzanas cargadas por estado (al 2026-06-24)

| Estado | Manzanas | Estado | Manzanas |
|--------|----------|--------|----------|
| 01 Aguascalientes | 24,385 | 08 Chihuahua | 114,469 |
| 02 Baja California | 69,638 | 09 CDMX | 67,224 |
| 03 Baja California Sur | 25,441 | 10 Durango | 72,056 |
| 04 Campeche | 24,872 | 11 Guanajuato | 115,349 |
| 05 Coahuila | 78,542 | 12 Guerrero | 95,795 |
| 06 Colima | 18,079 | 13 Hidalgo | 83,194 |
| 07 Chiapas | 111,927 | 14 Jalisco | 141,004 |
| **15–32** | *en carga* | | |

---

## 11. ETLs en curso y cómo lanzarlos

### 11.1 Lanzar ETL como proceso independiente de VS Code

En Windows, los procesos lanzados desde el terminal integrado de VS Code mueren al cerrar VS Code. Para lanzar un ETL que sobreviva al cierre de VS Code o Claude Code:

```powershell
# Desde PowerShell externo (Windows Terminal / CMD fuera de VS Code)
$logFile = "C:\Users\Arturo Solis Munoz\Desktop\predik-geo\logs\etl_denue_18_32.log"
$workDir = "C:\Users\Arturo Solis Munoz\Desktop\predik-geo"
$python  = "$workDir\.venv\Scripts\python.exe"

Start-Process -FilePath $python `
    -ArgumentList "-u backend/scripts/etl_maestro.py --solo-denue --estados 18,19,20,21,22,23,24,25,26,27,28,29,30,31,32" `
    -WorkingDirectory $workDir `
    -RedirectStandardOutput $logFile `
    -RedirectStandardError "$logFile.err" `
    -WindowStyle Hidden `
    -PassThru | Select-Object Id, StartTime
```

> Los tokens de la sesión Claude **no afectan** los procesos ETL. Son procesos del SO independientes de la conversación.

### 11.2 DENUE — estados 18–32

En curso (PID 17208, relanzado 2026-06-24 11:52). Log en `logs/etl_denue_18_32.log`.

> **Bug corregido (2026-06-24):** `etl_maestro.py` línea 254 llamaba a `etl.aggregate_h3()` que fue eliminado en la refactorización H3. El proceso moría silenciosamente al terminar de descargar cada estado. Fix: eliminada esa línea.

Si se interrumpe, relanzar con `Start-Process` (ver 11.1) apuntando a los estados pendientes:

```bash
# Desde terminal externo:
python backend/scripts/etl_maestro.py --solo-denue --estados 19,20,21,...
```

### 11.3 Manzana — estados 15–32

En curso (PID 8948, proceso huérfano — padre ya no existe, sobrevive cierre de VS Code). Log en `logs/etl_manzana_10_32.log`.

Si se interrumpe:

```powershell
# Ver el último estado completado en el log:
Get-Content logs\etl_manzana_10_32.log | Select-String "Cargadas:"

# Relanzar desde el estado que faltó:
Start-Process -FilePath ".venv\Scripts\python.exe" `
    -ArgumentList "-u backend/scripts/etl_manzana.py" `
    -WorkingDirectory "C:\Users\Arturo Solis Munoz\Desktop\predik-geo" `
    -RedirectStandardOutput "logs\etl_manzana_continua.log" `
    -WindowStyle Hidden
```

---

## 12. Decisión técnica: eliminación de H3

**Fecha:** 2026-06-24

**Razón:** Los cubos hexagonales H3 eran redundantes con los AGEBs y manzanas del INEGI, que son unidades estadísticas reales con datos demográficos ya asociados, mayor precisión espacial y sin dependencias adicionales de infraestructura. La extensión PostgreSQL H3 impediría despliegues en servicios gestionados (RDS, Cloud SQL, Supabase).

**Archivos modificados:**

| Archivo | Cambio |
|---------|--------|
| `requirements.txt` | `h3>=4.0.0` removido |
| `app/models/cube.py` | Vaciado — modelos `CommercialDensityH3` y `PopulationDensityH3` eliminados |
| `app/etl/base.py` | Contrato reducido a 3 pasos: `extract → transform → load_raw` |
| `app/etl/denue.py` | `aggregate_h3()` eliminado |
| `app/etl/poblacion.py` | Reemplazado por no-op |
| `app/services/zona_analysis.py` | Reescrito: consulta DENUE + AGEBs + manzanas directamente |
| `app/services/densidad_poblacional.py` | Fast-path de cubo H3 eliminado; solo raw_data |
| `app/services/reporte.py` | `import h3` removido; `clasificar_por_oportunidad` usa `shapely.Point.within(Polygon)` |
| `app/api/v1/reporte.py` | `h3_resolution` eliminado del schema `ReporteRequest` |
| `app/api/v1/etl.py` | `h3_resolution` y llamada a `aggregate_h3` eliminados |
| `app/api/v1/admin.py` | `bd-status` monitorea `manzana_vivienda` en lugar del cubo H3 |
| `app/scheduler.py` | Job `etl_poblacion` eliminado |
| `alembic/versions/0006_drop_cube_h3.py` | Migración que elimina las dos tablas del cubo |

---

## 13. Tokens y servicios externos

| Variable de entorno | Servicio | Notas |
|--------------------|----------|-------|
| `INEGI_DENUE_TOKEN` | API DENUE INEGI | Configurado. Mismo token que BIE |
| `INEGI_BIE_API_TOKEN` | API BIE INEGI | Configurado. Mismo token que DENUE |
| `MAPTILER_KEY` | MapTiler (frontend) | Para tiles de mapa base |

Token INEGI (gratuito): `https://www.inegi.org.mx/servicios/api_indicadores.html`

---

## 14. Configuración de la aplicación

### Arranque

```bash
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Infraestructura local (Docker)

```bash
docker-compose -f infra/docker-compose.yml up -d
docker-compose -f infra/docker-compose.yml ps
```

### Migraciones

```bash
alembic upgrade head     # Aplica todas las migraciones
alembic current          # Ver estado actual
alembic downgrade -1     # Revertir última migración
```

### Variables de entorno requeridas (`.env` en raíz)

```
DATABASE_URL=postgresql+psycopg2://admin:dev_password_local@localhost:5432/geodata_predik_clone
INEGI_DENUE_TOKEN=<token>
INEGI_BIE_API_TOKEN=<token>
JWT_SECRET_KEY=<clave-secreta>
REDIS_URL=redis://localhost:6379
```

### CORS

Acepta peticiones desde `http://localhost:5173` (Vite dev), `http://localhost:3000` y `http://127.0.0.1:5173`.

### Middleware

- `QueryLogMiddleware`: registra todas las peticiones en `core.query_log`
- `CORSMiddleware`: habilitado con credenciales y métodos/headers wildcard
- `check_rate_limit`: Redis — inyectado en endpoints de análisis y reporte
