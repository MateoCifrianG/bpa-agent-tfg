"""
ejecutar.py — Endpoints para ejecutar y gestionar automatizaciones reales.

POST /api/ejecutar/{auto_id}           → Ejecutar ahora (manual)
GET  /api/ejecutar/{auto_id}/historial → Historial de ejecuciones
POST /api/ejecutar/{auto_id}/programar → Programar con cron
DELETE /api/ejecutar/{auto_id}/programar → Desprogramar
GET  /api/ejecutar/scheduler/jobs       → Ver jobs activos
GET  /api/ejecutar/connectors/smtp-presets → Presets SMTP conocidos
POST /api/ejecutar/test/email          → Probar conector email
POST /api/ejecutar/test/telegram       → Probar conector Telegram
POST /api/ejecutar/test/webhook        → Probar webhook saliente
"""
from __future__ import annotations

from typing import Optional
from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.jwt import get_current_user
from app.database import get_db
from app.models.automatizacion import Automatizacion
from app.models.empresa import Empresa
from app.models.ejecucion_log import EjecucionLog
from app.models.user import User
from app.services.automation_executor import ejecutar_automatizacion
from app.services.scheduler import (
    programar_automatizacion,
    desprogramar_automatizacion,
    listar_jobs_activos,
)
from app.services.connectors.email_connector import enviar_email, SMTP_PRESETS
from app.services.connectors.telegram_connector import enviar_mensaje as tg_mensaje, verificar_bot
from app.services.connectors.webhook_connector import enviar_webhook

router = APIRouter(prefix="/api/ejecutar", tags=["ejecutar"])


async def _get_empresa_id(db: AsyncSession, user: User) -> str:
    r = await db.execute(select(Empresa).where(Empresa.user_id == user.id))
    emp = r.scalars().first()
    if not emp:
        raise HTTPException(404, "No tienes empresa registrada")
    return emp.id


# ── Ejecutar ahora ────────────────────────────────────────────────
@router.post("/{auto_id}")
async def ejecutar_ahora(
    auto_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    empresa_id = await _get_empresa_id(db, user)
    resultado = await ejecutar_automatizacion(
        auto_id=auto_id,
        empresa_id=empresa_id,
        db=db,
        triggered_by="manual",
    )
    if not resultado["ok"]:
        raise HTTPException(400, detail=resultado["mensaje"])
    return resultado


# ── Historial de ejecuciones ─────────────────────────────────────
@router.get("/{auto_id}/historial")
async def historial(
    auto_id: str,
    limit: int = 50,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    empresa_id = await _get_empresa_id(db, user)
    # Verificar propiedad
    r = await db.execute(
        select(Automatizacion).where(
            Automatizacion.id == auto_id,
            Automatizacion.empresa_id == empresa_id,
        )
    )
    if not r.scalar_one_or_none():
        raise HTTPException(404, "Automatización no encontrada")

    logs_r = await db.execute(
        select(EjecucionLog)
        .where(EjecucionLog.automatizacion_id == auto_id)
        .order_by(EjecucionLog.created_at.desc())
        .limit(limit)
    )
    logs = logs_r.scalars().all()
    return [
        {
            "id": l.id,
            "estado": l.estado,
            "mensaje": l.mensaje,
            "triggered_by": l.triggered_by,
            "duracion_ms": l.duracion_ms,
            "created_at": l.created_at,
        }
        for l in logs
    ]


# ── Programar con cron ────────────────────────────────────────────
class ProgramarBody(BaseModel):
    cron_expr: str  # "0 9 * * 1" = lunes a las 9h


@router.post("/{auto_id}/programar")
async def programar(
    auto_id: str,
    body: ProgramarBody,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    empresa_id = await _get_empresa_id(db, user)
    r = await db.execute(
        select(Automatizacion).where(
            Automatizacion.id == auto_id,
            Automatizacion.empresa_id == empresa_id,
        )
    )
    auto = r.scalar_one_or_none()
    if not auto:
        raise HTTPException(404, "Automatización no encontrada")

    auto.tipo_trigger = "cron"
    auto.cron_expr    = body.cron_expr
    auto.estado       = "activa"
    await db.commit()

    programar_automatizacion(auto_id, empresa_id, body.cron_expr)
    return {"ok": True, "mensaje": f"Automatización programada: {body.cron_expr}"}


@router.delete("/{auto_id}/programar")
async def desprogramar(
    auto_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    empresa_id = await _get_empresa_id(db, user)
    r = await db.execute(
        select(Automatizacion).where(
            Automatizacion.id == auto_id,
            Automatizacion.empresa_id == empresa_id,
        )
    )
    auto = r.scalar_one_or_none()
    if not auto:
        raise HTTPException(404, "Automatización no encontrada")

    auto.tipo_trigger = "manual"
    auto.cron_expr    = None
    await db.commit()

    desprogramar_automatizacion(auto_id)
    return {"ok": True, "mensaje": "Automatización desprogramada"}


# ── Scheduler info ────────────────────────────────────────────────
@router.get("/scheduler/jobs")
async def jobs_activos(user: User = Depends(get_current_user)):
    return listar_jobs_activos()


# ── Presets SMTP ──────────────────────────────────────────────────
@router.get("/connectors/smtp-presets")
async def smtp_presets(user: User = Depends(get_current_user)):
    return SMTP_PRESETS


# ── Tests de conectores ───────────────────────────────────────────
class TestEmailBody(BaseModel):
    smtp_host: str
    smtp_port: int = 587
    smtp_user: str
    smtp_password: str
    destinatario: str


@router.post("/test/email")
async def test_email(body: TestEmailBody, user: User = Depends(get_current_user)):
    resultado = await enviar_email(
        smtp_host=body.smtp_host,
        smtp_port=body.smtp_port,
        smtp_user=body.smtp_user,
        smtp_password=body.smtp_password,
        destinatario=body.destinatario,
        asunto="✅ Test BPA-Agent — Conector Email funcionando",
        cuerpo=(
            "Este es un mensaje de prueba enviado por BPA-Agent.\n\n"
            "Si recibes este email, el conector está configurado correctamente.\n\n"
            "— BPA-Agent"
        ),
    )
    if not resultado["ok"]:
        raise HTTPException(400, detail=resultado["error"])
    return resultado


class TestTelegramBody(BaseModel):
    bot_token: str
    chat_id: str


@router.post("/test/telegram")
async def test_telegram(body: TestTelegramBody, user: User = Depends(get_current_user)):
    # Verificar bot primero
    verificacion = await verificar_bot(bot_token=body.bot_token)
    if not verificacion["ok"]:
        raise HTTPException(400, detail=verificacion["error"])

    resultado = await tg_mensaje(
        bot_token=body.bot_token,
        chat_id=body.chat_id,
        mensaje=(
            "✅ <b>Test BPA-Agent</b>\n\n"
            "Conector de Telegram funcionando correctamente.\n"
            f"Bot: <b>@{verificacion.get('bot_username', '?')}</b>"
        ),
    )
    if not resultado["ok"]:
        raise HTTPException(400, detail=resultado["error"])
    return {**resultado, "bot": verificacion}


class TestWebhookBody(BaseModel):
    url: str
    method: str = "POST"
    payload: Optional[dict] = None


@router.post("/test/webhook")
async def test_webhook(body: TestWebhookBody, user: User = Depends(get_current_user)):
    resultado = await enviar_webhook(
        url=body.url,
        payload=body.payload or {"source": "bpa-agent", "test": True, "mensaje": "Test de BPA-Agent"},
        method=body.method,
    )
    if not resultado["ok"]:
        raise HTTPException(400, detail=resultado["error"])
    return resultado
