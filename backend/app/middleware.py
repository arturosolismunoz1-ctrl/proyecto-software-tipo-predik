import os
import time
from uuid import uuid4

from starlette.middleware.base import BaseHTTPMiddleware
from starlette.requests import Request

from app.db import SessionLocal
from app.models.core import QueryLog

# Solo se loguean endpoints de análisis de negocio (los que consume el rate limiter)
_LOGGED_PREFIXES = ("/api/v1/zona/", "/api/v1/analisis", "/api/v1/reporte/")


class QueryLogMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next):
        should_log = any(request.url.path.startswith(p) for p in _LOGGED_PREFIXES)

        if not should_log:
            return await call_next(request)

        start = time.monotonic()
        response = await call_next(request)
        duration_ms = int((time.monotonic() - start) * 1000)

        # org_id y user_id vienen del JWT si el endpoint está protegido;
        # se leen del estado que get_current_user almacena en request.state.
        org_id = getattr(request.state, "org_id", None)
        user_id = getattr(request.state, "user_id", None)

        if org_id:
            try:
                db = SessionLocal()
                db.add(
                    QueryLog(
                        id=str(uuid4()),
                        organization_id=org_id,
                        user_id=user_id,
                        endpoint=f"{request.method} {request.url.path}",
                        request_summary=str(request.query_params) or "",
                        duration_ms=str(duration_ms),
                        status_code=str(response.status_code),
                    )
                )
                db.commit()
            except Exception:
                pass
            finally:
                db.close()

        return response
