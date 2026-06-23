from uuid import uuid4
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel, Field
from sqlalchemy.orm import Session

from sqlalchemy import func as sqlfunc, or_

from app.deps import get_db, get_current_user
from app.models.raw_data import DenueEstablishment
from app.rate_limit import check_rate_limit
from app.services.zona_analysis import calculate_commercial_concentration, save_zona_analysis_result, ZonaAnalysisResult
from app.services.densidad_poblacional import calculate_densidad_poblacional

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
    cantidad: int
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
    _rl: None = Depends(check_rate_limit),
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


# ── Densidad Poblacional ──────────────────────────────────────────────────────

class PorGenero(BaseModel):
    masculino: int
    femenino: int


class PorGrupoEdad(BaseModel):
    field_0_14: int = Field(alias="0_14")
    field_15_64: int = Field(alias="15_64")
    field_65_mas: int = Field(alias="65_mas")

    model_config = {"populate_by_name": True}


class DetalleAgeb(BaseModel):
    cvegeo: str
    nom_ent: str
    nom_mun: str
    pobtot: int
    fraccion_area: float
    area_km2: float
    densidad_hab_km2: float
    geom: str


class DensidadPoblacionalRequest(BaseModel):
    geometry: Geometry


class DensidadPoblacionalResponse(BaseModel):
    zona: ZonaInfo
    poblacion_total: int
    densidad_hab_km2: float
    por_genero: PorGenero
    por_grupo_edad: PorGrupoEdad
    viviendas_habitadas: int
    promedio_ocupantes: float
    agebs_analizadas: int
    detalle_agebs: List[DetalleAgeb]
    analysis_id: str


@router.post("/densidad-poblacional", response_model=DensidadPoblacionalResponse)
async def analizar_densidad_poblacional(
    request: DensidadPoblacionalRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    _rl: None = Depends(check_rate_limit),
):
    validate_geometry(request.geometry)

    try:
        polygon = {"type": request.geometry.type, "coordinates": request.geometry.coordinates}
        result = calculate_densidad_poblacional(
            db=db,
            organization_id=current_user["org_id"],
            polygon=polygon,
        )
        save_zona_analysis_result(
            db=db,
            organization_id=current_user["org_id"],
            polygon=polygon,
            result=result,
            analysis_type="densidad_poblacional",
        )
    except ValueError as exc:
        raise HTTPException(
            status_code=404,
            detail={
                "error": {
                    "code": str(exc),
                    "message": "La zona no tiene datos demográficos disponibles.",
                    "details": {},
                }
            },
        )

    return DensidadPoblacionalResponse(
        zona=ZonaInfo(**result["zona"]),
        poblacion_total=result["poblacion_total"],
        densidad_hab_km2=result["densidad_hab_km2"],
        por_genero=PorGenero(**result["por_genero"]),
        por_grupo_edad=PorGrupoEdad(**result["por_grupo_edad"]),
        viviendas_habitadas=result["viviendas_habitadas"],
        promedio_ocupantes=result["promedio_ocupantes"],
        agebs_analizadas=result["agebs_analizadas"],
        detalle_agebs=[DetalleAgeb(**a) for a in result["detalle_agebs"]],
        analysis_id=result["analysis_id"],
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


# ── Establecimientos individuales ─────────────────────────────────────────────

class EstablecimientoItem(BaseModel):
    nombre: str
    clase_actividad: str
    codigo_scian: str
    estrato_personal: str
    colonia: str
    municipio: str
    lat: float
    lon: float


class EstablecimientosRequest(BaseModel):
    geometry: Geometry
    keyword: Optional[str] = None        # filtra nombre o clase por substring
    scian_prefix: Optional[str] = None   # filtra por prefijo SCIAN, e.g. "4511"


class EstablecimientosResponse(BaseModel):
    total: int
    establecimientos: List[EstablecimientoItem]


@router.post("/establecimientos", response_model=EstablecimientosResponse)
async def obtener_establecimientos(
    request: EstablecimientosRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
    _rl: None = Depends(check_rate_limit),
):
    validate_geometry(request.geometry)

    import json
    from geoalchemy2 import functions as geo_funcs
    from sqlalchemy import select

    polygon_json = json.dumps({"type": request.geometry.type, "coordinates": request.geometry.coordinates})

    stmt = select(
        DenueEstablishment.nombre,
        DenueEstablishment.clase_actividad,
        DenueEstablishment.codigo_scian,
        DenueEstablishment.estrato_personal,
        DenueEstablishment.colonia,
        DenueEstablishment.municipio,
        sqlfunc.ST_X(DenueEstablishment.geom).label("lon"),
        sqlfunc.ST_Y(DenueEstablishment.geom).label("lat"),
    ).where(
        DenueEstablishment.geom.isnot(None),
        geo_funcs.ST_Intersects(
            DenueEstablishment.geom,
            geo_funcs.ST_GeomFromGeoJSON(polygon_json),
        ),
    )

    if request.scian_prefix:
        stmt = stmt.where(DenueEstablishment.codigo_scian.like(f"{request.scian_prefix}%"))

    if request.keyword:
        kw = request.keyword.lower()
        stmt = stmt.where(
            or_(
                sqlfunc.lower(DenueEstablishment.nombre).like(f"%{kw}%"),
                sqlfunc.lower(DenueEstablishment.clase_actividad).like(f"%{kw}%"),
            )
        )

    rows = db.execute(stmt).all()

    items = [
        EstablecimientoItem(
            nombre=r.nombre or "",
            clase_actividad=r.clase_actividad or "",
            codigo_scian=r.codigo_scian or "",
            estrato_personal=r.estrato_personal or "",
            colonia=r.colonia or "",
            municipio=r.municipio or "",
            lat=float(r.lat),
            lon=float(r.lon),
        )
        for r in rows
        if r.lat and r.lon
    ]

    return EstablecimientosResponse(total=len(items), establecimientos=items)
