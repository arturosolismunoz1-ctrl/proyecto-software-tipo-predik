from typing import Any, Dict, List, Optional

from fastapi import APIRouter, HTTPException
from pydantic import BaseModel

from app.connectors.registry import get_connector, list_connectors, sync_connector

router = APIRouter()


class SyncRequest(BaseModel):
    polygon: Optional[Dict[str, Any]] = None


class ConnectorStatus(BaseModel):
    nombre: str
    estado: str
    ultima_sincronizacion: str
    registros: int
    mensaje: Optional[str] = None


@router.get("/conectores", response_model=List[ConnectorStatus])
async def obtener_conectores():
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
async def health_connector(nombre: str):
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
async def sync_connector_endpoint(nombre: str, request: Optional[SyncRequest] = None):
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
