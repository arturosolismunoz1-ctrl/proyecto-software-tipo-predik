from typing import Any, Dict, List, Optional

from fastapi import APIRouter, Depends, HTTPException, status
from pydantic import BaseModel
from sqlalchemy import text

from app.connectors.registry import get_connector, list_connectors, sync_connector
from app.deps import get_current_user, get_db

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


class TablaStatus(BaseModel):
    tabla: str
    registros: int
    estado: str       # "poblada" | "parcial" | "vacia"


class BDStatus(BaseModel):
    tablas: List[TablaStatus]
    resumen: str
    listo_para_reportes: bool


@router.get("/bd-status", response_model=BDStatus, summary="Estado de poblacion de la base de datos")
async def bd_status(db=Depends(get_db), _=Depends(require_admin)):
    """Muestra cuántos registros tiene cada tabla clave y si el sistema está listo."""
    _TABLAS = [
        ("raw_data.denue_establishments", 100_000, "DENUE establecimientos"),
        ("raw_data.ageb_geometries",      10_000,  "AGEBs geometrias (MGN)"),
        ("raw_data.ageb_demographics",    10_000,  "AGEBs censo 2020"),
        ("raw_data.manzana_vivienda",      1_000,  "Manzanas vivienda"),
    ]

    tablas = []
    for tabla_sql, umbral_ok, _ in _TABLAS:
        try:
            n = db.execute(text(f"SELECT COUNT(*) FROM {tabla_sql}")).scalar() or 0
        except Exception:
            n = -1
        if n < 0:
            estado = "error"
        elif n == 0:
            estado = "vacia"
        elif n < umbral_ok:
            estado = "parcial"
        else:
            estado = "poblada"
        tablas.append(TablaStatus(tabla=tabla_sql, registros=n, estado=estado))

    denue_ok  = next((t for t in tablas if "denue" in t.tabla), None)
    ageb_ok   = next((t for t in tablas if "geometries" in t.tabla), None)
    listo = bool(denue_ok and denue_ok.registros > 1_000)

    vacias = [t.tabla.split(".")[-1] for t in tablas if t.estado == "vacia"]
    parciales = [t.tabla.split(".")[-1] for t in tablas if t.estado == "parcial"]

    if vacias:
        resumen = f"Tablas vacias: {', '.join(vacias)}"
    elif parciales:
        resumen = f"Carga parcial en: {', '.join(parciales)}"
    else:
        resumen = "Base de datos completamente poblada"

    return BDStatus(tablas=tablas, resumen=resumen, listo_para_reportes=listo)


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
