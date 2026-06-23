from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.v1.schemas import AnalisisSummary, ConcentracionComercialResponse
from app.deps import get_db, get_current_user
from app.models.analytics import ZonaAnalysisResult

router = APIRouter()


class ComparacionItem(BaseModel):
    analysis_id: str
    analysis_type: str
    zona: Dict[str, Any]
    resumen: Dict[str, Any]


class ComparacionResponse(BaseModel):
    total: int
    items: List[ComparacionItem]


@router.get("/", response_model=List[AnalisisSummary])
async def listar_analisis(db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
    results = db.execute(select(ZonaAnalysisResult)).scalars().all()
    summaries = []
    for record in results:
        result_json = record.result_json or {}
        summaries.append(
            AnalisisSummary(
                analysis_id=record.id,
                analysis_type=record.analysis_type or "concentracion_comercial",
                entidad=result_json.get("zona", {}).get("entidad", "Desconocido"),
                municipio=result_json.get("zona", {}).get("municipio", "Desconocido"),
                created_at=record.created_at.isoformat() if record.created_at else "",
            )
        )
    return summaries


@router.get("/{analysis_id}", response_model=ConcentracionComercialResponse)
async def obtener_analisis(analysis_id: str, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
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
        zona=result["zona"],
        total_establecimientos=result["total_establecimientos"],
        por_categoria=result["por_categoria"],
        negocios_ancla=result["negocios_ancla"],
        celdas_heatmap=result["celdas_heatmap"],
        analysis_id=result["analysis_id"],
    )


@router.get("/comparar", response_model=ComparacionResponse)
async def comparar_analisis(
    ids: str,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    """Compara 2 o más análisis guardados lado a lado. ids = UUIDs separados por coma."""
    id_list = [i.strip() for i in ids.split(",") if i.strip()]
    if len(id_list) < 2:
        raise HTTPException(
            status_code=400,
            detail={
                "error": {
                    "code": "IDS_INSUFICIENTES",
                    "message": "Se requieren al menos 2 IDs de análisis para comparar.",
                    "details": {},
                }
            },
        )

    items: List[ComparacionItem] = []
    for aid in id_list:
        record = db.get(ZonaAnalysisResult, aid)
        if record is None:
            raise HTTPException(
                status_code=404,
                detail={
                    "error": {
                        "code": "ANALISIS_NO_ENCONTRADO",
                        "message": f"No se encontró el análisis {aid}.",
                        "details": {"analysis_id": aid},
                    }
                },
            )

        result = record.result_json or {}
        analysis_type = record.analysis_type or "concentracion_comercial"

        if analysis_type == "densidad_poblacional":
            resumen = {
                "poblacion_total": result.get("poblacion_total", 0),
                "densidad_hab_km2": result.get("densidad_hab_km2", 0),
                "viviendas_habitadas": result.get("viviendas_habitadas", 0),
                "agebs_analizadas": result.get("agebs_analizadas", 0),
            }
        else:
            resumen = {
                "total_establecimientos": result.get("total_establecimientos", 0),
                "categorias": len(result.get("por_categoria", [])),
                "negocios_ancla": len(result.get("negocios_ancla", [])),
            }

        items.append(
            ComparacionItem(
                analysis_id=aid,
                analysis_type=analysis_type,
                zona=result.get("zona", {}),
                resumen=resumen,
            )
        )

    return ComparacionResponse(total=len(items), items=items)


@router.delete("/{analysis_id}")
async def eliminar_analisis(analysis_id: str, db: Session = Depends(get_db), current_user: dict = Depends(get_current_user)):
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
    db.delete(record)
    db.commit()
    return {"deleted": True}
