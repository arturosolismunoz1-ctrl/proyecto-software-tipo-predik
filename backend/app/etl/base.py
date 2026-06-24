from abc import ABC, abstractmethod
from typing import Any, Dict, List


class BaseETL(ABC):
    """Defines the three-step ETL contract for all data sources."""

    @abstractmethod
    async def extract(self, **params) -> List[Any]:
        ...

    @abstractmethod
    def transform(self, raw_items: List[Any]) -> List[Any]:
        ...

    @abstractmethod
    def load_raw(self, features: List[Any], db) -> int:
        """Upsert features into raw_data schema. Returns inserted/updated count."""
        ...

    async def run(self, db, **params) -> Dict[str, int]:
        raw = await self.extract(**params)
        features = self.transform(raw)
        loaded = self.load_raw(features, db)
        return {"extracted": len(raw), "loaded": loaded, "aggregated": 0}
