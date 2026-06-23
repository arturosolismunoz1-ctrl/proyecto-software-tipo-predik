from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel

from app.connectors.registry import get_connector, list_connectors, sync_connector
from app.deps import get_current_user

router = APIRouter()


def require_admin(current_user: dict = Depends(get_current_user)) -> dict:
    if current_user.get("role") != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail={"error": {"code": "PERMISOS_INSUFICIENTES", "message": "Se requiere rol admin."}},
        )
    return current_user


class SyncRequest(BaseModel):
    polygon: Optional[Dict[str, Any]] = None


class ConnectorStatus(BaseModel):
    nombre: str
    estado: str
    ultima_sincronizacion: str
    registros: int
    mensaje: Optional[str] = None


@router.get("/conectores", response_model=List[ConnectorStatus])
async def obtener_conectores(current_user: dict = Depends(require_admin)):
    connectors = []
    for descriptor in list_connectors():
        connectors.append(
            ConnectorStatus(
                nombre=descriptor.connector.name,
                estado=descriptor.status,
                ultima_sincronizacion=descriptor.last_synced.isoformat() if descriptor.last_synced else "",
                registros=descriptor.records_synced,
                mensaje=descriptor.message,
            )
        )
    return connectors


@router.get("/conectores/{nombre}/health", response_model=ConnectorStatus)
async def health_connector(nombre: str, current_user: dict = Depends(require_admin)):
    descriptor = get_connector(nombre)
    if descriptor is None:
        raise HTTPException(status_code=404, detail="Connector not found")
    return ConnectorStatus(
        nombre=descriptor.connector.name,
        estado=descriptor.status,
        ultima_sincronizacion=descriptor.last_synced.isoformat() if descriptor.last_synced else "",
        registros=descriptor.records_synced,
        mensaje=descriptor.message,
    )


@router.post("/conectores/{nombre}/sync", response_model=ConnectorStatus)
async def sync_connector_endpoint(nombre: str, request: Optional[SyncRequest] = None, current_user: dict = Depends(require_admin)):
    polygon = request.polygon if request else None
    try:
        descriptor = await sync_connector(nombre, polygon)
    except KeyError as exc:
        raise HTTPException(status_code=404, detail=str(exc))
    return ConnectorStatus(
        nombre=descriptor.connector.name,
        estado=descriptor.status,
        ultima_sincronizacion=descriptor.last_synced.isoformat() if descriptor.last_synced else "",
        registros=descriptor.records_synced,
        mensaje=descriptor.message,
    )
