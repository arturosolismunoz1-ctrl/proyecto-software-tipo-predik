from uuid import uuid4
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from app.deps import get_db, get_current_user
from app.services.zona_analysis import calculate_commercial_concentration, save_zona_analysis_result, ZonaAnalysisResult

router = APIRouter()


class Geometry(BaseModel):
    type: str
    coordinates: List[Any]


class Filtros(BaseModel):
    categorias: Optional[List[str]] = None
    zoom_level: Optional[int] = Field(default=14, ge=1, le=20)


class ZonaInfo(BaseModel):
    entidad: str
    municipio: str
    area_km2: float


class CategoriaResumen(BaseModel):
    categoria: str
    codigo_scian: str
    cantidad: int


class NegocioAncla(BaseModel):
    nombre: str
    categoria: str
    lat: float
    lon: float


class CeldaHeatmap(BaseModel):
    h3_index: str
    intensidad: float
    geom: str


class ConcentracionComercialRequest(BaseModel):
    geometry: Geometry
    filtros: Optional[Filtros] = None


class ConcentracionComercialResponse(BaseModel):
    zona: ZonaInfo
    total_establecimientos: int
    por_categoria: List[CategoriaResumen]
    negocios_ancla: List[NegocioAncla]
    celdas_heatmap: List[CeldaHeatmap]
    analysis_id: str


def validate_geometry(geometry: Geometry) -> None:
    if geometry.type != "Polygon":
        raise HTTPException(
            status_code=400,
            detail={
                "error": {
                    "code": "GEOMETRIA_INVALIDA",
                    "message": "El tipo de geometría debe ser Polygon.",
                    "details": {},
                }
            },
        )

    if not geometry.coordinates or not isinstance(geometry.coordinates[0], list):
        raise HTTPException(
            status_code=400,
            detail={
                "error": {
                    "code": "GEOMETRIA_INVALIDA",
                    "message": "La geometría no contiene coordenadas válidas.",
                    "details": {},
                }
            },
        )


@router.post("/concentracion-comercial", response_model=ConcentracionComercialResponse)
async def analizar_concentracion_comercial(
    request: ConcentracionComercialRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    validate_geometry(request.geometry)

    try:
        payload_polygon = {"type": request.geometry.type, "coordinates": request.geometry.coordinates}
        results = calculate_commercial_concentration(
            db=db,
            organization_id=current_user["org_id"],
            polygon=payload_polygon,
            filtros=request.filtros.model_dump() if request.filtros else None,
        )
        save_zona_analysis_result(
            db=db,
            organization_id=current_user["org_id"],
            polygon=payload_polygon,
            result=results,
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=404,
            detail={
                "error": {
                    "code": str(exc),
                    "message": "La geografía no tiene datos disponibles en esta zona.",
                    "details": {},
                }
            },
        )

    return ConcentracionComercialResponse(
        zona=ZonaInfo(
            entidad=results["zona"]["entidad"],
            municipio=results["zona"]["municipio"],
            area_km2=results["zona"]["area_km2"],
        ),
        total_establecimientos=results["total_establecimientos"],
        por_categoria=[CategoriaResumen(**categoria) for categoria in results["por_categoria"]],
        negocios_ancla=[NegocioAncla(**negocio) for negocio in results["negocios_ancla"]],
        celdas_heatmap=[CeldaHeatmap(**celda) for celda in results["celdas_heatmap"]],
        analysis_id=results["analysis_id"] or str(uuid4()),
    )


@router.get("/analisis/{analysis_id}", response_model=ConcentracionComercialResponse)
async def obtener_concentracion_guardada(
    analysis_id: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    record = db.get(ZonaAnalysisResult, analysis_id)
    if record is None:
        raise HTTPException(
            status_code=404,
            detail={
                "error": {
                    "code": "ANALISIS_NO_ENCONTRADO",
                    "message": "No se encontró el análisis solicitado.",
                    "details": {},
                }
            },
        )

    result = record.result_json
    return ConcentracionComercialResponse(
        zona=ZonaInfo(**result["zona"]),
        total_establecimientos=result["total_establecimientos"],
        por_categoria=[CategoriaResumen(**categoria) for categoria in result["por_categoria"]],
        negocios_ancla=[NegocioAncla(**negocio) for negocio in result["negocios_ancla"]],
        celdas_heatmap=[CeldaHeatmap(**celda) for celda in result["celdas_heatmap"]],
        analysis_id=result["analysis_id"],
    )
