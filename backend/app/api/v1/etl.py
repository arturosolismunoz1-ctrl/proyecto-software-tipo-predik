from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends
from pydantic import BaseModel

from app.api.v1.admin import require_admin
from app.deps import get_db
from app.etl.denue import DenueETL

router = APIRouter()

_ETL_REGISTRY: Dict[str, Any] = {
    "inegi_denue": DenueETL,
}


class ETLRunRequest(BaseModel):
    estado: str = "09"
    keyword: str = ""
    max_records: int = 100
    h3_resolution: int = 9
    polygon: Optional[Dict[str, Any]] = None


class ETLRunResult(BaseModel):
    source: str
    extracted: int
    loaded: int
    aggregated: int


@router.post("/etl/{source}/run", response_model=ETLRunResult)
async def run_etl(
    source: str,
    req: ETLRunRequest = ETLRunRequest(),
    db=Depends(get_db),
    _current_user: dict = Depends(require_admin),
) -> ETLRunResult:
    etl_cls = _ETL_REGISTRY.get(source)
    if etl_cls is None:
        from fastapi import HTTPException
        raise HTTPException(status_code=404, detail=f"ETL source '{source}' not found")

    etl = etl_cls()
    stats = await etl.run(
        db,
        resolution=req.h3_resolution,
        estado=req.estado,
        keyword=req.keyword,
        max_records=req.max_records,
        polygon=req.polygon,
    )
    return ETLRunResult(source=source, **stats)
