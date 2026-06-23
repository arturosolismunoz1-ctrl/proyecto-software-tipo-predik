from typing import List

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.v1.schemas import AnalisisSummary, ConcentracionComercialResponse
from app.deps import get_db, get_current_user
from app.models.analytics import ZonaAnalysisResult

router = APIRouter()


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
