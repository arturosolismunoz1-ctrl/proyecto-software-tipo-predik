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

## Próximos pasos (por orden de prioridad)

- [ ] **Frontend MVP** — scaffolding React + Vite, pantalla de login, mapa Leaflet, dibujar polígono, mostrar resultado de concentración y densidad.
- [ ] **`.env.example`** — documentar variables: `DATABASE_URL`, `JWT_SECRET`, `INEGI_DENUE_TOKEN`, `REDIS_URL`.
- [ ] **CI/CD** — GitHub Actions que corra `make test` en cada PR.
