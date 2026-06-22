# PROMPT DE CONTINUIDAD — Pegar esto como primer mensaje en Claude Code (VS Code)

Copia y pega TODO el contenido de este archivo como tu primer mensaje a Claude dentro de VS Code. Antes de pegarlo, abre en VS Code la carpeta del proyecto: `predik-geo` (en el Desktop, es el repositorio Git con la historia completa).

---

## CONTEXTO DEL PROYECTO

Estoy construyendo un clon funcional de **GeoData Intelligence** (plataforma de inteligencia geoespacial y geomarketing de PREDIK Data-Driven), para uso propio/comercialización futura como SaaS. Ya trabajé el diseño completo de arquitectura, documentación y los primeros pasos de implementación con instancias anteriores de Claude. Tú vas a continuar exactamente desde donde se quedó ese trabajo, con acceso directo a los archivos de este repositorio.

**Lee primero `docs/00-README.md` y todo el contenido de la carpeta `/docs`** — ahí está toda la documentación técnica completa: arquitectura, flujos de negocio, especificación de APIs, modelo de base de datos, casos de uso, decisiones técnicas (ADRs), estrategia de ambientes/Git, logging, y data lake/mart. Esto es la fuente de verdad del proyecto, no la reescribas desde cero.

**Lee también `docs/10-bitacora-de-avance.md`** — ahí está el registro cronológico exacto de qué se ha hecho y qué falta.

## RESUMEN EJECUTIVO DE LO YA DECIDIDO (no se re-discute, ya está acordado)

- **Stack:** Backend en FastAPI (Python), Frontend en React + Vite + Leaflet/Mapbox, Base de datos PostgreSQL 16 + PostGIS, caché Redis.
- **Arquitectura de datos en 3 capas:** `raw_data` (crudo de cada conector) → `cube` (agregados pre-calculados por celda H3, multi-resolución) → `analytics` (resultados de análisis servidos al usuario). Las consultas en vivo del usuario SIEMPRE van contra `cube`, nunca contra `raw_data` directamente.
- **Arquitectura de conectores:** toda fuente de datos externa (INEGI DENUE, INEGI Censo/AGEB, INEGI BIE, Google Places, futuros proveedores) implementa una interfaz común `BaseConnector` (`fetch()`, `health_check()`) y normaliza su respuesta al modelo `GeoFeature`. Existe también un "conector genérico configurable por YAML" para APIs REST simples nuevas sin escribir código.
- **Multi-tenancy modelado desde el día 1:** todas las tablas de negocio llevan `organization_id`, aunque hoy solo exista una organización activa — para no tener que migrar dolorosamente cuando se vuelva SaaS real.
- **MVP elegido para empezar:** módulo de "Concentración Comercial" usando INEGI DENUE como primera fuente de datos.
- **Todas las decisiones técnicas importantes están documentadas como ADR** en `docs/06-decisiones-tecnicas-adr.md` — consúltalo antes de proponer alternativas a algo ya decidido ahí.

## HERRAMIENTAS YA INTEGRADAS EN MI MÁQUINA (no las reinstales, ya existen)

- **Git** configurado, repositorio remoto en GitHub: `https://github.com/arturosolismunoz1-ctrl/proyecto-software-tipo-predik` (privado)
- **Docker Desktop** instalado y funcionando (requirió WSL2 + Ubuntu como prerequisito, ya resuelto)
- **`infra/docker-compose.yml`** creado y probado — levanta `db` (PostgreSQL 16 + PostGIS 3.4, puerto 5432) y `redis` (puerto 6379). Levantar con `make dev`.
- **`.venv/`** ya creado con todas las dependencias instaladas (`make install` ya fue ejecutado).
- Credenciales locales de la base de datos (ambiente Dev, NO usar en producción):
  - DB: `geodata_predik_clone`  |  Usuario: `admin`  |  Password: `dev_password_local`  |  Host: `localhost:5432`
- **Makefile** en el root con todos los comandos frecuentes — ejecutar `make help` para ver la lista completa.

## ESTADO ACTUAL DEL CÓDIGO (al 2026-06-22)

### Ya implementado y commiteado en git:
- `backend/app/main.py` — entrada de FastAPI con routers registrados
- `backend/app/db.py` — sesión SQLAlchemy + engine
- `backend/app/models/` — ORM completo: `core`, `raw_data`, `cube`, `analytics`
- `backend/app/connectors/base.py` — `BaseConnector` + `GeoFeature` (interfaz abstracta)
- `backend/app/connectors/inegi/denue.py` — `DenueConnector` con fallback a datos demo
- `backend/app/connectors/registry.py` — registro centralizado de conectores
- `backend/app/api/v1/zona.py` — `POST /api/v1/zona/concentracion-comercial`
- `backend/app/api/v1/analisis.py` — `GET/DELETE /api/v1/analisis/{id}`
- `backend/app/api/v1/admin.py` — `GET /api/v1/admin/conectores` y health/sync
- `backend/app/services/zona_analysis.py` — lógica de cálculo de concentración
- `backend/alembic/versions/0001_initial_schemas.py` — primera migración con PostGIS y H3
- `backend/tests/` — tests básicos de zona API, conectores y análisis guardados

### Pendiente (por orden de prioridad):
1. **Confirmar push a GitHub** — verificar con `git branch -a` y pushear si es necesario.
2. **Módulo densidad poblacional** — endpoint `POST /api/v1/zona/densidad-poblacional` + lógica con datos AGEB/Censo.
3. **Autenticación JWT** — endpoints `POST /api/v1/auth/login` y `/refresh` + middleware.
4. **Poblar cubos H3 con datos reales** — ETL que lea de INEGI DENUE y llene `cube.commercial_density_h3`.
5. **Integración real con API INEGI DENUE** — `DenueConnector` actualmente usa datos demo hardcodeados.
6. **Frontend** — scaffolding React + Vite, mapa Leaflet, panel de análisis.

## FLUJO DE TRABAJO QUE DEBES SEGUIR (no negociable)

1. **Todo cambio se guarda LOCALMENTE en los archivos reales del repositorio** (no en respuestas de chat, no en artifacts separados).
2. **Nunca trabajamos directo sobre `main` ni `develop`.** Para cada tarea nueva: `git checkout develop && git checkout -b feature/nombre-descriptivo`.
3. Al terminar una tarea: `git add` → `git commit` (Conventional Commits: `feat:`, `fix:`, `docs:`, `chore:`) → `git push -u origin feature/nombre-descriptivo`. Yo abriré el Pull Request, tú no.
4. **Cada decisión técnica nueva relevante → nuevo ADR** en `docs/06-decisiones-tecnicas-adr.md`, mismo formato.
5. **Cada hito completado → actualizar** `docs/10-bitacora-de-avance.md` con fecha.
6. Usa `make dev` para levantar Docker, `make run` para la API, `make test` para los tests.
7. **Ambientes completamente separados** — nunca mezclar credenciales entre Dev/QA/Prod (ver `docs/07-control-de-versiones-y-ambientes.md`).

## INSTRUCCIÓN DE ARRANQUE

Antes de escribir cualquier código:
1. Ejecuta `git log --oneline` y `git branch -a` para ver el estado del repo.
2. Lee `docs/10-bitacora-de-avance.md` para ver exactamente qué está hecho y qué sigue.
3. Confírmame que entendiste el estado actual y pregúntame si seguimos con el punto 1 de "Pendiente" de arriba, o si prefiero algo distinto primero.
