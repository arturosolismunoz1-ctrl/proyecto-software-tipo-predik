import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Literal, Optional
from uuid import uuid4

from geoalchemy2 import functions as geo_funcs
from sqlalchemy import Text, cast, func, insert, select
from sqlalchemy.orm import Session

from app.models.analytics import ZonaAnalysisResult
from app.models.raw_data import AgebDemographics, AgebGeometry, DenueEstablishment, ManzanaVivienda


def calculate_commercial_concentration(
    db: Session,
    organization_id: str,
    polygon: Dict[str, Any],
    filtros: Optional[Dict[str, Any]] = None,
    nivel_geografico: Literal["ageb", "manzana"] = "ageb",
) -> Dict[str, Any]:
    filtro_categorias = filtros.get("categorias") if filtros else None
    polygon_json = json.dumps(polygon)
    poly_geom = geo_funcs.ST_GeomFromGeoJSON(polygon_json)

    # --- Establecimientos dentro del polígono ---
    stmt_denue = select(
        DenueEstablishment.clase_actividad,
        DenueEstablishment.codigo_scian,
        func.count().label("cantidad"),
    ).where(
        DenueEstablishment.geom.isnot(None),
        geo_funcs.ST_Intersects(DenueEstablishment.geom, poly_geom),
    ).group_by(DenueEstablishment.clase_actividad, DenueEstablishment.codigo_scian)

    if filtro_categorias:
        stmt_denue = stmt_denue.where(DenueEstablishment.clase_actividad.in_(filtro_categorias))

    denue_rows = db.execute(stmt_denue).all()
    if not denue_rows:
        raise ValueError("ZONA_SIN_COBERTURA")

    total_establecimientos = sum(r.cantidad for r in denue_rows)
    por_categoria = sorted(
        [
            {
                "categoria": r.clase_actividad or "Sin categoría",
                "codigo_scian": r.codigo_scian or "",
                "cantidad": r.cantidad,
            }
            for r in denue_rows
        ],
        key=lambda x: x["cantidad"],
        reverse=True,
    )

    ANCLA_THRESHOLD = 2.0
    promedio = total_establecimientos / len(por_categoria) if por_categoria else 0
    negocios_ancla = [
        {"nombre": cat["categoria"], "categoria": cat["categoria"], "lat": 0.0, "lon": 0.0}
        for cat in por_categoria
        if cat["cantidad"] >= promedio * ANCLA_THRESHOLD
    ]

    # --- Subquery de establecimientos en zona ---
    denue_en_zona = (
        select(DenueEstablishment.id, DenueEstablishment.geom)
        .where(
            DenueEstablishment.geom.isnot(None),
            geo_funcs.ST_Intersects(DenueEstablishment.geom, poly_geom),
        )
        .subquery()
    )

    # --- Celdas del heatmap: manzanas → AGEBs según nivel o disponibilidad ---
    heatmap_cells: List[Dict] = []
    zona_nom_mun = "Desconocido"
    zona_nom_loc = "Desconocido"

    if nivel_geografico == "manzana":
        heatmap_cells, zona_nom_mun = _query_manzanas(db, poly_geom, denue_en_zona)

    if not heatmap_cells:
        heatmap_cells, zona_nom_mun, zona_nom_loc = _query_agebs(db, poly_geom, denue_en_zona)

    # --- Área del polígono ---
    area_km2 = db.execute(
        select(func.ST_Area(func.ST_Transform(poly_geom, 3857)) / 1_000_000)
    ).scalar_one_or_none() or 0.0

    return {
        "zona": {
            "entidad": zona_nom_loc,
            "municipio": zona_nom_mun,
            "area_km2": float(area_km2),
        },
        "total_establecimientos": total_establecimientos,
        "por_categoria": por_categoria,
        "negocios_ancla": negocios_ancla,
        "celdas_heatmap": heatmap_cells,
        "analysis_id": str(uuid4()),
    }


def _query_agebs(db, poly_geom, denue_en_zona):
    stmt = (
        select(
            AgebGeometry.cvegeo,
            AgebGeometry.nom_mun,
            AgebGeometry.nom_loc,
            func.ST_AsGeoJSON(AgebGeometry.geom).label("geom"),
            AgebDemographics.pobtot,
            func.count(denue_en_zona.c.id).label("num_estab"),
        )
        .outerjoin(AgebDemographics, AgebGeometry.cvegeo_9 == AgebDemographics.cvegeo)
        .outerjoin(denue_en_zona, geo_funcs.ST_Within(denue_en_zona.c.geom, AgebGeometry.geom))
        .where(geo_funcs.ST_Intersects(AgebGeometry.geom, poly_geom))
        .group_by(
            AgebGeometry.cvegeo,
            AgebGeometry.nom_mun,
            AgebGeometry.nom_loc,
            AgebGeometry.geom,
            AgebDemographics.pobtot,
        )
    )
    rows = db.execute(stmt).all()
    if not rows:
        return [], "Desconocido", "Desconocido"

    max_estab = max((r.num_estab for r in rows), default=1) or 1
    cells = [
        {
            "h3_index": r.cvegeo,
            "intensidad": float(r.num_estab / max_estab),
            "cantidad": int(r.num_estab),
            "geom": r.geom or "",
        }
        for r in rows
    ]
    first = rows[0]
    return cells, first.nom_mun or "Desconocido", first.nom_loc or "Desconocido"


def _query_manzanas(db, poly_geom, denue_en_zona):
    stmt = (
        select(
            ManzanaVivienda.cvegeo,
            ManzanaVivienda.clave_mun,
            ManzanaVivienda.vivpar_hab,
            func.max(cast(ManzanaVivienda.indicadores, Text)).label("indicadores_text"),
            func.ST_AsGeoJSON(ManzanaVivienda.geom).label("geom"),
            func.count(denue_en_zona.c.id).label("num_estab"),
        )
        .outerjoin(denue_en_zona, geo_funcs.ST_Within(denue_en_zona.c.geom, ManzanaVivienda.geom))
        .where(geo_funcs.ST_Intersects(ManzanaVivienda.geom, poly_geom))
        .group_by(
            ManzanaVivienda.cvegeo,
            ManzanaVivienda.clave_mun,
            ManzanaVivienda.vivpar_hab,
            ManzanaVivienda.geom,
        )
    )
    rows = db.execute(stmt).all()
    if not rows:
        return [], "Desconocido"

    max_estab = max((r.num_estab for r in rows), default=1) or 1
    cells = [
        {
            "h3_index": r.cvegeo,
            "intensidad": float(r.num_estab / max_estab),
            "cantidad": int(r.num_estab),
            "geom": r.geom or "",
        }
        for r in rows
    ]
    first = rows[0]
    return cells, first.clave_mun or "Desconocido"


def save_zona_analysis_result(
    db: Session,
    organization_id: str,
    polygon: Dict[str, Any],
    result: Dict[str, Any],
    analysis_type: str = "concentracion_comercial",
) -> str:
    analysis_id = result.get("analysis_id") or str(uuid4())
    polygon_json = json.dumps(polygon)
    stmt = insert(ZonaAnalysisResult).values(
        id=analysis_id,
        organization_id=organization_id,
        user_id=None,
        polygon=geo_funcs.ST_SetSRID(
            geo_funcs.ST_GeomFromGeoJSON(polygon_json),
            4326,
        ),
        analysis_type=analysis_type,
        result_json=result,
        created_at=datetime.now(timezone.utc),
    )
    db.execute(stmt)
    db.commit()
    return analysis_id
