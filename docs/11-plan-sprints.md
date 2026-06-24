# Plan de Sprints — Predik-Geo SaaS

Documento de planificación ágil del proyecto. Define fases, sprints, objetivos, criterios de aceptación y KPIs de seguimiento.

---

## 1. Principios de planificación

| Principio | Decisión adoptada |
|---|---|
| Duración de sprint | 1 semana (entregas rápidas y ajustes frecuentes) |
| Tamaño de sprint | 5–8 tareas técnicas por sprint |
| Definition of Done | Código en rama, tests pasando, funcionalidad visible en localhost, bitácora actualizada |
| Prioridad | Valor de negocio > deuda técnica > features secundarios |
| Dependencias | Un sprint no empieza hasta que el anterior esté en DoD |
| Datos simulados | Aceptados en fases tempranas; sustituibles por datos reales sin cambiar contratos de API |
| Documentación | Cada sprint actualiza `10-bitacora-de-avance.md`; decisiones de arquitectura van en `06-decisiones-tecnicas-adr.md` |

---

## 2. Resumen de fases

```
FASE 0 — Cierre técnico     │ Sprint 0.1 – 0.2 │ Semanas 1–2  │ ~100% backend
FASE 1 — Frontend Enterprise │ Sprint 1.1 – 1.3 │ Semanas 3–5  │ Layout + mapa base
FASE 2 — Site Selector       │ Sprint 2.1 – 2.3 │ Semanas 6–8  │ Módulo core del SaaS
FASE 3 — POI Explorer        │ Sprint 3.1 – 3.2 │ Semanas 9–10 │ Análisis de audiencias
FASE 4 — Reportes Ejecutivos │ Sprint 4.1       │ Semana 11    │ PDF + PNG premium
FASE 5 — SaaS / Producción   │ Sprint 5.1 – 5.2 │ Semanas 12–13│ Cloud + multi-tenant
```

**Hito de demo a clientes:** final de Fase 2 (semana 8)
**MVP en producción:** final de Fase 5 (semana 13)

---

## 3. Estado de partida (al iniciar el plan)

| Componente | Estado | Notas |
|---|---|---|
| Backend FastAPI | ✅ 90% | Auth, ETL, reportes, BIE, AGEBs cargados |
| Migración cvegeo_9 | ⏳ Pendiente aplicar | `alembic upgrade head` — fix del JOIN |
| DENUE completo | ⚠️ Parcial | ~528k establecimientos; faltan estados |
| Frontend MVP | ✅ Funcional | react-leaflet — será reemplazado en Fase 1 |
| Tests backend | ✅ Pasando | 49+ tests |
| Despliegue cloud | ❌ Pendiente | Fase 5 |

---

## FASE 0 — Cierre técnico y estabilización del backend

> **Objetivo:** Cerrar todos los bugs conocidos antes de construir encima. Al terminar, un reporte generado en el frontend usará AGEBs reales con demografía Censo 2020.

---

### Sprint 0.1 — Fix JOIN + Verificación end-to-end

**Objetivo:** El fix del JOIN cvegeo_9 está aplicado y verificado con datos reales.

| # | Tarea | Responsable | Criterio de éxito |
|---|---|---|---|
| 0.1.1 | Aplicar migración `0005_add_cvegeo9_index` | Dev | `alembic upgrade head` sin errores |
| 0.1.2 | Verificar JOIN >50,000 matches | Dev | Query SQL confirma >50k |
| 0.1.3 | Generar reporte de prueba (Mérida — Little Caesars vs Domino's) | Dev | El reporte usa AGEBs reales (no H3), `usa_agebs: true` en preview |
| 0.1.4 | Generar reporte CDMX (Benito Juárez) para validar escala | Dev | AGEBs coloreadas por densidad/poder adquisitivo |
| 0.1.5 | Actualizar tests backend para cubrir AGEBs | Dev | Tests unitarios `query_agebs_en_poligono` con datos semilla |

**Definition of Done:**
- `ageb_geometries.cvegeo_9` populado para los 82,283 registros
- Un reporte generado desde el frontend muestra polígonos AGEB (no hexágonos H3)
- KPIs del reporte incluyen `poblacion_alcanzada > 0`

**Riesgo:** El JOIN puede ser lento en polígonos grandes (CDMX completa). Si tarda > 2 min, escalar a Sprint 0.2.

---

### Sprint 0.2 — Completar DENUE + Calidad del backend

**Objetivo:** DENUE con cobertura nacional de los estados clave y backend sin errores silenciosos.

| # | Tarea | Responsable | Criterio de éxito |
|---|---|---|---|
| 0.2.1 | Correr ETL DENUE para estados prioritarios: 09, 14, 15, 19, 21, 31 | Dev | >100k establecimientos adicionales en BD |
| 0.2.2 | Optimizar query AGEBs: agregar hint `ST_Intersects` con índice GIST | Dev | Reporte CDMX < 30 segundos |
| 0.2.3 | Reemplazar `except Exception: pass` restantes en `reporte.py` | Dev | Todos los errores tienen `logger.exception()` |
| 0.2.4 | Lazy health check en `registry.py` (no en import time) | Dev | Startup del servidor < 3 segundos |
| 0.2.5 | Actualizar `00-README.md` con estado real del proyecto | Dev | Tabla de estado refleja realidad al 2026-06-23 |

**Definition of Done:**
- BD tiene >600k establecimientos DENUE en al menos 6 estados
- Reportes de Ciudad de México, Guadalajara, Monterrey, Mérida funcionan correctamente
- No hay `except: pass` en la capa de servicios

---

## FASE 1 — Frontend Enterprise Base

> **Objetivo:** Reemplazar el frontend MVP (react-leaflet + Tailwind básico) con la arquitectura enterprise definida en el Super Prompt. Al terminar, el nuevo frontend replica las funciones del MVP actual pero sobre la base técnica correcta.

**Stack que entra en esta fase:**
- MapLibre GL JS + `react-map-gl` (reemplaza react-leaflet)
- Deck.gl (capas de datos sobre el mapa)
- Shadcn/ui (componentes enterprise)
- Zustand (estado global — ya existe, se migra)
- TanStack Query (cache de API calls)
- Apache ECharts (gráficas)
- Framer Motion (animaciones)
- Turf.js (cálculos geoespaciales en cliente)

---

### Sprint 1.1 — Setup + Layout Principal

**Objetivo:** El nuevo proyecto frontend arranca con el layout enterprise completo (sin funcionalidad real todavía).

| # | Tarea | Criterio de éxito |
|---|---|---|
| 1.1.1 | Nuevo proyecto Vite + TypeScript con todas las dependencias | `npm run dev` funciona |
| 1.1.2 | Tema oscuro enterprise (colores, tipografía Inter, shadcn/ui dark) | Pantalla en dark mode igual que Palantir/CARTO |
| 1.1.3 | TopBar: Logo + Global Search + Selector de proyecto + Perfil | Visible y responsive |
| 1.1.4 | LeftNav: íconos + labels para Dashboard, Site Selector, POI Explorer, Maps, Reports | Navegación entre rutas |
| 1.1.5 | Estructura de carpetas enterprise (`src/modules/`, `src/shared/`) | Arquitectura reflejada en código |
| 1.1.6 | Sistema de routing (React Router v6, rutas protegidas) | Login → / redirige según auth |
| 1.1.7 | Zustand stores: `useAuthStore`, `useMapStore`, `useProjectStore` | State compartido entre módulos |

**Definition of Done:**
- `npm run dev` muestra layout completo en dark mode
- Login funciona con el backend existente
- Navegación entre las 4 secciones principales funciona (aunque estén vacías)

---

### Sprint 1.2 — Mapa Base + Funcionalidad MVP migrada

**Objetivo:** El mapa con MapLibre GL funciona igual que el MVP actual.

| # | Tarea | Criterio de éxito |
|---|---|---|
| 1.2.1 | Mapa MapLibre GL con tiles MapTiler Streets v2 | Mapa renderiza en el 70% del viewport |
| 1.2.2 | Selector Estado → Municipio (dropdowns + fly-to) | Seleccionar Mérida navega el mapa |
| 1.2.3 | Herramienta de dibujo de polígono (reemplaza leaflet-draw) | Se puede dibujar polígono y rectángulo |
| 1.2.4 | Overlay de AGEBs coloreadas (Deck.gl GeoJsonLayer) | Al generar reporte, polígonos de AGEBs aparecen |
| 1.2.5 | Overlay de puntos DENUE (Deck.gl ScatterplotLayer) | Puntos por capa con el color correcto |
| 1.2.6 | TanStack Query para todos los API calls | Cache de catálogo de estados/municipios |
| 1.2.7 | Widget contexto económico BIE migrado | Aparece al seleccionar estado |

**Definition of Done:**
- Se puede completar un análisis completo (seleccionar zona → capas → generar → ver en mapa)
- Performance: el mapa no se congela con 82k AGEBs en viewport
- El flujo MVP existente funciona 100% en el nuevo stack

---

### Sprint 1.3 — Sistema de Capas + Visualizaciones

**Objetivo:** El RightPanel tiene el sistema completo de KPIs y control de capas.

| # | Tarea | Criterio de éxito |
|---|---|---|
| 1.3.1 | RightPanel dinámico (se abre/cierra con animación Framer Motion) | Transición suave |
| 1.3.2 | KPI cards con ECharts (total establecimientos, zonas, población) | Gráficas micro de tendencia |
| 1.3.3 | Layer Control: toggle de visibilidad por capa + opacidad | Cada capa tiene su toggle |
| 1.3.4 | Distribución por nivel (PREMIUM/ALTA/etc.) con ECharts Donut | Donut chart visible en RightPanel |
| 1.3.5 | Top 10 zonas por concentración con tabla TanStack Table | Tabla ordenable y filtrable |
| 1.3.6 | Heatmap de densidad con Deck.gl HeatmapLayer (toggle) | Activar/desactivar heatmap sobre el mapa |

**Definition of Done:**
- El RightPanel muestra todos los KPIs después de un análisis
- El usuario puede comparar visualmente capas activando/desactivando
- El heatmap es visualmente impactante (referencia: CARTO/Kepler.gl)

---

## FASE 2 — Site Selector (Módulo Core)

> **Objetivo:** Implementar el módulo más importante de la plataforma. Al terminar esta fase, hay un producto demostrable a clientes.

---

### Sprint 2.1 — Score de Potencial + Heatmap

**Objetivo:** Cada AGEB tiene un Score de Potencial y el mapa lo muestra como heatmap.

| # | Tarea | Criterio de éxito |
|---|---|---|
| 2.1.1 | Algoritmo de Score en backend (ponderación: densidad 40% + poder adquisitivo 30% + vacío competitivo 30%) | Endpoint `GET /api/v1/site-selector/score?polygon=...` |
| 2.1.2 | Nueva tabla `analytics.ageb_score` (score 0-100, componentes) | Migración `0006_ageb_score` aplicada |
| 2.1.3 | Heatmap de Score con Deck.gl HeatmapLayer (verde-amarillo-rojo) | Score visible sobre el mapa en Site Selector |
| 2.1.4 | Panel lateral: Top 20 AGEBs por score con ranking | Lista ordenada en RightPanel |
| 2.1.5 | Tooltip en AGEB: Score, NSE, Población, Establecimientos | Al hover sobre un AGEB, aparece el tooltip |

**Definition of Done:**
- El mapa muestra el heatmap de potencial de forma inmediata (< 5 segundos)
- La lista de Top 20 AGEBs es ordenable por score
- El score tiene interpretación textual ("Alta oportunidad", "Zona saturada", etc.)

---

### Sprint 2.2 — Cuadrantes + Comparación de Zonas

**Objetivo:** El usuario puede comparar dos zonas y ver cuáles cuadrantes tienen mayor potencial.

| # | Tarea | Criterio de éxito |
|---|---|---|
| 2.2.1 | Sistema de cuadrantes sobre el mapa (grid semafórica) | Verde/amarillo/rojo visibles al zoom city-level |
| 2.2.2 | Herramienta "Comparar zonas": dibujar 2 polígonos y ver métricas lado a lado | Panel split con KPIs de Zona A vs Zona B |
| 2.2.3 | Filtros en Site Selector: NSE mínimo, score mínimo, distancia a competencia | Aplicables en tiempo real sobre el mapa |
| 2.2.4 | Análisis de canibalización (radio 500m/1km/5km configurable) | Al seleccionar un punto, muestra sucursales propias en el radio |
| 2.2.5 | Tabla de resultados con TanStack Table (exportable a CSV) | Tabla descargable desde el RightPanel |

**Definition of Done:**
- El usuario puede identificar visualmente los 3 mejores cuadrantes en cualquier ciudad
- La comparación de zonas funciona con cualquier polígono
- La tabla es exportable a CSV

---

### Sprint 2.3 — Export PDF + Pulido de Site Selector

**Objetivo:** El Site Selector está completo y produce reportes PDF para entregar a clientes.

| # | Tarea | Criterio de éxito |
|---|---|---|
| 2.3.1 | Export PDF del análisis Site Selector (librería: `@react-pdf/renderer` o `puppeteer`) | PDF descargable con mapa + tabla Top 20 + KPIs |
| 2.3.2 | Export PNG del viewport del mapa | Screenshot del estado actual del mapa |
| 2.3.3 | Diseño del PDF: logo, portada, tabla de zonas, mapa, métricas clave | Diseño corporativo premium |
| 2.3.4 | Guardar análisis en historial (`analytics.zona_analysis_results`) | El usuario puede ver sus últimos 20 análisis |
| 2.3.5 | UX Polish: loading states, empty states, errores amigables en Site Selector | Sin pantallas en blanco o errores técnicos visibles al usuario |

**Definition of Done:**
- Se puede hacer un análisis completo en Site Selector y descargar un PDF ejecutivo
- El PDF tiene diseño profesional (no texto plano)
- **Hito de demo:** se puede mostrar el producto a un cliente potencial al final de este sprint

---

## FASE 3 — POI Explorer

> **Objetivo:** El usuario puede seleccionar cualquier establecimiento en el mapa y ver métricas de su zona de influencia.

---

### Sprint 3.1 — Selección de POI + Zona de Influencia

**Objetivo:** Click en cualquier punto del mapa abre un panel con métricas del POI.

| # | Tarea | Criterio de éxito |
|---|---|---|
| 3.1.1 | Click en establecimiento DENUE abre panel POI en RightPanel | Panel animado con datos del negocio |
| 3.1.2 | Zona de influencia configurable: radio 500m, 1km, 5km (isócrona aproximada con círculo) | Círculo de influencia visible en el mapa |
| 3.1.3 | Métricas de la zona: establecimientos similares en radio, demografía, NSE promedio | Indicadores numéricos en panel |
| 3.1.4 | Listado de competidores dentro del radio (tabla TanStack) | Tabla filtrable por actividad económica |
| 3.1.5 | Endpoint backend: `GET /api/v1/poi/{clee}/zona-influencia?radio_km=1` | Respuesta < 2 segundos |

**Definition of Done:**
- Click en cualquier establecimiento del mapa abre el panel POI en < 1 segundo
- Los competidores del radio se muestran correctamente
- El radio de influencia es ajustable sin recargar la página

---

### Sprint 3.2 — Análisis de Audiencias + Comparación de POIs

**Objetivo:** El usuario puede ver el perfil de audiencia de un POI y comparar dos puntos.

| # | Tarea | Criterio de éxito |
|---|---|---|
| 3.2.1 | Panel de audiencia estimada: NSE, rango de edad, género (datos Censo + heurísticas) | Barras y donut charts en ECharts |
| 3.2.2 | Herramienta "Comparar POIs": seleccionar 2 puntos y ver métricas comparativas | Layout split en RightPanel |
| 3.2.3 | Score de atractivo del POI (combinación de demografía + competencia + flujo de personas estimado) | Score 0-100 con interpretación |
| 3.2.4 | Export PDF del análisis POI | Descargable, mismo template que Site Selector |
| 3.2.5 | Placeholder para datos reales de movilidad (Veraset/Unacast) | Componente diseñado, datos = Censo por ahora |

**Definition of Done:**
- La comparación entre 2 POIs funciona visualmente
- El score de atractivo tiene una interpretación de texto clara
- Los gráficos de audiencia se renderizan correctamente

---

## FASE 4 — Reportes Ejecutivos

> **Objetivo:** El usuario puede generar un reporte ejecutivo con los datos visibles en pantalla en cualquier módulo.

---

### Sprint 4.1 — Sistema de Reportes Premium

| # | Tarea | Criterio de éxito |
|---|---|---|
| 4.1.1 | Botón "Generar Reporte" disponible en todos los módulos | Visible en TopBar o dentro de cada módulo |
| 4.1.2 | Template PDF ejecutivo (portada + resumen + mapa + tablas + gráficas) | Diseño premium con logo y colores del sistema |
| 4.1.3 | Exportar vista actual del mapa como PNG (screenshot automático) | Captura del estado exacto del mapa al momento de generar |
| 4.1.4 | Excel mejorado: una hoja por sección, gráficas embebidas | Compatible con Excel 2016+ |
| 4.1.5 | Historial de reportes generados (últimos 20, descargables) | Panel en la sección Reports de LeftNav |

**Definition of Done:**
- Se puede generar un PDF completo desde Site Selector y desde POI Explorer
- El PDF tiene logo, portada, mapa, tablas y gráficas
- El tiempo de generación es < 15 segundos

---

## FASE 5 — SaaS / Producción

> **Objetivo:** La plataforma está desplegada en la nube, accesible desde cualquier navegador, con CI/CD automático.

---

### Sprint 5.1 — Despliegue Cloud

| # | Tarea | Criterio de éxito |
|---|---|---|
| 5.1.1 | Base de datos en Render PostgreSQL (o Supabase) + migrar datos | Todas las migraciones aplicadas en producción |
| 5.1.2 | Backend en Render.com (FastAPI + Gunicorn) | `https://api.predik-geo.com/health` responde |
| 5.1.3 | Frontend en Vercel (build Vite) | `https://app.predik-geo.com` carga el login |
| 5.1.4 | Variables de entorno configuradas: DB, JWT secret, INEGI token, MapTiler key | Sin credenciales en código |
| 5.1.5 | CI/CD: GitHub Actions — test + lint + deploy en push a `main` | Pipeline verde en < 5 minutos |

**Definition of Done:**
- La plataforma es accesible desde cualquier computadora con navegador
- El pipeline CI/CD funciona automáticamente
- No hay datos sensibles en el repositorio

---

### Sprint 5.2 — Multi-tenant + Planes SaaS

| # | Tarea | Criterio de éxito |
|---|---|---|
| 5.2.1 | Auth multi-tenant: cada organización tiene su namespace | Organización A no ve datos de Organización B |
| 5.2.2 | Planes: Starter (50 consultas/mes), Basic (500), Plus (5,000) | Definidos en tabla `core.organizations` |
| 5.2.3 | Rate limiting activado con `RATE_LIMIT_ENABLED=true` | El límite se aplica correctamente |
| 5.2.4 | Onboarding de nuevo cliente: endpoint `POST /api/v1/admin/organizaciones` | Se puede crear un cliente desde el panel admin |
| 5.2.5 | Panel Admin mejorado: estado de BD, lista de organizaciones, uso mensual | Visible solo para rol `admin` |

**Definition of Done:**
- Se puede crear un nuevo cliente en < 5 minutos
- El rate limiting no bloquea análisis normales (verificar la lógica de doble conteo preview+generar)
- El sistema está listo para tener más de 1 organización usando la plataforma simultáneamente

---

## 4. Dependencias entre sprints

```
Sprint 0.1 ──┐
             ├──► Sprint 0.2 ──┐
                               ├──► Sprint 1.1 ──► Sprint 1.2 ──► Sprint 1.3
                               │                                        │
                               │                                        ▼
                               │                               Sprint 2.1 ──► 2.2 ──► 2.3
                               │                                                         │
                               │                                                         ▼
                               │                                               Sprint 3.1 ──► 3.2
                               │                                                                │
                               │                                                                ▼
                               │                                                        Sprint 4.1
                               │                                                                │
                               │                                                                ▼
                               └──────────────────────────────────────────────────► Sprint 5.1 ──► 5.2
```

---

## 5. Backlog de deuda técnica (no bloqueante, atacar entre sprints)

| ID | Deuda | Sprint sugerido |
|---|---|---|
| DT-01 | Isócronas reales (reemplazar radio circular con tiempo de manejo) | Entre 3.1 y 3.2 |
| DT-02 | Datos de movilidad reales (Veraset / Unacast / INEGI ENIM) | Fase 3 o posterior |
| DT-03 | Cache Redis para queries de AGEBs repetidas | 0.2 o 1.2 |
| DT-04 | Lazy health check en `registry.py` | 0.2 |
| DT-05 | Scoring IA real (modelo ML en lugar de ponderación fija) | Post Fase 2 |
| DT-06 | Tests de integración para el nuevo frontend | 1.2 |
| DT-07 | Monitoreo en producción (Sentry + Uptime Kuma) | 5.1 |
| DT-08 | Auditoría de seguridad JWT (rotación de secretos, blacklist de tokens) | 5.2 |

---

## 6. KPIs de seguimiento del proyecto

| KPI | Sprint 0 | Sprint 2 (demo) | Sprint 5 (MVP prod) |
|---|---|---|---|
| AGEBs con geometría + demografía | >50,000 | >50,000 | >50,000 |
| Establecimientos DENUE en BD | >600k | >1M | >2M |
| Tiempo de generación de reporte | < 60 seg | < 30 seg | < 15 seg |
| Módulos funcionales | 1 (Reportes) | 2 (+ Site Selector) | 4 (todos) |
| Organizaciones activas en prod | 0 | 0 | ≥ 1 (Arturo + piloto) |
| Tests automatizados backend | >49 | >80 | >120 |
| Cobertura de estados con DENUE | 6 | 16 | 32 |

---

## 7. Velocidad estimada y duración total

| Formato de trabajo | Duración estimada |
|---|---|
| Sesiones diarias de ~2h | 13 semanas (≈ 3 meses) |
| Sesiones intensivas (4–6h) | 7–8 semanas (≈ 2 meses) |
| Solo fines de semana | 6–7 meses |

**Recomendación:** Sesiones de 2–3 horas, 4–5 días por semana. El bloqueo principal no es el código sino las cargas de datos (ETL pesados en hardware local).

---

## 8. Riesgos del proyecto

| Riesgo | Probabilidad | Impacto | Mitigación |
|---|---|---|---|
| Hardware local no aguanta ETL DENUE completo | Alta | Alto | Correr ETL en segmentos (1 estado a la vez), o migrar BD a la nube antes de cargar |
| API INEGI DENUE cambia o cae | Media | Alto | Cache agresivo en BD; no depender de la API para reportes ya generados |
| Performance del JOIN AGEBs en polígonos grandes | Media | Medio | Índices GIST + limitar polígonos a nivel municipio/colonia, no estados completos |
| Datos de movilidad/afluencia no disponibles sin costo | Alta | Medio | Usar Censo 2020 como proxy para NSE/demografía; movilidad = backlog futuro |
| Deuda técnica por el doble conteo preview+generar en rate limiter | Baja | Bajo | Documentado, resolver en Sprint 5.2 antes de activar rate limiting |

---

*Documento creado: 2026-06-23 | Versión: 1.0*
*Actualizar al inicio de cada sprint con el estado real vs planeado.*
