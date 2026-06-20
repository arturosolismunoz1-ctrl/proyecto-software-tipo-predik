# 03. Especificación de APIs

Todas las APIs siguen REST sobre JSON, versionadas bajo `/api/v1/`. Documentación interactiva auto-generada vía FastAPI en `/docs` (Swagger) y `/redoc` en cada ambiente.

## 3.1 Convenciones generales

- **Auth:** Bearer Token (JWT) en header `Authorization: Bearer <token>`, excepto endpoints públicos de salud.
- **Formato de polígonos:** GeoJSON estándar (`Polygon` / `Point` + `radius_meters`).
- **Errores:** formato uniforme:
```json
{
  "error": {
    "code": "ZONA_SIN_COBERTURA",
    "message": "La zona consultada no tiene datos disponibles en esta geografía.",
    "details": {}
  }
}
```
- **Paginación:** `?page=1&page_size=50` en endpoints que listan colecciones.
- **Versionado:** breaking changes implican `/api/v2/`, nunca se modifica el contrato de `/v1/` en producción.

## 3.2 Endpoint: Concentración Comercial

```
POST /api/v1/zona/concentracion-comercial
```

**Request:**
```json
{
  "geometry": {
    "type": "Polygon",
    "coordinates": [[[-89.62, 20.97], [-89.60, 20.97], [-89.60, 20.95], [-89.62, 20.95], [-89.62, 20.97]]]
  },
  "filtros": {
    "categorias": ["Restaurantes", "Retail"],
    "zoom_level": 14
  }
}
```

**Response 200:**
```json
{
  "zona": {
    "entidad": "Yucatán",
    "municipio": "Mérida",
    "area_km2": 1.42
  },
  "total_establecimientos": 137,
  "por_categoria": [
    { "categoria": "Servicios de preparación de alimentos y bebidas", "codigo_scian": "722", "cantidad": 45 },
    { "categoria": "Comercio al por menor", "codigo_scian": "461", "cantidad": 30 }
  ],
  "negocios_ancla": [
    { "nombre": "Plaza Comercial X", "categoria": "Centro comercial", "lat": 20.96, "lon": -89.61 }
  ],
  "celdas_heatmap": [
    { "h3_index": "8a2a1072b59ffff", "intensidad": 0.82, "geom": "..." }
  ],
  "analysis_id": "uuid-para-recuperar-este-resultado-despues"
}
```

**Errores posibles:**
| Código HTTP | `error.code` | Causa |
|---|---|---|
| 400 | `GEOMETRIA_INVALIDA` | El polígono no es válido (auto-intersección, vacío) |
| 404 | `ZONA_SIN_COBERTURA` | La geografía no tiene datos DENUE disponibles |
| 429 | `LIMITE_CONSULTAS_EXCEDIDO` | El usuario/organización excedió su cuota del plan |

## 3.3 Endpoint: Densidad Poblacional

```
POST /api/v1/zona/densidad-poblacional
```

**Request:** mismo formato de `geometry` que el endpoint anterior.

**Response 200:**
```json
{
  "poblacion_total": 1366,
  "total_hogares": 471,
  "distribucion_edad": { "0-14": 0.18, "15-24": 0.18, "25-49": 0.35, "50-60": 0.10, "60+": 0.19 },
  "distribucion_genero": { "hombre": 0.46, "mujer": 0.54 },
  "distribucion_nse": { "AB": 0.05, "C+": 0.20, "C": 0.30, "C-": 0.20, "D+": 0.15, "D": 0.08, "E": 0.02 }
}
```

## 3.4 Endpoint: gestión de conectores (admin)

```
GET  /api/v1/admin/conectores                  → lista conectores registrados y su estado
POST /api/v1/admin/conectores/{nombre}/sync     → dispara sincronización manual
GET  /api/v1/admin/conectores/{nombre}/health   → health check individual
```

**Response de `GET /conectores`:**
```json
{
  "conectores": [
    { "nombre": "inegi_denue", "ultima_sincronizacion": "2026-06-19T03:00:00Z", "estado": "ok", "registros": 482931 },
    { "nombre": "inegi_censo", "ultima_sincronizacion": "2026-06-19T03:15:00Z", "estado": "ok", "registros": 12044 },
    { "nombre": "google_places", "ultima_sincronizacion": null, "estado": "no_configurado", "registros": 0 }
  ]
}
```

## 3.5 Endpoint: análisis guardados

```
GET  /api/v1/analisis                  → lista análisis previos del usuario/organización
GET  /api/v1/analisis/{analysis_id}    → recupera un análisis guardado completo
DELETE /api/v1/analisis/{analysis_id}  → elimina un análisis guardado
```

## 3.6 Endpoints de salud y autenticación

```
GET  /api/v1/health            → estado general del sistema (DB, conectores críticos)
POST /api/v1/auth/login        → autenticación, devuelve JWT
POST /api/v1/auth/refresh      → renueva token
```

## 3.7 Contrato del Conector Genérico (interno, no HTTP público)

Para que cualquier desarrollador agregue una fuente nueva sin tocar el core, todo conector debe implementar:

```python
class BaseConnector(ABC):
    name: str
    requires_auth: bool

    async def fetch(self, polygon: Polygon, **params) -> list[GeoFeature]: ...
    def health_check(self) -> bool: ...
```

Ver `01-arquitectura-del-sistema.md` y `06-decisiones-tecnicas-adr.md` (ADR-002) para el razonamiento detrás de este contrato.
