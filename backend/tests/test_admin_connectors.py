from fastapi.testclient import TestClient
from app.main import app

client = TestClient(app)


def test_get_conectores():
    response = client.get("/api/v1/admin/conectores")
    assert response.status_code == 200
    assert isinstance(response.json(), list)


def test_health_connector():
    response = client.get("/api/v1/admin/conectores/inegi_denue/health")
    assert response.status_code == 200
    payload = response.json()
    assert payload["nombre"] == "inegi_denue"
    assert payload["estado"] in ["ok", "error"]


def test_sync_connector():
    response = client.post("/api/v1/admin/conectores/inegi_denue/sync")
    assert response.status_code == 200
    payload = response.json()
    assert payload["nombre"] == "inegi_denue"
    assert payload["registros"] == 3
    assert payload["mensaje"] == "Sync completed with 3 feature(s)."


def test_sync_connector_with_polygon_body():
    payload = {
        "polygon": {
            "type": "Polygon",
            "coordinates": [
                [
                    [ -99.14, 19.42 ],
                    [ -99.13, 19.42 ],
                    [ -99.13, 19.43 ],
                    [ -99.14, 19.43 ],
                    [ -99.14, 19.42 ],
                ]
            ]
        }
    }
    response = client.post("/api/v1/admin/conectores/inegi_denue/sync", json=payload)
    assert response.status_code == 200
    data = response.json()
    assert data["nombre"] == "inegi_denue"
    assert data["registros"] == 3
    assert "feature(s)" in data["mensaje"]
