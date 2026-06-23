from fastapi.testclient import TestClient

from app.main import app
from app.api.v1.admin import require_admin

client = TestClient(app)

FAKE_ADMIN = {"user_id": "00000000-0000-0000-0000-000000000001", "org_id": "00000000-0000-0000-0000-000000000002", "role": "admin"}


def _override_admin():
    return FAKE_ADMIN


def test_get_conectores():
    app.dependency_overrides[require_admin] = _override_admin
    try:
        response = client.get("/api/v1/admin/conectores")
        assert response.status_code == 200
        assert isinstance(response.json(), list)
    finally:
        app.dependency_overrides.clear()


def test_health_connector():
    app.dependency_overrides[require_admin] = _override_admin
    try:
        response = client.get("/api/v1/admin/conectores/inegi_denue/health")
        assert response.status_code == 200
        payload = response.json()
        assert payload["nombre"] == "inegi_denue"
        assert payload["estado"] in ["ok", "error"]
    finally:
        app.dependency_overrides.clear()


def test_sync_connector():
    app.dependency_overrides[require_admin] = _override_admin
    try:
        response = client.post("/api/v1/admin/conectores/inegi_denue/sync")
        assert response.status_code == 200
        payload = response.json()
        assert payload["nombre"] == "inegi_denue"
        assert payload["registros"] == 3
        assert payload["mensaje"] == "Sync completed with 3 feature(s)."
    finally:
        app.dependency_overrides.clear()


def test_sync_connector_with_polygon_body():
    app.dependency_overrides[require_admin] = _override_admin
    try:
        payload = {
            "polygon": {
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
        }
        response = client.post("/api/v1/admin/conectores/inegi_denue/sync", json=payload)
        assert response.status_code == 200
        data = response.json()
        assert data["nombre"] == "inegi_denue"
        assert data["registros"] == 3
        assert "feature(s)" in data["mensaje"]
    finally:
        app.dependency_overrides.clear()


def test_admin_sin_token_retorna_401():
    response = client.get("/api/v1/admin/conectores")
    assert response.status_code == 401


def test_admin_con_rol_analyst_retorna_403():
    app.dependency_overrides[require_admin] = lambda: (_ for _ in ()).throw(
        __import__("fastapi").HTTPException(
            status_code=403,
            detail={"error": {"code": "PERMISOS_INSUFICIENTES", "message": "Se requiere rol admin."}}
        )
    )
    try:
        response = client.get("/api/v1/admin/conectores")
        assert response.status_code == 403
    finally:
        app.dependency_overrides.clear()
