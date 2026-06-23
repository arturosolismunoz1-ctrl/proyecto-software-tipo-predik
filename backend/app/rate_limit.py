import os
from datetime import datetime, timezone

from fastapi import Depends, HTTPException, status
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app.deps import get_db, get_current_user
from app.models.core import Organization, QueryLog

_PLAN_LIMITS = {
    "starter": int(os.getenv("PLAN_STARTER_MONTHLY_LIMIT", "50")),
    "basic":   int(os.getenv("PLAN_BASIC_MONTHLY_LIMIT",   "500")),
    "plus":    int(os.getenv("PLAN_PLUS_MONTHLY_LIMIT",    "5000")),
}
_RATE_LIMIT_ENABLED = os.getenv("RATE_LIMIT_ENABLED", "false").lower() == "true"


def check_rate_limit(
    db: Session = Depends(get_db),
    current_user: dict = Depends(get_current_user),
) -> None:
    if not _RATE_LIMIT_ENABLED:
        return

    org_id = current_user["org_id"]
    org = db.get(Organization, org_id)
    if org is None:
        return

    limit = _PLAN_LIMITS.get(org.plan, _PLAN_LIMITS["starter"])

    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    count = db.execute(
        select(func.count(QueryLog.id)).where(
            QueryLog.organization_id == org_id,
            QueryLog.created_at >= month_start,
        )
    ).scalar_one_or_none() or 0

    if count >= limit:
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail={
                "error": {
                    "code": "LIMITE_CONSULTAS_EXCEDIDO",
                    "message": f"Límite mensual de {limit} consultas alcanzado para el plan '{org.plan}'.",
                    "details": {"plan": org.plan, "limite": limit, "consumido": count},
                }
            },
        )
