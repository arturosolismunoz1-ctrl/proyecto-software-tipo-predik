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

## Convenciones de este repositorio

- Toda esta carpeta `/docs` vive **dentro del repositorio de código**, no en un Drive/Notion separado y desactualizado. Los cambios de arquitectura van en el mismo Pull Request que el código que los implementa.
- Los diagramas usan sintaxis [Mermaid](https://mermaid.js.org/), por lo que se renderizan automáticamente en GitHub/GitLab sin herramientas externas.
- Las decisiones técnicas importantes **no se discuten solo en chat/WhatsApp** — se documentan como ADR (ver `06-decisiones-tecnicas-adr.md`) para que el razonamiento quede trazable.
- Este documento (`00-README.md`) debe actualizarse cada vez que se agregue un nuevo documento a `/docs`.

## Estado del proyecto

| Fase | Estado |
|---|---|
| Definición de arquitectura | ✅ Completo |
| Módulo: Concentración Comercial (DENUE) | 🔲 En diseño |
| Módulo: Densidad Poblacional | 🔲 Pendiente |
| Módulo: Afluencia Vehicular | 🔲 Pendiente (depende de proveedor externo) |
| Módulo: Afluencia de Personas / POI Explorer | 🔲 Pendiente (depende de proveedor de movilidad) |
| Módulo: Site Selector (IA) | 🔲 Pendiente (depende de los anteriores) |
