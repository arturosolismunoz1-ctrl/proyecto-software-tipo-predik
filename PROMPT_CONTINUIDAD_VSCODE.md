# PROMPT DE CONTINUIDAD — Pegar esto como primer mensaje en Claude Code (VS Code)

Copia y pega TODO el contenido de este archivo como tu primer mensaje a Claude dentro de VS Code. Antes de pegarlo, abre en VS Code la carpeta del proyecto: `PROYECTO SOFTWARE TIPO PREDIK` (la misma que ya tienes en tu computadora, con el repo Git ya conectado a GitHub).

---

## CONTEXTO DEL PROYECTO

Estoy construyendo un clon funcional de **GeoData Intelligence** (plataforma de inteligencia geoespacial y geomarketing de PREDIK Data-Driven), para uso propio/comercialización futura como SaaS. Ya trabajé el diseño completo de arquitectura, documentación y los primeros pasos de infraestructura con otra instancia de Claude (vía claude.ai). Tú vas a continuar exactamente desde donde se quedó ese trabajo, con acceso directo a los archivos de este repositorio.

**Lee primero `docs/00-README.md` y todo el contenido de la carpeta `/docs`** — ahí está toda la documentación técnica completa: arquitectura, flujos de negocio, especificación de APIs, modelo de base de datos, casos de uso, decisiones técnicas (ADRs), estrategia de ambientes/Git, logging, y data lake/mart. Esto es la fuente de verdad del proyecto, no la reescribas desde cero.

**Lee también `docs/10-bitacora-de-avance.md`** — ahí está el registro cronológico exacto de qué se ha hecho y qué falta.

## RESUMEN EJECUTIVO DE LO YA DECIDIDO (no se re-discute, ya está acordado)

- **Stack:** Backend en FastAPI (Python), Frontend en React + Vite + Leaflet/Mapbox, Base de datos PostgreSQL 16 + PostGIS, caché Redis.
- **Arquitectura de datos en 3 capas:** `raw_data` (crudo de cada conector) → `cube` (agregados pre-calculados por celda H3, multi-resolución) → `analytics` (resultados de análisis servidos al usuario). Las consultas en vivo del usuario SIEMPRE van contra `cube`, nunca contra `raw_data` directamente.
- **Arquitectura de conectores:** toda fuente de datos externa (INEGI DENUE, INEGI Censo/AGEB, INEGI BIE, Google Places, futuros proveedores) implementa una interfaz común `BaseConnector` (`fetch()`, `health_check()`) y normaliza su respuesta al modelo `GeoFeature`. Existe también un "conector genérico configurable por YAML" para APIs REST simples nuevas sin escribir código.
- **Multi-tenancy modelado desde el día 1:** todas las tablas de negocio llevan `organization_id`, aunque hoy solo exista una organización activa — para no tener que migrar dolorosamente cuando se vuelva SaaS real.
- **MVP elegido para empezar:** módulo de "Concentración Comercial" usando INEGI DENUE como primera fuente de datos.
- **Todas las decisiones técnicas importantes están documentadas como ADR** en `docs/06-decisiones-tecnicas-adr.md` — consúltalo antes de proponer alternativas a algo ya decidido ahí.

## FLUJO DE TRABAJO QUE DEBES SEGUIR (no negociable, ya está en producción)

1. **Todo cambio de código se guarda LOCALMENTE en los archivos reales del repositorio** (no en respuestas de chat, no en artifacts separados) — exactamente la misma carpeta que tengo abierta en VS Code.
2. **Nunca trabajamos directo sobre `main` ni `develop`.** Para cada tarea nueva, crea una rama `feature/nombre-descriptivo` a partir de `develop`.
3. Al terminar una tarea: `git add` → `git commit` (con mensaje estilo Conventional Commits: `feat:`, `fix:`, `docs:`, `chore:`) → `git push -u origin feature/nombre-descriptivo`. Yo (el humano) abriré el Pull Request en GitHub y haré el merge — tú no necesitas hacerlo automáticamente, solo avísame cuándo está listo para PR.
4. **Estado de Git en este momento:** ya existe la rama `feature/docker-compose-dev` con el primer `docker-compose.yml` (PostgreSQL+PostGIS + Redis). Verifica con `git status` y `git branch -a` si ese push ya llegó a GitHub o si hay que reintentarlo — quedó pendiente de confirmar en la sesión anterior.
5. Cada vez que se tome una decisión técnica nueva relevante, agrégala como un nuevo ADR en `docs/06-decisiones-tecnicas-adr.md`, siguiendo el mismo formato (Contexto → Decisión → Alternativas consideradas → Consecuencias).
6. Actualiza `docs/10-bitacora-de-avance.md` después de completar cada hito importante, con fecha.
7. **Ambientes:** Dev (local, lo que estamos armando ahora), QA y Producción son completamente separados — nunca mezclar credenciales ni bases de datos entre ellos (detalle completo en `docs/07-control-de-versiones-y-ambientes.md`).

## HERRAMIENTAS YA INTEGRADAS EN MI MÁQUINA (no las reinstales, ya existen)

- **Git** configurado, repositorio remoto en GitHub: `https://github.com/arturosolismunoz1-ctrl/proyecto-software-tipo-predik` (privado)
- **Docker Desktop** instalado y funcionando (requirió WSL2 + Ubuntu como prerequisito, ya resuelto)
- **`infra/docker-compose.yml`** ya creado y probado — levanta `db` (PostgreSQL 16 + PostGIS 3.4, puerto 5432) y `redis` (puerto 6379). Ya verificado que ambos contenedores corren en estado `healthy`.
- Credenciales locales de la base de datos (ambiente Dev, NO usar en producción):
  - DB: `geodata_predik_clone`
  - Usuario: `admin`
  - Password: `dev_password_local`
  - Host: `localhost:5432`

## SIGUIENTE PASO INMEDIATO AL RETOMAR

1. Confirma en mi terminal si la rama `feature/docker-compose-dev` ya se subió correctamente a GitHub (`git branch -a` para verlo, o `git push -u origin feature/docker-compose-dev` de nuevo si hace falta).
2. Una vez confirmado eso, seguimos con (en este orden, según `docs/01-arquitectura-del-sistema.md` y `docs/04-base-de-datos.md`):
   - Crear `backend/requirements.txt` con las dependencias (FastAPI, SQLAlchemy, GeoAlchemy2, Alembic, psycopg2, etc.)
   - Configurar Alembic y la primera migración con los esquemas `core`, `raw_data`, `cube`, `analytics` (el SQL completo ya está en `docs/04-base-de-datos.md`, solo hay que convertirlo a migraciones de Alembic)
   - Implementar `BaseConnector` y el modelo `GeoFeature` (`backend/app/connectors/base.py`)
   - Implementar `DenueConnector` (`backend/app/connectors/inegi/denue.py`)
   - Implementar el endpoint `POST /api/v1/zona/concentracion-comercial`

## INSTRUCCIÓN DE ARRANQUE PARA TI (Claude en VS Code)

Antes de escribir cualquier código, lee completo `/docs` para tener el contexto completo, luego confírmame que entendiste el estado actual y pregúntame si seguimos con el paso 1 de "Siguiente paso inmediato" de arriba, o si prefiero algo distinto primero.
