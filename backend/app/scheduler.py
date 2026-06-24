"""Scheduler de sincronización nocturna (APScheduler).

Activar con SCHEDULER_ENABLED=true en .env.
La hora de ejecución se configura con SCHEDULER_SYNC_TIME (formato HH:MM, UTC).
Default: 08:00 UTC (02:00 Ciudad de México en horario de verano).

Tareas programadas:
  1. ETL DENUE — extrae y actualiza raw_data.denue_establishments.
"""
import asyncio
import logging
import os

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.db import SessionLocal

logger = logging.getLogger(__name__)

_scheduler: BackgroundScheduler | None = None


def _sync_time() -> tuple[int, int]:
    raw = os.getenv("SCHEDULER_SYNC_TIME", "08:00")
    try:
        h, m = raw.split(":")
        return int(h), int(m)
    except ValueError:
        return 8, 0


def _job_etl_denue() -> None:
    from app.etl.denue import DenueETL

    logger.info("[scheduler] Iniciando ETL DENUE -> raw_data.denue_establishments")
    db = SessionLocal()
    try:
        etl = DenueETL()
        count = asyncio.run(etl.run(db=db))
        logger.info("[scheduler] ETL DENUE completado: %d registros procesados", count.get("loaded", 0))
    except Exception as exc:
        logger.error("[scheduler] ETL DENUE fallo: %s", exc)
    finally:
        db.close()


def start_scheduler() -> None:
    global _scheduler
    if not os.getenv("SCHEDULER_ENABLED", "false").lower() == "true":
        logger.info("[scheduler] Desactivado (SCHEDULER_ENABLED != true)")
        return

    hour, minute = _sync_time()
    _scheduler = BackgroundScheduler(timezone="UTC")

    _scheduler.add_job(
        _job_etl_denue,
        CronTrigger(hour=hour, minute=minute),
        id="etl_denue",
        replace_existing=True,
    )

    _scheduler.start()
    logger.info("[scheduler] Activo — ETL DENUE %02d:%02d UTC", hour, minute)


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("[scheduler] Detenido")
