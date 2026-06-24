"""
API BIE — Indicadores macroeconómicos por entidad federativa (INEGI).

Endpoints:
  GET  /api/v1/bie/indicadores              → catálogo de indicadores disponibles
  GET  /api/v1/bie/estado/{clave}           → resumen económico de un estado
  GET  /api/v1/bie/estado/{clave}/{ind_key} → serie histórica de un indicador
  GET  /api/v1/bie/stats                    → cobertura de datos en BD (admin)
  POST /api/v1/bie/sync/{clave}             → dispara carga BIE para un estado (admin)
  POST /api/v1/bie/sync                     → dispara carga BIE para todos los estados (admin)
"""
import logging
import os
from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, Query, BackgroundTasks
from pydantic import BaseModel
from sqlalchemy.orm import Session

from app.connectors.inegi.bie import INDICADORES
from app.deps import get_db, get_current_user
from app.services.bie import (
    cargar_indicadores_estado,
    resumen_economico_estado,
    serie_historica,
    stats_carga,
)

logger = logging.getLogger(__name__)
router = APIRouter()

_ESTADOS_VALIDOS = {f"{i:02d}" for i in range(1, 33)}


# ── Schemas ────────────────────────────────────────────────────────────────────

class IndicadorMeta(BaseModel):
    key: str
    id: str
    nombre: str
    descripcion: str
    frecuencia: str
    unidad: str


class ValorIndicador(BaseModel):
    valor: Optional[float]
    nombre: str
    unidad: str
    periodo: Optional[str] = None
    interpretacion: str = ""


class ResumenEconomico(BaseModel):
    fuente: str
    estado_clave: str = ""
    advertencia: Optional[str] = None
    indicadores: Dict[str, Any]


class PuntoSerie(BaseModel):
    periodo: str
    fecha: Optional[str]
    valor: float


class StatsBIE(BaseModel):
    total_registros: int
    estados_con_datos: int
    ultima_carga: Optional[str]
    token_configurado: bool
    indicadores_disponibles: List[str]


# ── Endpoints ──────────────────────────────────────────────────────────────────

@router.get(
    "/indicadores",
    response_model=List[IndicadorMeta],
    summary="Catálogo de indicadores BIE disponibles",
)
def listar_indicadores(_: dict = Depends(get_current_user)):
    return [
        IndicadorMeta(
            key=k,
            id=v["id"],
            nombre=v["nombre"],
            descripcion=v["descripcion"],
            frecuencia=v["freq_label"],
            unidad=v["unidad"],
        )
        for k, v in INDICADORES.items()
    ]


@router.get(
    "/estado/{clave_estado}",
    response_model=ResumenEconomico,
    summary="Resumen económico de un estado (contexto para análisis de zona)",
)
def resumen_estado(
    clave_estado: str,
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    clave = clave_estado.zfill(2)
    if clave not in _ESTADOS_VALIDOS:
        raise HTTPException(status_code=404, detail=f"Estado '{clave_estado}' no válido")

    resumen = resumen_economico_estado(db, clave)
    return ResumenEconomico(
        fuente=resumen.get("fuente", "demo"),
        estado_clave=resumen.get("estado_clave", clave),
        advertencia=resumen.get("advertencia"),
        indicadores=resumen.get("indicadores", {}),
    )


@router.get(
    "/estado/{clave_estado}/{indicador_key}",
    response_model=List[PuntoSerie],
    summary="Serie histórica de un indicador para un estado",
)
def serie_estado(
    clave_estado: str,
    indicador_key: str,
    limit: int = Query(default=12, ge=1, le=60),
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    clave = clave_estado.zfill(2)
    if clave not in _ESTADOS_VALIDOS:
        raise HTTPException(status_code=404, detail=f"Estado '{clave_estado}' no válido")
    if indicador_key not in INDICADORES:
        raise HTTPException(
            status_code=404,
            detail=f"Indicador '{indicador_key}' no encontrado. Disponibles: {list(INDICADORES.keys())}",
        )

    serie = serie_historica(db, clave, indicador_key, limit)
    return [PuntoSerie(**p) for p in serie]


@router.get(
    "/stats",
    response_model=StatsBIE,
    summary="Estadísticas de cobertura de datos BIE en BD",
)
def estadisticas_bie(
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    return StatsBIE(**stats_carga(db))


def _sync_estado_bg(estado_clave: str, db: Session) -> None:
    token = os.getenv("INEGI_BIE_API_TOKEN", "")
    if not token:
        logger.warning("BIE sync omitida: INEGI_BIE_API_TOKEN no configurado")
        return
    try:
        resultados = cargar_indicadores_estado(db, estado_clave, token)
        logger.info("BIE sync completado estado=%s: %s", estado_clave, resultados)
    except Exception:
        logger.exception("BIE sync falló para estado=%s", estado_clave)
    finally:
        db.close()


@router.post(
    "/sync/{clave_estado}",
    summary="Dispara carga BIE para un estado (requiere INEGI_BIE_API_TOKEN)",
)
def sync_estado(
    clave_estado: str,
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    clave = clave_estado.zfill(2)
    if clave not in _ESTADOS_VALIDOS:
        raise HTTPException(status_code=404, detail=f"Estado '{clave_estado}' no válido")

    token = os.getenv("INEGI_BIE_API_TOKEN", "")
    if not token:
        raise HTTPException(
            status_code=503,
            detail="INEGI_BIE_API_TOKEN no configurado. Obténlo en https://www.inegi.org.mx/servicios/api_indicadores.html",
        )

    background_tasks.add_task(_sync_estado_bg, clave, db)
    return {"message": f"Sincronización BIE iniciada para estado {clave}", "estado": clave}


@router.post(
    "/sync",
    summary="Dispara carga BIE para los 32 estados (puede tardar varios minutos)",
)
def sync_todos(
    background_tasks: BackgroundTasks,
    db: Session = Depends(get_db),
    _: dict = Depends(get_current_user),
):
    token = os.getenv("INEGI_BIE_API_TOKEN", "")
    if not token:
        raise HTTPException(
            status_code=503,
            detail="INEGI_BIE_API_TOKEN no configurado. Obténlo en https://www.inegi.org.mx/servicios/api_indicadores.html",
        )

    for clave in _ESTADOS_VALIDOS:
        background_tasks.add_task(_sync_estado_bg, clave, db)

    return {
        "message": "Sincronización BIE iniciada para 32 estados en background",
        "estados": sorted(_ESTADOS_VALIDOS),
    }
