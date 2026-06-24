# Reporte de Avance — Predik-Geo SaaS
**Corte:** 2026-06-24 | **Rol:** SCRUM Master + PM  
**Actualizar:** Al inicio de cada sprint o cuando cambie el estado de una fase.

---

## Tablero ejecutivo

| Indicador | Valor |
|---|---|
| **Avance global del producto final** | **38%** |
| **Avance dentro del plan de sprints** | **9%** (1.2 de 13 sprints cerrados) |
| **Velocidad real** | ~2 sprints equivalentes / mes de trabajo intensivo |
| **ETA Demo a clientes** | Semana 8 desde hoy (cierre Sprint 2.3) |
| **ETA MVP en producción** | Semana 13 desde hoy (cierre Sprint 5.2) |
| **Estado semáforo** | 🟡 EN RIESGO — data pipeline y frontend enterprise son cuellos de botella |

---

## Desglose de avance global (38%)

```
Backend API (peso 15%)             ████████████████░░  90% →  13.5 pts
ETL / Data pipeline (peso 10%)     ████████░░░░░░░░░░  65% →   6.5 pts
Frontend MVP (peso 5%)             ████████████████░░  88% →   4.4 pts
Manzanas / granularidad (peso 5%)  █████████░░░░░░░░░  65% →   3.3 pts
Frontend Enterprise (peso 15%)     ░░░░░░░░░░░░░░░░░░   0% →   0.0 pts
Site Selector (peso 20%)           ░░░░░░░░░░░░░░░░░░   0% →   0.0 pts
POI Explorer (peso 15%)            ░░░░░░░░░░░░░░░░░░   0% →   0.0 pts
Reportes PDF premium (peso 5%)     ██░░░░░░░░░░░░░░░░  15% →   0.8 pts
Cloud / SaaS (peso 10%)            ░░░░░░░░░░░░░░░░░░   0% →   0.0 pts
──────────────────────────────────────────────────────────────────
TOTAL                                                    38.5 / 100
```

---

## Estado por fase y sprint

### FASE 0 — Cierre técnico y estabilización
> Semanas 1–2 del plan | **Avance: 60%**

#### Sprint 0.1 — Fix JOIN + Verificación end-to-end | 60% ✅

| Tarea | Estado | Notas |
|---|---|---|
| 0.1.1 Migración `0005_add_cvegeo9_index` | ✅ CERRADO | 82,283 registros actualizados |
| 0.1.2 Verificar JOIN >50k matches | ✅ CERRADO | 63,876 matches confirmados |
| 0.1.3 Reporte Mérida con AGEBs reales | ✅ CERRADO | Little Caesars vs Domino's con polígonos AGEB |
| 0.1.4 Reporte CDMX para validar escala | ❌ PENDIENTE | No verificado con polígono grande |
| 0.1.5 Tests unitarios `query_agebs_en_poligono` | ❌ PENDIENTE | Tests no actualizados |

**Tareas extra completadas fuera del plan (sesión 9):**
- ✅ CRS bug fix EPSG:6372→4326 — sin esto los AGEBs nunca aparecían en ningún reporte
- ✅ Soporte nivel manzana completo — backend + API + frontend con parámetro `nivel_geografico`
- ✅ Fix BIE ImportError al arrancar el servidor
- ✅ Performance subquery DENUE — de timeout a 0.8 segundos
- ✅ Fix HTTP 500 en endpoint manzanas — GROUP BY en columna JSON + rollback de transacción

#### Sprint 0.2 — DENUE + Calidad de backend | 60% ✅

| Tarea | Estado | Notas |
|---|---|---|
| 0.2.1 ETL DENUE estados prioritarios (09, 14, 15, 19, 21, 31) | ❌ PENDIENTE | Sigue en ~528k establecimientos |
| 0.2.2 Optimizar query AGEBs con subquery | ✅ CERRADO | Pre-filtra DENUE antes del JOIN espacial |
| 0.2.3 Reemplazar `except: pass` con `logger.exception` | ✅ CERRADO | Incluye `db.rollback()` por cascada de transacción |
| 0.2.4 Lazy health check en `registry.py` | ❌ PENDIENTE | Sigue ejecutando HTTP a INEGI al importar el módulo |
| 0.2.5 Actualizar `00-README.md` | ✅ CERRADO | Estado refleja la realidad al 2026-06-24 |

---

### FASE 1 — Frontend Enterprise Base
> Semanas 3–5 | **Avance: 0%** 🔲

| Sprint | Avance | Estado |
|---|---|---|
| 1.1 Setup + Layout Principal (dark mode, shadcn/ui, TopBar, LeftNav) | 0% | NO INICIADO |
| 1.2 Mapa MapLibre GL + MVP migrado (Deck.gl, TanStack Query) | 0% | NO INICIADO |
| 1.3 Sistema de capas + KPI panel enterprise + ECharts + heatmap | 0% | NO INICIADO |

> El MVP actual con react-leaflet queda operativo como fallback. El Enterprise frontend es una construcción nueva sobre el mismo backend — no un refactor.

---

### FASE 2 — Site Selector (módulo core del SaaS)
> Semanas 6–8 | **Avance: 0%** 🔲

| Sprint | Avance | Estado |
|---|---|---|
| 2.1 Score de potencial + heatmap | 0% | NO INICIADO |
| 2.2 Cuadrantes + comparación de zonas + filtros | 0% | NO INICIADO |
| 2.3 Export PDF + pulido ← **HITO: DEMO A CLIENTES** | 0% | NO INICIADO |

---

### FASE 3 — POI Explorer
> Semanas 9–10 | **Avance: 0%** 🔲

| Sprint | Avance | Estado |
|---|---|---|
| 3.1 Selección de POI + zona de influencia | 0% | NO INICIADO |
| 3.2 Análisis de audiencias + comparación de POIs | 0% | NO INICIADO |

---

### FASE 4 — Reportes Ejecutivos
> Semana 11 | **Avance: 20%** 🔲

| Sprint | Avance | Estado | Nota |
|---|---|---|---|
| 4.1 PDF premium + Export PNG + Excel mejorado + historial | 20% | PARCIAL | Backend KMZ/Excel ya funciona; PDF premium y PNG = 0% |

---

### FASE 5 — SaaS / Producción
> Semanas 12–13 | **Avance: 0%** 🔲

| Sprint | Avance | Estado |
|---|---|---|
| 5.1 Despliegue cloud (Render + Vercel + CI/CD) | 0% | NO INICIADO |
| 5.2 Multi-tenant + planes SaaS + rate limiting | 0% | NO INICIADO |

---

## Ruta crítica

La secuencia que determina la fecha del demo a clientes (semana 8) y del MVP en producción (semana 13). **No hay paralelismo posible entre estos pasos.**

```
[HOY] Cerrar Sprint 0.2
        │
        ▼
 ETL DENUE estados clave              ← CUELLO DE BOTELLA 1
 (09 CDMX / 14 Jalisco / 15 Edomex)    Sin datos = sin valor de demo
        │
        ▼
 Sprint 1.1 Setup Enterprise          ← CUELLO DE BOTELLA 2
 (todo el frontend depende de aquí)     2 semanas reales estimadas
        │
        ▼
 Sprint 1.2 MapLibre GL + MVP migrado
        │
        ▼
 Sprint 1.3 KPI Panel enterprise
        │
        ▼
 Sprint 2.1 Score de potencial
        │
        ▼
 Sprint 2.2 Comparación de zonas
        │
        ▼
 Sprint 2.3 PDF Export                ← HITO: DEMO A CLIENTES (semana 8)
        │
        ▼
 Sprint 5.1 Cloud deployment
        │
        ▼
 Sprint 5.2 Multi-tenant              ← HITO: MVP EN PRODUCCIÓN (semana 13)
```

**Único trabajo paralelizable:** El ETL de datos (DENUE + manzanas restantes) puede correr en background mientras se construye el frontend enterprise.

---

## Riesgos

| # | Riesgo | Prob | Impacto | Estado | Mitigación |
|---|---|---|---|---|---|
| R1 | **ETL DENUE incompleto** — 528k estab. de ~6 estados. Sin CDMX, GDL, MTY el Site Selector no tiene valor de demo | 🔴 Alta | 🔴 Alto | **ACTIVO** | Correr ETL estados 09/14/15 antes de iniciar Fase 1 |
| R2 | **Frontend Enterprise subestimado** — MapLibre + Deck.gl + shadcn/ui es stack nuevo. Sprints 1.1–1.3 probablemente toman el doble | 🔴 Alta | 🟡 Medio | **LATENTE** | Planear 2 semanas por sprint de Fase 1 en lugar de 1 |
| R3 | **Manzanas sin cobertura nacional** — 25/32 estados con 0 manzanas | 🟡 Media | 🟡 Medio | **ACTIVO** | ETL en background. No promover el feature en demo hasta tener CDMX + GDL + MTY |
| R4 | **Hardware local para ETL pesado** — DENUE completo (32 estados × 20 sectores) puede colapsar la máquina | 🟡 Media | 🔴 Alto | **CONOCIDO** | Correr 1 estado a la vez, de noche. Migrar BD a nube antes de Sprint 5.1 |
| R5 | **API INEGI DENUE inestable** — algunos keywords causan abort de conexión | 🟡 Media | 🟡 Medio | **CONOCIDO** | Retry logic + los datos ya cargados en BD son suficientes para operar |
| R6 | **Sin datos de afluencia real** — NSE se infiere por escolaridad/infraestructura, no movilidad | 🔴 Alta | 🟡 Medio | **ESTRUCTURAL** | Encuadrar el producto como "inteligencia censal geoespacial", no "afluencia". Movilidad = backlog |
| R7 | **Deuda técnica en producción** — lazy health check, tests desactualizados, rate limiter con doble conteo | 🟡 Media | 🟡 Medio | **ACTIVO** | Atacar en Sprint 0.2 antes de iniciar Fase 1 |

---

## Backlog de deuda técnica (no bloqueante)

| ID | Deuda | Sprint sugerido |
|---|---|---|
| DT-01 | Isócronas reales (reemplazar radio circular con tiempo de manejo) | Entre 3.1 y 3.2 |
| DT-02 | Datos de movilidad reales (Veraset / INEGI ENIM) | Fase 3 o posterior |
| DT-03 | Cache Redis para queries de AGEBs repetidas | 0.2 o 1.2 |
| DT-04 | Lazy health check en `registry.py` | 0.2 |
| DT-05 | Scoring IA real (modelo ML en lugar de ponderación fija) | Post Fase 2 |
| DT-06 | Tests de integración para el frontend enterprise | 1.2 |
| DT-07 | Monitoreo en producción (Sentry + Uptime Kuma) | 5.1 |
| DT-08 | Auditoría de seguridad JWT (rotación de secretos, blacklist) | 5.2 |
| DT-09 | Rate limiter: resolver doble conteo preview+generar | 5.2 (antes de activar) |

---

## KPIs de seguimiento del proyecto

| KPI | Hoy (2026-06-24) | Meta Sprint 2 (demo) | Meta Sprint 5 (prod) |
|---|---|---|---|
| AGEBs con geometría + demografía | **63,876** | >50,000 ✅ | >50,000 ✅ |
| Establecimientos DENUE en BD | **~528k** | >1M ❌ | >2M ❌ |
| Manzanas cargadas | **352,884** (7/32 estados) | >1M (15+ estados) | cobertura nacional |
| Tiempo de generación de reporte | **~5 seg** | <30 seg ✅ | <15 seg |
| Módulos funcionales | **1** (Reportes MVP) | 2 (+ Site Selector) | 4 (todos) |
| Estados con DENUE | **~6** | 16 | 32 |
| Organizaciones en producción | **0** | 0 | ≥1 (piloto) |
| Tests automatizados backend | **49+** | >80 | >120 |

---

## Sprint backlog próximas 2 semanas

**Para desbloquear la ruta crítica:**

| Prioridad | Tarea | Impacto |
|---|---|---|
| 🔴 1 | ETL DENUE estados 09 (CDMX), 14 (Jalisco), 15 (Edomex) | Desbloquea valor de demo en las 3 ciudades más importantes |
| 🔴 2 | ETL manzanas restantes (25 estados en background) | Completa el feature de granularidad fina |
| 🟡 3 | Lazy health check en `registry.py` | Elimina deuda técnica antes de Fase 1 |
| 🟡 4 | Tests unitarios `query_agebs_en_poligono` | Cierra DoD del Sprint 0.1 |
| 🟡 5 | Reporte CDMX Benito Juárez (verificar escala) | Cierra DoD del Sprint 0.1 |
| 🟢 6 | Iniciar Sprint 1.1 — setup enterprise frontend | Arranca la ruta crítica principal |

---

*Documento creado: 2026-06-24 | Versión: 1.0*  
*Actualizar: al inicio de cada sprint con estado real vs planeado.*
