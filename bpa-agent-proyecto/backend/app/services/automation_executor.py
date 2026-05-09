"""
AutomationExecutor — ejecuta automatizaciones reales.

Soporta:
  - email      → envío de email via SMTP
  - telegram   → mensaje vía Telegram Bot
  - slack      → mensaje vía Slack Incoming Webhook
  - teams      → mensaje vía Teams Incoming Webhook
  - webhook_out → petición HTTP a cualquier URL
  - script     → (futuro) script Python embebido

El config_json de la automatización almacena los parámetros cifrados.
"""
from __future__ import annotations

import json
import time
import logging
from datetime import datetime, timezone
from typing import TYPE_CHECKING

from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models.automatizacion import Automatizacion
from app.models.ejecucion_log import EjecucionLog
from app.services.connectors import email_connector, telegram_connector, webhook_connector

if TYPE_CHECKING:
    pass

log = logging.getLogger(__name__)


async def ejecutar_automatizacion(
    auto_id: str,
    empresa_id: str,
    db: AsyncSession,
    triggered_by: str = "manual",
    contexto_extra: dict | None = None,
) -> dict:
    """
    Ejecuta una automatización por su ID.
    Registra el resultado en ejecuciones_log.
    Devuelve {"ok": True/False, "mensaje": "...", "log_id": "..."}
    """
    # Cargar automatización
    result = await db.execute(
        select(Automatizacion).where(
            Automatizacion.id == auto_id,
            Automatizacion.empresa_id == empresa_id,
        )
    )
    auto = result.scalar_one_or_none()
    if not auto:
        return {"ok": False, "mensaje": "Automatización no encontrada"}

    if auto.estado == "pausada":
        return {"ok": False, "mensaje": "La automatización está pausada"}

    # Parsear config
    config: dict = {}
    if auto.config_json:
        try:
            config = json.loads(auto.config_json)
        except Exception:
            pass

    # Merge contexto extra (variables dinámicas del agente)
    if contexto_extra:
        config.update(contexto_extra)

    t_start = time.monotonic()
    resultado = await _ejecutar_accion(auto.tipo_accion, config)
    duracion_ms = int((time.monotonic() - t_start) * 1000)

    # Registrar log
    estado_log = "ok" if resultado.get("ok") else "error"
    log_entry = EjecucionLog(
        automatizacion_id=auto_id,
        empresa_id=empresa_id,
        estado=estado_log,
        mensaje=resultado.get("mensaje") or resultado.get("error"),
        triggered_by=triggered_by,
        duracion_ms=str(duracion_ms),
    )
    db.add(log_entry)

    # Actualizar automatización
    auto.ejecuciones = (auto.ejecuciones or 0) + 1
    auto.last_run_at = datetime.now(timezone.utc)
    if estado_log == "error":
        auto.estado = "error"
    elif auto.estado in ("pendiente", "error"):
        auto.estado = "activa"

    await db.commit()
    await db.refresh(log_entry)

    return {
        "ok": resultado.get("ok", False),
        "mensaje": resultado.get("mensaje") or resultado.get("error"),
        "log_id": log_entry.id,
        "duracion_ms": duracion_ms,
    }


async def _ejecutar_accion(tipo_accion: str, config: dict) -> dict:
    """Despacha la acción al conector correspondiente."""

    if tipo_accion == "email":
        required = ["smtp_host", "smtp_port", "smtp_user", "smtp_password", "destinatario", "asunto", "cuerpo"]
        missing = [k for k in required if not config.get(k)]
        if missing:
            return {"ok": False, "error": f"Faltan parámetros de email: {', '.join(missing)}"}
        return await email_connector.enviar_email(
            smtp_host=config["smtp_host"],
            smtp_port=int(config["smtp_port"]),
            smtp_user=config["smtp_user"],
            smtp_password=config["smtp_password"],
            destinatario=config["destinatario"],
            asunto=config["asunto"],
            cuerpo=config["cuerpo"],
            cuerpo_html=config.get("cuerpo_html"),
            remitente_nombre=config.get("remitente_nombre", "BPA-Agent"),
        )

    elif tipo_accion == "telegram":
        required = ["bot_token", "chat_id", "mensaje"]
        missing = [k for k in required if not config.get(k)]
        if missing:
            return {"ok": False, "error": f"Faltan parámetros de Telegram: {', '.join(missing)}"}
        return await telegram_connector.enviar_mensaje(
            bot_token=config["bot_token"],
            chat_id=config["chat_id"],
            mensaje=config["mensaje"],
        )

    elif tipo_accion == "slack":
        if not config.get("webhook_url"):
            return {"ok": False, "error": "Falta webhook_url de Slack"}
        return await webhook_connector.enviar_slack(
            webhook_url=config["webhook_url"],
            mensaje=config.get("mensaje", "Automatización ejecutada por BPA-Agent"),
            titulo=config.get("titulo", "BPA-Agent"),
            color=config.get("color", "#4CAF50"),
        )

    elif tipo_accion == "teams":
        if not config.get("webhook_url"):
            return {"ok": False, "error": "Falta webhook_url de Teams"}
        return await webhook_connector.enviar_teams(
            webhook_url=config["webhook_url"],
            titulo=config.get("titulo", "BPA-Agent"),
            mensaje=config.get("mensaje", "Automatización ejecutada por BPA-Agent"),
        )

    elif tipo_accion == "webhook_out":
        if not config.get("url"):
            return {"ok": False, "error": "Falta url del webhook"}
        return await webhook_connector.enviar_webhook(
            url=config["url"],
            payload=config.get("payload", {"source": "bpa-agent", "timestamp": str(datetime.now(timezone.utc))}),
            method=config.get("method", "POST"),
            headers=config.get("headers"),
        )

    else:
        return {"ok": False, "error": f"Tipo de acción desconocido: {tipo_accion}"}
