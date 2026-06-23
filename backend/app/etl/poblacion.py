"""ETL: ageb_demographics + ageb_geometries → cube.population_density_h3

Estrategia:
  Para cada AGEB con geometría y datos demográficos:
  1. Obtener el centroide del AGEB.
  2. Calcular el índice H3 (resolución configurable, default 8).
  3. Agregar todos los AGEBs que caen en la misma celda H3.
  4. Upsert en cube.population_density_h3.
"""
from datetime import datetime, timezone
from typing import Optional

import h3
from geoalchemy2.elements import WKTElement
from sqlalchemy import func, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.models.cube import PopulationDensityH3
from app.models.raw_data import AgebDemographics, AgebGeometry


def _h3_boundary_to_wkt(boundary: list) -> str:
    coords = [(lng, lat) for lat, lng in boundary]
    coords.append(coords[0])
    return "POLYGON((" + ", ".join(f"{lon} {lat}" for lon, lat in coords) + "))"


def run_poblacion_etl(
    db: Session,
    h3_resolution: int = 8,
    entidad_filter: Optional[str] = None,
    batch_size: int = 500,
) -> int:
    query = (
        select(AgebGeometry, AgebDemographics)
        .join(AgebDemographics, AgebDemographics.cvegeo == AgebGeometry.cvegeo)
        .where(AgebGeometry.geom.isnot(None))
    )
    if entidad_filter:
        query = query.where(AgebGeometry.clave_ent == entidad_filter)

    rows = db.execute(query).all()
    if not rows:
        return 0

    # Agrupa por celda H3
    cells: dict = {}

    for ageb_geom, ageb_dem in rows:
        centroid = db.execute(
            select(
                func.ST_X(func.ST_Centroid(AgebGeometry.geom)),
                func.ST_Y(func.ST_Centroid(AgebGeometry.geom)),
            ).where(AgebGeometry.cvegeo == ageb_geom.cvegeo)
        ).one_or_none()

        if centroid is None:
            continue
        lon, lat = centroid

        try:
            cell = h3.latlng_to_cell(lat, lon, h3_resolution)
        except Exception:
            continue

        if cell not in cells:
            cells[cell] = {
                "h3_index": cell,
                "h3_resolution": h3_resolution,
                "entidad": ageb_geom.nom_ent or "",
                "municipio": ageb_geom.nom_mun or "",
                "pobtot": 0,
                "pobmas": 0,
                "pobfem": 0,
                "p_0a14": 0,
                "p_15a64": 0,
                "p_65ymas": 0,
                "vivpar_hab": 0,
            }

        c = cells[cell]
        c["pobtot"] += ageb_dem.pobtot or 0
        c["pobmas"] += ageb_dem.pobmas or 0
        c["pobfem"] += ageb_dem.pobfem or 0
        c["p_0a14"] += ageb_dem.p_0a14 or 0
        c["p_15a64"] += ageb_dem.p_15a64 or 0
        c["p_65ymas"] += ageb_dem.p_65ymas or 0
        c["vivpar_hab"] += ageb_dem.vivpar_hab or 0

    now = datetime.now(timezone.utc)
    batch = []

    for cell_data in cells.values():
        boundary = h3.cell_to_boundary(cell_data["h3_index"])
        wkt_hex = _h3_boundary_to_wkt(boundary)
        center = h3.cell_to_latlng(cell_data["h3_index"])
        wkt_centroid = f"POINT({center[1]} {center[0]})"

        # Área aproximada del hexágono en km² para calcular densidad
        area_km2 = h3.cell_area(cell_data["h3_index"], unit="km^2")
        densidad = cell_data["pobtot"] / area_km2 if area_km2 > 0 else 0.0

        batch.append(
            {
                **cell_data,
                "densidad_hab_km2": round(densidad, 2),
                "geom_centroid": WKTElement(wkt_centroid, srid=4326),
                "geom_hexagon": WKTElement(wkt_hex, srid=4326),
                "last_refreshed": now,
            }
        )

        if len(batch) >= batch_size:
            _flush(db, batch)
            batch.clear()

    if batch:
        _flush(db, batch)

    db.commit()
    return len(cells)


def _flush(db: Session, batch: list) -> None:
    stmt = pg_insert(PopulationDensityH3).values(batch)
    update_cols = {
        k: getattr(stmt.excluded, k)
        for k in batch[0]
        if k != "h3_index"
    }
    stmt = stmt.on_conflict_do_update(index_elements=["h3_index"], set_=update_cols)
    db.execute(stmt)
