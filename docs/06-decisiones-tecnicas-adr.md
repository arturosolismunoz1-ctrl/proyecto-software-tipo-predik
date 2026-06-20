# 06. Decisiones Técnicas (ADR — Architecture Decision Records)

Cada decisión importante se documenta con este formato: **Contexto → Decisión → Alternativas consideradas → Consecuencias**. Esto evita que el razonamiento se pierda en chats o se repita la misma discusión meses después.

---

## ADR-001: Uso de PostgreSQL + PostGIS como motor de base de datos

**Contexto:** necesitamos almacenar y consultar datos geoespaciales (puntos, polígonos) de forma eficiente, con posibilidad de migrar a la nube sin reescritura.

**Decisión:** usar PostgreSQL 16 con extensión PostGIS.

**Alternativas consideradas:**
- MongoDB con soporte geoespacial → descartado: peor soporte de operaciones geoespaciales avanzadas (intersecciones, buffers) comparado con PostGIS, y peor encaje con modelo relacional multi-tenant.
- MySQL con tipos espaciales → descartado: soporte geoespacial significativamente más limitado que PostGIS.
- Motor especializado (ej. Elasticsearch con geo_shape) → descartado para esta fase: agrega complejidad operativa sin necesidad — PostGIS cubre el caso de uso actual.

**Consecuencias:** PostGIS es el estándar de la industria para este tipo de plataformas, tiene soporte nativo en todos los proveedores cloud principales (RDS, Cloud SQL, Supabase, Neon), y permite que dev/QA/prod usen exactamente el mismo motor.

---

## ADR-002: Arquitectura de conectores con interfaz común (`BaseConnector`)

**Contexto:** el sistema debe poder integrar múltiples fuentes de datos externas (varias APIs de INEGI, Google Places, futuros proveedores de tráfico/movilidad) sin que el core del sistema dependa de los detalles de cada una.

**Decisión:** todo conector implementa una interfaz abstracta común (`fetch()`, `health_check()`) y normaliza su respuesta al modelo `GeoFeature`. Se añade además un "conector genérico configurable por YAML" para APIs REST simples, evitando código nuevo para integraciones triviales.

**Alternativas consideradas:**
- Integrar cada API directamente en los endpoints/servicios → descartado: alto acoplamiento, cada API nueva requeriría tocar lógica de negocio existente.

**Consecuencias:** agregar una fuente de datos nueva es una tarea aislada (nuevo archivo, sin tocar el orquestador). Facilita testing (se puede mockear `BaseConnector` fácilmente).

---

## ADR-003: Capa de cubo agregado con H3 en vez de consultas directas a `raw_data`

**Contexto:** a medida que el volumen de datos crece (millones de establecimientos, datos de movilidad), las consultas geoespaciales directas sobre datos crudos se vuelven lentas y costosas en recursos, especialmente en un escenario SaaS multi-usuario concurrente.

**Decisión:** implementar una capa intermedia de datos pre-agregados por celda hexagonal H3, en múltiples resoluciones, refrescada vía proceso ETL batch (no en tiempo real). Las consultas del usuario final siempre golpean esta capa, nunca `raw_data` directamente salvo fallback excepcional.

**Alternativas consideradas:**
- Geohash en vez de H3 → descartado: las celdas de geohash se distorsionan según latitud y no tienen geometría uniforme; H3 (hexágonos) da mejor precisión y funciones nativas de vecindad.
- Cachear solo a nivel de respuesta HTTP (Redis) sin capa de agregación → descartado: no resuelve el problema de fondo (la primera consulta de cada zona seguiría siendo lenta), y no escala bien a "cualquier polígono dibujado libremente" por el usuario.

**Consecuencias:** las consultas en producción son consistentemente rápidas independientemente del volumen de `raw_data`. El costo se paga en el proceso batch (predecible, fuera de horario pico), no en cada request de usuario.

---

## ADR-004: Modelo de datos multi-tenant desde el día 1

**Contexto:** el proyecto inicia como herramienta interna de un solo cliente, pero el objetivo declarado es eventualmente ofrecerlo como SaaS a múltiples organizaciones.

**Decisión:** todas las tablas relevantes de negocio incluyen `organization_id` desde la primera migración, aunque hoy exista una sola organización activa.

**Alternativas consideradas:**
- Modelar sin multi-tenancy ahora y migrar después → descartado: las migraciones de "single-tenant a multi-tenant" sobre datos en producción son de las más riesgosas y costosas en cualquier sistema; es mucho más barato modelarlo bien desde el inicio.

**Consecuencias:** ligera complejidad adicional ahora (filtrar por organización en cada query) a cambio de evitar una migración de alto riesgo en el futuro.

---

## ADR-005: Separación estricta de ambientes Dev / QA / Producción

**Contexto:** evitar el riesgo de que pruebas o desarrollo afecten datos o usuarios reales, y evitar dependencia de "la laptop de alguien" para que el sistema funcione.

**Decisión:** tres bases de datos y tres despliegues completamente independientes (ver `07-control-de-versiones-y-ambientes.md`), cada uno con sus propias credenciales y, cuando aplique, sus propias cuotas de APIs externas.

**Consecuencias:** mayor disciplina operativa requerida (variables de entorno por ambiente, pipelines de CI/CD), a cambio de eliminar la clase de incidentes más común en proyectos pequeños: "funcionaba en mi máquina" o "se rompió producción al probar algo".

---

## ADR-006: Control de versiones obligatorio vía Git, sin código fuera de repositorio

**Contexto:** evitar pérdida de trabajo, falta de trazabilidad de cambios, y archivos tipo `final_v2_ahora_si.zip` viviendo en computadoras personales sin respaldo ni historial.

**Decisión:** todo el código y la documentación (`/docs`, este mismo set de archivos) vive en GitHub/GitLab. Ningún cambio se considera "real" hasta que está en un repositorio remoto, con historial de commits legible.

**Consecuencias:** ver el detalle operativo completo en `07-control-de-versiones-y-ambientes.md`.

---

## ADR-007: Diferir la implementación de Data Lake/Data Warehouse dedicados

**Contexto:** el sistema integra múltiples fuentes de datos y a futuro podría necesitar analítica masiva (entrenamiento de modelos de IA tipo Site Selector, benchmarks multi-organización). Existe la tentación de implementar herramientas de Data Lake (S3) y Data Warehouse (BigQuery/Snowflake) desde el inicio.

**Decisión:** mantener todo en PostgreSQL (con la separación lógica `raw_data`/`cube`/`analytics`) hasta que aparezcan señales concretas de necesidad (ver `09-data-lake-y-data-mart.md`, sección 9.4), y documentar desde ahora la ruta de migración futura.

**Alternativas consideradas:**
- Implementar Data Lake/Warehouse desde el día 1 → descartado: complejidad operativa y costo no justificados en la escala actual del proyecto (single-tenant inicial, volumen moderado).

**Consecuencias:** se evita sobre-ingeniería prematura. El riesgo se mitiga documentando explícitamente las señales que deben disparar la migración, para no llegar tarde a esa decisión.
