from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)


def test_concentracion_comercial_invalid_geometry_type():
    response = client.post(
        "/api/v1/zona/concentracion-comercial",
        json={
            "geometry": {"type": "Point", "coordinates": [0, 0]},
            "filtros": {"categorias": ["restaurante"]},
        },
    )

    assert response.status_code == 400
    assert response.json()["detail"]["error"]["code"] == "GEOMETRIA_INVALIDA"


def test_concentracion_comercial_zona_sin_cobertura(monkeypatch):
    def fake_calculate_commercial_concentration(*, db, organization_id, polygon, filtros):
        raise ValueError("ZONA_SIN_COBERTURA")

    monkeypatch.setattr(
        "app.api.v1.zona.calculate_commercial_concentration",
        fake_calculate_commercial_concentration,
    )

    response = client.post(
        "/api/v1/zona/concentracion-comercial",
        json={
            "geometry": {
                "type": "Polygon",
                "coordinates": [
                    [
                        [ -99.14, 19.42 ],
                        [ -99.13, 19.42 ],
                        [ -99.13, 19.43 ],
                        [ -99.14, 19.43 ],
                        [ -99.14, 19.42 ],
                    ]
                ],
            },
            "filtros": {"categorias": ["restaurante"]},
        },
    )

    assert response.status_code == 404
    assert response.json()["detail"]["error"]["code"] == "ZONA_SIN_COBERTURA"
