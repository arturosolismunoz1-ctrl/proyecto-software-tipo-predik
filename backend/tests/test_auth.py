import uuid
import bcrypt
import pytest
from fastapi.testclient import TestClient

from app.main import app
from app.auth import create_access_token, create_refresh_token
from app.deps import get_db

client = TestClient(app)

# ── Fixtures ──────────────────────────────────────────────────────────────────

ORG_ID = str(uuid.uuid4())
USER_ID = str(uuid.uuid4())
PLAIN_PASSWORD = "test_password_123"


class FakeUser:
    id = USER_ID
    organization_id = ORG_ID
    email = "test@example.com"
    hashed_password = bcrypt.hashpw(PLAIN_PASSWORD.encode(), bcrypt.gensalt()).decode()
    role = "admin"


class FakeResult:
    def __init__(self, value):
        self._value = value

    def scalar_one_or_none(self):
        return self._value


class FakeDB:
    def __init__(self, user):
        self._user = user

    def execute(self, *args, **kwargs):
        return FakeResult(self._user)

    def get(self, model, pk):
        return self._user if self._user and str(self._user.id) == str(pk) else None


# ── Login ─────────────────────────────────────────────────────────────────────

def _db_with_user(user):
    def override():
        yield FakeDB(user)
    return override


def test_login_exitoso():
    app.dependency_overrides[get_db] = _db_with_user(FakeUser())
    try:
        response = client.post(
            "/api/v1/auth/login",
            json={"email": "test@example.com", "password": PLAIN_PASSWORD},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert "refresh_token" in data
        assert data["token_type"] == "bearer"
    finally:
        app.dependency_overrides.clear()


def test_login_password_incorrecta():
    app.dependency_overrides[get_db] = _db_with_user(FakeUser())
    try:
        response = client.post(
            "/api/v1/auth/login",
            json={"email": "test@example.com", "password": "password_incorrecta"},
        )
        assert response.status_code == 401
        assert response.json()["detail"]["error"]["code"] == "CREDENCIALES_INVALIDAS"
    finally:
        app.dependency_overrides.clear()


def test_login_email_no_existe():
    app.dependency_overrides[get_db] = _db_with_user(None)
    try:
        response = client.post(
            "/api/v1/auth/login",
            json={"email": "noexiste@example.com", "password": PLAIN_PASSWORD},
        )
        assert response.status_code == 401
        assert response.json()["detail"]["error"]["code"] == "CREDENCIALES_INVALIDAS"
    finally:
        app.dependency_overrides.clear()


# ── Refresh token ─────────────────────────────────────────────────────────────

def test_refresh_token_valido():
    refresh_token = create_refresh_token(user_id=USER_ID)
    app.dependency_overrides[get_db] = _db_with_user(FakeUser())
    try:
        response = client.post(
            "/api/v1/auth/refresh",
            json={"refresh_token": refresh_token},
        )
        assert response.status_code == 200
        data = response.json()
        assert "access_token" in data
        assert data["token_type"] == "bearer"
    finally:
        app.dependency_overrides.clear()


def test_refresh_con_access_token_falla():
    """No se puede usar un access token como refresh token."""
    access_token = create_access_token(user_id=USER_ID, org_id=ORG_ID, role="admin")
    response = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": access_token},
    )
    assert response.status_code == 401
    assert response.json()["detail"]["error"]["code"] == "TOKEN_INVALIDO"


def test_refresh_token_invalido():
    response = client.post(
        "/api/v1/auth/refresh",
        json={"refresh_token": "esto.no.es.un.jwt"},
    )
    assert response.status_code == 401


# ── Endpoints protegidos ──────────────────────────────────────────────────────

def test_endpoint_protegido_sin_token():
    response = client.post(
        "/api/v1/zona/concentracion-comercial",
        json={"geometry": {"type": "Polygon", "coordinates": []}},
    )
    assert response.status_code == 401


def test_endpoint_protegido_token_invalido():
    response = client.post(
        "/api/v1/zona/concentracion-comercial",
        json={"geometry": {"type": "Polygon", "coordinates": []}},
        headers={"Authorization": "Bearer token_basura"},
    )
    assert response.status_code == 401
    assert response.json()["detail"]["error"]["code"] == "TOKEN_INVALIDO"


def test_endpoint_protegido_token_valido_llega_a_logica(monkeypatch):
    """Con token válido el request pasa la capa de auth (error de negocio, no 401)."""
    access_token = create_access_token(user_id=USER_ID, org_id=ORG_ID, role="admin")

    response = client.post(
        "/api/v1/zona/concentracion-comercial",
        json={
            "geometry": {
                "type": "Polygon",
                "coordinates": [
                    [[-99.14, 19.42], [-99.13, 19.42], [-99.13, 19.43], [-99.14, 19.43], [-99.14, 19.42]]
                ],
            }
        },
        headers={"Authorization": f"Bearer {access_token}"},
    )
    # Debe fallar por lógica de negocio (sin datos en cubo), NO por auth
    assert response.status_code != 401
