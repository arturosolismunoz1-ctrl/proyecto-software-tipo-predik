import os
from datetime import datetime, timedelta, timezone
from typing import Any, Dict

from jose import JWTError, jwt

JWT_SECRET = os.getenv("JWT_SECRET", "dev_secret_change_in_production")
ALGORITHM = "HS256"
ACCESS_TOKEN_EXPIRE_MINUTES = 30
REFRESH_TOKEN_EXPIRE_DAYS = 7


def create_access_token(user_id: str, org_id: str, role: str) -> str:
    payload = {
        "sub": user_id,
        "org_id": org_id,
        "role": role,
        "type": "access",
        "exp": datetime.now(timezone.utc) + timedelta(minutes=ACCESS_TOKEN_EXPIRE_MINUTES),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=ALGORITHM)


def create_refresh_token(user_id: str) -> str:
    payload = {
        "sub": user_id,
        "type": "refresh",
        "exp": datetime.now(timezone.utc) + timedelta(days=REFRESH_TOKEN_EXPIRE_DAYS),
    }
    return jwt.encode(payload, JWT_SECRET, algorithm=ALGORITHM)


def decode_token(token: str) -> Dict[str, Any]:
    """Raises JWTError si el token es inválido o expiró."""
    return jwt.decode(token, JWT_SECRET, algorithms=[ALGORITHM])
