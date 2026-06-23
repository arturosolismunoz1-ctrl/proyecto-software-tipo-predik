# PROMPT DE CONTINUIDAD — Pegar esto como primer mensaje en Claude Code (VS Code)

Copia y pega TODO el contenido de este archivo como tu primer mensaje a Claude dentro de VS Code. Antes de pegarlo, abre en VS Code la carpeta del proyecto: `predik-geo` (en el Desktop, es el repositorio Git con la historia completa).

---

## CONTEXTO DEL PROYECTO

Estoy construyendo un clon funcional de **GeoData Intelligence** (plataforma de inteligencia geoespacial y geomarketing de PREDIK Data-Driven), para uso propio/comercialización futura como SaaS. Ya trabajé el diseño completo de arquitectura, documentación y los primeros pasos de implementación con instancias anteriores de Claude. Tú vas a continuar exactamente desde donde se quedó ese trabajo, con acceso directo a los archivos de este repositorio.

**Lee primero `docs/00-README.md` y todo el contenido de la carpeta `/docs`** — ahí está toda la documentación técnica completa: arquitectura, flujos de negocio, especificación de APIs, modelo de base de datos, casos de uso, decisiones técnicas (ADRs), estrategia de ambientes/Git, logging, y data lake/mart. Esto es la fuente de verdad del proyecto, no la reescribas desde cero.

**Lee también `docs/10-bitacora-de-avance.md`** — ahí está el registro cronológico exacto de qué se ha hecho y qué falta.

## RESUMEN EJECUTIVO DE LO YA DECIDIDO (no se re-discute, ya está acordado)

- **Stack:** Backend en FastAPI (Python), Frontend en React + Vite + Leaflet/Mapbox, Base de datos PostgreSQL 16 + PostGIS + H3, caché Redis.
- **Arquitectura de datos en 3 capas:** `raw_data` (crudo de cada conector) → `cube` (agregados pre-calculados por celda H3, multi-resolución) → `analytics` (resultados de análisis servidos al usuario).
- **Arquitectura de conectores:** toda fuente de datos externa implementa `BaseConnector` (`fetch()`, `health_check()`) y normaliza su respuesta al modelo `GeoFeature`.
- **Multi-tenancy modelado desde el día 1:** todas las tablas de negocio llevan `organization_id`.
- **MVP elegido:** módulo de "Concentración Comercial" usando INEGI DENUE como primera fuente de datos.
- **Autenticación:** JWT con access token (30 min) + refresh token (7 días). Algoritmo HS256. Secret en variable de entorno `JWT_SECRET`.
- **AGEBs reemplazan a H3:** los hexágonos H3 son el fallback. Cuando `raw_data.ageb_geometries` está poblado, el reporte usa polígonos AGEB reales de INEGI en lugar de H3.

## HERRAMIENTAS YA INTEGRADAS EN MI MÁQUINA

- **Git** configurado, repositorio remoto en GitHub: `https://github.com/arturosolismunoz1-ctrl/proyecto-software-tipo-predik` (privado)
- **Docker Desktop** instalado y funcionando (requirió WSL2 + Ubuntu como prerequisito, ya resuelto)
- **`infra/docker-compose.yml`** usa imagen custom `infra/Dockerfile.db` que incluye H3 v4.2.2. Levantar con `make dev`.
- **`.venv/`** creado con todas las dependencias instaladas (`make install` ya fue ejecutado).
- Credenciales locales de la base de datos (ambiente Dev):
  - DB: `geodata_predik_clone` | Usuario: `admin` | Password: `dev_password_local` | Host: `localhost:5432`
- Usuario de prueba en DB: `admin@predik.local` / `dev_password_admin` (creado con `make seed`)
- **INEGI_DENUE_TOKEN** configurado en `.env` — token real de INEGI para la API DENUE.

## ESTADO ACTUAL DEL CÓDIGO (al 2026-06-23)

### Base de datos — 10 tablas:
| Tabla | Registros | Estado |
|---|---|---|
| `raw_data.denue_establishments` | ~360 (creciendo) | ETL maestro corriendo |
| `raw_data.ageb_demographics` | **128,626** | ✅ Completo (32 estados) |
| `raw_data.ageb_geometries` | 0 | ⏳ Esperando MGN 2025 |
| `cube.commercial_density_h3` | ~294 | Parcial |

### Backend — API endpoints implementados:
- `POST /api/v1/auth/login` y `/auth/refresh` (JWT)
- `POST /api/v1/zona/concentracion-comercial` — heatmap H3
- `POST /api/v1/zona/densidad-poblacional` — densidad poblacional
- `POST /api/v1/zona/establecimientos` — puntos DENUE en polígono
- `GET/DELETE /api/v1/analisis` y `/analisis/{id}`
- `GET /api/v1/admin/conectores`, health, sync
- `POST /api/v1/admin/etl/{source}/run` — ETL por keyword/estado
- `POST /api/v1/admin/etl/maestro/run` — ETL maestro paginado (todos los estados)
- `GET /api/v1/admin/bd-status` — estado de población de la BD ← NUEVO
- `POST /api/v1/reporte/generar` — reporte genérico multicapa (KMZ o Excel) ← NUEVO
- `GET /api/v1/catalogo/estados` — 32 estados de México ← NUEVO
- `GET /api/v1/catalogo/municipios/{clave}` — municipios por estado ← NUEVO

### Scripts de datos (en `backend/scripts/`):
- `etl_maestro.py` — ETL maestro: itera 20 sectores SCIAN × 32 estados via DENUE API
- `descargar_censo_2020.py` — descarga automática Censo 2020 AGEB (32 estados desde INEGI)
- `load_censo_2020.py` — carga CSV AGEB a `ageb_demographics`
- `load_marco_geoestadistico.py` — carga MGN shapefiles a `ageb_geometries` (con `--dir` auto-discovery)
- `prueba_funcional_ecatepec.py` — prueba: papelerías Ecatepec → KMZ
- `prueba_guadalajara_fastfood.py` — prueba: McDonald's vs Burger King Guadalajara → KMZ
- `generar_kmz_ecatepec.py` — genera KMZ via API (no DB directo)

### Servicios clave (`backend/app/services/`):
- `reporte.py` — servicio genérico de reportes:
  - `query_agebs_en_poligono()` — consulta AGEBs + demographics + conteo DENUE por AGEB
  - `clasificar_por_densidad()` — colorea zonas verde→amarillo→rojo
  - `clasificar_por_oportunidad()` — ALTA/MEDIA_ALTA/MEDIA/BAJA/SATURADA
  - `generar_kmz()` — KMZ con AGEBs (si existen) o H3 (fallback) + puntos por capa
  - `generar_excel()` — Excel con resumen + hoja por capa
  - `generar_reporte()` — orquesta todo; usa AGEBs si `ageb_geometries` está poblada, fallback a H3

### Datos descargados en `data/`:
- `data/censo_2020/` — 32 CSVs `RESAGEBURB_XXcsv20.csv` (~850 MB total) — ✅ Ya cargados
- `data/mgn/` — carpeta lista, esperando que termine la descarga del ZIP MGN 2025 (~2.7 GB)

## QUIRKS Y BUGS CONOCIDOS (muy importante para no repetir errores)

1. **INEGI DENUE — wildcard "."**: Los clientes HTTP Python (httpx, requests, urllib) normalizan `/./` → `/` (RFC). El endpoint `BuscarEntidad/./estado/...` NO funciona desde código. **Solución:** iterar sobre `SECTORES_DENUE` (lista de 20 keywords de sectores SCIAN en `etl_maestro.py`).
2. **keyword "mcdonald"**: causa que el servidor INEGI aborte la conexión. Usar `"mc donalds"` (con espacio).
3. **INEGI DENUE token**: debe cargarse con `load_dotenv()` en `main.py` — si no, el servidor no lo hereda del `.env`.
4. **Censo 2020**: El archivo correcto es `RESAGEBURB_XXcsv20.csv` ("Principales resultados por AGEB y manzana urbana"). El archivo ITER ("por localidad") es diferente y no sirve para cruce con AGEBs.
5. **MGN — nombres de campos**: varían por edición. El script usa `_FIELD_ALIASES` para resolver nombres alternativos (`CVEGEO`/`CLAVE`/`CVE_GEO`, etc.).
6. **API-first**: los scripts de prueba/análisis deben llamar HTTP endpoints, nunca importar modelos ORM directamente.

## TAREA INMEDIATA AL REANUDAR

### 1. Cargar el MGN 2025 (cuando termine la descarga)
El usuario está descargando el MGN 2025 (~2.7 GB ZIP) manualmente desde INEGI.
Cuando termine y esté descomprimido en `data/mgn/`, ejecutar:
```powershell
python backend/scripts/load_marco_geoestadistico.py --dir data/mgn/
```
El script auto-descubre todos los `*a.shp` (AGEBs urbanas) y los carga.

### 2. Relanzar el ETL DENUE maestro
El proceso anterior tuvo problemas de output buffering (ya corregido con `sys.stdout.reconfigure`).
```powershell
# Probar primero con 3 estados
python backend/scripts/etl_maestro.py --solo-denue --estados 09,14,15

# Si funciona, todos los 32 estados
python backend/scripts/etl_maestro.py --solo-denue
```

### 3. Verificar el sistema completo con bd-status
```powershell
# Levantar server
make run

# Verificar estado (necesitas token JWT)
# POST /api/v1/auth/login con admin@predik.local / dev_password_admin
# GET /api/v1/admin/bd-status
```

### 4. Prueba funcional completa con AGEBs
Una vez cargado el MGN, repetir la prueba de Ecatepec papelerías pero ahora los polígonos del KMZ deben ser AGEBs reales (no hexágonos H3):
```powershell
python backend/scripts/prueba_funcional_ecatepec.py
```

### 5. Frontend (Etapa 4) — pendiente después de BD completa
El frontend NO se ha iniciado todavía. Stack: React + Vite + Leaflet + shadcn/ui.
Funcionalidades requeridas:
- Login con JWT
- Mapa Leaflet con dibujo de polígono
- Dropdowns: estado → municipio (usando `/api/v1/catalogo/`)
- Barra de búsqueda: keyword de negocio (1 o más, colores diferentes)
- Botón "Generar reporte" → llama `POST /api/v1/reporte/generar`
- Visualización resultado en mapa (AGEBs coloreadas + puntos)
- Descarga KMZ / Excel

## FLUJO DE TRABAJO (no negociable)

1. **Todo cambio se guarda LOCALMENTE en los archivos reales del repositorio**.
2. **Nunca trabajamos directo sobre `main` ni `develop`.** Para cada tarea nueva: `git checkout develop && git checkout -b feature/nombre-descriptivo`.
3. Al terminar: `git add` → `git commit` (Conventional Commits) → `git push`.
4. **Cada decisión técnica nueva → nuevo ADR** en `docs/06-decisiones-tecnicas-adr.md`.
5. **Cada hito completado → actualizar** `docs/10-bitacora-de-avance.md`.
6. Usa `make dev` para levantar Docker, `make run` para la API, `make test` para los tests.
7. **API-first:** los scripts de prueba/análisis siempre llaman HTTP endpoints, nunca importan modelos ORM directamente.

## INSTRUCCIÓN DE ARRANQUE

Antes de escribir cualquier código:
1. Ejecuta `git log --oneline -10` y `git status` para ver el estado del repo.
2. Lee `docs/10-bitacora-de-avance.md`.
3. Verifica Docker con `docker ps` — si no, ejecuta `make dev`.
4. Ejecuta `GET /api/v1/admin/bd-status` para ver qué tablas están pobladas.
5. Confírmame el estado actual y por dónde seguimos.
