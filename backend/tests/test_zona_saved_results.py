from datetime import datetime, timezone

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


class DummyRecord:
    def __init__(self, id: str, result_json: dict, created_at: str, analysis_type: str = "concentracion_comercial"):
        self.id = id
        self.result_json = result_json
        self.created_at = datetime.fromisoformat(created_at)
        self.analysis_type = analysis_type


class DummyDB:
    def __init__(self, record=None, records=None):
        self.record = record
        self.records = records or []
        self.deleted = False
        self.committed = False

    def get(self, model, key):
        return self.record if self.record and self.record.id == key else None

    def execute(self, statement):
        class Result:
            def __init__(self, records):
                self._records = records

            def scalars(self):
                class ScalarResult:
                    def __init__(self, records):
                        self._records = records

                    def all(self):
                        return self._records

                return ScalarResult(self._records)

        return Result(self.records)

    def delete(self, record):
        if self.record and self.record.id == record.id:
            self.deleted = True
            self.record = None

    def commit(self):
        self.committed = True


def test_obtener_analisis_guardado(monkeypatch):
    analysis_id = "00000000-0000-0000-0000-000000000001"
    sample_result = {
        "zona": {"entidad": "Demo", "municipio": "Demo", "area_km2": 0.0},
        "total_establecimientos": 0,
        "por_categoria": [],
        "negocios_ancla": [],
        "celdas_heatmap": [],
        "analysis_id": analysis_id,
    }

    dummy_db = DummyDB(record=DummyRecord(analysis_id, sample_result, "2026-06-20T00:00:00+00:00"))

    monkeypatch.setattr("app.api.v1.analisis.get_db", lambda: iter([dummy_db]))

    response = client.get(f"/api/v1/analisis/{analysis_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["analysis_id"] == analysis_id
    assert data["zona"]["entidad"] == "Demo"


def test_listar_analisis_guardado(monkeypatch):
    analysis_id = "00000000-0000-0000-0000-000000000003"
    sample_result = {
        "zona": {"entidad": "Demo", "municipio": "Demo", "area_km2": 0.0},
        "total_establecimientos": 0,
        "por_categoria": [],
        "negocios_ancla": [],
        "celdas_heatmap": [],
        "analysis_id": analysis_id,
    }
    record = DummyRecord(analysis_id, sample_result, "2026-06-20T00:00:00+00:00")
    dummy_db = DummyDB(records=[record])

    monkeypatch.setattr("app.api.v1.analisis.get_db", lambda: iter([dummy_db]))

    response = client.get("/api/v1/analisis/")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["analysis_id"] == analysis_id
    assert data[0]["entidad"] == "Demo"


def test_eliminar_analisis(monkeypatch):
    analysis_id = "00000000-0000-0000-0000-000000000002"
    sample_result = {
        "zona": {"entidad": "Demo", "municipio": "Demo", "area_km2": 0.0},
        "total_establecimientos": 0,
        "por_categoria": [],
        "negocios_ancla": [],
        "celdas_heatmap": [],
        "analysis_id": analysis_id,
    }
    record = DummyRecord(analysis_id, sample_result, "2026-06-20T00:00:00+00:00")
    dummy_db = DummyDB(record=record)

    monkeypatch.setattr("app.api.v1.analisis.get_db", lambda: iter([dummy_db]))

    response = client.delete(f"/api/v1/analisis/{analysis_id}")
    assert response.status_code == 200
    assert response.json()["deleted"] is True
    assert dummy_db.deleted is True
    assert dummy_db.committed is True
