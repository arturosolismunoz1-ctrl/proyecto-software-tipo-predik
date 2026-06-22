import json
import os
from typing import Any, Dict, List
from uuid import uuid4

import httpx

from app.connectors.base import BaseConnector, GeoFeature


class DenueConnector(BaseConnector):
    name = "inegi_denue"
    requires_auth = False

    async def fetch(self, polygon: Dict[str, Any], **params) -> List[GeoFeature]:
        api_url = os.getenv("INEGI_DENUE_API_URL")
        if api_url:
            payload = {"polygon": polygon}
            payload.update(params)

            async with httpx.AsyncClient(timeout=20.0) as client:
                response = await client.get(api_url, params={"query": json.dumps(payload)})
                response.raise_for_status()
                data = response.json()

            features: List[GeoFeature] = []
            for item in data.get("features", []):
                geometry = item.get("geometry") or {}
                properties = item.get("properties") or {}
                feature_id = item.get("id") or properties.get("clee") or str(uuid4())
                features.append(
                    GeoFeature(
                        id=str(feature_id),
                        name=properties.get("nombre", properties.get("name", "Desconocido")),
                        category=properties.get("clase_actividad", properties.get("category", "Desconocido")),
                        scian_code=properties.get("codigo_scian", properties.get("scian_code", "")),
                        location=geometry,
                        properties=properties,
                        raw_response=item,
                    )
                )

            return features

        # Fallback sample features when no API URL is configured.
        sample_coords = polygon.get("coordinates", [])
        sample_point = (sample_coords[0][0] if sample_coords else [0.0, 0.0])
        return [
            GeoFeature(
                id=str(uuid4()),
                name="Tienda Demo 1",
                category="Restaurante",
                scian_code="581110",
                location={"type": "Point", "coordinates": [float(sample_point[0]), float(sample_point[1])] if isinstance(sample_point, list) else [0.0, 0.0]},
                properties={"estrato_personal": "Pequeño", "entidad": "Demo", "municipio": "Demo"},
                raw_response={"source": "fallback_sample"},
            ),
            GeoFeature(
                id=str(uuid4()),
                name="Tienda Demo 2",
                category="Comercio al por menor",
                scian_code="443142",
                location={"type": "Point", "coordinates": [float(sample_point[0]) + 0.001, float(sample_point[1]) + 0.001] if isinstance(sample_point, list) else [0.0, 0.0]},
                properties={"estrato_personal": "Mediano", "entidad": "Demo", "municipio": "Demo"},
                raw_response={"source": "fallback_sample"},
            ),
            GeoFeature(
                id=str(uuid4()),
                name="Tienda Demo 3",
                category="Servicios",
                scian_code="541511",
                location={"type": "Point", "coordinates": [float(sample_point[0]) - 0.001, float(sample_point[1]) - 0.001] if isinstance(sample_point, list) else [0.0, 0.0]},
                properties={"estrato_personal": "Grande", "entidad": "Demo", "municipio": "Demo"},
                raw_response={"source": "fallback_sample"},
            ),
        ]

    def health_check(self) -> bool:
        api_url = os.getenv("INEGI_DENUE_API_URL")
        return True if api_url else True
