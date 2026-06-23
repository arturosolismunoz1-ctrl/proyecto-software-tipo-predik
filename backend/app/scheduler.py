"""Scheduler de sincronización nocturna (APScheduler).

Activar con SCHEDULER_ENABLED=true en .env.
La hora de ejecución se configura con SCHEDULER_SYNC_TIME (formato HH:MM, UTC).
Default: 08:00 UTC (02:00 Ciudad de México en horario de verano).

Tareas programadas:
  1. ETL DENUE — extrae establecimientos y reconstruye cube.commercial_density_h3.
  2. ETL Población — agrega ageb_demographics en cube.population_density_h3.
"""
import asyncio
import logging
import os

from apscheduler.schedulers.background import BackgroundScheduler
from apscheduler.triggers.cron import CronTrigger

from app.db import SessionLocal
from app.etl.poblacion import run_poblacion_etl

logger = logging.getLogger(__name__)

_scheduler: BackgroundScheduler | None = None


def _sync_time() -> tuple[int, int]:
    raw = os.getenv("SCHEDULER_SYNC_TIME", "08:00")
    try:
        h, m = raw.split(":")
        return int(h), int(m)
    except ValueError:
        return 8, 0


# ── Tareas ────────────────────────────────────────────────────────────────────

def _job_etl_poblacion() -> None:
    logger.info("[scheduler] Iniciando ETL Población → cube.population_density_h3")
    db = SessionLocal()
    try:
        count = run_poblacion_etl(db)
        logger.info("[scheduler] ETL Población completado: %d celdas H3 procesadas", count)
    except Exception as exc:
        logger.error("[scheduler] ETL Población falló: %s", exc)
    finally:
        db.close()


def _job_etl_denue() -> None:
    """Lanza el ETL de DENUE de forma async desde un hilo síncrono."""
    from app.etl.denue import DenueETL

    logger.info("[scheduler] Iniciando ETL DENUE → cube.commercial_density_h3")
    db = SessionLocal()
    try:
        etl = DenueETL()
        count = asyncio.run(etl.run(db=db))
        logger.info("[scheduler] ETL DENUE completado: %d celdas H3 procesadas", count)
    except Exception as exc:
        logger.error("[scheduler] ETL DENUE falló: %s", exc)
    finally:
        db.close()


# ── Ciclo de vida ─────────────────────────────────────────────────────────────

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
    _scheduler.add_job(
        _job_etl_poblacion,
        CronTrigger(hour=hour, minute=minute + 15),  # 15 min después del DENUE
        id="etl_poblacion",
        replace_existing=True,
    )

    _scheduler.start()
    logger.info(
        "[scheduler] Activo — ETL DENUE %02d:%02d UTC, ETL Población %02d:%02d UTC",
        hour, minute, hour, (minute + 15) % 60,
    )


def stop_scheduler() -> None:
    global _scheduler
    if _scheduler and _scheduler.running:
        _scheduler.shutdown(wait=False)
        logger.info("[scheduler] Detenido")
