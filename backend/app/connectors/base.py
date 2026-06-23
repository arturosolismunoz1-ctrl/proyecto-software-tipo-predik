from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


class GeoFeature(BaseModel):
    id: str = Field(..., description="Unique feature identifier")
    name: str = Field(..., description="Feature name or business name")
    category: str = Field(..., description="Readable category name")
    scian_code: str = Field(..., description="SCIÁN category code")
    location: Dict[str, Any] = Field(..., description="GeoJSON location payload")
    properties: Dict[str, Any] = Field(default_factory=dict)
    raw_response: Dict[str, Any] = Field(default_factory=dict)


class BaseConnector(ABC):
    name: str
    requires_auth: bool = False

    @abstractmethod
    async def fetch(self, polygon: Optional[Dict[str, Any]] = None, **params) -> List[GeoFeature]:
        ...

    @abstractmethod
    def health_check(self) -> bool:
        ...
