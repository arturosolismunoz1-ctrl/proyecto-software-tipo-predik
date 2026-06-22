from dataclasses import dataclass
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional

from app.connectors.base import BaseConnector
from app.connectors.inegi.denue import DenueConnector


@dataclass
class ConnectorDescriptor:
    connector: BaseConnector
    last_synced: Optional[datetime] = None
    records_synced: int = 0
    status: str = "unknown"
    message: Optional[str] = None


_connectors: Dict[str, ConnectorDescriptor] = {}


def register_connector(connector: BaseConnector) -> None:
    descriptor = ConnectorDescriptor(
        connector=connector,
        status="ok" if connector.health_check() else "error",
        message=None,
    )
    _connectors[connector.name] = descriptor


def get_connector(name: str) -> Optional[ConnectorDescriptor]:
    return _connectors.get(name)


def list_connectors() -> List[ConnectorDescriptor]:
    return list(_connectors.values())


async def sync_connector(name: str, polygon: Optional[Dict[str, Any]] = None) -> ConnectorDescriptor:
    descriptor = get_connector(name)
    if descriptor is None:
        raise KeyError(f"Connector '{name}' no registrado")

    features = await descriptor.connector.fetch(polygon or {})
    descriptor.last_synced = datetime.now(timezone.utc)
    descriptor.records_synced = len(features)
    descriptor.status = "ok"
    descriptor.message = f"Sync completed with {len(features)} feature(s)."
    return descriptor


register_connector(DenueConnector())
