# GeoData Clone — Documentación Técnica

Plataforma de inteligencia geoespacial y geomarketing (clon funcional inspirado en GeoData Intelligence de PREDIK Data-Driven), desarrollada para uso propio / futura comercialización como SaaS.

## Índice de documentos

| Documento | Contenido |
|---|---|
| [01-arquitectura-del-sistema.md](./01-arquitectura-del-sistema.md) | Arquitectura general, componentes, diagramas |
| [02-flujos-de-negocio.md](./02-flujos-de-negocio.md) | Flujos end-to-end de cada módulo funcional |
| [03-especificacion-apis.md](./03-especificacion-apis.md) | Contratos REST, endpoints, request/response |
| [04-base-de-datos.md](./04-base-de-datos.md) | Modelo de datos, esquema, capas (raw/cube/analytics) |
| [05-casos-de-uso.md](./05-casos-de-uso.md) | User stories, actores, criterios de aceptación |
| [06-decisiones-tecnicas-adr.md](./06-decisiones-tecnicas-adr.md) | Architecture Decision Records |
| [07-control-de-versiones-y-ambientes.md](./07-control-de-versiones-y-ambientes.md) | Git, ramas, CI/CD, Dev/QA/Prod |
| [08-logging-y-observabilidad.md](./08-logging-y-observabilidad.md) | Qué se registra, cómo y dónde |
| [09-data-lake-y-data-mart.md](./09-data-lake-y-data-mart.md) | Estrategia de datos a largo plazo |
| [10-bitacora-de-avance.md](./10-bitacora-de-avance.md) | Registro de sesiones, decisiones y cambios del proyecto |
| [11-plan-sprints.md](./11-plan-sprints.md) | Plan de sprints ágil — fases, DoD, KPIs y dependencias |
| [12-reporte-avance-pm.md](./12-reporte-avance-pm.md) | Reporte PM/SCRUM — avance por etapa, ruta crítica, riesgos (corte 2026-06-24) |

## Convenciones de este repositorio

- Toda esta carpeta `/docs` vive **dentro del repositorio de código**, no en un Drive/Notion separado y desactualizado. Los cambios de arquitectura van en el mismo Pull Request que el código que los implementa.
- Los diagramas usan sintaxis [Mermaid](https://mermaid.js.org/), por lo que se renderizan automáticamente en GitHub/GitLab sin herramientas externas.
- Las decisiones técnicas importantes **no se discuten solo en chat/WhatsApp** — se documentan como ADR (ver `06-decisiones-tecnicas-adr.md`) para que el razonamiento quede trazable.
- Este documento (`00-README.md`) debe actualizarse cada vez que se agregue un nuevo documento a `/docs`.

## Estado del proyecto

| Fase | Estado |
|---|---|
| Definición de arquitectura | ✅ Completo |
| Infraestructura (Docker + PostgreSQL + PostGIS + H3 + Redis) | ✅ Completo |
| Base de datos (migración + seed dev) | ✅ Completo |
| Autenticación JWT (login, refresh, middleware) | ✅ Completo |
| Backend FastAPI + Auth JWT + Rate Limiter | ✅ 90% completo |
| ETL DENUE real (INEGI) — ~528k establecimientos | ✅ Parcial (6 estados) |
| ETL MGN 2025 + Censo 2020 (AGEBs + demografía) | ✅ Cargado — JOIN fix pendiente aplicar |
| BIE INEGI (indicadores económicos por estado) | ✅ Completo con fallback demo |
| Frontend MVP (react-leaflet) — reportes, mapa, capas, BIE | ✅ Funcional |
| Frontend Enterprise (MapLibre + Deck.gl + shadcn/ui) | 🔲 Sprint 1 — próximo |
| Site Selector (módulo core del SaaS) | 🔲 Sprint 2 |
| POI Explorer (análisis de audiencias) | 🔲 Sprint 3 |
| Reportes Ejecutivos PDF premium | 🔲 Sprint 4 |
| Despliegue cloud (Render + Vercel) + Multi-tenant | 🔲 Sprint 5 |
