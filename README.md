# predik-geo

Plataforma propia de inteligencia geoespacial y geomarketing, inspirada en GeoData Intelligence (PREDIK Data-Driven). Permite analizar densidad comercial, población y afluencia dentro de polígonos geográficos, con datos de INEGI y otras fuentes configurables.

## Estructura del repositorio

```
predik-geo/
├── backend/          API FastAPI + modelos SQLAlchemy + conectores + tests
│   ├── alembic/      Migraciones de base de datos
│   ├── app/
│   │   ├── api/v1/   Endpoints REST versionados
│   │   ├── connectors/  Conectores de datos (INEGI DENUE, etc.)
│   │   ├── models/   Modelos ORM (core, raw_data, cube, analytics)
│   │   └── services/ Lógica de negocio
│   └── tests/        Tests unitarios y de integración
├── frontend/         App React + Vite + Leaflet (pendiente de implementar)
├── docs/             Documentación técnica completa (leer antes de tocar código)
├── infra/            docker-compose.yml para ambiente de desarrollo
├── Makefile          Comandos de uso frecuente
└── .env.example      Plantilla de variables de entorno
```

## Requisitos previos

- Docker Desktop (con WSL2 habilitado en Windows)
- Python 3.11+
- Git

## Setup inicial (primera vez)

```bash
# 1. Clonar el repo
git clone https://github.com/arturosolismunoz1-ctrl/proyecto-software-tipo-predik predik-geo
cd predik-geo

# 2. Copiar variables de entorno
cp .env.example .env
# Editar .env si es necesario (las credenciales por defecto funcionan en local)

# 3. Instalar dependencias Python
make install

# 4. Levantar base de datos y Redis
make dev

# 5. Aplicar migraciones
make migrate

# 6. Levantar la API
make run
# API disponible en http://localhost:8000
# Documentación interactiva: http://localhost:8000/docs
```

## Comandos del día a día

```bash
make dev          # Levanta PostgreSQL+PostGIS y Redis
make run          # Levanta la API FastAPI (hot-reload)
make test         # Corre los tests
make test-cov     # Tests con reporte de cobertura
make migrate      # Aplica migraciones pendientes
make db-shell     # psql directo al contenedor
make down         # Detiene Docker
make help         # Lista todos los comandos disponibles
```

## Workflow de desarrollo

1. Crea una rama desde `develop` para cada tarea:
   ```bash
   git checkout develop
   git checkout -b feature/nombre-descriptivo
   ```
2. Haz commits con [Conventional Commits](https://www.conventionalcommits.org/):
   `feat:`, `fix:`, `docs:`, `chore:`, `test:`, `refactor:`
3. Push y abre Pull Request hacia `develop` (nunca directo a `main`).
4. Actualiza `docs/10-bitacora-de-avance.md` al cerrar cada hito.

## Documentación técnica

Toda la documentación está en [`docs/`](docs/). Leer antes de escribir código nuevo:

| Archivo | Contenido |
|---|---|
| [00-README.md](docs/00-README.md) | Índice y estado del proyecto |
| [01-arquitectura-del-sistema.md](docs/01-arquitectura-del-sistema.md) | Componentes, capas, decisiones |
| [03-especificacion-apis.md](docs/03-especificacion-apis.md) | Contratos REST completos |
| [04-base-de-datos.md](docs/04-base-de-datos.md) | Esquemas y modelo de datos |
| [06-decisiones-tecnicas-adr.md](docs/06-decisiones-tecnicas-adr.md) | ADRs — consultar antes de proponer cambios |
| [10-bitacora-de-avance.md](docs/10-bitacora-de-avance.md) | Estado actual y próximos pasos |

## Estado actual

Ver [`docs/10-bitacora-de-avance.md`](docs/10-bitacora-de-avance.md) para el detalle actualizado.

**Implementado:**
- `POST /api/v1/zona/concentracion-comercial` — funciona con datos demo
- `GET/DELETE /api/v1/analisis` — gestión de análisis guardados
- `GET /api/v1/admin/conectores` — admin de conectores de datos
- Modelos ORM completos (core, raw_data, cube, analytics)
- Primera migración Alembic con PostGIS y H3

**Pendiente:**
- Densidad poblacional (datos INEGI Censo/AGEB)
- Autenticación JWT
- Frontend React + mapa Leaflet
- Integración real con API INEGI DENUE
