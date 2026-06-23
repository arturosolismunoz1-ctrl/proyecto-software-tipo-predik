import os
from datetime import date, datetime, timezone
from typing import Any, Dict, List, Optional
from uuid import uuid4

import httpx

from app.connectors.base import BaseConnector, GeoFeature

_BASE_URL = "https://www.inegi.org.mx/app/api/denue/v1/consulta"
_MAX_PER_REQUEST = 2500


def _extract_scian(clee: str) -> str:
    """CLEE positions 5-10 (0-indexed) hold the 6-digit SCIAN code."""
    return clee[5:11] if len(clee) >= 11 else ""


def _parse_ubicacion(ubicacion: str) -> tuple[str, str]:
    """Return (municipio, entidad) from INEGI Ubicacion string."""
    parts = [p.strip() for p in ubicacion.split(",")]
    entidad = parts[-1] if len(parts) >= 1 else ""
    municipio = parts[-2] if len(parts) >= 2 else ""
    return municipio, entidad


def _item_to_geo_feature(item: Dict[str, Any]) -> Optional[GeoFeature]:
    try:
        lat = float(item.get("Latitud", 0) or 0)
        lon = float(item.get("Longitud", 0) or 0)
    except (ValueError, TypeError):
        return None

    if lat == 0.0 and lon == 0.0:
        return None

    clee = item.get("CLEE", "")
    ubicacion = item.get("Ubicacion", "")
    municipio, entidad = _parse_ubicacion(ubicacion)

    return GeoFeature(
        id=item.get("Id") or clee or str(uuid4()),
        name=item.get("Nombre", "Desconocido"),
        category=item.get("Clase_actividad", "Sin categoría"),
        scian_code=_extract_scian(clee),
        location={"type": "Point", "coordinates": [lon, lat]},
        properties={
            "clee": clee,
            "razon_social": item.get("Razon_social", ""),
            "estrato_personal": item.get("Estrato", ""),
            "tipo": item.get("Tipo", ""),
            "colonia": item.get("Colonia", ""),
            "cp": item.get("CP", ""),
            "entidad": entidad,
            "municipio": municipio,
            "calle": item.get("Calle", ""),
            "num_exterior": item.get("Num_Exterior", ""),
            "telefono": item.get("Telefono", ""),
            "correo": item.get("Correo_e", ""),
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        },
        raw_response=item,
    )


def _filter_by_bbox(features: List[GeoFeature], polygon: Dict[str, Any]) -> List[GeoFeature]:
    coords = polygon.get("coordinates", [[]])
    if not coords or not coords[0]:
        return features
    ring = coords[0]
    lons = [c[0] for c in ring]
    lats = [c[1] for c in ring]
    min_lon, max_lon = min(lons), max(lons)
    min_lat, max_lat = min(lats), max(lats)

    result = []
    for f in features:
        pt = f.location.get("coordinates", [])
        if len(pt) >= 2 and min_lon <= pt[0] <= max_lon and min_lat <= pt[1] <= max_lat:
            result.append(f)
    return result


class DenueConnector(BaseConnector):
    name = "inegi_denue"
    requires_auth = True

    async def fetch(self, polygon: Optional[Dict[str, Any]] = None, **params) -> List[GeoFeature]:
        token = os.getenv("INEGI_DENUE_TOKEN")
        if not token:
            return self._fallback(polygon)

        estado      = str(params.get("estado", "09")).zfill(2)
        keyword     = params.get("keyword", "") or ""
        max_records = min(int(params.get("max_records", 100)), _MAX_PER_REQUEST)

        features = await self._buscar_entidad(token, keyword, estado, max_records)

        if polygon:
            features = _filter_by_bbox(features, polygon)

        return features

    async def _buscar_entidad(
        self, token: str, keyword: str, estado: str, max_records: int
    ) -> List[GeoFeature]:
        """Busca establecimientos en toda una entidad federativa."""
        if not keyword:
            return []
        url = f"{_BASE_URL}/BuscarEntidad/{keyword}/{estado}/0/{max_records}/{token}"
        async with httpx.AsyncClient(timeout=30.0) as client:
            resp = await client.get(url)
            resp.raise_for_status()
            data = resp.json()

        features = []
        for item in data if isinstance(data, list) else []:
            geo = _item_to_geo_feature(item)
            if geo:
                features.append(geo)
        return features

    def health_check(self) -> bool:
        return bool(os.getenv("INEGI_DENUE_TOKEN"))

    def _fallback(self, polygon: Optional[Dict[str, Any]]) -> List[GeoFeature]:
        """Return demo features when no token is configured."""
        sample_coords: list = []
        if polygon:
            outer = polygon.get("coordinates", [[]])
            if outer:
                sample_coords = outer[0]
        ref = sample_coords[0] if sample_coords else [-99.1332, 19.4326]
        lon, lat = float(ref[0]), float(ref[1])

        return [
            GeoFeature(
                id=str(uuid4()),
                name="Tienda Demo 1",
                category="Restaurante",
                scian_code="581110",
                location={"type": "Point", "coordinates": [lon, lat]},
                properties={"estrato_personal": "0 a 5 personas", "entidad": "Demo", "municipio": "Demo"},
                raw_response={"source": "fallback_sample"},
            ),
            GeoFeature(
                id=str(uuid4()),
                name="Tienda Demo 2",
                category="Comercio al por menor",
                scian_code="461110",
                location={"type": "Point", "coordinates": [lon + 0.001, lat + 0.001]},
                properties={"estrato_personal": "6 a 10 personas", "entidad": "Demo", "municipio": "Demo"},
                raw_response={"source": "fallback_sample"},
            ),
            GeoFeature(
                id=str(uuid4()),
                name="Tienda Demo 3",
                category="Servicios",
                scian_code="541511",
                location={"type": "Point", "coordinates": [lon - 0.001, lat - 0.001]},
                properties={"estrato_personal": "11 a 30 personas", "entidad": "Demo", "municipio": "Demo"},
                raw_response={"source": "fallback_sample"},
            ),
        ]
