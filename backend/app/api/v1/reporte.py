"""
Endpoint de generacion de reportes geoespaciales.

POST /api/v1/reporte/generar
  Recibe un poligono, una o mas capas de busqueda con colores,
  corre ETL, clasifica hexagonos y devuelve KMZ o Excel.

No se necesitan scripts ad-hoc: este endpoint es el punto unico
de entrada para cualquier busqueda.
"""
from typing import Any, Dict, List, Literal, Optional

from fastapi import APIRouter, Depends
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.deps import get_db, get_current_user
from app.rate_limit import check_rate_limit
from app.services.reporte import generar_reporte, preview_reporte

router = APIRouter()


# ── Schemas ────────────────────────────────────────────────────────────────────

class CapaBusqueda(BaseModel):
    keyword: str = Field(
        ...,
        description="Termino de busqueda (nombre, marca o tipo de negocio). Ej: 'burger king', 'papeleria', 'farmacia'",
        examples=["burger king"],
    )
    label: str = Field(
        ...,
        description="Nombre visible en el reporte para esta capa",
        examples=["Burger King"],
    )
    color: Literal["red", "green", "blue", "yellow", "orange", "purple", "cyan", "pink"] = Field(
        default="blue",
        description="Color de los puntos en el mapa",
    )
    estado: str = Field(
        default="09",
        description="Codigo de entidad INEGI (2 digitos). Ej: '09'=CDMX, '14'=Jalisco, '15'=EdoMex",
        examples=["14"],
    )
    icon: Literal["circle", "star"] = Field(
        default="circle",
        description="Tipo de icono en el mapa. 'star' para marcas propias, 'circle' para competencia",
    )
    scian_prefix: Optional[str] = Field(
        default=None,
        description="Prefijo SCIAN para filtro adicional. Ej: '4611' = farmacias",
    )


class Geometry(BaseModel):
    type: str
    coordinates: List[Any]


class ReporteRequest(BaseModel):
    nombre: str = Field(
        default="Reporte geoespacial",
        description="Titulo del reporte",
    )
    polygon: Geometry = Field(
        ...,
        description="Poligono GeoJSON del area de analisis",
    )
    capas: List[CapaBusqueda] = Field(
        ...,
        min_length=1,
        max_length=8,
        description="Una o mas capas de busqueda. Cada capa = un tipo/marca de negocio",
    )
    formato: Literal["kmz", "excel"] = Field(
        default="kmz",
        description="Formato de salida",
    )
    clasificacion_hexagonos: Literal["densidad", "oportunidad", "poder_adquisitivo"] = Field(
        default="densidad",
        description=(
            "densidad: colorea segun cantidad de establecimientos. "
            "oportunidad: verde=zona libre (alta oportunidad), rojo=saturada con todas las cadenas. "
            "poder_adquisitivo: clasifica AGEBs por escolaridad promedio INEGI (zonas premium)"
        ),
    )
    max_records: int = Field(default=2500, ge=1, le=2500)
    h3_resolution: int = Field(default=9, ge=7, le=11)
    ejecutar_etl: bool = Field(
        default=True,
        description="False para usar datos ya cargados en DB (omite la llamada a INEGI)",
    )
    nivel_geografico: Literal["ageb", "manzana"] = Field(
        default="ageb",
        description=(
            "ageb: zonas a nivel AGEB (~1km²) con demografía Censo 2020. "
            "manzana: máxima granularidad (~100m²) con datos de vivienda e infraestructura."
        ),
    )


# ── Endpoint ───────────────────────────────────────────────────────────────────

@router.post(
    "/generar",
    summary="Generar reporte geoespacial (KMZ o Excel)",
    response_description="Archivo KMZ o Excel listo para descargar",
)
async def generar_reporte_endpoint(
    request: ReporteRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    _rl: None = Depends(check_rate_limit),
):
    polygon = {"type": request.polygon.type, "coordinates": request.polygon.coordinates}
    capas = [c.model_dump() for c in request.capas]

    archivo = await generar_reporte(
        db=db,
        organization_id=current_user["org_id"],
        nombre=request.nombre,
        polygon=polygon,
        capas=capas,
        formato=request.formato,
        clasificacion_hexagonos=request.clasificacion_hexagonos,
        max_records=request.max_records,
        h3_resolution=request.h3_resolution,
        ejecutar_etl=request.ejecutar_etl,
        nivel_geografico=request.nivel_geografico,
    )

    if request.formato == "kmz":
        filename = f"{request.nombre.replace(' ', '_')}.kmz"
        return Response(
            content=archivo,
            media_type="application/vnd.google-earth.kmz",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )
    else:
        filename = f"{request.nombre.replace(' ', '_')}.xlsx"
        return Response(
            content=archivo,
            media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            headers={"Content-Disposition": f'attachment; filename="{filename}"'},
        )


@router.post(
    "/preview",
    summary="Preview del reporte en GeoJSON para visualización en mapa",
    response_description="GeoJSON con zonas coloreadas + puntos + KPIs",
)
async def preview_reporte_endpoint(
    request: ReporteRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    _rl: None = Depends(check_rate_limit),
):
    polygon = {"type": request.polygon.type, "coordinates": request.polygon.coordinates}
    capas = [c.model_dump() for c in request.capas]

    resultado = await preview_reporte(
        db=db,
        organization_id=current_user["org_id"],
        polygon=polygon,
        capas=capas,
        clasificacion_hexagonos=request.clasificacion_hexagonos,
        max_records=request.max_records,
        h3_resolution=request.h3_resolution,
        ejecutar_etl=request.ejecutar_etl,
        nivel_geografico=request.nivel_geografico,
    )
    return resultado
