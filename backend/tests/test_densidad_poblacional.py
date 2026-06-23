from fastapi.testclient import TestClient

from app.main import app
from app.deps import get_db, get_current_user

client = TestClient(app)

FAKE_USER = {
    "user_id": "00000000-0000-0000-0000-000000000001",
    "org_id": "00000000-0000-0000-0000-000000000002",
    "role": "admin",
}

_VALID_POLYGON = {
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
}

_FAKE_RESULT = {
    "zona": {"entidad": "Ciudad de México", "municipio": "Cuauhtémoc", "area_km2": 1.23},
    "poblacion_total": 5000,
    "densidad_hab_km2": 4065.04,
    "por_genero": {"masculino": 2400, "femenino": 2600},
    "por_grupo_edad": {"0_14": 800, "15_64": 3500, "65_mas": 700},
    "viviendas_habitadas": 1800,
    "promedio_ocupantes": 2.78,
    "agebs_analizadas": 3,
    "detalle_agebs": [
        {
            "cvegeo": "0900100010001",
            "nom_ent": "Ciudad de México",
            "nom_mun": "Cuauhtémoc",
            "pobtot": 5000,
            "fraccion_area": 1.0,
            "area_km2": 1.23,
            "densidad_hab_km2": 4065.04,
            "geom": '{"type":"MultiPolygon","coordinates":[]}',
        }
    ],
    "analysis_id": "aaaaaaaa-0000-0000-0000-000000000000",
}


def _override_auth():
    return FAKE_USER


# ── Validación de geometría ───────────────────────────────────────────────────

def test_densidad_geometria_invalida_tipo():
    app.dependency_overrides[get_current_user] = _override_auth
    try:
        response = client.post(
            "/api/v1/zona/densidad-poblacional",
            json={"geometry": {"type": "Point", "coordinates": [0, 0]}},
        )
        assert response.status_code == 400
        assert response.json()["detail"]["error"]["code"] == "GEOMETRIA_INVALIDA"
    finally:
        app.dependency_overrides.clear()


def test_densidad_sin_token_retorna_401():
    response = client.post(
        "/api/v1/zona/densidad-poblacional",
        json={"geometry": _VALID_POLYGON},
    )
    assert response.status_code == 401


# ── Sin datos demográficos ────────────────────────────────────────────────────

def test_densidad_zona_sin_datos(monkeypatch):
    app.dependency_overrides[get_current_user] = _override_auth

    def fake_calculate(**kwargs):
        raise ValueError("ZONA_SIN_DATOS_DEMOGRAFICOS")

    monkeypatch.setattr(
        "app.api.v1.zona.calculate_densidad_poblacional",
        fake_calculate,
    )

    try:
        response = client.post(
            "/api/v1/zona/densidad-poblacional",
            json={"geometry": _VALID_POLYGON},
        )
        assert response.status_code == 404
        assert response.json()["detail"]["error"]["code"] == "ZONA_SIN_DATOS_DEMOGRAFICOS"
    finally:
        app.dependency_overrides.clear()


# ── Respuesta exitosa ─────────────────────────────────────────────────────────

def test_densidad_respuesta_exitosa(monkeypatch):
    app.dependency_overrides[get_current_user] = _override_auth

    monkeypatch.setattr(
        "app.api.v1.zona.calculate_densidad_poblacional",
        lambda **kwargs: _FAKE_RESULT,
    )
    monkeypatch.setattr(
        "app.api.v1.zona.save_zona_analysis_result",
        lambda **kwargs: _FAKE_RESULT["analysis_id"],
    )

    try:
        response = client.post(
            "/api/v1/zona/densidad-poblacional",
            json={"geometry": _VALID_POLYGON},
        )
        assert response.status_code == 200
        data = response.json()
        assert data["poblacion_total"] == 5000
        assert data["densidad_hab_km2"] == 4065.04
        assert data["por_genero"]["masculino"] == 2400
        assert data["por_grupo_edad"]["0_14"] == 800
        assert data["agebs_analizadas"] == 3
        assert len(data["detalle_agebs"]) == 1
        assert data["analysis_id"] == _FAKE_RESULT["analysis_id"]
    finally:
        app.dependency_overrides.clear()


def test_densidad_zona_info_en_respuesta(monkeypatch):
    app.dependency_overrides[get_current_user] = _override_auth

    monkeypatch.setattr(
        "app.api.v1.zona.calculate_densidad_poblacional",
        lambda **kwargs: _FAKE_RESULT,
    )
    monkeypatch.setattr(
        "app.api.v1.zona.save_zona_analysis_result",
        lambda **kwargs: _FAKE_RESULT["analysis_id"],
    )

    try:
        response = client.post(
            "/api/v1/zona/densidad-poblacional",
            json={"geometry": _VALID_POLYGON},
        )
        assert response.status_code == 200
        zona = response.json()["zona"]
        assert zona["entidad"] == "Ciudad de México"
        assert zona["municipio"] == "Cuauhtémoc"
        assert zona["area_km2"] == 1.23
    finally:
        app.dependency_overrides.clear()
