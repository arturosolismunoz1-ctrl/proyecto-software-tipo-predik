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

## Próximos pasos planeados (no iniciados aún)

- [ ] Confirmar push exitoso de `feature/docker-compose-dev` y abrir el primer Pull Request hacia `develop`
- [ ] Modelos SQLAlchemy + primera migración Alembic (esquemas `core`, `raw_data`, `cube`, `analytics`)
- [ ] Implementar `BaseConnector` (interfaz abstracta) y `GeoFeature` (modelo común)
- [ ] Implementar `DenueConnector` (primera fuente de datos real: INEGI DENUE)
- [ ] Endpoint `POST /api/v1/zona/concentracion-comercial`
- [ ] Scaffolding inicial del frontend (React + Vite + Leaflet)
