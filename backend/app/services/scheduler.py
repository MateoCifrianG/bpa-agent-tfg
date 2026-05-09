"""
Scheduler de automatizaciones — ejecuta tareas programadas con APScheduler.
Completamente gratuito y embebido en el servidor FastAPI.

Cada automatización con tipo_trigger="cron" y un cron_expr válido se programa
automáticamente al arrancar el servidor o al crearse/activarse.
"""
from __future__ import annotations

import logging
from typing import Optional

from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from sqlalchemy import select

from app.database import AsyncSessionLocal
from app.models.automatizacion import Automatizacion

log = logging.getLogger(__name__)

# Instancia global del scheduler
_scheduler: Optional[AsyncIOScheduler] = None


def get_scheduler() -> AsyncIOScheduler:
    global _scheduler
    if _scheduler is None:
        _scheduler = AsyncIOScheduler(timezone="Europe/Madrid")
    return _scheduler


async def start_scheduler():
    """Arranca el scheduler y carga todas las automatizaciones activas."""
    scheduler = get_scheduler()
    if not scheduler.running:
        scheduler.start()
        log.info("Scheduler iniciado")
        await _load_all_cron_jobs()


async def stop_scheduler():
    scheduler = get_scheduler()
    if scheduler.running:
        scheduler.shutdown(wait=False)
        log.info("Scheduler detenido")


async def _load_all_cron_jobs():
    """Carga todas las automatizaciones con trigger cron desde la BD."""
    try:
        async with AsyncSessionLocal() as db:
            result = await db.execute(
                select(Automatizacion).where(
                    Automatizacion.tipo_trigger == "cron",
                    Automatizacion.cron_expr.isnot(None),
                    Automatizacion.estado == "activa",
                )
            )
            autos = result.scalars().all()
            for auto in autos:
                _programar_job(auto.id, auto.empresa_id, auto.cron_expr)
            log.info("Cargados %d cron jobs", len(autos))
    except Exception as exc:
        log.warning("Error cargando cron jobs: %s", exc)


def _programar_job(auto_id: str, empresa_id: str, cron_expr: str):
    """Añade o reemplaza un job en el scheduler."""
    scheduler = get_scheduler()
    job_id = f"auto_{auto_id}"

    # Eliminar si ya existe
    existing = scheduler.get_job(job_id)
    if existing:
        existing.remove()

    try:
        trigger = CronTrigger.from_crontab(cron_expr, timezone="Europe/Madrid")
        scheduler.add_job(
            _run_auto_job,
            trigger=trigger,
            id=job_id,
            args=[auto_id, empresa_id],
            replace_existing=True,
            misfire_grace_time=300,  # 5 min de gracia si el servidor estaba caído
        )
        log.info("Job programado: %s → %s", job_id, cron_expr)
    except Exception as exc:
        log.warning("Error programando job %s: %s", job_id, exc)


def _desprogramar_job(auto_id: str):
    """Elimina un job del scheduler."""
    scheduler = get_scheduler()
    job_id = f"auto_{auto_id}"
    job = scheduler.get_job(job_id)
    if job:
        job.remove()
        log.info("Job eliminado: %s", job_id)


async def _run_auto_job(auto_id: str, empresa_id: str):
    """Función que ejecuta el scheduler cuando llega la hora."""
    from app.services.automation_executor import ejecutar_automatizacion
    log.info("Ejecutando automatización programada: %s", auto_id)
    try:
        async with AsyncSessionLocal() as db:
            result = await ejecutar_automatizacion(
                auto_id=auto_id,
                empresa_id=empresa_id,
                db=db,
                triggered_by="cron",
            )
            log.info("Automatización %s → %s", auto_id, result.get("mensaje"))
    except Exception as exc:
        log.error("Error en job %s: %s", auto_id, exc)


# ── API pública para el router ─────────────────────────────────
def programar_automatizacion(auto_id: str, empresa_id: str, cron_expr: str):
    _programar_job(auto_id, empresa_id, cron_expr)


def desprogramar_automatizacion(auto_id: str):
    _desprogramar_job(auto_id)


def listar_jobs_activos() -> list[dict]:
    scheduler = get_scheduler()
    jobs = []
    for job in scheduler.get_jobs():
        jobs.append({
            "id": job.id,
            "next_run": str(job.next_run_time) if job.next_run_time else None,
            "trigger": str(job.trigger),
        })
    return jobs
