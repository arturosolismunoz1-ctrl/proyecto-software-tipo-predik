import bcrypt
from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from app.auth import create_access_token, create_refresh_token, decode_token
from app.deps import get_db
from app.models.core import User
from jose import JWTError

router = APIRouter()


class LoginRequest(BaseModel):
    email: str
    password: str


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"


class RefreshRequest(BaseModel):
    refresh_token: str


class AccessTokenResponse(BaseModel):
    access_token: str
    token_type: str = "bearer"


@router.post("/login", response_model=TokenResponse)
def login(request: LoginRequest, db: Session = Depends(get_db)):
    user = db.execute(
        select(User).where(User.email == request.email)
    ).scalar_one_or_none()

    invalid = HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail={"error": {"code": "CREDENCIALES_INVALIDAS", "message": "Email o contraseña incorrectos."}},
        headers={"WWW-Authenticate": "Bearer"},
    )

    if not user:
        raise invalid

    if not bcrypt.checkpw(request.password.encode(), user.hashed_password.encode()):
        raise invalid

    access_token = create_access_token(
        user_id=str(user.id),
        org_id=str(user.organization_id),
        role=user.role,
    )
    refresh_token = create_refresh_token(user_id=str(user.id))

    return TokenResponse(access_token=access_token, refresh_token=refresh_token)


@router.post("/refresh", response_model=AccessTokenResponse)
def refresh(request: RefreshRequest, db: Session = Depends(get_db)):
    try:
        payload = decode_token(request.refresh_token)
    except JWTError:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": {"code": "TOKEN_INVALIDO", "message": "Refresh token inválido o expirado."}},
        )

    if payload.get("type") != "refresh":
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": {"code": "TOKEN_INVALIDO", "message": "Se requiere un refresh token."}},
        )

    user = db.get(User, payload["sub"])
    if not user:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail={"error": {"code": "USUARIO_NO_ENCONTRADO", "message": "El usuario ya no existe."}},
        )

    access_token = create_access_token(
        user_id=str(user.id),
        org_id=str(user.organization_id),
        role=user.role,
    )
    return AccessTokenResponse(access_token=access_token)
