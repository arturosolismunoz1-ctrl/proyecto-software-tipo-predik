"""Servicio de densidad poblacional.

Consulta directa a raw_data.ageb_geometries + raw_data.ageb_demographics
con ponderación proporcional de área intersectada.
"""
import json
from typing import Any, Dict, List
from uuid import uuid4

from geoalchemy2 import functions as geo_funcs
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.models.raw_data import AgebDemographics, AgebGeometry


def calculate_densidad_poblacional(
    db: Session,
    organization_id: str,
    polygon: Dict[str, Any],
) -> Dict[str, Any]:
    polygon_json = json.dumps(polygon)
    polygon_geom = geo_funcs.ST_GeomFromGeoJSON(polygon_json)

    query = (
        select(
            AgebGeometry,
            AgebDemographics,
            (
                func.ST_Area(func.ST_Intersection(AgebGeometry.geom, polygon_geom))
                / func.nullif(func.ST_Area(AgebGeometry.geom), 0)
            ).label("fraccion_area"),
        )
        .join(AgebDemographics, AgebDemographics.cvegeo == AgebGeometry.cvegeo_9, isouter=True)
        .where(geo_funcs.ST_Intersects(AgebGeometry.geom, polygon_geom))
    )
    rows = db.execute(query).all()

    if not rows:
        raise ValueError("ZONA_SIN_DATOS_DEMOGRAFICOS")

    pobtot = pobmas = pobfem = p_0a14 = p_15a64 = p_65ymas = vivpar_hab = 0.0
    prom_ocup_vals: List[float] = []
    entidad = municipio = ""
    detalle: List[Dict[str, Any]] = []

    for ageb_geom, ageb_dem, fraccion in rows:
        fraccion = float(fraccion or 1.0)
        fraccion = min(max(fraccion, 0.0), 1.0)

        if not entidad and ageb_geom.nom_ent:
            entidad = ageb_geom.nom_ent
        if not municipio and ageb_geom.nom_mun:
            municipio = ageb_geom.nom_mun

        ageb_pobtot  = (ageb_dem.pobtot    or 0)   if ageb_dem else 0
        ageb_pobmas  = (ageb_dem.pobmas    or 0)   if ageb_dem else 0
        ageb_pobfem  = (ageb_dem.pobfem    or 0)   if ageb_dem else 0
        ageb_p0a14   = (ageb_dem.p_0a14    or 0)   if ageb_dem else 0
        ageb_p15a64  = (ageb_dem.p_15a64   or 0)   if ageb_dem else 0
        ageb_p65     = (ageb_dem.p_65ymas  or 0)   if ageb_dem else 0
        ageb_viv     = (ageb_dem.vivpar_hab or 0)  if ageb_dem else 0
        ageb_ocup    = (ageb_dem.prom_ocup  or 0.0) if ageb_dem else 0.0

        pobtot    += ageb_pobtot  * fraccion
        pobmas    += ageb_pobmas  * fraccion
        pobfem    += ageb_pobfem  * fraccion
        p_0a14    += ageb_p0a14   * fraccion
        p_15a64   += ageb_p15a64  * fraccion
        p_65ymas  += ageb_p65     * fraccion
        vivpar_hab += ageb_viv    * fraccion
        if ageb_ocup:
            prom_ocup_vals.append(ageb_ocup)

        ageb_area_km2 = db.execute(
            select(
                func.coalesce(
                    func.ST_Area(func.ST_Transform(AgebGeometry.geom, 3857)) / 1_000_000,
                    0.0,
                )
            ).where(AgebGeometry.cvegeo == ageb_geom.cvegeo)
        ).scalar_one_or_none() or 0.0

        ageb_area_ef = float(ageb_area_km2) * fraccion
        ageb_densidad = (ageb_pobtot * fraccion) / ageb_area_ef if ageb_area_ef > 0 else 0.0

        geom_json = db.execute(
            select(func.ST_AsGeoJSON(AgebGeometry.geom)).where(
                AgebGeometry.cvegeo == ageb_geom.cvegeo
            )
        ).scalar_one_or_none()

        detalle.append({
            "cvegeo":          ageb_geom.cvegeo,
            "nom_ent":         ageb_geom.nom_ent or "",
            "nom_mun":         ageb_geom.nom_mun or "",
            "pobtot":          int(round(ageb_pobtot * fraccion)),
            "fraccion_area":   round(fraccion, 4),
            "area_km2":        round(ageb_area_ef, 4),
            "densidad_hab_km2": round(ageb_densidad, 2),
            "geom":            geom_json or "",
        })

    area_km2 = db.execute(
        select(
            func.coalesce(
                func.ST_Area(
                    func.ST_Transform(func.ST_Union(AgebGeometry.geom), 3857)
                ) / 1_000_000,
                0.0,
            )
        ).where(geo_funcs.ST_Intersects(AgebGeometry.geom, polygon_geom))
    ).scalar_one_or_none() or 0.0

    densidad = pobtot / float(area_km2) if area_km2 > 0 else 0.0
    prom_ocup = round(sum(prom_ocup_vals) / len(prom_ocup_vals), 2) if prom_ocup_vals else 0.0

    return {
        "zona": {
            "entidad":  entidad or "Desconocido",
            "municipio": municipio or "Desconocido",
            "area_km2": round(float(area_km2), 4),
        },
        "poblacion_total":   int(round(pobtot)),
        "densidad_hab_km2":  round(densidad, 2),
        "por_genero":        {"masculino": int(round(pobmas)), "femenino": int(round(pobfem))},
        "por_grupo_edad":    {
            "0_14":   int(round(p_0a14)),
            "15_64":  int(round(p_15a64)),
            "65_mas": int(round(p_65ymas)),
        },
        "viviendas_habitadas": int(round(vivpar_hab)),
        "promedio_ocupantes":  prom_ocup,
        "agebs_analizadas":    len(rows),
        "detalle_agebs":       detalle,
        "analysis_id":         str(uuid4()),
    }
