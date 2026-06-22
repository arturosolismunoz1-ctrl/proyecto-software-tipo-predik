import json
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

from sqlalchemy import func, insert, select
from sqlalchemy.orm import Session
from geoalchemy2 import functions as geo_funcs

from app.models.analytics import ZonaAnalysisResult
from app.models.cube import CommercialDensityH3


def _extract_polygon_geojson(geometry: Dict[str, Any]) -> str:
    return {
        "type": geometry["type"],
        "coordinates": geometry["coordinates"],
    }


def calculate_commercial_concentration(
    db: Session,
    organization_id: str,
    polygon: Dict[str, Any],
    filtros: Optional[Dict[str, Any]] = None,
) -> Dict[str, Any]:
    filtro_categorias = filtros.get("categorias") if filtros else None
    polygon_json = json.dumps(polygon)

    query = select(CommercialDensityH3).where(
        geo_funcs.ST_Intersects(
            CommercialDensityH3.geom_hexagon,
            geo_funcs.ST_GeomFromGeoJSON(polygon_json),
        )
    )

    rows = db.execute(query).scalars().all()

    if not rows:
        raise ValueError("ZONA_SIN_COBERTURA")

    categorias_agg: Dict[str, Dict[str, Any]] = {}
    total_establecimientos = 0

    for row in rows:
        por_categoria = row.por_categoria or {}
        row_total = 0
        for categoria, cantidad in por_categoria.items():
            if filtro_categorias and categoria not in filtro_categorias:
                continue
            cantidad = cantidad or 0
            row_total += cantidad
            if categoria not in categorias_agg:
                categorias_agg[categoria] = {
                    "categoria": categoria,
                    "codigo_scian": categoria,
                    "cantidad": 0,
                }
            categorias_agg[categoria]["cantidad"] += cantidad

        total_establecimientos += row_total if filtro_categorias else (row.total_establecimientos or 0)

    por_categoria = sorted(categorias_agg.values(), key=lambda item: item["cantidad"], reverse=True)

    area_km2 = db.execute(
        select(
            func.coalesce(
                func.ST_Area(
                    func.ST_Transform(
                        func.ST_Union(CommercialDensityH3.geom_hexagon),
                        3857,
                    )
                ) / 1000000,
                0.0,
            )
        ).where(
            geo_funcs.ST_Intersects(
                CommercialDensityH3.geom_hexagon,
                geo_funcs.ST_GeomFromGeoJSON(polygon_json),
            )
        )
    ).scalar_one_or_none() or 0.0

    heatmap_cells: List[Dict[str, Any]] = []
    for row in rows:
        geom_json = db.execute(select(func.ST_AsGeoJSON(row.geom_hexagon))).scalar_one_or_none()
        intensidade = float((row.total_establecimientos or 0) / max(total_establecimientos, 1))
        heatmap_cells.append(
            {
                "h3_index": row.h3_index,
                "intensidad": intensidade,
                "geom": geom_json or "",
            }
        )

    return {
        "zona": {
            "entidad": rows[0].entidad or "Desconocido",
            "municipio": rows[0].municipio or "Desconocido",
            "area_km2": float(area_km2),
        },
        "total_establecimientos": total_establecimientos,
        "por_categoria": por_categoria,
        "negocios_ancla": [],
        "celdas_heatmap": heatmap_cells,
        "analysis_id": str(uuid4()),
    }


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
