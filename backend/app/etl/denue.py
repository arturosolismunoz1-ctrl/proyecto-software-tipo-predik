from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional

from geoalchemy2.elements import WKTElement
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.orm import Session

from app.connectors.base import GeoFeature
from app.connectors.inegi.denue import DenueConnector
from app.etl.base import BaseETL
from app.models.raw_data import DenueEstablishment


class DenueETL(BaseETL):
    def __init__(self) -> None:
        self.connector = DenueConnector()

    async def extract(self, **params) -> List[GeoFeature]:
        polygon: Optional[Dict[str, Any]] = params.pop("polygon", None)
        return await self.connector.fetch(polygon=polygon, **params)

    def transform(self, raw_items: List[GeoFeature]) -> List[GeoFeature]:
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
