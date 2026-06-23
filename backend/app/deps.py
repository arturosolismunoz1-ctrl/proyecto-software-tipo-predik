from typing import Dict, Any

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from jose import JWTError
from sqlalchemy.orm import Session

from app.auth import decode_token
from app.db import SessionLocal

bearer_scheme = HTTPBearer()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_current_user(
    request: Request,
    credentials: HTTPAuthorizationCredentials = Depends(bearer_scheme),
) -> Dict[str, Any]:
    token = credentials.credentials
    try:
        payload = decode_token(token)
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": {"code": "TOKEN_INVALIDO", "message": "Token inválido o expirado."}},
            headers={"WWW-Authenticate": "Bearer"},
        )

    if payload.get("type") != "access":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": {"code": "TOKEN_INVALIDO", "message": "Se requiere un access token."}},
            headers={"WWW-Authenticate": "Bearer"},
        )

    user = {
        "user_id": payload["sub"],
        "org_id": payload["org_id"],
        "role": payload["role"],
    }
    # Exponer en request.state para que QueryLogMiddleware pueda leerlo
    request.state.org_id = user["org_id"]
    request.state.user_id = user["user_id"]
    return user
