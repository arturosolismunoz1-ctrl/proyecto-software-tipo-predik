from abc import ABC, abstractmethod
from typing import Any, Dict, List


class BaseETL(ABC):
    """
    Defines the four-step ETL contract for all data sources.
    extract → transform → load_raw → aggregate_h3
    """

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

    @abstractmethod
    def aggregate_h3(self, db, resolution: int = 9) -> int:
        """Recompute H3 cube from raw_data. Returns number of hex cells written."""
        ...

    async def run(self, db, resolution: int = 9, **params) -> Dict[str, int]:
        raw = await self.extract(**params)
        features = self.transform(raw)
        loaded = self.load_raw(features, db)
        aggregated = self.aggregate_h3(db, resolution)
        return {"extracted": len(raw), "loaded": loaded, "aggregated": aggregated}
