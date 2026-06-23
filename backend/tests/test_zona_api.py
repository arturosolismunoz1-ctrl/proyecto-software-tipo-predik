from fastapi.testclient import TestClient

from app.main import app
from app.deps import get_db, get_current_user

client = TestClient(app)

FAKE_USER = {"user_id": "00000000-0000-0000-0000-000000000001", "org_id": "00000000-0000-0000-0000-000000000002", "role": "admin"}


def _override_auth():
    return FAKE_USER


def test_concentracion_comercial_invalid_geometry_type():
    app.dependency_overrides[get_current_user] = _override_auth
    try:
        response = client.post(
            "/api/v1/zona/concentracion-comercial",
            json={
                "geometry": {"type": "Point", "coordinates": [0, 0]},
                "filtros": {"categorias": ["restaurante"]},
            },
        )
        assert response.status_code == 400
        assert response.json()["detail"]["error"]["code"] == "GEOMETRIA_INVALIDA"
    finally:
        app.dependency_overrides.clear()


def test_concentracion_comercial_zona_sin_cobertura(monkeypatch):
    app.dependency_overrides[get_current_user] = _override_auth

    def fake_calculate_commercial_concentration(*, db, organization_id, polygon, filtros):
        raise ValueError("ZONA_SIN_COBERTURA")

    monkeypatch.setattr(
        "app.api.v1.zona.calculate_commercial_concentration",
        fake_calculate_commercial_concentration,
    )

    try:
        response = client.post(
            "/api/v1/zona/concentracion-comercial",
            json={
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [
                        [
                            [-99.14, 19.42],
                            [-99.13, 19.42],
                            [-99.13, 19.43],
                            [-99.14, 19.43],
                            [-99.14, 19.42],
                        ]
                    ],
                },
                "filtros": {"categorias": ["restaurante"]},
            },
        )
        assert response.status_code == 404
        assert response.json()["detail"]["error"]["code"] == "ZONA_SIN_COBERTURA"
    finally:
        app.dependency_overrides.clear()
