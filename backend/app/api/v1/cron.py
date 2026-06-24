"""Endpoints para ETLs nocturnos invocados por Supabase pg_cron.
Usan autenticacion via API key (CRON_SECRET) en lugar de JWT."""
import os

from fastapi import APIRouter, Depends, HTTPException, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer

from app.deps import get_db
from app.etl.denue import DenueETL

router = APIRouter(prefix="/cron", tags=["cron"])
cron_scheme = HTTPBearer(auto_error=False)


def verify_cron(credentials: HTTPAuthorizationCredentials | None = Depends(cron_scheme)) -> None:
    secret = os.getenv("CRON_SECRET", "")
    if not secret:
        raise HTTPException(status_code=503, detail="CRON_SECRET no configurado")
    if not credentials or credentials.credentials != secret:
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="CRON_SECRET invalido o ausente",
        )


@router.post("/etl/denue")
async def cron_etl_denue(
    db=Depends(get_db),
    _=Depends(verify_cron),
):
    etl = DenueETL()
    stats = await etl.run(db=db, resolution=9, estado="09", keyword="", max_records=5000)
    return {"status": "ok", "source": "denue", **stats}


@router.post("/etl/poblacion")
async def cron_etl_poblacion(
    db=Depends(get_db),
    _=Depends(verify_cron),
):
    from app.etl.poblacion import run_poblacion_etl
    count = run_poblacion_etl(db)
    return {"status": "ok", "processed": count, "note": "No-op: datos de poblacion se consultan directamente desde AGEBs"}
