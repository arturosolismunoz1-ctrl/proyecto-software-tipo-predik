"""Servicio de densidad poblacional.

Estrategia de consulta:
  1. Intenta consultar cube.population_density_h3 (fast path, pre-agregado).
  2. Si el cubo está vacío para esa zona, hace fallback a raw_data (AGEBs + demografía)
     con ponderación proporcional de área.
"""
import json
from typing import Any, Dict, List
from uuid import uuid4

from sqlalchemy import func, select
from sqlalchemy.orm import Session
from geoalchemy2 import functions as geo_funcs

from app.models.cube import PopulationDensityH3
from app.models.raw_data import AgebGeometry, AgebDemographics


# ── Fast path: consulta el cubo ───────────────────────────────────────────────

def _from_cube(
    db: Session,
    polygon_json: str,
) -> Dict[str, Any] | None:
    polygon_geom = geo_funcs.ST_GeomFromGeoJSON(polygon_json)

    query = select(PopulationDensityH3).where(
        geo_funcs.ST_Intersects(PopulationDensityH3.geom_hexagon, polygon_geom)
    )
    rows = db.execute(query).scalars().all()

    if not rows:
        return None

    pobtot = sum(r.pobtot or 0 for r in rows)
    pobmas = sum(r.pobmas or 0 for r in rows)
    pobfem = sum(r.pobfem or 0 for r in rows)
    p_0a14 = sum(r.p_0a14 or 0 for r in rows)
    p_15a64 = sum(r.p_15a64 or 0 for r in rows)
    p_65ymas = sum(r.p_65ymas or 0 for r in rows)
    vivpar_hab = sum(r.vivpar_hab or 0 for r in rows)
    entidad = next((r.entidad for r in rows if r.entidad), "Desconocido")
    municipio = next((r.municipio for r in rows if r.municipio), "Desconocido")

    area_km2 = db.execute(
        select(
            func.coalesce(
                func.ST_Area(
                    func.ST_Transform(
                        func.ST_Union(PopulationDensityH3.geom_hexagon), 3857
                    )
                ) / 1_000_000,
                0.0,
            )
        ).where(geo_funcs.ST_Intersects(PopulationDensityH3.geom_hexagon, polygon_geom))
    ).scalar_one_or_none() or 0.0

    densidad = pobtot / float(area_km2) if area_km2 > 0 else 0.0

    detalle: List[Dict[str, Any]] = []
    for r in rows:
        geom_json = db.execute(
            select(func.ST_AsGeoJSON(PopulationDensityH3.geom_hexagon)).where(
                PopulationDensityH3.h3_index == r.h3_index
            )
        ).scalar_one_or_none()
        detalle.append({
            "cvegeo": r.h3_index,
            "nom_ent": r.entidad or "",
            "nom_mun": r.municipio or "",
            "pobtot": r.pobtot or 0,
            "fraccion_area": 1.0,
            "area_km2": 0.0,
            "densidad_hab_km2": float(r.densidad_hab_km2 or 0),
            "geom": geom_json or "",
        })

    return {
        "zona": {
            "entidad": entidad,
            "municipio": municipio,
            "area_km2": round(float(area_km2), 4),
        },
        "poblacion_total": pobtot,
        "densidad_hab_km2": round(densidad, 2),
        "por_genero": {"masculino": pobmas, "femenino": pobfem},
        "por_grupo_edad": {"0_14": p_0a14, "15_64": p_15a64, "65_mas": p_65ymas},
        "viviendas_habitadas": vivpar_hab,
        "promedio_ocupantes": 0.0,
        "agebs_analizadas": len(rows),
        "detalle_agebs": detalle,
        "analysis_id": str(uuid4()),
        "_source": "cube",
    }


# ── Fallback: raw_data con ponderación proporcional ───────────────────────────

def _from_raw(
    db: Session,
    polygon_json: str,
) -> Dict[str, Any] | None:
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
        .join(AgebDemographics, AgebDemographics.cvegeo == AgebGeometry.cvegeo, isouter=True)
        .where(geo_funcs.ST_Intersects(AgebGeometry.geom, polygon_geom))
    )
    rows = db.execute(query).all()

    if not rows:
        return None

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

        ageb_pobtot = (ageb_dem.pobtot or 0) if ageb_dem else 0
        ageb_pobmas = (ageb_dem.pobmas or 0) if ageb_dem else 0
        ageb_pobfem = (ageb_dem.pobfem or 0) if ageb_dem else 0
        ageb_p0a14 = (ageb_dem.p_0a14 or 0) if ageb_dem else 0
        ageb_p15a64 = (ageb_dem.p_15a64 or 0) if ageb_dem else 0
        ageb_p65 = (ageb_dem.p_65ymas or 0) if ageb_dem else 0
        ageb_viv = (ageb_dem.vivpar_hab or 0) if ageb_dem else 0
        ageb_ocup = (ageb_dem.prom_ocup or 0.0) if ageb_dem else 0.0

        pobtot += ageb_pobtot * fraccion
        pobmas += ageb_pobmas * fraccion
        pobfem += ageb_pobfem * fraccion
        p_0a14 += ageb_p0a14 * fraccion
        p_15a64 += ageb_p15a64 * fraccion
        p_65ymas += ageb_p65 * fraccion
        vivpar_hab += ageb_viv * fraccion
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
            "cvegeo": ageb_geom.cvegeo,
            "nom_ent": ageb_geom.nom_ent or "",
            "nom_mun": ageb_geom.nom_mun or "",
            "pobtot": int(round(ageb_pobtot * fraccion)),
            "fraccion_area": round(fraccion, 4),
            "area_km2": round(ageb_area_ef, 4),
            "densidad_hab_km2": round(ageb_densidad, 2),
            "geom": geom_json or "",
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

    pobtot_int = int(round(pobtot))
    densidad = pobtot / float(area_km2) if area_km2 > 0 else 0.0
    prom_ocup = round(sum(prom_ocup_vals) / len(prom_ocup_vals), 2) if prom_ocup_vals else 0.0

    return {
        "zona": {
            "entidad": entidad or "Desconocido",
            "municipio": municipio or "Desconocido",
            "area_km2": round(float(area_km2), 4),
        },
        "poblacion_total": pobtot_int,
        "densidad_hab_km2": round(densidad, 2),
        "por_genero": {"masculino": int(round(pobmas)), "femenino": int(round(pobfem))},
        "por_grupo_edad": {
            "0_14": int(round(p_0a14)),
            "15_64": int(round(p_15a64)),
            "65_mas": int(round(p_65ymas)),
        },
        "viviendas_habitadas": int(round(vivpar_hab)),
        "promedio_ocupantes": prom_ocup,
        "agebs_analizadas": len(rows),
        "detalle_agebs": detalle,
        "analysis_id": str(uuid4()),
        "_source": "raw",
    }


# ── Punto de entrada público ──────────────────────────────────────────────────

def calculate_densidad_poblacional(
    db: Session,
    organization_id: str,
    polygon: Dict[str, Any],
) -> Dict[str, Any]:
    polygon_json = json.dumps(polygon)

    result = _from_cube(db, polygon_json) or _from_raw(db, polygon_json)

    if result is None:
        raise ValueError("ZONA_SIN_DATOS_DEMOGRAFICOS")

    # _source es interno, no se expone en la respuesta Pydantic
    result.pop("_source", None)
    return result
