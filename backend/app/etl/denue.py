from collections import Counter
from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional

import h3
from geoalchemy2.elements import WKTElement
from sqlalchemy import func
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.connectors.base import GeoFeature
from app.connectors.inegi.denue import DenueConnector
from app.etl.base import BaseETL
from app.models.cube import CommercialDensityH3
from app.models.raw_data import DenueEstablishment


def _h3_boundary_to_wkt(boundary: list) -> str:
    """Convert h3 cell_to_boundary result to WKT POLYGON (closes the ring)."""
    coords = [(lng, lat) for lat, lng in boundary]
    coords.append(coords[0])
    coord_str = ", ".join(f"{lon} {lat}" for lon, lat in coords)
    return f"POLYGON(({coord_str}))"


class DenueETL(BaseETL):
    def __init__(self) -> None:
        self.connector = DenueConnector()

    async def extract(self, **params) -> List[GeoFeature]:
        polygon: Optional[Dict[str, Any]] = params.pop("polygon", None)
        return await self.connector.fetch(polygon=polygon, **params)

    def transform(self, raw_items: List[GeoFeature]) -> List[GeoFeature]:
        # GeoFeature normalization is done inside the connector; nothing extra here.
        return raw_items

    def load_raw(self, features: List[GeoFeature], db: Session) -> int:
        if not features:
            return 0

        rows = []
        for f in features:
            props = f.properties
            coords = f.location.get("coordinates", [0.0, 0.0])
            lon, lat = float(coords[0]), float(coords[1])
            rows.append(
                {
                    "clee": props.get("clee") or None,
                    "nombre": f.name,
                    "razon_social": props.get("razon_social", ""),
                    "clase_actividad": f.category,
                    "codigo_scian": f.scian_code,
                    "estrato_personal": props.get("estrato_personal", ""),
                    "entidad": props.get("entidad", ""),
                    "municipio": props.get("municipio", ""),
                    "localidad": "",
                    "colonia": props.get("colonia", ""),
                    "cp": props.get("cp", ""),
                    "geom": WKTElement(f"POINT({lon} {lat})", srid=4326),
                    "fuente_actualizacion": date.today(),
                    "fetched_at": datetime.now(timezone.utc),
                    "raw_response": f.raw_response,
                }
            )

        stmt = pg_insert(DenueEstablishment).values(rows)
        # On CLEE conflict, update all mutable fields; if CLEE is NULL skip the constraint.
        stmt = stmt.on_conflict_do_update(
            index_elements=["clee"],
            set_={
                "nombre": stmt.excluded.nombre,
                "razon_social": stmt.excluded.razon_social,
                "clase_actividad": stmt.excluded.clase_actividad,
                "codigo_scian": stmt.excluded.codigo_scian,
                "estrato_personal": stmt.excluded.estrato_personal,
                "entidad": stmt.excluded.entidad,
                "municipio": stmt.excluded.municipio,
                "colonia": stmt.excluded.colonia,
                "cp": stmt.excluded.cp,
                "geom": stmt.excluded.geom,
                "fuente_actualizacion": stmt.excluded.fuente_actualizacion,
                "fetched_at": stmt.excluded.fetched_at,
                "raw_response": stmt.excluded.raw_response,
            },
        )
        db.execute(stmt)
        db.commit()
        return len(rows)

    def aggregate_h3(self, db: Session, resolution: int = 9) -> int:
        rows = (
            db.query(
                DenueEstablishment.clase_actividad,
                DenueEstablishment.entidad,
                DenueEstablishment.municipio,
                func.ST_X(DenueEstablishment.geom).label("lon"),
                func.ST_Y(DenueEstablishment.geom).label("lat"),
            )
            .filter(DenueEstablishment.geom.isnot(None))
            .all()
        )

        if not rows:
            return 0

        cells: Dict[str, Dict[str, Any]] = {}
        for row in rows:
            if row.lat is None or row.lon is None:
                continue
            cell = h3.latlng_to_cell(float(row.lat), float(row.lon), resolution)
            if cell not in cells:
                cells[cell] = {
                    "categories": [],
                    "entidad": row.entidad or "",
                    "municipio": row.municipio or "",
                }
            cells[cell]["categories"].append(row.clase_actividad or "Sin categoría")

        h3_rows = []
        for cell, data in cells.items():
            cat_counts = Counter(data["categories"])
            top_cat = cat_counts.most_common(1)[0][0] if cat_counts else ""
            por_categoria = dict(cat_counts)

            centroid_latlng = h3.cell_to_latlng(cell)
            boundary = h3.cell_to_boundary(cell)
            centroid_wkt = f"POINT({centroid_latlng[1]} {centroid_latlng[0]})"
            hex_wkt = _h3_boundary_to_wkt(boundary)

            h3_rows.append(
                {
                    "h3_index": cell,
                    "h3_resolution": resolution,
                    "entidad": data["entidad"],
                    "municipio": data["municipio"],
                    "total_establecimientos": len(data["categories"]),
                    "por_categoria": por_categoria,
                    "top_categoria": top_cat,
                    "geom_centroid": WKTElement(centroid_wkt, srid=4326),
                    "geom_hexagon": WKTElement(hex_wkt, srid=4326),
                    "last_refreshed": datetime.now(timezone.utc),
                }
            )

        if not h3_rows:
            return 0

        stmt = pg_insert(CommercialDensityH3).values(h3_rows)
        stmt = stmt.on_conflict_do_update(
            index_elements=["h3_index"],
            set_={
                "total_establecimientos": stmt.excluded.total_establecimientos,
                "por_categoria": stmt.excluded.por_categoria,
                "top_categoria": stmt.excluded.top_categoria,
                "geom_centroid": stmt.excluded.geom_centroid,
                "geom_hexagon": stmt.excluded.geom_hexagon,
                "last_refreshed": stmt.excluded.last_refreshed,
            },
        )
        db.execute(stmt)
        db.commit()
        return len(h3_rows)
