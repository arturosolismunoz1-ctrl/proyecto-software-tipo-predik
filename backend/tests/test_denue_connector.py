"""
Tests for DenueConnector — uses httpx mock to avoid real network calls.
"""
import pytest
import httpx
from unittest.mock import AsyncMock, patch

from app.connectors.inegi.denue import (
    DenueConnector,
    _extract_scian,
    _parse_ubicacion,
    _item_to_geo_feature,
    _filter_by_bbox,
)

SAMPLE_ITEM = {
    "CLEE": "09002311830003261000000000U6",
    "Id": "742937",
    "Nombre": "TORTILLERIA LAS MINAS",
    "Razon_social": "",
    "Clase_actividad": "Elaboración de tortillas de maíz",
    "Estrato": "0 a 5 personas",
    "Tipo_vialidad": "CALLE",
    "Calle": "12",
    "Num_Exterior": "",
    "Num_Interior": "",
    "Colonia": "PRO HOGAR",
    "CP": "02600",
    "Ubicacion": "AZCAPOTZALCO, Azcapotzalco, CIUDAD DE MÉXICO",
    "Telefono": "",
    "Correo_e": "",
    "Sitio_internet": "",
    "Tipo": "Fijo",
    "Longitud": "-99.15394677",
    "Latitud": "19.47587760",
    "tipo_corredor_industrial": "",
    "nom_corredor_industrial": "",
    "numero_local": "",
}


def test_extract_scian_from_clee():
    assert _extract_scian("09002311830003261000000000U6") == "311830"


def test_extract_scian_short_clee():
    assert _extract_scian("0900") == ""


def test_parse_ubicacion_standard():
    municipio, entidad = _parse_ubicacion("AZCAPOTZALCO, Azcapotzalco, CIUDAD DE MÉXICO")
    assert entidad == "CIUDAD DE MÉXICO"
    assert municipio == "Azcapotzalco"


def test_parse_ubicacion_with_extra_spaces():
    municipio, entidad = _parse_ubicacion(
        "AZCAPOTZALCO                  , Azcapotzalco, CIUDAD DE MÉXICO"
    )
    assert entidad == "CIUDAD DE MÉXICO"
    assert municipio == "Azcapotzalco"


def test_item_to_geo_feature_maps_fields():
    geo = _item_to_geo_feature(SAMPLE_ITEM)
    assert geo is not None
    assert geo.id == "742937"
    assert geo.name == "TORTILLERIA LAS MINAS"
    assert geo.scian_code == "311830"
    assert geo.location["type"] == "Point"
    lon, lat = geo.location["coordinates"]
    assert abs(lon - (-99.15394677)) < 1e-5
    assert abs(lat - 19.47587760) < 1e-5
    assert geo.properties["entidad"] == "CIUDAD DE MÉXICO"
    assert geo.properties["municipio"] == "Azcapotzalco"


def test_item_to_geo_feature_skips_zero_coords():
    item = {**SAMPLE_ITEM, "Latitud": "0", "Longitud": "0"}
    assert _item_to_geo_feature(item) is None


def test_item_to_geo_feature_skips_invalid_coords():
    item = {**SAMPLE_ITEM, "Latitud": "abc", "Longitud": "xyz"}
    assert _item_to_geo_feature(item) is None


def test_filter_by_bbox_includes_inside():
    geo = _item_to_geo_feature(SAMPLE_ITEM)
    polygon = {
        "type": "Polygon",
        "coordinates": [[
            [-99.2, 19.4],
            [-99.1, 19.4],
            [-99.1, 19.5],
            [-99.2, 19.5],
            [-99.2, 19.4],
        ]],
    }
    result = _filter_by_bbox([geo], polygon)
    assert len(result) == 1


def test_filter_by_bbox_excludes_outside():
    geo = _item_to_geo_feature(SAMPLE_ITEM)
    polygon = {
        "type": "Polygon",
        "coordinates": [[
            [-98.0, 18.0],
            [-97.9, 18.0],
            [-97.9, 18.1],
            [-98.0, 18.1],
            [-98.0, 18.0],
        ]],
    }
    result = _filter_by_bbox([geo], polygon)
    assert len(result) == 0


@pytest.mark.asyncio
async def test_connector_uses_fallback_when_no_token(monkeypatch):
    monkeypatch.delenv("INEGI_DENUE_TOKEN", raising=False)
    connector = DenueConnector()
    features = await connector.fetch()
    assert len(features) == 3
    assert all(f.raw_response.get("source") == "fallback_sample" for f in features)


def _mock_http_response(data):
    """Create an httpx.Response with a stub request so raise_for_status() works."""
    req = httpx.Request("GET", "https://mock.inegi.test/")
    return httpx.Response(200, json=data, request=req)


@pytest.mark.asyncio
async def test_connector_fetch_real_api_response(monkeypatch):
    monkeypatch.setenv("INEGI_DENUE_TOKEN", "fake-token-test")

    async def mock_get(self, url, **kwargs):
        return _mock_http_response([SAMPLE_ITEM])

    with patch("httpx.AsyncClient.get", new=mock_get):
        connector = DenueConnector()
        features = await connector.fetch(estado="09", keyword="tortilleria")

    assert len(features) == 1
    assert features[0].name == "TORTILLERIA LAS MINAS"
    assert features[0].scian_code == "311830"


@pytest.mark.asyncio
async def test_connector_filters_by_polygon(monkeypatch):
    monkeypatch.setenv("INEGI_DENUE_TOKEN", "fake-token-test")

    outside_item = {
        **SAMPLE_ITEM,
        "Id": "999",
        "Latitud": "18.0",
        "Longitud": "-98.0",
    }

    async def mock_get(self, url, **kwargs):
        return _mock_http_response([SAMPLE_ITEM, outside_item])

    polygon = {
        "type": "Polygon",
        "coordinates": [[
            [-99.2, 19.4],
            [-99.1, 19.4],
            [-99.1, 19.5],
            [-99.2, 19.5],
            [-99.2, 19.4],
        ]],
    }

    with patch("httpx.AsyncClient.get", new=mock_get):
        connector = DenueConnector()
        features = await connector.fetch(polygon=polygon)

    assert len(features) == 1
    assert features[0].id == "742937"


def test_health_check_true_with_token(monkeypatch):
    monkeypatch.setenv("INEGI_DENUE_TOKEN", "some-token")
    assert DenueConnector().health_check() is True


def test_health_check_false_without_token(monkeypatch):
    monkeypatch.delenv("INEGI_DENUE_TOKEN", raising=False)
    assert DenueConnector().health_check() is False
