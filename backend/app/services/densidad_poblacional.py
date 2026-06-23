import json
from typing import Any, Dict, List, Optional
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session
from geoalchemy2 import functions as geo_funcs

from app.models.raw_data import AgebGeometry, AgebDemographics


def calculate_densidad_poblacional(
    db: Session,
    organization_id: str,
    polygon: Dict[str, Any],
) -> Dict[str, Any]:
    polygon_json = json.dumps(polygon)
    polygon_geom = geo_funcs.ST_GeomFromGeoJSON(polygon_json)

    # AGEBs que intersectan el polígono, con sus datos demográficos
    query = (
        select(AgebGeometry, AgebDemographics)
        .join(
            AgebDemographics,
            AgebDemographics.cvegeo == AgebGeometry.cvegeo,
            isouter=True,
        )
        .where(geo_funcs.ST_Intersects(AgebGeometry.geom, polygon_geom))
    )
    rows = db.execute(query).all()

    if not rows:
        raise ValueError("ZONA_SIN_DATOS_DEMOGRAFICOS")

    # Totales agregados
    pobtot = 0
    pobmas = 0
    pobfem = 0
    p_0a14 = 0
    p_15a64 = 0
    p_65ymas = 0
    vivpar_hab = 0
    prom_ocup_vals: List[float] = []
    entidad = ""
    municipio = ""

    detalle: List[Dict[str, Any]] = []

    for ageb_geom, ageb_dem in rows:
        if not entidad and ageb_geom.nom_ent:
            entidad = ageb_geom.nom_ent
        if not municipio and ageb_geom.nom_mun:
            municipio = ageb_geom.nom_mun

        ageb_pobtot = (ageb_dem.pobtot or 0) if ageb_dem else 0
        ageb_pobmas = (ageb_dem.pobmas or 0) if ageb_dem else 0
        ageb_pobfem = (ageb_dem.pobfem or 0) if ageb_dem else 0
        ageb_p0a14 = (ageb_dem.p_0a14 or 0) if ageb_dem else 0
        ageb_p15a64 = (ageb_dem.p_15a64 or 0) if ageb_dem else 0
        ageb_p65 = (ageb_dem.p_65ymas or 0) if ageb_dem else 0
        ageb_viv = (ageb_dem.vivpar_hab or 0) if ageb_dem else 0
        ageb_ocup = (ageb_dem.prom_ocup or 0.0) if ageb_dem else 0.0

        pobtot += ageb_pobtot
        pobmas += ageb_pobmas
        pobfem += ageb_pobfem
        p_0a14 += ageb_p0a14
        p_15a64 += ageb_p15a64
        p_65ymas += ageb_p65
        vivpar_hab += ageb_viv
        if ageb_ocup:
            prom_ocup_vals.append(ageb_ocup)

        # Área individual del AGEB en km²
        ageb_area_km2 = db.execute(
            select(
                func.coalesce(
                    func.ST_Area(func.ST_Transform(AgebGeometry.geom, 3857)) / 1_000_000,
                    0.0,
                )
            ).where(AgebGeometry.cvegeo == ageb_geom.cvegeo)
        ).scalar_one_or_none() or 0.0

        ageb_densidad = ageb_pobtot / ageb_area_km2 if ageb_area_km2 > 0 else 0.0

        geom_json = db.execute(
            select(func.ST_AsGeoJSON(AgebGeometry.geom)).where(
                AgebGeometry.cvegeo == ageb_geom.cvegeo
            )
        ).scalar_one_or_none()

        detalle.append(
            {
                "cvegeo": ageb_geom.cvegeo,
                "nom_ent": ageb_geom.nom_ent or "",
                "nom_mun": ageb_geom.nom_mun or "",
                "pobtot": ageb_pobtot,
                "area_km2": round(float(ageb_area_km2), 4),
                "densidad_hab_km2": round(ageb_densidad, 2),
                "geom": geom_json or "",
            }
        )

    # Área total del polígono consultado en km²
    area_km2 = db.execute(
        select(
            func.coalesce(
                func.ST_Area(
                    func.ST_Transform(
                        func.ST_Union(AgebGeometry.geom),
                        3857,
                    )
                ) / 1_000_000,
                0.0,
            )
        ).where(geo_funcs.ST_Intersects(AgebGeometry.geom, polygon_geom))
    ).scalar_one_or_none() or 0.0

    densidad_hab_km2 = pobtot / area_km2 if area_km2 > 0 else 0.0
    promedio_ocupantes = (
        round(sum(prom_ocup_vals) / len(prom_ocup_vals), 2) if prom_ocup_vals else 0.0
    )

    return {
        "zona": {
            "entidad": entidad or "Desconocido",
            "municipio": municipio or "Desconocido",
            "area_km2": round(float(area_km2), 4),
        },
        "poblacion_total": pobtot,
        "densidad_hab_km2": round(densidad_hab_km2, 2),
        "por_genero": {"masculino": pobmas, "femenino": pobfem},
        "por_grupo_edad": {
            "0_14": p_0a14,
            "15_64": p_15a64,
            "65_mas": p_65ymas,
        },
        "viviendas_habitadas": vivpar_hab,
        "promedio_ocupantes": promedio_ocupantes,
        "agebs_analizadas": len(rows),
        "detalle_agebs": detalle,
        "analysis_id": str(uuid4()),
    }
