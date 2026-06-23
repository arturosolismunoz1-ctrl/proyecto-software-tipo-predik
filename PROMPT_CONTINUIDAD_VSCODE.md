# PROMPT DE CONTINUIDAD — Pegar esto como primer mensaje en Claude Code (VS Code)

Copia y pega TODO el contenido de este archivo como tu primer mensaje a Claude dentro de VS Code. Antes de pegarlo, abre en VS Code la carpeta del proyecto: `predik-geo` (en el Desktop, es el repositorio Git con la historia completa).

---

## CONTEXTO DEL PROYECTO

Estoy construyendo un clon funcional de **GeoData Intelligence** (plataforma de inteligencia geoespacial y geomarketing de PREDIK Data-Driven), para uso propio/comercialización futura como SaaS. Ya trabajé el diseño completo de arquitectura, documentación y los primeros pasos de implementación con instancias anteriores de Claude. Tú vas a continuar exactamente desde donde se quedó ese trabajo, con acceso directo a los archivos de este repositorio.

**Lee primero `docs/00-README.md` y todo el contenido de la carpeta `/docs`** — ahí está toda la documentación técnica completa: arquitectura, flujos de negocio, especificación de APIs, modelo de base de datos, casos de uso, decisiones técnicas (ADRs), estrategia de ambientes/Git, logging, y data lake/mart. Esto es la fuente de verdad del proyecto, no la reescribas desde cero.

**Lee también `docs/10-bitacora-de-avance.md`** — ahí está el registro cronológico exacto de qué se ha hecho y qué falta.

## RESUMEN EJECUTIVO DE LO YA DECIDIDO (no se re-discute, ya está acordado)

- **Stack:** Backend en FastAPI (Python), Frontend en React + Vite + Leaflet/Mapbox, Base de datos PostgreSQL 16 + PostGIS + H3, caché Redis.
- **Arquitectura de datos en 3 capas:** `raw_data` (crudo de cada conector) → `cube` (agregados pre-calculados por celda H3, multi-resolución) → `analytics` (resultados de análisis servidos al usuario). Las consultas en vivo del usuario SIEMPRE van contra `cube`, nunca contra `raw_data` directamente.
- **Arquitectura de conectores:** toda fuente de datos externa implementa `BaseConnector` (`fetch()`, `health_check()`) y normaliza su respuesta al modelo `GeoFeature`.
- **Multi-tenancy modelado desde el día 1:** todas las tablas de negocio llevan `organization_id`.
- **MVP elegido:** módulo de "Concentración Comercial" usando INEGI DENUE como primera fuente de datos.
- **Autenticación:** JWT con access token (30 min) + refresh token (7 días). Algoritmo HS256. Secret en variable de entorno `JWT_SECRET`.
- **Todas las decisiones técnicas importantes están documentadas como ADR** en `docs/06-decisiones-tecnicas-adr.md`.

## HERRAMIENTAS YA INTEGRADAS EN MI MÁQUINA (no las reinstales, ya existen)

- **Git** configurado, repositorio remoto en GitHub: `https://github.com/arturosolismunoz1-ctrl/proyecto-software-tipo-predik` (privado)
- **Docker Desktop** instalado y funcionando (requirió WSL2 + Ubuntu como prerequisito, ya resuelto)
- **`infra/docker-compose.yml`** usa imagen custom `infra/Dockerfile.db` que incluye H3 v4.2.2. Levantar con `make dev`.
- **`.venv/`** creado con todas las dependencias instaladas (`make install` ya fue ejecutado).
- Credenciales locales de la base de datos (ambiente Dev, NO usar en producción):
  - DB: `geodata_predik_clone` | Usuario: `admin` | Password: `dev_password_local` | Host: `localhost:5432`
- Usuario de prueba en DB: `admin@predik.local` / `dev_password_admin` (creado con `make seed`)
- **Makefile** en el root — ejecutar `make help` para ver todos los comandos.

## ESTADO ACTUAL DEL CÓDIGO (al 2026-06-23, commit b670e41)

### Ya implementado y commiteado en git:

**Infraestructura:**
- `infra/Dockerfile.db` — imagen PostgreSQL 16 + PostGIS 3.4 + H3 4.2.2
- `infra/docker-compose.yml` — db + redis, usa Dockerfile.db
- `Makefile` — dev, run, test, seed, migrate, migrate-down, lint, test-cov, db-shell, etl

**Base de datos — 10 tablas totales:**
- Migración `0001`: `core.organizations`, `core.users`, `core.api_credentials`, `core.query_log`, `raw_data.denue_establishments`, `cube.commercial_density_h3`, `analytics.zona_analysis_results`
- Migración `0002`: `raw_data.ageb_geometries`, `raw_data.ageb_demographics`, `raw_data.manzana_vivienda`
- Extensiones activas: PostGIS 3.4.3, H3 4.2.2, H3-PostGIS 4.2.2
- `backend/scripts/seed_dev.py` — crea org y usuario admin (idempotente)

**Backend — modelos y conectores:**
- `backend/app/models/` — ORM completo: `core`, `raw_data` (incl. AGEB), `cube`, `analytics`
- `backend/app/connectors/inegi/denue.py` — `DenueConnector` con API real INEGI (token via `INEGI_DENUE_TOKEN`)
- `backend/app/etl/base.py` + `backend/app/etl/denue.py` — pipeline ETL: extract→transform→load_raw→aggregate_h3

**Backend — API:**
- `POST /api/v1/auth/login` y `POST /api/v1/auth/refresh` (JWT HS256, 30min/7días)
- `POST /api/v1/zona/concentracion-comercial` (protegido JWT)
- `POST /api/v1/zona/densidad-poblacional` (protegido JWT) — densidad hab/km², por género/edad, detalle AGEB
- `GET/DELETE /api/v1/analisis` y `/analisis/{id}` (protegidos JWT)
- `GET /api/v1/admin/conectores`, health, sync (requiere `role == admin`)
- `POST /api/v1/admin/etl/{source}/run` (requiere `role == admin`)

**Scripts de carga de datos:**
- `backend/scripts/run_etl.py` — CLI para lanzar ETL DENUE por polígono/bbox
- `backend/scripts/load_marco_geoestadistico.py` — carga shapefile MGN → `ageb_geometries`
- `backend/scripts/load_censo_2020.py` — carga CSV Censo 2020 → `ageb_demographics`

**Tests — 49/49 verde:**
- `test_auth.py` (9), `test_zona_api.py` (2), `test_zona_saved_results.py` (3)
- `test_admin_connectors.py` (6), `test_zona_analysis.py` (1)
- `test_denue_connector.py` (11), `test_denue_etl.py` (12)
- `test_densidad_poblacional.py` (5)

### Pendiente (por orden de prioridad):
1. **Frontend MVP** — React + Vite + Leaflet: login, mapa, dibujar polígono, mostrar resultado de concentración comercial y densidad poblacional.
2. **`.env.example`** — documentar variables: `DATABASE_URL`, `JWT_SECRET`, `INEGI_DENUE_TOKEN`, `REDIS_URL`.
3. **CI/CD** — GitHub Actions que corra `make test` en cada PR.

## FLUJO DE TRABAJO QUE DEBES SEGUIR (no negociable)

1. **Todo cambio se guarda LOCALMENTE en los archivos reales del repositorio** (no en respuestas de chat).
2. **Nunca trabajamos directo sobre `main` ni `develop`.** Para cada tarea nueva: `git checkout develop && git checkout -b feature/nombre-descriptivo`.
3. Al terminar una tarea: `git add` → `git commit` (Conventional Commits: `feat:`, `fix:`, `docs:`, `chore:`) → `git push -u origin feature/nombre-descriptivo`. Yo abriré el Pull Request, tú no.
4. **Cada decisión técnica nueva relevante → nuevo ADR** en `docs/06-decisiones-tecnicas-adr.md`.
5. **Cada hito completado → actualizar** `docs/10-bitacora-de-avance.md` con fecha.
6. Usa `make dev` para levantar Docker, `make run` para la API, `make test` para los tests.
7. **Patrón de tests obligatorio:** usar `app.dependency_overrides` para mockear dependencias FastAPI. El `monkeypatch` de pytest NO alcanza dependencias registradas con `Depends()`.
8. **Ambientes completamente separados** — nunca mezclar credenciales entre Dev/QA/Prod.

## INSTRUCCIÓN DE ARRANQUE

Antes de escribir cualquier código:
1. Ejecuta `git log --oneline` y `git status` para ver el estado del repo.
2. Lee `docs/10-bitacora-de-avance.md` para ver exactamente qué está hecho y qué sigue.
3. Verifica que Docker esté corriendo con `docker ps` — si no, ejecuta `make dev`.
4. Confírmame que entendiste el estado actual y pregúntame por dónde seguir.
