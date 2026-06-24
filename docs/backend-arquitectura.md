# Backend — Arquitectura Técnica

**Proyecto:** predik-geo (clon SaaS de PREDIK GeoData Intelligence)
**Fecha:** 2026-06-24
**Alembic head:** `0005_add_cvegeo9_index`

---

## 1. Visión general

predik-geo es una plataforma de inteligencia geoespacial comercial para México. El backend expone una API REST sobre datos del INEGI (DENUE, MGN, Censo 2020, BIE) almacenados en PostgreSQL con extensiones PostGIS y H3.

### Stack

| Capa | Tecnología |
|------|-----------|
| API | FastAPI 0.x + Python 3.12 |
| Base de datos | PostgreSQL 16 + PostGIS 3.4 + H3 v4.2.2 |
| ORM | SQLAlchemy 2.x (síncrono) |
| Migraciones | Alembic |
| Cache/rate-limit | Redis |
| Auth | JWT (python-jose) + bcrypt |
| ETL geoespacial | pyshp, shapely, pyproj, geopandas |
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
│       └── 0005_add_cvegeo9_index.py
├── app/
│   ├── main.py              # FastAPI app, CORS, lifespan, scheduler
│   ├── db.py                # SessionLocal, Base
│   ├── auth.py              # JWT: create_access_token, create_refresh_token, decode_token
│   ├── deps.py              # get_db, get_current_user
│   ├── middleware.py        # QueryLogMiddleware
│   ├── rate_limit.py        # check_rate_limit
│   ├── scheduler.py         # APScheduler (start/stop)
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
│   │   └── cube.py
│   ├── connectors/
│   │   ├── base.py          # BaseConnector, GeoFeature
│   │   ├── registry.py
│   │   └── inegi/
│   │       ├── denue.py
│   │       └── bie.py
│   ├── etl/
│   │   ├── base.py
│   │   ├── denue.py         # DenueETL: load_raw(), aggregate_h3()
│   │   └── poblacion.py
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

La base de datos tiene cuatro esquemas con propósitos distintos:

| Esquema | Propósito |
|---------|-----------|
| `core` | Multi-tenancy: organizaciones, usuarios, credenciales, auditoría |
| `raw_data` | Datos brutos de fuentes externas (DENUE, MGN, Censo, BIE) |
| `cube` | Cubos pre-agregados en celdas H3 para visualización rápida |
| `analytics` | Resultados de análisis guardados por organización |

---

## 4. Migraciones Alembic

### 0001 — initial_schemas

Crea las extensiones PostgreSQL (`pgcrypto`, `postgis`, `h3`, `h3_postgis`) y los cuatro esquemas. Crea las siguientes tablas:

- `core.organizations`: organizaciones (multi-tenant), PK UUID, campo `plan` (starter/pro/enterprise)
- `core.users`: usuarios vinculados a organización, campo `role` (admin/analyst)
- `core.api_credentials`: credenciales de conectores cifradas por organización
- `core.query_log`: log de peticiones (endpoint, duración, status code)
- `raw_data.denue_establishments`: establecimientos DENUE con geometría POINT SRID 4326; índices GIST en `geom` y B-tree en `codigo_scian`
- `cube.commercial_density_h3`: cubo de densidad comercial por celda H3; índice GIST en `geom_hexagon`
- `analytics.zona_analysis_results`: resultados de análisis de zona (JSON + polígono); índice GIST en `polygon`

### 0002 — ageb_tables

Revises: `0001_initial_schemas`. Agrega tablas del Marco Geoestadístico y Censo 2020:

- `raw_data.ageb_geometries`: polígonos de AGEBs (MULTIPOLYGON SRID 4326), campos clave `cvegeo` (PK, hasta 16 chars), `clave_ent`, `clave_mun`, `cve_ageb`, `ambito` (Urbana/Rural); índices GIST en `geom` y B-tree en `clave_ent`
- `raw_data.ageb_demographics`: indicadores demográficos del Censo 2020 por AGEB; columnas estructuradas para población por género y grupos de edad, vivienda, educación y salud; columna `indicadores` JSON con todos los campos crudos del CSV
- `raw_data.manzana_vivienda`: inventario nacional de vivienda a nivel manzana (MULTIPOLYGON SRID 4326), cvegeo de 16 chars, campos de vivienda e infraestructura (agua, drenaje, luz); índices GIST en `geom` y B-tree en `cvegeo_ageb`

### 0003 — cube_population

Revises: `0002_ageb_tables`. Agrega:

- `cube.population_density_h3`: cubo de densidad poblacional por celda H3, columnas de población por género y grupos de edad, `densidad_hab_km2`; índices GIST en `geom_hexagon` y B-tree en `h3_resolution`

### 0004 — bie_indicadores

Revises: `0003_cube_population`. Agrega:

- `raw_data.bie_indicadores`: series de tiempo del Banco de Información Económica (INEGI); constraint único en `(indicador_id, area_clave, periodo)`; índices en `estado_clave`, `indicador_id` y `periodo_fecha`

### 0005 — add_cvegeo9_index

Revises: `0004_bie_indicadores`. Agrega columna `cvegeo_9 VARCHAR(9)` a `raw_data.ageb_geometries` y la puebla con `clave_ent(2) + clave_mun(3) + cve_ageb(4)`. Crea índice B-tree. Razón: el shapefile MGN almacena CVEGEO en formato de 9 o 13 chars; el Censo 2020 usa siempre 9 chars, por lo que este campo normaliza el JOIN entre tablas.

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
| cvegeo | VARCHAR(16) PK | 9–16 chars según formato MGN |
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
| con_agua / con_dren / con_luz | INTEGER | infraestructura |
| geom | MULTIPOLYGON SRID 4326 | índice GIST |
| indicadores | JSON | campos adicionales del Censo |
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

### 5.3 Esquema `cube`

**`cube.commercial_density_h3`**

| Columna | Tipo | Notas |
|---------|------|-------|
| h3_index | VARCHAR(20) PK | índice H3 hex string |
| h3_resolution | SMALLINT | resolución H3 (tipicamente 9) |
| entidad / municipio | VARCHAR | |
| total_establecimientos | INTEGER | |
| por_categoria | JSON | conteo por categoría SCIAN |
| top_categoria | VARCHAR(255) | |
| geom_centroid | POINT SRID 4326 | |
| geom_hexagon | POLYGON SRID 4326 | índice GIST |
| last_refreshed | TIMESTAMPTZ | |

**`cube.population_density_h3`**

| Columna | Tipo | Notas |
|---------|------|-------|
| h3_index | VARCHAR(20) PK | |
| h3_resolution | SMALLINT | |
| entidad / municipio | VARCHAR | |
| pobtot / pobmas / pobfem | INTEGER | |
| p_0a14 / p_15a64 / p_65ymas | INTEGER | |
| vivpar_hab | INTEGER | |
| densidad_hab_km2 | FLOAT | |
| geom_centroid | POINT SRID 4326 | |
| geom_hexagon | POLYGON SRID 4326 | índice GIST |
| last_refreshed | TIMESTAMPTZ | |

### 5.4 Esquema `analytics`

**`analytics.zona_analysis_results`**

| Columna | Tipo | Notas |
|---------|------|-------|
| id | UUID PK | |
| organization_id | UUID FK | |
| user_id | UUID FK | nullable |
| polygon | POLYGON SRID 4326 | polígono del área analizada; índice GIST |
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
| POST | `/zona/concentracion-comercial` | Analiza concentración comercial en un polígono GeoJSON; devuelve totales, categorías SCIAN, negocios ancla y celdas heatmap H3 |
| POST | `/zona/densidad-poblacional` | Analiza densidad poblacional en un polígono; devuelve datos Censo 2020 por AGEB intersectada |
| POST | `/zona/establecimientos` | Lista establecimientos individuales DENUE dentro de un polígono; permite filtro por `keyword` y `scian_prefix` |
| GET | `/zona/analisis/{analysis_id}` | Recupera un análisis de concentración comercial guardado por su UUID |

### 6.3 Análisis guardados — `/analisis`

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/analisis/` | Lista todos los análisis guardados de la organización |
| GET | `/analisis/{analysis_id}` | Obtiene un análisis guardado por UUID |
| GET | `/analisis/comparar?ids=uuid1,uuid2` | Compara 2 o más análisis en paralelo (resumen side-by-side) |
| DELETE | `/analisis/{analysis_id}` | Elimina un análisis guardado |

### 6.4 Reportes geoespaciales — `/reporte`

| Método | Ruta | Descripción |
|--------|------|-------------|
| POST | `/reporte/generar` | Genera reporte KMZ o Excel para un polígono con 1–8 capas de búsqueda; soporta clasificación por densidad, oportunidad o poder adquisitivo |
| POST | `/reporte/preview` | Preview del reporte en GeoJSON para visualización en mapa antes de generar el archivo |

Parámetros clave de `ReporteRequest`:
- `polygon`: GeoJSON Polygon del área
- `capas`: lista de `CapaBusqueda` (keyword, label, color, estado, icon, scian_prefix)
- `formato`: `kmz` o `excel`
- `clasificacion_hexagonos`: `densidad` | `oportunidad` | `poder_adquisitivo`
- `nivel_geografico`: `ageb` o `manzana`
- `ejecutar_etl`: `true` para consultar INEGI en tiempo real, `false` para usar datos en BD

### 6.5 Catálogo geográfico — `/catalogo`

No requiere autenticación.

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/catalogo/estados` | Lista los 32 estados con clave INEGI y abreviatura |
| GET | `/catalogo/municipios/{clave_estado}` | Municipios predefinidos de un estado |
| GET | `/catalogo/municipio-bbox/{clave_estado}/{clave_mun}` | Bounding box de un municipio consultado desde `ageb_geometries` |

### 6.6 BIE — Indicadores económicos — `/bie`

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/bie/indicadores` | Catálogo de indicadores BIE disponibles (ITAEE, desocupación, empleo formal) |
| GET | `/bie/estado/{clave_estado}` | Resumen económico de un estado (último valor de cada indicador) |
| GET | `/bie/estado/{clave_estado}/{indicador_key}` | Serie histórica de un indicador para un estado; parámetro `limit` (default 12, máx 60) |
| GET | `/bie/stats` | Estadísticas de cobertura de datos BIE en la BD |
| POST | `/bie/sync/{clave_estado}` | Dispara carga BIE en background para un estado |
| POST | `/bie/sync` | Dispara carga BIE en background para los 32 estados |

### 6.7 Administración — `/admin`

Requieren rol `admin`.

| Método | Ruta | Descripción |
|--------|------|-------------|
| GET | `/admin/bd-status` | Estado de población de tablas clave (registros y umbral mínimo) |
| GET | `/admin/conectores` | Lista conectores registrados y su estado |
| GET | `/admin/conectores/{nombre}/health` | Estado de salud de un conector específico |
| POST | `/admin/conectores/{nombre}/sync` | Dispara sincronización de un conector |
| POST | `/admin/etl/{source}/run` | Ejecuta un ETL específico (actualmente sólo `inegi_denue`) |
| POST | `/admin/etl/maestro/run` | Ejecuta el ETL maestro DENUE paginado para los estados indicados |

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
| Endpoint usado | `GET /BuscarEntidad/{keyword}/{estado}/{inicio}/{fin}/{token}` |
| Máximo por llamada | 2,500 registros |
| Token env var | `INEGI_DENUE_TOKEN` |

El conector normaliza la respuesta de la API al dataclass `GeoFeature` y extrae el código SCIAN desde las posiciones 5–10 del campo `CLEE`. Cuando el token no está configurado devuelve 3 features de demostración.

### 7.2 BIE (INEGI)

**Archivo:** `backend/app/connectors/inegi/bie.py`

| Campo | Valor |
|-------|-------|
| Clase | `BIEConnector` (hereda `BaseConnector`) |
| Nombre | `inegi_bie` |
| URL base | `https://www.inegi.org.mx/app/api/indicadores/desarrolladores/jsonxml` |
| Endpoint usado | `GET /INDICATOR/{ids}/es/{area}/false/BIE-BISE/2.0/{token}?type=json` |
| Área | `00` (nacional; los IDs de indicadores estatales son distintos por entidad) |
| Token env var | `INEGI_BIE_API_TOKEN` (mismo token que DENUE) |

**Indicadores configurados:**

| Key | ID BIE | Nombre | Frecuencia |
|-----|--------|--------|-----------|
| `itaee` | 452001 | Actividad Económica (ITAEE) | Mensual |
| `desocupacion` | 444612 | Tasa de Desocupación (ENOE) | Trimestral |
| `empleo_formal` | 935 | Trabajadores asegurados IMSS | Mensual |

Cuando el token no está configurado el servicio devuelve datos demo precargados para los 32 estados.

---

## 8. Scripts ETL

Todos los scripts se ejecutan desde el directorio raíz del repositorio.

### 8.1 `etl_maestro.py` — Orquestador principal

**Ruta:** `backend/scripts/etl_maestro.py`

Orquesta las tres fuentes principales de datos. Es el punto de entrada para poblar la BD desde cero.

```bash
# Cargar todo (MGN + Censo + DENUE)
python backend/scripts/etl_maestro.py --todo

# Solo DENUE (todos los estados)
python backend/scripts/etl_maestro.py --solo-denue

# DENUE para estados específicos
python backend/scripts/etl_maestro.py --solo-denue --estados 09,14,15

# Solo geometrías MGN
python backend/scripts/etl_maestro.py --solo-geo

# Solo Censo 2020
python backend/scripts/etl_maestro.py --solo-censo

# Filtrar por estados (cualquier combinación)
python backend/scripts/etl_maestro.py --todo --estados 09,14,15 --h3-res 9
```

La descarga DENUE itera sobre 20 sectores SCIAN (`comercio`, `restaurante`, `salud`, etc.) para cubrir ~95% de los establecimientos, ya que la API no soporta wildcard. Usa `ON CONFLICT DO UPDATE` por `clee` para resolver duplicados entre sectores.

### 8.2 `etl_mgn_maestro.py` — MGN + Censo 2020

**Ruta:** `backend/scripts/etl_mgn_maestro.py`

Script especializado para cargar el Marco Geoestadístico y demografía de AGEBs.

```bash
# Carga completa (MGN + Censo 2020)
python backend/scripts/etl_mgn_maestro.py

# Solo geometrías MGN
python backend/scripts/etl_mgn_maestro.py --solo-mgn

# Solo Censo 2020 (ya teniendo las geometrías)
python backend/scripts/etl_mgn_maestro.py --solo-censo

# Solo un estado (para pruebas)
python backend/scripts/etl_mgn_maestro.py --entidad 31
```

Requiere `data/mgn/mg_2025_integrado.zip` (ZIP nacional) o ZIPs por estado `01_aguascalientes.zip`...`32_zacatecas.zip`.

### 8.3 `load_marco_geoestadistico.py` — Carga de shapefiles MGN

**Ruta:** `backend/scripts/load_marco_geoestadistico.py`

Carga shapefiles de AGEBs urbanas del MGN 2025 en `raw_data.ageb_geometries`. Maneja reproyección de EPSG:6372 (LCC México ITRF2008) a EPSG:4326 (WGS84), múltiples encodings (UTF-8, latin-1, cp1252) y normaliza el campo `cvegeo_9`.

```bash
# Desde ZIP integrado nacional (recomendado)
python backend/scripts/load_marco_geoestadistico.py --zip data/mgn/mg_2025_integrado.zip

# Desde directorio con ZIPs por estado
python backend/scripts/load_marco_geoestadistico.py --zip-dir data/mgn/

# Desde shapefile ya extraído
python backend/scripts/load_marco_geoestadistico.py --shapefile data/mgn/00a.shp

# Desde directorio ya extraído (auto-descubre *a.shp)
python backend/scripts/load_marco_geoestadistico.py --dir data/mgn/

# Filtrar por entidad (con --zip o --shapefile)
python backend/scripts/load_marco_geoestadistico.py --zip data/mgn/mg_2025_integrado.zip --entidad 09
```

### 8.4 `load_censo_2020.py` — Carga de demografía Censo 2020

**Ruta:** `backend/scripts/load_censo_2020.py`

Carga CSVs `RESAGEBURB_<EE>_2020.CSV` del Censo de Población y Vivienda 2020 en `raw_data.ageb_demographics`. Sólo procesa filas donde `MZA == "000"` (totales de AGEB).

```bash
# Un solo estado
python backend/scripts/load_censo_2020.py --csv data/censo/RESAGEBURB_09_2020.CSV

# Directorio con múltiples archivos
python backend/scripts/load_censo_2020.py --dir data/censo/
```

### 8.5 `etl_manzana.py` — Datos de vivienda a nivel manzana

**Ruta:** `backend/scripts/etl_manzana.py`

Combina geometrías de manzanas del shapefile `*m.shp` del MGN 2025 con demografía del Censo 2020 (filas con `MZA != "000"`) y carga en `raw_data.manzana_vivienda`. Usa psycopg2 directamente para upserts masivos.

```bash
# Todos los estados disponibles
python backend/scripts/etl_manzana.py

# Un estado específico
python backend/scripts/etl_manzana.py --estado 14
```

Requiere los ZIPs de estado en `data/mgn/` con formato `{NN}_{nombre_estado}.zip` y los CSVs del Censo en `data/censo_2020/RESAGEBURB_{NN}CSV20.csv`.

### 8.6 `etl_bie.py` — Indicadores económicos BIE

**Ruta:** `backend/scripts/etl_bie.py`

Descarga series históricas completas de los indicadores BIE (ITAEE, desocupación, empleo formal IMSS) y las carga en `raw_data.bie_indicadores`. Requiere `INEGI_BIE_API_TOKEN` en `.env`.

```bash
# Todos los estados (serie histórica completa)
python backend/scripts/etl_bie.py

# Solo un estado
python backend/scripts/etl_bie.py --estado 14

# Ver datos sin insertar
python backend/scripts/etl_bie.py --dry-run
```

---

## 9. Estado actual de la base de datos

| Tabla | Registros | Tamaño | Cobertura |
|-------|-----------|--------|-----------|
| `raw_data.ageb_geometries` | 82,283 | 352 MB | 32 estados (completo) |
| `raw_data.ageb_demographics` | 66,750 | 137 MB | 32 estados (completo) |
| `raw_data.denue_establishments` | 1,407,499 | ~1.3 GB | 15/32 estados (01–15) |
| `raw_data.manzana_vivienda` | 534,577 | — | 9/32 estados (01–09) |
| `raw_data.bie_indicadores` | 38,752 | — | ITAEE, desocupación, empleo formal |
| `cube.commercial_density_h3` | 62,249 hexágonos | — | Resolución H3-9 |
| `cube.population_density_h3` | 0 | — | Sin poblar (ETL pendiente) |
| `analytics.zona_analysis_results` | 7 | — | Análisis guardados |

---

## 10. ETLs pendientes

### 10.1 DENUE — estados 16–32

Faltan 17 estados. Ejecutar:

```bash
python backend/scripts/etl_maestro.py --solo-denue --estados 16,17,18,19,20,21,22,23,24,25,26,27,28,29,30,31,32
```

Tiempo estimado: 6–10 horas. El script es idempotente (ON CONFLICT DO UPDATE por `clee`).

### 10.2 Manzana — estados 10–32

Faltan 23 estados. Ejecutar por estado para controlar progreso:

```bash
python backend/scripts/etl_manzana.py --estado 10
python backend/scripts/etl_manzana.py --estado 11
# ... continuar hasta estado 32
```

Requiere que los ZIPs de MGN por estado estén en `data/mgn/` y los CSVs del Censo en `data/censo_2020/`.

### 10.3 `cube.population_density_h3` — cubo de densidad poblacional

La tabla está vacía. El ETL que agrega `ageb_demographics` → celdas H3 no ha sido ejecutado. El módulo `backend/app/etl/poblacion.py` contiene la lógica de agregación. Ejecutar vía API:

```bash
# Disparar desde endpoint admin (requiere rol admin)
POST /api/v1/admin/etl/inegi_denue/run  # Solo disponible para DENUE actualmente
```

El ETL de población requiere implementación del endpoint específico o ejecución directa del script cuando esté disponible.

---

## 11. Tokens y servicios externos

| Variable de entorno | Servicio | Notas |
|--------------------|----------|-------|
| `INEGI_DENUE_TOKEN` | API DENUE INEGI | Configurado. Mismo token que BIE |
| `INEGI_BIE_API_TOKEN` | API BIE INEGI | Configurado. Mismo token que DENUE |
| `MAPTILER_KEY` | MapTiler (frontend) | Para tiles de mapa base |

Obtener token INEGI (gratuito): `https://www.inegi.org.mx/servicios/api_indicadores.html`

---

## 12. Configuración de la aplicación

### Arranque

```bash
# Activar entorno virtual
cd backend
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Migraciones

```bash
# Aplicar todas las migraciones
alembic upgrade head

# Ver estado actual
alembic current

# Revertir última migración
alembic downgrade -1
```

### Variables de entorno requeridas (`.env` en raíz)

```
DATABASE_URL=postgresql+psycopg2://user:password@localhost:5432/predikgeo
INEGI_DENUE_TOKEN=<token>
INEGI_BIE_API_TOKEN=<token>
JWT_SECRET_KEY=<clave-secreta>
REDIS_URL=redis://localhost:6379
```

### CORS

El servidor acepta peticiones desde `http://localhost:5173` (Vite dev), `http://localhost:3000` y `http://127.0.0.1:5173`.

### Middleware

- `QueryLogMiddleware`: registra todas las peticiones en `core.query_log`
- `CORSMiddleware`: habilitado con credenciales y métodos/headers wildcard
- `check_rate_limit`: dependencia inyectada en endpoints de análisis y reporte (implementado sobre Redis)
