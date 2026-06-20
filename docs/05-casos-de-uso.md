# 05. Casos de Uso

## 5.1 Actores del sistema

| Actor | Descripción |
|---|---|
| **Analista de Expansión** | Usuario final principal. Evalúa zonas para decidir aperturas, reubicaciones o cierres. |
| **Administrador de Organización** | Gestiona usuarios, planes, credenciales de APIs externas dentro de su organización. |
| **Administrador de Plataforma (interno)** | Gestiona conectores, monitorea salud del sistema, da de alta nuevas organizaciones (rol propio del equipo dueño del producto). |
| **Sistema / Scheduler** | Actor no humano: dispara sincronizaciones y reconstrucción del cubo. |

## 5.2 CU-01: Analizar concentración comercial de una zona

- **Actor:** Analista de Expansión
- **Precondición:** el usuario está autenticado y tiene cuota de consultas disponible en su plan.
- **Flujo principal:**
  1. El usuario dibuja un polígono (o define punto + radio) sobre el mapa.
  2. El sistema muestra el total de establecimientos, desglose por categoría y mapa de calor.
  3. El usuario puede filtrar por categoría específica.
  4. El usuario guarda el análisis para consultarlo después.
- **Flujo alterno:** si la zona no tiene cobertura de datos, el sistema informa explícitamente "sin datos disponibles" en vez de mostrar un resultado vacío ambiguo.
- **Criterios de aceptación:**
  - La respuesta se entrega en menos de 2 segundos (gracias a consulta al cubo, no a `raw_data`).
  - El desglose por categoría usa nomenclatura SCIAN reconocible por el usuario de negocio (no solo el código).

## 5.3 CU-02: Consultar densidad poblacional de una zona

- **Actor:** Analista de Expansión
- **Flujo principal:**
  1. El usuario selecciona una zona ya analizada (o una nueva).
  2. El sistema muestra población total, hogares, y distribuciones de edad/género/NSE.
- **Regla de negocio crítica:** cuando el polígono solo cubre parcialmente un AGEB, el sistema pondera la población proporcionalmente al área cubierta (no asigna el 100% del AGEB si solo se tocó el 10%).

## 5.4 CU-03: Comparar dos o más zonas

- **Actor:** Analista de Expansión
- **Flujo principal:**
  1. El usuario selecciona 2+ análisis guardados previamente.
  2. El sistema presenta una tabla comparativa lado a lado (densidad comercial, población, etc.)
- **Nota:** este caso de uso reutiliza `analytics.zona_analysis_results` — no recalcula nada, solo lee resultados ya guardados.

## 5.5 CU-04: Administrar conectores de datos

- **Actor:** Administrador de Plataforma
- **Flujo principal:**
  1. El administrador consulta el estado de cada conector (última sincronización, # de registros, errores).
  2. El administrador puede disparar una sincronización manual si detecta datos desactualizados.
  3. El administrador puede dar de alta un nuevo conector genérico configurando su YAML (ver `01-arquitectura-del-sistema.md`).
- **Criterio de aceptación:** dar de alta una API REST simple nueva no debe requerir despliegue de código, solo configuración.

## 5.6 CU-05: Onboarding de una nueva organización (preparación SaaS)

- **Actor:** Administrador de Plataforma
- **Flujo principal:**
  1. Se crea un registro en `core.organizations` con su plan correspondiente (Starter/Basic/Plus, replicando el modelo de planes visto en la propuesta comercial de referencia).
  2. Se crea el usuario administrador de esa organización.
  3. Se asignan límites de consultas según el plan.
- **Nota:** este caso de uso no se activa para el primer cliente (uso interno), pero el modelo de datos ya lo soporta sin migración futura.

## 5.7 CU-06: Sincronización automática de datos (actor: Sistema)

- **Actor:** Scheduler
- **Flujo principal:**
  1. Cada noche, el scheduler dispara la sincronización de cada conector activo.
  2. Cada conector trae datos nuevos/actualizados a `raw_data`.
  3. Se dispara el rebuild del cubo correspondiente.
  4. Se registra el resultado en logs (ver `08-logging-y-observabilidad.md`).
- **Criterio de aceptación:** si un conector falla, los demás deben completar su sincronización igual (aislamiento de fallos).

## 5.8 CU-07: Auditoría de uso (preparación para billing futuro)

- **Actor:** Administrador de Organización
- **Flujo principal:**
  1. El administrador consulta cuántas consultas ha hecho su organización en el periodo.
  2. El sistema muestra esto basado en `core.query_log`.
- **Nota:** esto es la base para, en el futuro, facturar por uso si el modelo SaaS lo requiere.
