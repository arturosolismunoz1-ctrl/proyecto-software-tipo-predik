from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


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


class AnalisisSummary(BaseModel):
    analysis_id: str
    analysis_type: str
    entidad: str
    municipio: str
    created_at: str


class DeleteResponse(BaseModel):
    deleted: bool
