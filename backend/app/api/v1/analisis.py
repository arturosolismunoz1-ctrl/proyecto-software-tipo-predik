import json
import logging
from datetime import date
from typing import Any, Dict, List, Literal, Optional

logger = logging.getLogger(__name__)

from fastapi import APIRouter, Depends, HTTPException
from fastapi.responses import Response
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.api.v1.schemas import AnalisisSummary, ConcentracionComercialResponse
from app.deps import get_db, get_current_user
from app.models.analytics import ZonaAnalysisResult

router = APIRouter()

# ── Wizard Caso 1: Análisis de competencia ────────────────────────────────────

_COLORES_COMPETENCIA = ["red", "blue", "orange", "purple", "cyan", "pink", "yellow"]


class AnalisisCompetenciaRequest(BaseModel):
    # Geografía
    clave_estado: str = Field(..., description="Clave de 2 dígitos del estado INEGI")
    claves_municipios: List[str] = Field(..., min_length=1, description="Una o más claves de municipio")
    polygon: Optional[Dict[str, Any]] = Field(None, description="Polígono manual (sobreescribe bbox)")

    # NSE — niveles socioeconómicos AMAI (score multi-variable, ver compute_nse_scores.py)
    nse_niveles: Optional[List[str]] = Field(
        None,
        description="Niveles NSE a incluir: AB, Cmas, C, Cmenos, Dmas, D, E. None = todos.",
    )

    # Marca propia
    marca_propia: Optional[str] = Field(None, description="Nombre de tu marca/cadena propia")
    scian_giros: Optional[List[str]] = Field(None, description="Uno o más códigos SCIAN para competencia indirecta")

    # Competencia directa
    competencia_directa: List[str] = Field(default_factory=list, description="Nombres de competidores directos")

    # Tipos de análisis
    incluir_sucursales: bool = True
    incluir_hubs: bool = True
    incluir_zonas_blancas: bool = True

    # Parámetros
    radio_hub_metros: int = Field(default=150, ge=50, le=500)
    nivel_geografico: Literal["ageb", "manzana"] = "ageb"
    formato_salida: Literal["kmz", "geojson"] = "kmz"
    max_records: int = Field(default=300, ge=1, le=2500)


@router.post(
    "/competencia",
    summary="Wizard Caso 1 — Análisis de competencia completo",
)
async def analisis_competencia(
    request: AnalisisCompetenciaRequest,
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
):
    from app.services.reporte import (
        bbox_municipios,
        query_puntos_indirecta,
        calcular_hubs,
        generar_kmz_maestro,
        query_puntos_capa,
        query_agebs_en_poligono,
        query_manzanas_en_poligono,
        clasificar_por_oportunidad,
        clasificar_por_densidad,
        clasificar_manzanas_por_infraestructura,
        _normalizar_intensidad,
        _kml_to_hex,
        run_etl_capas,
    )

    # 1. Polígono — manual o bbox de municipios
    try:
        polygon = request.polygon or bbox_municipios(
            db, request.clave_estado, request.claves_municipios
        )
    except ValueError as e:
        raise HTTPException(status_code=422, detail=str(e))

    # 2. Construir capas (marca propia + competidores directos)
    capas: List[Dict[str, Any]] = []
    scian_giros = request.scian_giros or []
    if request.marca_propia and request.incluir_sucursales:
        capas.append({
            "keyword":      request.marca_propia,
            "label":        request.marca_propia,
            "color":        "green",
            "icon":         "star",
            "estado":       request.clave_estado,
            "scian_prefixes": scian_giros,
        })
    for i, comp in enumerate(request.competencia_directa):
        capas.append({
            "keyword":      comp,
            "label":        comp,
            "color":        _COLORES_COMPETENCIA[i % len(_COLORES_COMPETENCIA)],
            "icon":         "circle",
            "estado":       request.clave_estado,
            "scian_prefixes": scian_giros,
        })

    # 3. ETL DENUE para cada capa
    if capas:
        await run_etl_capas(db, capas, polygon, request.max_records)

    # 4. Obtener puntos por capa (marca + directa)
    capas_con_puntos = []
    for capa in capas:
        puntos = query_puntos_capa(db, polygon, capa["keyword"], capa.get("scian_prefixes"))
        capas_con_puntos.append({**capa, "puntos": puntos})

    # 5. Zonas geográficas (AGEBs o manzanas) con filtro NSE opcional
    hexagonos_raw: List[Dict] = []
    usa_manzanas = False

    if request.nivel_geografico == "manzana":
        try:
            manzanas = query_manzanas_en_poligono(db, polygon)
            if manzanas:
                hexagonos_raw = _normalizar_intensidad(manzanas)
                usa_manzanas = True
        except Exception:
            logger.exception("Error consultando manzanas")
            db.rollback()

    if not usa_manzanas:
        try:
            agebs = query_agebs_en_poligono(
                db, polygon,
                nse_niveles=request.nse_niveles or None,
            )
            if agebs:
                hexagonos_raw = _normalizar_intensidad(agebs)
        except Exception:
            logger.exception("Error consultando AGEBs")
            db.rollback()

    # 6. Clasificar zonas
    clasificacion = "oportunidad" if request.incluir_zonas_blancas else "densidad"
    if not hexagonos_raw:
        hexagonos: List[Dict] = []
    elif usa_manzanas:
        hexagonos = clasificar_manzanas_por_infraestructura(hexagonos_raw)
    elif clasificacion == "oportunidad" and capas_con_puntos:
        hexagonos = clasificar_por_oportunidad(hexagonos_raw, capas_con_puntos)
    else:
        hexagonos = clasificar_por_densidad(hexagonos_raw)

    # 7. Competencia indirecta (mismo SCIAN, excluye marcas listadas)
    puntos_indirecta: List[Dict] = []
    if scian_giros:
        exclude = [k for k in [request.marca_propia] + list(request.competencia_directa) if k]
        try:
            puntos_indirecta = query_puntos_indirecta(db, polygon, scian_giros, exclude)
        except Exception:
            logger.exception("Error consultando competencia indirecta")

    # 8. Hubs de competencia directa
    hubs: List[Dict] = []
    if request.incluir_hubs:
        todos_directa = [p for c in capas_con_puntos if c.get("icon") != "star"
                         for p in c.get("puntos", [])]
        hubs = calcular_hubs(todos_directa, request.radio_hub_metros)

    # 9. Respuesta
    nombre = (
        f"Análisis {request.marca_propia or 'competencia'} — "
        f"{', '.join(request.claves_municipios)} — {date.today()}"
    )

    if request.formato_salida == "kmz":
        archivo = generar_kmz_maestro(
            nombre=nombre,
            zonas=hexagonos,
            capas_directa=capas_con_puntos,
            puntos_indirecta=puntos_indirecta,
            hubs=hubs,
            radio_hub=request.radio_hub_metros,
        )
        safe_name = nombre.replace(" ", "_").replace("—", "-")[:60]
        return Response(
            content=archivo,
            media_type="application/vnd.google-earth.kmz",
            headers={"Content-Disposition": f'attachment; filename="{safe_name}.kmz"'},
        )

    # GeoJSON para preview en mapa
    zonas_features = []
    for z in hexagonos:
        if not z.get("geom"):
            continue
        try:
            geom = json.loads(z["geom"])
        except Exception:
            continue
        props = {
            "label":      z.get("label", ""),
            "hex_color":  _kml_to_hex(z.get("color", "CC888888")),
            "cantidad":   z.get("cantidad", 0),
            "intensidad": round(z.get("intensidad", 0), 4),
            "nivel":      z.get("nivel", ""),
            "cvegeo":     z.get("cvegeo", ""),
            "nom_mun":    z.get("nom_mun", ""),
            "pobtot":     z.get("pobtot", 0),
            "graproes":   z.get("graproes", 0.0),
            "tipo_zona":  "manzana" if usa_manzanas else "ageb",
        }
        zonas_features.append({"type": "Feature", "geometry": geom, "properties": props})

    total_estab = sum(len(c["puntos"]) for c in capas_con_puntos)
    return {
        "zonas": zonas_features,
        "capas": [
            {
                "label":    c["label"],
                "keyword":  c["keyword"],
                "color":    c["color"],
                "icon":     c.get("icon", "circle"),
                "estado":   c["estado"],
                "cantidad": len(c["puntos"]),
                "puntos":   c["puntos"],
            }
            for c in capas_con_puntos
        ],
        "indirecta": {
            "cantidad": len(puntos_indirecta),
            "puntos":   puntos_indirecta,
        },
        "hubs": hubs,
        "resumen": {
            "total_establecimientos": total_estab,
            "total_directa":          total_estab,
            "total_indirecta":        len(puntos_indirecta),
            "total_hubs":             len(hubs),
            "total_zonas":            len(hexagonos),
            "nivel_geografico":       request.nivel_geografico,
            "clasificacion":          clasificacion,
        },
    }


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
