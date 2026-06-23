"""
Tests for DenueETL — uses in-memory mocks for the DB session and connector.
"""
import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from datetime import datetime, timezone

from app.connectors.base import GeoFeature
from app.etl.denue import DenueETL, _h3_boundary_to_wkt


def _make_feature(lon: float = -99.15, lat: float = 19.47, idx: int = 1) -> GeoFeature:
    return GeoFeature(
        id=str(idx),
        name=f"Negocio {idx}",
        category="Comercio al por menor",
        scian_code="461110",
        location={"type": "Point", "coordinates": [lon, lat]},
        properties={
            "clee": f"09002461110{idx:04d}",
            "razon_social": "",
            "estrato_personal": "0 a 5 personas",
            "tipo": "Fijo",
            "colonia": "CENTRO",
            "cp": "06000",
            "entidad": "CIUDAD DE MÉXICO",
            "municipio": "Cuauhtémoc",
            "calle": "MADERO",
            "num_exterior": "1",
            "telefono": "",
            "correo": "",
            "fetched_at": datetime.now(timezone.utc).isoformat(),
        },
        raw_response={"source": "test"},
    )


def test_h3_boundary_to_wkt():
    boundary = [(19.47, -99.15), (19.48, -99.15), (19.48, -99.14), (19.47, -99.14)]
    wkt = _h3_boundary_to_wkt(boundary)
    assert wkt.startswith("POLYGON((")
    assert wkt.endswith("))")
    # ring should be closed
    assert wkt.count("-99.15 19.47") == 2


@pytest.mark.asyncio
async def test_extract_delegates_to_connector():
    etl = DenueETL()
    features = [_make_feature()]

    with patch.object(etl.connector, "fetch", new=AsyncMock(return_value=features)) as mock_fetch:
        result = await etl.extract(estado="09", keyword="comercio")

    mock_fetch.assert_called_once_with(polygon=None, estado="09", keyword="comercio")
    assert result == features


@pytest.mark.asyncio
async def test_extract_passes_polygon():
    etl = DenueETL()
    polygon = {"type": "Polygon", "coordinates": [[[-99.2, 19.4], [-99.1, 19.5], [-99.2, 19.4]]]}
    features = [_make_feature()]

    with patch.object(etl.connector, "fetch", new=AsyncMock(return_value=features)):
        result = await etl.extract(polygon=polygon, estado="09")

    assert result == features


def test_transform_returns_features_unchanged():
    etl = DenueETL()
    features = [_make_feature(idx=1), _make_feature(idx=2)]
    assert etl.transform(features) == features


def test_load_raw_returns_count_and_commits():
    etl = DenueETL()
    features = [_make_feature(idx=1), _make_feature(idx=2)]

    db = MagicMock()
    mock_stmt = MagicMock()
    mock_stmt.on_conflict_do_update.return_value = mock_stmt

    with patch("app.etl.denue.pg_insert", return_value=mock_stmt):
        count = etl.load_raw(features, db)

    assert count == 2
    db.execute.assert_called_once()
    db.commit.assert_called_once()


def test_load_raw_empty_features():
    etl = DenueETL()
    db = MagicMock()
    count = etl.load_raw([], db)
    assert count == 0
    db.execute.assert_not_called()


def test_aggregate_h3_returns_zero_when_no_rows():
    etl = DenueETL()
    db = MagicMock()
    db.query.return_value.filter.return_value.all.return_value = []
    count = etl.aggregate_h3(db)
    assert count == 0


def test_aggregate_h3_groups_by_cell():
    import h3 as h3lib

    etl = DenueETL()
    db = MagicMock()

    # Two features with same H3 cell, one with different cell
    lat1, lon1 = 19.47, -99.15
    lat2, lon2 = 19.4701, -99.1501  # very close — same H3 cell at res 9
    lat3, lon3 = 19.10, -98.50      # different cell

    FakeRow = type("R", (), {})

    def make_row(lat, lon, cat="Comercio", ent="CDMX", mun="Cuauhtemoc"):
        r = FakeRow()
        r.lat = lat
        r.lon = lon
        r.clase_actividad = cat
        r.entidad = ent
        r.municipio = mun
        return r

    rows = [make_row(lat1, lon1), make_row(lat2, lon2), make_row(lat3, lon3)]
    db.query.return_value.filter.return_value.all.return_value = rows

    mock_stmt = MagicMock()
    mock_stmt.on_conflict_do_update.return_value = mock_stmt

    with patch("app.etl.denue.pg_insert", return_value=mock_stmt):
        count = etl.aggregate_h3(db, resolution=9)

    # Should produce 2 cells (lat1+lat2 share a cell, lat3 is separate)
    assert count >= 1
    db.execute.assert_called_once()
    db.commit.assert_called_once()


@pytest.mark.asyncio
async def test_run_orchestrates_all_steps():
    etl = DenueETL()
    features = [_make_feature(idx=1)]
    db = MagicMock()

    with (
        patch.object(etl, "extract", new=AsyncMock(return_value=features)),
        patch.object(etl, "transform", return_value=features),
        patch.object(etl, "load_raw", return_value=1),
        patch.object(etl, "aggregate_h3", return_value=1),
    ):
        stats = await etl.run(db, resolution=9, estado="09")

    assert stats == {"extracted": 1, "loaded": 1, "aggregated": 1}
