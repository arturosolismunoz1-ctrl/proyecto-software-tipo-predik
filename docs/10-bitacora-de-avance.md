# Bitácora de Avance del Proyecto

Registro cronológico de hitos completados, para tener trazabilidad de qué se ha hecho y qué falta.

## 2026-06-20

### ✅ Documentación técnica completa
- Arquitectura del sistema, flujos de negocio, especificación de APIs, modelo de base de datos, casos de uso, ADRs, estrategia de ambientes, logging y data lake/mart.
- Ubicación: `/docs`

### ✅ Control de versiones configurado
- Cuenta de GitHub creada: `arturosolismunoz1-ctrl`
- Repositorio privado creado: `proyecto-software-tipo-predik`
- Rama `main` (producción) y `develop` (trabajo diario) creadas
- Ruleset de protección sobre `main` configurado (`Require a pull request before merging`, `Block force pushes`) — queda activo pero no forzado hasta upgrade a GitHub Team (limitación del plan gratuito en repos privados)

### ✅ Ambiente de desarrollo local funcionando
- Docker Desktop instalado en Windows (requirió instalar WSL2 + Ubuntu como prerequisito)
- `infra/docker-compose.yml` creado con dos servicios:
  - `db`: PostgreSQL 16 + PostGIS 3.4 (puerto 5432)
  - `redis`: Redis 7 alpine (puerto 6379)
- Contenedores levantados y verificados: ambos en estado `Up` / `healthy`
- Rama de trabajo `feature/docker-compose-dev` creada localmente, con commit:
  `feat: agrega docker-compose con PostgreSQL+PostGIS y Redis para ambiente de desarrollo`
- **Pendiente de confirmar:** que el `git push` de esa rama haya llegado correctamente a GitHub (la rama no aparecía aún en el listado remoto — último paso en validación).

## 2026-06-22

### ✅ Implementación inicial del backend FastAPI commiteada a git
- Modelos SQLAlchemy completos: `core`, `raw_data`, `cube`, `analytics`
- Primera migración Alembic: esquemas + PostGIS + extensión H3
- `BaseConnector` + `GeoFeature` (interfaz abstracta de conectores)
- `DenueConnector` con fallback a datos demo (sin integración real a INEGI aún)
- Registro centralizado de conectores (`registry.py`)
- Endpoints implementados:
  - `POST /api/v1/zona/concentracion-comercial`
  - `GET /DELETE /api/v1/analisis` y `/api/v1/analisis/{id}`
  - `GET /api/v1/admin/conectores` con health check y sync
- Suite inicial de tests (`backend/tests/`)

### ✅ Reorganización y limpieza del repositorio
- Proyecto movido a carpeta limpia `predik-geo/` en el Desktop (eliminada estructura anidada incorrecta)
- `.gitkeep` eliminados de todos los directorios que ya contienen código
- `Makefile` creado en el root con comandos: `make dev`, `make run`, `make test`, `make migrate`, `make db-shell`, etc.
- `README.md` actualizado con instrucciones completas de setup y uso
- `PROMPT_CONTINUIDAD_VSCODE.md` actualizado con estado actual del código
- `.gitignore` mejorado (cobertura, htmlcov, volúmenes Docker)

## 2026-06-22 (sesión 2)

### ✅ Stoppers de infraestructura resueltos

**STOPPER 1 — Extensión H3 no instalada en Docker**
- La imagen `postgis/postgis:16-3.4` no incluye H3 por defecto.
- Solución: `infra/Dockerfile.db` que extiende la imagen base e instala `postgresql-16-h3` vía apt-get PGDG.
- `infra/docker-compose.yml` actualizado para usar `build:` en lugar de `image:`.
- H3 v4.2.2 verificado activo con `SELECT extname FROM pg_extension WHERE extname LIKE 'h3%'`.

**STOPPER 5 — Tipos de geometría incorrectos en la migración**
- La migración usaba `sa.types.UserDefinedType()` para columnas PostGIS, lo que causa `AttributeError` al correr.
- Solución: reemplazado con `geoalchemy2.Geometry` con tipo y SRID explícitos en las 3 columnas afectadas.
- `CREATE EXTENSION` actualizado con `CASCADE` para resolver dependencia de `postgis_raster`.

**STOPPER 3 — Sin organización ni usuario en DB**
- Sin seed, toda inserción en `analytics.zona_analysis_results` fallaba por violación de FK.
- Solución: `backend/scripts/seed_dev.py` — idempotente, crea `Demo Org` y usuario `admin@predik.local`.
- Comando `make seed` agregado al Makefile.
- Credenciales de dev: `admin@predik.local` / `dev_password_admin`.

### ✅ Migración Alembic ejecutada correctamente por primera vez
- 7 tablas creadas: `core.organizations`, `core.users`, `core.api_credentials`, `core.query_log`, `raw_data.denue_establishments`, `cube.commercial_density_h3`, `analytics.zona_analysis_results`.
- Extensiones activas: PostGIS 3.4.3, H3 4.2.2, H3-PostGIS 4.2.2.

### ✅ Autenticación JWT implementada y testeada
- `backend/app/auth.py` — `create_access_token`, `create_refresh_token`, `decode_token` usando `python-jose` (HS256).
  - Access token: 30 min. Refresh token: 7 días. Payload incluye `user_id`, `org_id`, `role`.
- `backend/app/deps.py` — dependencias compartidas `get_db` y `get_current_user` (HTTPBearer).
- `backend/app/api/v1/auth.py` — `POST /api/v1/auth/login` y `POST /api/v1/auth/refresh`.
  - Login valida email + contraseña bcrypt. Refresh valida tipo de token antes de emitir nuevo access.
- Endpoints protegidos: `zona`, `analisis` (todos los endpoints de negocio requieren JWT).
- `organization_id` ya no es hardcodeado — se extrae del token JWT en cada request.
- `analisis.py` corregido para importar `get_db` de `app.deps` (no de `zona.py`).

### ✅ Dependencias actualizadas
- `bcrypt>=4.0.0` — hashing de contraseñas (passlib descartado por incompatibilidad con bcrypt 5.x).
- `python-jose[cryptography]>=3.3.0` — JWT.
- `pydantic[email]>=2.7.0` — validación de email en modelos.

### ✅ Suite de tests completa — 19/19 verde
- `test_auth.py` (9 tests): login exitoso, password incorrecta, email inexistente, refresh válido, refresh con access token, token inválido, endpoints protegidos sin/con token.
- `test_zona_api.py` y `test_zona_saved_results.py` actualizados a `app.dependency_overrides` (patrón correcto para FastAPI — `monkeypatch` no alcanza dependencias cacheadas por `Depends`).
- Todos los tests de endpoints de negocio ahora incluyen override de `get_current_user`.

### Commit de referencia
- `47f4e62` — `feat: agrega autenticación JWT y corrige stoppers de infraestructura`

---

## 2026-06-23

### ✅ Tablas AGEB/Censo 2020 y scripts de carga geoespacial

- **Migración `0002_ageb_tables`** aplicada: 3 tablas nuevas en `raw_data`:
  - `ageb_geometries` — polígonos del Marco Geoestadístico Nacional (MGN) con índice GIST
  - `ageb_demographics` — indicadores del Censo 2020 por AGEB (población, vivienda, salud, educación)
  - `manzana_vivienda` — geometrías e indicadores a nivel manzana con índice GIST
- **`backend/scripts/load_marco_geoestadistico.py`** — carga shapefiles del MGN hacia `ageb_geometries`; resolución automática de campos entre versiones del MGN, upsert por `cvegeo`, filtro opcional por entidad.
- **`backend/scripts/load_censo_2020.py`** — carga CSVs del Censo 2020 hacia `ageb_demographics`; agrupa columnas de edad crudas en grupos `p_0a14/p_15a64/p_65ymas`, soporte para un archivo o directorio completo, modo `--manzanas`.
- **`pyshp>=3.0` y `shapely>=2.0`** agregados a `requirements.txt`.
- **44/44 tests verdes** tras el commit.

### Commit de referencia
- `7d2246e` — `feat: agrega tablas AGEB/Censo 2020 y scripts de carga geoespacial`

---

### ✅ Endpoint densidad poblacional

- **`POST /api/v1/zona/densidad-poblacional`** — recibe un GeoJSON Polygon, hace JOIN PostGIS entre `ageb_geometries` y `ageb_demographics`, calcula:
  - Población total, por género (masculino/femenino), por grupo de edad (0-14, 15-64, 65+)
  - Densidad hab/km², viviendas habitadas, promedio de ocupantes
  - Detalle por AGEB (cvegeo, área, densidad, geometría GeoJSON)
- Guarda resultado en `analytics.zona_analysis_results` con `analysis_type="densidad_poblacional"`.
- Protegido con JWT; devuelve 404 con código `ZONA_SIN_DATOS_DEMOGRAFICOS` si no hay AGEBs en el polígono.
- 5 tests nuevos. **Total: 49/49 verdes.**

### Commit de referencia
- `b670e41` — `feat: implementa endpoint POST /api/v1/zona/densidad-poblacional`

---

## 2026-06-23 (sesión 3 — ETL real, reportes genéricos, datos INEGI completos)

### ✅ ETL DENUE real — 322 papelerías Ecatepec verificadas

- **`backend/app/connectors/inegi/denue.py`** — corregido; eliminado endpoint `BuscarAreaActividadEntidad` (devuelve 404 en API real). La función `fetch()` ahora usa `BuscarEntidad` con keyword real.
- **`backend/app/main.py`** — agregado `load_dotenv()` para que el proceso servidor cargue el token INEGI desde `.env`.
- **Quirk descubierto:** keyword `"."` como wildcard se normaliza a `/` por todos los clientes HTTP Python (RFC). Solución: iterar sobre lista `SECTORES_DENUE` (20 categorías SCIAN).
- **Quirk descubierto:** keyword `"mcdonald"` causa abort de conexión en API INEGI. Usar `"mc donalds"` (con espacio).
- Prueba funcional exitosa: 322 papelerías en Ecatepec, 265 celdas H3 con gradiente de color.

### ✅ Endpoint /zona/establecimientos

- **`POST /api/v1/zona/establecimientos`** — devuelve puntos DENUE individuales dentro de un polígono filtrados por keyword. Usado por scripts de generación KMZ.
- Modelo `CeldaHeatmap` actualizado con campo `cantidad: int`.

### ✅ Reporte genérico multicapa

- **`backend/app/services/reporte.py`** (nuevo) — servicio completo de generación de reportes:
  - `run_etl_capas()` — corre ETL DENUE por cada capa
  - `query_puntos_capa()` — consulta establecimientos por keyword en polígono
  - `query_agebs_en_poligono()` — consulta AGEBs + demographics + conteo DENUE por AGEB (ST_Within)
  - `clasificar_por_densidad()` — gradiente verde→amarillo→rojo según densidad
  - `clasificar_por_oportunidad()` — ALTA/MEDIA_ALTA/MEDIA/BAJA/SATURADA
  - `generar_kmz()` — bytes KMZ con AGEBs (si existen) o H3 (fallback) + puntos por capa
  - `generar_excel()` — bytes Excel con resumen + hoja por capa
  - `generar_reporte()` — orquestador principal; detecta automáticamente si usar AGEBs o H3
- **`POST /api/v1/reporte/generar`** — endpoint genérico que acepta: polygon + N capas (keyword, label, color, estado) + formato (kmz/excel) + clasificacion_hexagonos (densidad/oportunidad).

### ✅ Catálogo estados y municipios

- **`GET /api/v1/catalogo/estados`** — 32 estados con clave INEGI, nombre, abreviatura.
- **`GET /api/v1/catalogo/municipios/{clave}`** — municipios de un estado (catálogo estático de los más consultados).

### ✅ ETL maestro + descarga masiva de datos

- **`backend/scripts/etl_maestro.py`** — ETL maestro que orquesta:
  1. Marco Geoestadístico Nacional (shapefiles MGN)
  2. Censo 2020 AGEB (CSVs)
  3. DENUE via API (paginado, sector por sector)
  - Itera 20 sectores SCIAN × 32 estados; deduplicación por CLEE via `ON CONFLICT DO UPDATE`.
- **`backend/scripts/descargar_censo_2020.py`** — descarga automática de los 32 estados desde URL directa INEGI. **Ejecutado exitosamente: 32/32 estados en 4.7 minutos, 128,626 AGEBs cargadas.**
- **`backend/scripts/load_censo_2020.py`** — corregido para: usar `POB0_14`/`POB15_64`/`POB65_MAS` (columnas reales del archivo), filtrar totales estatales/municipales (AGEB="0000", MUN="000").
- **`backend/scripts/load_marco_geoestadistico.py`** — agregada función `load_directory()` con auto-discovery de shapefiles `*a.shp` en cualquier estructura de carpetas MGN.

### ✅ Endpoint de estado de la base de datos

- **`GET /api/v1/admin/bd-status`** — muestra conteo de registros y estado (vacia/parcial/poblada) de las 4 tablas clave. Indica si el sistema está listo para generar reportes.

### Estado de datos al cierre de sesión:
| Tabla | Registros |
|---|---|
| `raw_data.ageb_demographics` | **128,626** ✅ |
| `raw_data.ageb_geometries` | 0 ⏳ (MGN 2025 descargándose ~2.7 GB) |
| `raw_data.denue_establishments` | ~360 (ETL maestro iniciado, en proceso) |
| `cube.commercial_density_h3` | ~294 |

---

---

## 2026-06-23 (sesión 4 — Frontend MVP + ejercicio Mérida)

### ✅ Ejercicio Mérida, Yucatán completado

- Script `backend/scripts/prueba_merida_cadenas.py` — ejecuta ETL + reporte completo vía API
- KMZ generado en `resultados/merida_cadenas.kmz`:
  - **14 Little Caesar's** (estrella amarilla)
  - **1 Dunkin'** (estrella naranja)
  - **15 Domino's Pizza** (marcador rojo)
  - **28 hexágonos H3** (fallback — AGEBs pendientes carga MGN)
- BD al momento del ejercicio: 528,808 establecimientos DENUE | 61,322 AGEBs demográficas

### ✅ Clasificación por poder adquisitivo implementada

- `clasificar_por_poder_adquisitivo()` en `backend/app/services/reporte.py`
  - `graproes >= 12` → PREMIUM (verde oscuro)
  - `graproes >= 9` → MEDIO-ALTO (verde)
  - `graproes >= 6` → MEDIO (ámbar)
  - `graproes < 6` → BAJO (gris)
- Nuevo campo `icon: "circle" | "star"` en `CapaBusqueda` (API + servicio)
- `clasificacion_hexagonos` ahora acepta `"poder_adquisitivo"` además de `"densidad"` y `"oportunidad"`
- `_kml_estilo_punto()` enruta a `_COLOR_ICONO_STAR_URL` cuando `icon="star"` (escala 1.1x)

### ✅ Frontend MVP — React + Vite + Leaflet

Archivos creados en `frontend/`:
- `package.json` — React 18, Vite 5, react-leaflet 4, leaflet-draw, Zustand, Tailwind
- `vite.config.ts` — proxy `/api` → `localhost:8000`
- `src/main.tsx`, `src/App.tsx` — entry point + React Router
- `src/pages/LoginPage.tsx` — login con branding dividido (como PREDIK)
- `src/pages/MapPage.tsx` — mapa Leaflet + sidebar de 3 pasos
- `src/api/client.ts` — fetch con JWT, `apiLogin`, `apiEstados`, `apiGenerarReporte`, `apiBdStatus`
- `src/store/useAuthStore.ts` — Zustand, persiste en localStorage
- `src/types.ts` — TypeScript types compartidos
- `src/index.css` — Tailwind + Leaflet + leaflet-draw CSS

**Features del frontend:**
- Login con doble panel (branding izquierda / form derecha) — estilo enterprise
- Mapa CartoDB Positron (mapa limpio tipo geomarketing profesional)
- Herramienta de dibujo: polígono y rectángulo via leaflet-draw
- Panel sidebar 3 pasos: 1) Área 2) Capas 3) Opciones
- Capas configurables: keyword, etiqueta, color (8 colores), icono (punto/estrella), estado (32 estados)
- Clasificación: densidad / oportunidad / poder adquisitivo
- Formato: KMZ o Excel
- Badges de estado de BD (DENUE y Censo)
- Descarga automática del archivo al generar reporte
- Spinner durante generación (3-8 min)

**URL:** http://localhost:5173 (backend en :8000, proxy configurado)

### ✅ CORS habilitado en backend

- `CORSMiddleware` agregado en `backend/app/main.py`
- Orígenes permitidos: `localhost:5173`, `localhost:3000`, `127.0.0.1:5173`

---

---

## 2026-06-23 (sesión 5 — MGN 2025 completo, mapa interactivo, KPIs, Admin)

### ✅ MGN 2025 descargado — 32 ZIPs de estados + ZIP integrado nacional

- Los 32 ZIPs (`01_aguascalientes.zip` … `32_zacatecas.zip`) + `mg_2025_integrado.zip` (245 MB) movidos a `data/mgn/`.
- El ZIP integrado contiene `00a.shp` — AGEBs urbanas nacionales (todos los estados en un solo shapefile).
- `data/censo_2020/` ya tiene todos los 32 CSVs demográficos (`RESAGEBURB_01CSV20.csv` … `RESAGEBURB_32CSV20.csv`).

### ✅ load_marco_geoestadistico.py — soporte nativo de ZIPs

- Nueva función `load_from_zip(zip_path)` — extrae el shapefile de AGEBs a un directorio temporal, carga, limpia.
- Nueva función `load_all_zips(directorio)` — procesa todos los ZIPs estado por estado en orden (01→32).
- Auto-detección de encoding desde `.cpg`; fallback a `utf-8 → latin-1 → cp1252`.
- Nuevo flag `--zip` y `--zip-dir` en CLI.

### ✅ etl_mgn_maestro.py — orquestador completo MGN + Censo 2020

Archivo: `backend/scripts/etl_mgn_maestro.py`

Pasos que ejecuta:
1. **Geometrías MGN** — extrae `00a.shp` del ZIP integrado → carga todos los AGEBs de 32 estados
2. **Demografía Censo 2020** — lee todos los CSVs de `data/censo_2020/` → carga `ageb_demographics`
3. **Índices PostGIS** — `GIST(geom)` en `ageb_geometries`, índice en `ageb_demographics(cvegeo)`
4. Reporte final con totales y count de AGEBs con geometría + demografía disponibles

Uso:
```bash
# Carga completa (MGN + Censo) — puede tardar 15-45 min según hardware
python backend/scripts/etl_mgn_maestro.py

# Solo geometrías (si ya tienes demografía)
python backend/scripts/etl_mgn_maestro.py --solo-mgn

# Solo demografía (si ya tienes geometrías)
python backend/scripts/etl_mgn_maestro.py --solo-censo

# Solo un estado (para pruebas rápidas)
python backend/scripts/etl_mgn_maestro.py --entidad 31
```

### ✅ Endpoint POST /reporte/preview — GeoJSON para visualización en mapa

- `backend/app/services/reporte.py` — nueva función `preview_reporte()`:
  - Misma lógica que `generar_reporte()` pero devuelve `dict` con GeoJSON en lugar de bytes KMZ/Excel
  - Convierte colores KML (AABBGGRR) a hex CSS (#RRGGBB) con `_kml_to_hex()`
  - Construye features GeoJSON para AGEBs (usa campo `geom`) y H3 (calcula boundary vía `h3.cell_to_boundary`)
  - Incluye `resumen` con KPIs: total establecimientos, total zonas, población alcanzada, zonas premium
- `backend/app/api/v1/reporte.py` — endpoint `POST /api/v1/reporte/preview`
  - Mismo schema `ReporteRequest` que `/generar`
  - Devuelve JSON: `{zonas: GeoJSONFeature[], capas: CapaPreview[], resumen: KPIs}`

### ✅ Frontend — resultados en el mapa

**Nuevo componente `frontend/src/components/ResultsOverlay.tsx`:**
- Hook `useMap()` + `useEffect` para gestionar capas Leaflet
- Polígonos de zonas coloreados con `L.geoJSON()` — opacidad proporcional a intensidad
- Puntos de establecimientos con `L.circleMarker()` — color por capa, radio mayor para estrellas
- Popup al click con nombre, AGEB/H3, población, escolaridad
- `map.fitBounds()` automático al primer resultado

### ✅ Frontend — Panel KPIs deslizable

**Nuevo componente `frontend/src/components/KPIPanel.tsx`:**
- Panel derecho 320px que aparece/desaparece con transición CSS
- KPI cards: total establecimientos, zonas analizadas, población alcanzada, zonas premium
- Barra de progreso por capa (cantidad relativa al máximo)
- Distribución por nivel (PREMIUM/MEDIO_ALTO/etc.) con badges de colores PREDIK
- Top 5 zonas por concentración de establecimientos

### ✅ Frontend — Panel Admin

**Nuevo componente `frontend/src/components/AdminPanel.tsx`:**
- Modal centrado con estado de BD (ageb_geometries, ageb_demographics, denue_total)
- Indicadores de salud: verde (>50k), amarillo (parcial), rojo (vacío)
- Comandos ETL copiables para correr desde terminal
- Botón Admin en header de MapPage

### ✅ MapPage.tsx — flujo rediseñado: Preview → Analizar → Descargar

Nuevo flujo al hacer clic en "Analizar y Descargar":
1. `POST /reporte/preview` con `ejecutar_etl: true` — corre ETL, devuelve GeoJSON
2. Los resultados aparecen en el mapa inmediatamente (zonas coloreadas + puntos)
3. Panel KPIs se abre automáticamente a la derecha
4. `POST /reporte/generar` con `ejecutar_etl: false` — genera archivo sin re-correr ETL
5. El archivo se descarga automáticamente al navegador

### ✅ Variables de entorno para producción documentadas

- `frontend/.env.example` — incluye `VITE_API_URL` para backend en producción
- `.env.example` — sección `Cloud/Producción` con ejemplos de `DATABASE_URL` en la nube
- `frontend/src/api/client.ts` — `BASE` usa `VITE_API_URL ?? ''` para ser agnóstico al ambiente

### Estado de datos al cierre de sesión 5:
| Tabla | Registros | Estado |
|---|---|---|
| `raw_data.ageb_demographics` | 128,626 | ✅ 32 estados |
| `raw_data.ageb_geometries` | 0 | ⏳ ETL pendiente — correr `etl_mgn_maestro.py` |
| `raw_data.denue_establishments` | ~528,808 | ✅ Parcial |
| `cube.commercial_density_h3` | ~294 | ✅ Del ejercicio Mérida |

### Próximo paso inmediato — ejecutar ETL MGN
```bash
# En terminal con servidor apagado (consume más RAM):
cd C:\Users\Arturo Solis Munoz\Desktop\predik-geo
python backend/scripts/etl_mgn_maestro.py
# Cuando termine (15-45 min), levantar servidor:
uvicorn backend.app.main:app --reload
```

---

## 2026-06-23 (sesión 6 — ETL completo MGN + Censo 2020; bloqueo JOIN activo)

### ✅ ETL Fase 1 — AGEBs Geometrías MGN 2025: COMPLETO

- `python backend/scripts/etl_mgn_maestro.py --solo-mgn`
- Fuente: `data/mgn/mg_2025_integrado.zip` → extrae `00a.shp` (nacional)
- **82,283 AGEBs urbanas** cargadas en `raw_data.ageb_geometries`
- Bug resuelto en Windows: `pyshp.Reader` mantenía handles de archivo abiertos al limpiar `TemporaryDirectory`. Fix: `reader.close()` explícito en bloque `finally` + `ignore_cleanup_errors=True`.
- Tiempo de carga: ~18 min en hardware local

### ✅ ETL Fase 2 — Demografía Censo 2020: cargado (bloqueo JOIN pendiente)

**3 bugs corregidos en `etl_mgn_maestro.py`:**

1. **CVEGEO 13→9 chars** — El ETL construía `ent+mun+loc+ageb` (13 chars) pero el shapefile MGN 2025 usa `ent+mun+ageb` (9 chars) en algunos registros. Corregido: `cvegeo = ent + mun + ageb`.

2. **ON CONFLICT duplicado dentro del mismo batch** — Cuando múltiples localidades comparten el mismo `ent+mun+ageb`, PostgreSQL fallaba con `CardinalityViolation`. Fix: acumular todas las filas del CSV en un `dict` indexado por cvegeo (agregando enteros con suma, flotantes con promedio ponderado por población) antes de hacer el INSERT. Eliminado el batch de 1,000 filas durante lectura; ahora se hace después sobre el dict ya deduplicado.

3. **UTF-8 BOM en cabeceras CSV** — Los CSVs de INEGI tienen `﻿` (BOM) al inicio, lo que hacía que la primera columna se llamara `ï»¿ENTIDAD` en lugar de `ENTIDAD`. `row.get("ENTIDAD")` devolvía `None` → `ent = "00"` → CVEGEOs inválidos para 31 de 32 estados. Fix: `encoding="utf-8-sig"` como primera opción en el bucle de encodings (strip automático de BOM).

**Resultado:** 66,750 AGEBs únicas en `raw_data.ageb_demographics`.

### ⚠️ BLOQUEO ACTIVO — JOIN geometría + demografía = 267 matches (esperado ~50,000)

**Diagnóstico:**
- `ageb_geometries` mezcla dos formatos de CVEGEO:
  - 9 chars: `140701467` (`ent+mun+ageb`) — 17,475 registros
  - 13 chars: `050300001522A` (`ent+mun+loc+ageb`) — 64,808 registros
- `ageb_demographics` usa solo 9 chars (correcto): `010010127` — 66,750 registros
- El JOIN solo puede hacer match con los 17,475 de 9 chars, y de esos solo 267 coinciden
- Raíz probable: el shapefile MGN 2025 usa CVEGEO = `ent+mun+loc+ageb` (13 chars) como estándar, y solo algunos registros tienen 9 chars. La demografía usa `ent+mun+ageb` (9 chars) sin localidad. El puente entre ambos formatos no está implementado.

**Próximo diagnóstico (siguiente sesión):**
```sql
-- Ver estructura del CVEGEO en geometrías (desglosar campos individuales)
SELECT cvegeo, clave_ent, clave_mun, cve_loc, cve_ageb
FROM raw_data.ageb_geometries
WHERE LENGTH(cvegeo) = 13
LIMIT 5;
-- Derivar cvegeo_9 = clave_ent + clave_mun + cve_ageb y hacer JOIN con demographics
```
El fix probablemente es: agregar columna `cvegeo_9` en `ageb_geometries` = `ent+mun+ageb` y hacer el JOIN por esa columna.

### Estado de datos al cierre de sesión 6:
| Tabla | Registros | Estado |
|---|---|---|
| `raw_data.ageb_geometries` | **82,283** | ✅ Cargado (mezcla 9+13 chars en CVEGEO) |
| `raw_data.ageb_demographics` | **66,750** | ✅ Cargado (9 chars, formato correcto) |
| `raw_data.denue_establishments` | ~528,808 | ✅ Parcial |
| JOIN geometría + demografía | **267** | ❌ Bloqueo — esperado ~50,000 |

---

## 2026-06-23 (sesión 7 — Frontend: contexto económico BIE + visibilidad de capas)

### ✅ Widget de contexto económico BIE integrado al sidebar

**Nuevo componente `frontend/src/components/EconomicContextWidget.tsx`:**
- Aparece automáticamente en el Paso 1 cuando el usuario selecciona un estado
- Consume `GET /api/v1/bie/estado/{clave}` — indicadores macroeconómicos INEGI BIE
- Muestra 4 KPIs en grid 2×2: Crecimiento económico (ITAEE), Desocupación, Empleo formal, PEA
- Colores semafóricos: verde (bueno) / ámbar (moderado) / rojo (crítico)
- Badge `Demo` cuando los datos son simulados; badge `BIE INEGI` cuando son reales
- Colapsable con animación; tooltip con interpretación al hacer hover sobre cada tile
- Fuente de datos indicada al pie: "Fuente: INEGI BIE"

**Integración en `MapPage.tsx`:** aparece entre los dropdowns de municipio y el divisor "o dibuja en el mapa".

### ✅ Nuevos tipos BIE en `api/client.ts`

- Interfaces `BieIndicadorValor` y `BieResumen` con tipos correctos para la respuesta del backend
- Función `apiBieResumen(claveEstado)` que consume el endpoint `/bie/estado/{clave}`

### ✅ Toggles de visibilidad de capas en el mapa

**`frontend/src/components/KPIPanel.tsx`:**
- Ícono ojo (visible/oculto) por cada capa en la sección "Establecimientos por capa"
- Al ocultar una capa: barra de progreso en gris, opacidad 40%, marcadores desaparecen del mapa
- Props nuevas: `visibleCapas?: Record<string, boolean>` y `onToggleCapa?: (keyword) => void`

**`frontend/src/components/ResultsOverlay.tsx`:**
- Nueva prop `visibleCapas?: Record<string, boolean>`
- Aplica filtro `if (visibleCapas && visibleCapas[capa.keyword] === false) return` antes de renderizar markers
- `visibleCapas` incluido en el `useEffect` dependency array para re-renderizar al togglear

**`frontend/src/pages/MapPage.tsx`:**
- Estado `visibleCapas: Record<string, boolean>` — inicializado a `{keyword: true}` por cada capa cuando llegan resultados del preview
- Handler `toggleCapa(keyword)` con `useCallback`
- Props `visibleCapas` y `onToggleCapa` pasadas a `KPIPanel`; `visibleCapas` a `ResultsOverlay`

---

## 2026-06-23 (sesión 8 — Fix bloqueo JOIN AGEB geometrías + demografía)

### ✅ Diagnóstico definitivo del bloqueo JOIN

**Raíz del problema:** La columna `cvegeo_9` existe en el modelo SQLAlchemy (`raw_data.py`) pero **no existe en la base de datos real** — nunca fue incluida en ninguna migración Alembic. Adicionalmente, el script de carga nunca calculaba ni guardaba el valor.

Consecuencia:
- `query_agebs_en_poligono()` falla silenciosamente (columna inexistente → excepción capturada)
- El sistema cae a hexágonos H3 como fallback — nunca usa AGEBs reales

### ✅ Fix implementado — 3 archivos modificados

**1. Nueva migración `0005_add_cvegeo9_index.py`:**
- `ALTER TABLE ageb_geometries ADD COLUMN cvegeo_9 VARCHAR(9)`
- `UPDATE` que puebla la columna para los 82,283 registros ya cargados:
  `cvegeo_9 = LPAD(clave_ent,2,'0') || LPAD(clave_mun,3,'0') || LPAD(cve_ageb,4,'0')`
- `CREATE INDEX idx_ageb_cvegeo9` para acelerar el JOIN

**2. `backend/scripts/load_marco_geoestadistico.py`:**
- Calcula `cvegeo_9` en cada registro antes del INSERT
- Lo incluye en el dict del batch y en el `on_conflict_do_update`

**3. Ningún cambio necesario en `reporte.py`:** el JOIN ya estaba correcto:
  `.outerjoin(AgebDemographics, AgebGeometry.cvegeo_9 == AgebDemographics.cvegeo)`

### ⚙️ Comando para aplicar el fix

```bash
cd C:\Users\Arturo Solis Munoz\Desktop\predik-geo
alembic -c backend/alembic.ini upgrade head
```

Esto agrega la columna y puebla los 82,283 registros en segundos. No requiere re-correr el ETL.

### ✅ Revisión de seguridad y riesgos — 4 problemas encontrados y 3 corregidos

**Bug 1 — CRÍTICO corregido: `clasificar_por_oportunidad` crasheaba con AGEBs reales**
- `backend/app/services/reporte.py`
- Accedía a `h["h3_index"]` pero los dicts de AGEB tienen `cvegeo`, no `h3_index` → `KeyError`
- Fix: cuando `h3_index` es `None`, calcula el centroide del polígono AGEB (parse de GeoJSON) y lo convierte a celda H3 para la comparación. Compatible con H3 nativo y AGEBs.

**Bug 2 — ENGAÑOSO corregido: `reporte_final()` reportaba el JOIN incorrecto**
- `backend/scripts/etl_mgn_maestro.py` línea 296
- Usaba `ON g.cvegeo = d.cvegeo` → seguiría mostrando 267 aunque el fix del cvegeo_9 funcionara
- Fix: `ON g.cvegeo_9 = d.cvegeo` (consistente con la query del servicio de reportes)

**Bug 3 — FUNCIONAL corregido: endpoints de reporte fuera del logging de QueryLog**
- `backend/app/middleware.py`
- `_LOGGED_PREFIXES` no incluía `/api/v1/reporte/` → rate limiter siempre veía count=0 aunque `RATE_LIMIT_ENABLED=true`
- Fix: agregado `/api/v1/reporte/` al prefijo → los reportes ahora se loguean y cuentan para el rate limit

**Riesgo 4 — BAJO (sin fix inmediato): health check HTTP en tiempo de importación**
- `backend/app/connectors/registry.py` llama `health_check()` (HTTP a INEGI) al importar el módulo
- Si INEGI está lento al arrancar el servidor, el startup puede tardar varios segundos extra
- No crashea, pero es frágil en producción; solución futura: lazy health check en un endpoint admin

**Nota sobre rate limiting:** `/preview` y `/generar` generan 2 entradas en QueryLog por análisis (una cada una). Cuando se active el rate limit en producción, una sola acción del usuario consumirá 2 cuotas. Diseño a revisar antes de activar `RATE_LIMIT_ENABLED=true`.

---

## Próximos pasos (actualizado al cierre sesión 8)

**PRIORIDAD 1 — Aplicar el fix del JOIN y verificar**
- Correr `alembic -c backend/alembic.ini upgrade head`
- Verificar con query SQL:
  ```sql
  SELECT COUNT(*) FROM raw_data.ageb_geometries WHERE cvegeo_9 IS NOT NULL;
  -- Esperado: ~82,000
  SELECT COUNT(*) 
  FROM raw_data.ageb_geometries g
  JOIN raw_data.ageb_demographics d ON g.cvegeo_9 = d.cvegeo;
  -- Esperado: >50,000
  ```
- Generar un reporte de prueba en Mérida o CDMX y confirmar que usa AGEBs (no H3)

**PRIORIDAD 2 — Frontend Enterprise (visión a mediano plazo)**
- Migración a MapLibre GL + Deck.gl (capas más potentes, heatmaps nativos)
- Módulos: Site Selector, POI Explorer, Interactive Maps, Reportes Ejecutivos
- Stack objetivo: shadcn/ui, TanStack Query, Apache ECharts, Framer Motion
- Ver `SUPER_PROMPT_ENTERPRISE.md` para la visión completa

**PRIORIDAD 3 — Logging en `reporte.py`**
- Reemplazar `except Exception: pass` por `logger.exception(...)` para no ocultar errores

**PRIORIDAD 4 — Completar DENUE**
- Correr `python backend/scripts/etl_maestro.py --solo-denue` para agregar estados faltantes

**PAUSED**
- Historial de análisis en UI
- CI/CD (GitHub Actions)
- SaaS migration (Supabase + Render + Vercel)
