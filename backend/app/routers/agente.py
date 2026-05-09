"""
agente.py — BPA-Agent v5: motor razonador con Ollama LLM + fallback motor_v4.
Motor principal: motor_v5 (Ollama — llama3.1:8b, completamente gratuito y local).
Fallback:        motor_v4 (pipeline NLP sin LLM, siempre disponible).
"""

from __future__ import annotations

import json
import logging
from datetime import datetime
from typing import Optional

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.jwt import get_current_user
from app.config import settings
from app.database import get_db
from app.models.conversacion import Conversacion
from app.models.empresa import Empresa
from app.models.user import User
from app.agents import motor_v4
from app.agents import motor_v5
from app.agents import motor_v6
from app.security.sanitize import limpiar_input

log = logging.getLogger(__name__)

router = APIRouter(prefix="/api/agente", tags=["agente"])


# ─────────────────────────── Schemas ─────────────────────────────

class MensajeIn(BaseModel):
    mensaje: str
    conversacion_id: Optional[str] = None


class MensajeOut(BaseModel):
    id: str
    empresa_id: str
    titulo: Optional[str] = None
    historial: Optional[str] = None
    fase: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None
    model_config = {"from_attributes": True}


# ──────────────────────── Helper BD ──────────────────────────────

async def _get_empresa(db: AsyncSession, user: User) -> Empresa:
    result = await db.execute(select(Empresa).where(Empresa.user_id == user.id))
    empresa = result.scalars().first()
    if not empresa:
        raise HTTPException(status_code=404, detail="No tienes empresa registrada")
    return empresa










# ─────────────────────────── Endpoints ───────────────────────────

@router.get("/conversaciones", response_model=list[MensajeOut])
async def list_conversaciones(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    empresa = await _get_empresa(db, user)
    result = await db.execute(
        select(Conversacion)
        .where(Conversacion.empresa_id == empresa.id)
        .order_by(Conversacion.updated_at.desc())
    )
    return result.scalars().all()


@router.post("/chat")
async def chat(
    body: MensajeIn,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    empresa = await _get_empresa(db, user)

    conv = None
    if body.conversacion_id:
        result = await db.execute(
            select(Conversacion).where(
                Conversacion.id == body.conversacion_id,
                Conversacion.empresa_id == empresa.id,
            )
        )
        conv = result.scalar_one_or_none()

    if not conv:
        conv = Conversacion(
            empresa_id=empresa.id,
            titulo=body.mensaje[:60],
            historial="[]",
            fase="diagnostico",
        )
        db.add(conv)
        await db.flush()

    try:
        historial = json.loads(conv.historial or "[]")
    except Exception:
        historial = []

    mensaje_limpio = limpiar_input(body.mensaje, max_len=2000)
    if not mensaje_limpio:
        raise HTTPException(status_code=422, detail="Mensaje vacío")
    historial.append({"role": "user", "content": mensaje_limpio})

    accion  = None
    entidad = None

    # ── Motor selection: v6 (motor propio) → v5 (Ollama) → v4 (NLP) ────────
    respuesta_texto = ""

    # Motor v6: motor razonador propio con KB sectorial (primera opción siempre)
    try:
        result_d = await motor_v6.responder(mensaje_limpio, empresa, db, historial)
        respuesta_texto = result_d["respuesta"]
        accion  = result_d.get("accion")
        entidad = result_d.get("entidad")
    except Exception as exc_v6:
        log.warning("motor_v6 falló (%s) — degradando a motor_v5", exc_v6)
        # Fallback v5: Ollama LLM local
        try:
            result_d = await motor_v5.responder(body.mensaje, empresa, db, historial)
            respuesta_texto = result_d["respuesta"]
            accion  = result_d.get("accion")
            entidad = result_d.get("entidad")
        except Exception as exc_v5:
            log.warning("motor_v5 falló (%s) — degradando a motor_v4", exc_v5)
            # Fallback v4: pipeline NLP puro, siempre disponible
            try:
                result_d = await motor_v4.responder(body.mensaje, empresa, db, historial)
                respuesta_texto = result_d["respuesta"]
                accion  = result_d.get("accion")
                entidad = result_d.get("entidad")
            except Exception as exc_v4:
                log.error("motor_v4 también falló: %s", exc_v4)
                respuesta_texto = "Lo siento, el motor de IA no está disponible en este momento."

    historial.append({"role": "assistant", "content": respuesta_texto})
    conv.historial = json.dumps(historial, ensure_ascii=False)

    await db.commit()
    await db.refresh(conv)

    return {
        "conversacion_id": conv.id,
        "respuesta": respuesta_texto,
        "fase": conv.fase,
        "accion": accion,
        "entidad": entidad,
    }


@router.delete("/conversaciones/{conv_id}", status_code=204)
async def delete_conversacion(
    conv_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    empresa = await _get_empresa(db, user)
    result = await db.execute(
        select(Conversacion).where(
            Conversacion.id == conv_id,
            Conversacion.empresa_id == empresa.id,
        )
    )
    conv = result.scalar_one_or_none()
    if not conv:
        raise HTTPException(status_code=404, detail="Conversación no encontrada")
    await db.delete(conv)
    await db.commit()
