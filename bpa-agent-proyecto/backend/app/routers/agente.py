"""
agente.py — BPA-Agent chat con acciones reales en BD.

El agente entiende lenguaje natural y puede:
  • Crear / eliminar procesos, KPIs y automatizaciones
  • Analizar datos reales de la empresa
  • Responder preguntas de negocio con contexto
  • Variar el lenguaje para parecer más humano
Sin coste de API externa (usa _smart_response por defecto).
Si se configura ANTHROPIC_API_KEY, usa Claude como backend.
"""

from __future__ import annotations

import json
import random
import re
from datetime import datetime
from typing import Any, Optional
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.auth.jwt import get_current_user
from app.config import settings
from app.database import get_db
from app.models.automatizacion import Automatizacion
from app.models.conversacion import Conversacion
from app.models.empresa import Empresa
from app.models.kpi import KPI
from app.models.proceso import Proceso
from app.models.user import User

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


# ─────────────────────── Helpers BD ─────────────────────────────

async def _get_empresa(db: AsyncSession, user: User) -> Empresa:
    result = await db.execute(select(Empresa).where(Empresa.user_id == user.id))
    empresa = result.scalars().first()
    if not empresa:
        raise HTTPException(status_code=404, detail="No tienes empresa registrada")
    return empresa


async def _load_all(db: AsyncSession, empresa_id: str):
    proc_res = await db.execute(select(Proceso).where(Proceso.empresa_id == empresa_id))
    kpi_res = await db.execute(select(KPI).where(KPI.empresa_id == empresa_id))
    auto_res = await db.execute(select(Automatizacion).where(Automatizacion.empresa_id == empresa_id))
    return (
        proc_res.scalars().all(),
        kpi_res.scalars().all(),
        auto_res.scalars().all(),
    )


# ───────────────────── Contexto del historial ────────────────────

def _last_bot_msg(historial: list) -> str:
    for m in reversed(historial):
        if m.get("role") == "assistant":
            return m.get("content", "")
    return ""


def _extract_bold_names(text: str) -> list[str]:
    """Extrae todos los nombres en **negrita** del texto."""
    return re.findall(r"\*\*([^*\n]{2,80})\*\*", text)


def _find_proceso(procesos, nombre_buscado: str) -> Optional[Proceso]:
    """Búsqueda flexible: exacta → contiene → comienza por."""
    nb = nombre_buscado.lower().strip()
    for p in procesos:
        if p.nombre.lower() == nb:
            return p
    for p in procesos:
        if nb in p.nombre.lower() or p.nombre.lower().startswith(nb[:6]):
            return p
    return None


def _find_auto(autos, nombre_buscado: str) -> Optional[Automatizacion]:
    nb = nombre_buscado.lower().strip()
    for a in autos:
        if a.nombre.lower() == nb:
            return a
    for a in autos:
        if nb in a.nombre.lower():
            return a
    return None


def _find_kpi(kpis, nombre_buscado: str) -> Optional[KPI]:
    nb = nombre_buscado.lower().strip()
    for k in kpis:
        if k.nombre.lower() == nb:
            return k
    for k in kpis:
        if nb in k.nombre.lower():
            return k
    return None


# ────────────────── Parsers de lenguaje natural ──────────────────

# Palabras que indican acción de creación
_CREATE_WORDS = r"crea(?:r)?|añade?(?:r)?|agrega?(?:r)?|registra?(?:r)?|nueva?|nuevo|dame|pon(?:me)?|incluye?(?:r)?"
# Palabras que indican eliminación
_DELETE_WORDS = r"elimina?(?:r)?|borra?(?:r)?|quita?(?:r)?|suprime?(?:r)?|elimina|borra"

# Patrones para detectar nombre entre comillas o después de "de/llamado/para"
_NAME_PATTERNS = [
    r'"([^"]{2,80})"',
    r"'([^']{2,80})'",
    r"llamad[oa]\s+(.{2,60}?)(?:\s+con|\s+para|\s+en|\s*$)",
    r"llamad[oa]s?\s+(.{2,60}?)(?:\s+con|\s+para|\s+en|\s*$)",
    r"de\s+(.{2,60}?)(?:\s+con\s+|\s+para\s+|\s+en\s+|\s+y\s+|\s*$)",
    r"para\s+(.{2,60}?)(?:\s+con\s+|\s+en\s+|\s*$)",
    r":\s*(.{2,60}?)(?:\s*$)",
]


def _extract_name(msg: str, after_keyword: Optional[str] = None) -> Optional[str]:
    """Extrae el nombre de la entidad a crear/buscar del mensaje."""
    text = msg
    if after_keyword:
        # Quedarse con la parte del mensaje después del keyword
        idx = msg.lower().find(after_keyword.lower())
        if idx >= 0:
            text = msg[idx + len(after_keyword):]

    text = text.strip(" ,.")

    for pat in _NAME_PATTERNS:
        m = re.search(pat, text, re.IGNORECASE)
        if m:
            candidate = m.group(1).strip(" ,.")
            # Descartar si es demasiado genérico
            if len(candidate) > 2 and candidate.lower() not in (
                "eso", "esto", "aquí", "ahí", "algo", "nada", "todo"
            ):
                return candidate[:100]

    # Último recurso: si quedan entre 3-80 chars y no empieza por stop-word
    text = re.sub(r"^(el|la|los|las|un|una|unos|unas|mi|mis|tu|sus)\s+", "", text.lower())
    if 3 <= len(text) <= 80:
        return text.strip(" ,.").capitalize()
    return None


def _extract_score(msg: str) -> Optional[int]:
    """Extrae un número de score (0-100) del mensaje."""
    m = re.search(r"\b([0-9]{1,3})\b", msg)
    if m:
        v = int(m.group(1))
        if 0 <= v <= 100:
            return v
    return None


# ───────────────── Respuestas variadas por intento ───────────────

def _r(*opciones: str) -> str:
    """Selecciona aleatoriamente entre las opciones de respuesta."""
    return random.choice(opciones)


# ────────────────────── Smart response ──────────────────────────

async def _smart_response(
    mensaje: str,
    empresa: Empresa,
    db: AsyncSession,
    historial: list,
) -> dict[str, Any]:
    """
    Genera una respuesta inteligente y ejecuta acciones reales en BD.
    Devuelve dict con: respuesta, accion (opcional), entidad (opcional).
    """
    msg = mensaje.lower().strip()
    procesos, kpis, autos = await _load_all(db, empresa.id)
    scores = [p for p in procesos if p.score is not None]
    prev_msg = _last_bot_msg(historial[:-1]) if len(historial) > 1 else ""
    prev_names = _extract_bold_names(prev_msg)

    def R(texto: str, accion: str = None, entidad: dict = None):
        return {"respuesta": texto, "accion": accion, "entidad": entidad}

    # ═══════════════════════════════════════════════════════════
    # 1. ACCIONES DE CREACIÓN
    # ═══════════════════════════════════════════════════════════

    is_create = bool(re.search(_CREATE_WORDS, msg))

    # ── Crear PROCESO ──
    if is_create and any(w in msg for w in ["proceso", "procesos", "flujo", "tarea", "actividad"]):
        nombre = _extract_name(msg, "proceso") or _extract_name(msg) or "Nuevo proceso"
        # Intentar inferir responsable y descripción del mensaje
        responsable = None
        m_resp = re.search(r"responsable[:\s]+(.{2,40}?)(?:\s+y|\s*$|,)", msg, re.I)
        if m_resp:
            responsable = m_resp.group(1).strip().capitalize()

        nuevo = Proceso(
            empresa_id=empresa.id,
            nombre=nombre.capitalize(),
            estado="pendiente",
            responsable=responsable,
        )
        db.add(nuevo)
        await db.commit()
        await db.refresh(nuevo)

        reply = _r(
            f"✅ ¡Proceso **{nuevo.nombre}** creado! Lo encontrarás en la sección **Procesos**.\n\n"
            f"Ahora puedes editarlo para añadir responsable, frecuencia y score. ¿Quieres que le asigne un score inicial?",

            f"✅ He registrado el proceso **{nuevo.nombre}** en el sistema. Aparece en tu sección **Procesos** con estado *pendiente*.\n\n"
            f"Para mejores análisis, añádele un score del 0 al 100 (0 = muy ineficiente, 100 = óptimo). ¿Lo hacemos?",
        )
        return R(reply, "created_proceso", {"id": nuevo.id, "nombre": nuevo.nombre})

    # ── Crear KPI ──
    if is_create and any(w in msg for w in ["kpi", "indicador", "métrica", "métrico", "objetivo"]):
        nombre = _extract_name(msg, "kpi") or _extract_name(msg, "indicador") or _extract_name(msg) or "Nuevo KPI"
        # Intentar extraer valor
        valor = "0"
        m_val = re.search(r"(?:valor|en|de|a)\s+([\d,.]+\s*%?)", msg, re.I)
        if m_val:
            valor = m_val.group(1).strip()

        nuevo = KPI(
            empresa_id=empresa.id,
            nombre=nombre.capitalize(),
            valor=valor,
            tendencia="up",
        )
        db.add(nuevo)
        await db.commit()
        await db.refresh(nuevo)

        reply = _r(
            f"✅ KPI **{nuevo.nombre}** creado con valor inicial `{valor}`.\n\nPuedes editarlo en la sección **KPIs** para añadir unidad y objetivo. ¿Quieres añadir otro indicador?",
            f"✅ He creado el indicador **{nuevo.nombre}**. Lo tienes disponible en **KPIs**. Si quieres cambiar el valor o añadir un objetivo, edítalo directamente.",
        )
        return R(reply, "created_kpi", {"id": nuevo.id, "nombre": nuevo.nombre})

    # ── Crear AUTOMATIZACIÓN ──
    if is_create and any(w in msg for w in ["automatiz", "automatización", "workflow", "flujo automático", "n8n", "robot", "bot", "script"]):
        nombre = (
            _extract_name(msg, "automatización") or
            _extract_name(msg, "automatiz") or
            _extract_name(msg, "para") or
            _extract_name(msg) or
            "Nueva automatización"
        )
        # Inferir herramienta
        herramienta = None
        for tool in ["n8n", "zapier", "make", "gmail", "sheets", "drive", "slack", "python"]:
            if tool in msg:
                herramienta = tool.capitalize()
                break

        nuevo = Automatizacion(
            empresa_id=empresa.id,
            nombre=nombre.capitalize(),
            estado="pendiente",
            herramienta=herramienta,
            ejecuciones=0,
        )
        db.add(nuevo)
        await db.commit()
        await db.refresh(nuevo)

        tool_msg = f" con **{herramienta}**" if herramienta else ""
        reply = _r(
            f"⚡ ¡Automatización **{nuevo.nombre}** registrada{tool_msg}!\n\nAparece en **Automatizaciones** con estado *pendiente*. "
            f"Cuando la pongas en marcha, cámbiala a *activa* para que cuente en las estadísticas.",

            f"⚡ He creado la automatización **{nuevo.nombre}**{tool_msg}. La encontrarás en la sección **Automatizaciones**.\n\n"
            f"¿Quieres que te ayude a estimar cuántas horas al mes te va a ahorrar?",
        )
        return R(reply, "created_auto", {"id": nuevo.id, "nombre": nuevo.nombre})

    # ═══════════════════════════════════════════════════════════
    # 2. ACCIONES DE ELIMINACIÓN
    # ═══════════════════════════════════════════════════════════

    is_delete = bool(re.search(_DELETE_WORDS, msg))

    if is_delete and any(w in msg for w in ["proceso", "procesos"]):
        nombre_buscado = _extract_name(msg, "proceso") or _extract_name(msg) or ""
        p = _find_proceso(procesos, nombre_buscado)
        if p:
            await db.delete(p)
            await db.commit()
            return R(
                f"🗑️ El proceso **{p.nombre}** ha sido eliminado del sistema.",
                "deleted_proceso",
            )
        return R(
            f"No he encontrado ningún proceso llamado *{nombre_buscado}*. "
            f"¿Quieres que te muestre la lista de procesos disponibles?",
        )

    if is_delete and any(w in msg for w in ["kpi", "indicador"]):
        nombre_buscado = _extract_name(msg, "kpi") or _extract_name(msg, "indicador") or _extract_name(msg) or ""
        k = _find_kpi(kpis, nombre_buscado)
        if k:
            await db.delete(k)
            await db.commit()
            return R(f"🗑️ El KPI **{k.nombre}** ha sido eliminado.", "deleted_kpi")
        return R(f"No encontré ningún KPI llamado *{nombre_buscado}*.")

    if is_delete and any(w in msg for w in ["automatiz", "workflow"]):
        nombre_buscado = _extract_name(msg, "automatiz") or _extract_name(msg) or ""
        a = _find_auto(autos, nombre_buscado)
        if a:
            await db.delete(a)
            await db.commit()
            return R(f"🗑️ La automatización **{a.nombre}** ha sido eliminada.", "deleted_auto")
        return R(f"No encontré ninguna automatización llamada *{nombre_buscado}*.")

    # ═══════════════════════════════════════════════════════════
    # 3. ACTUALIZACIÓN DE SCORE
    # ═══════════════════════════════════════════════════════════

    if any(w in msg for w in ["actualiza", "cambia", "pon", "asigna", "establece"]) and "score" in msg:
        score_val = _extract_score(msg)
        nombre_buscado = _extract_name(msg, "proceso") or (prev_names[0] if prev_names else None) or ""
        p = _find_proceso(procesos, nombre_buscado) if nombre_buscado else None
        if p and score_val is not None:
            p.score = score_val
            await db.commit()
            emoji = "🔴" if score_val < 40 else "🟡" if score_val < 70 else "🟢"
            return R(
                f"{emoji} Score de **{p.nombre}** actualizado a **{score_val}/100**.",
                "updated_proceso",
                {"id": p.id, "nombre": p.nombre, "score": score_val},
            )
        if not p:
            return R("¿De qué proceso quieres actualizar el score? Dime el nombre exacto.")
        if score_val is None:
            return R("¿A qué valor quieres cambiar el score? Dime un número del 0 al 100.")

    # ═══════════════════════════════════════════════════════════
    # 4. PREGUNTAS / CONSULTAS
    # ═══════════════════════════════════════════════════════════

    # ── SALUDO ──
    saludos = ["hola", "buenas", "hey", "qué tal", "buenos", "hi", "hello", "ola", "buenass"]
    if any(msg == s or msg.startswith(s + " ") or msg.startswith(s + ",") or msg == s + "!" for s in saludos):
        n_turns = len([m for m in historial if m["role"] == "user"])
        if n_turns <= 1:
            intro = _r(
                f"¡Hola! Soy **BPA-Agent** 👋, tu asistente de procesos para **{empresa.nombre}**.",
                f"¡Buenas! Soy el agente BPA de **{empresa.nombre}**. Estoy aquí para ayudarte.",
                f"¡Hola! Encantado. Soy **BPA-Agent**, conectado a **{empresa.nombre}**.",
            )
            if not procesos:
                return R(
                    intro + "\n\n"
                    "Veo que todavía no tienes procesos registrados. Puedo creártelos directamente desde aquí. "
                    "Por ejemplo, di: *\"crea un proceso de facturación mensual\"* y lo añado al sistema al momento."
                )
            criticos = [p for p in scores if p.score < 50]
            resumen = f"Tienes **{len(procesos)} proceso(s)**, **{len(autos)} automatización(es)** y **{len(kpis)} KPI(s)**"
            if criticos:
                resumen += f". **⚠️ {len(criticos)} proceso(s) crítico(s)** necesitan atención"
            return R(intro + "\n\n" + resumen + ".\n\n¿Qué quieres hacer hoy?")
        else:
            return R(_r(
                "¡Hola de nuevo! ¿En qué puedo ayudarte ahora?",
                "¿Qué tal? Aquí estoy. ¿Qué necesitas?",
                "¡Buenas! ¿Qué quieres analizar o crear?",
            ))

    # ── META: el usuario se queja del bot ──
    if any(w in msg for w in ["siempre lo mismo", "siempre dices", "misma respuesta", "siempre eso",
                               "repetit", "no me ayudas", "inutil", "inútil", "que haces",
                               "para qué sirves", "para que sirves", "no funciona"]):
        return R(_r(
            "Tienes razón, lo siento. Puedo hacer bastante más que solo responder: "
            "puedo **crear** procesos, KPIs y automatizaciones directamente desde aquí, "
            "**analizar** el estado de tu empresa y **eliminar** registros. "
            "¿Qué quieres que haga exactamente?",

            "Me pillas. Déjame ser más útil. Dime qué necesitas: "
            "¿crear algo nuevo, analizar un proceso concreto, ver estadísticas? "
            "Cuéntame y lo hago.",
        ))

    # ── MOSTRAR / LISTAR ──
    if any(w in msg for w in ["muestra", "lista", "ver", "dame", "tengo", "cuántos", "cuantos", "qué tengo"]):
        if any(w in msg for w in ["proceso", "procesos"]):
            if not procesos:
                return R("No tienes procesos registrados. Di *\"crea un proceso de [nombre]\"* y lo añado ahora mismo.")
            lines = []
            for p in sorted(procesos, key=lambda x: x.score or 999):
                emoji = "🔴" if (p.score or 0) < 40 else "🟡" if (p.score or 0) < 70 else "🟢"
                score_str = f" — {p.score}/100" if p.score is not None else " — sin score"
                lines.append(f"{emoji} **{p.nombre}**{score_str}")
            return R(f"📋 Tus **{len(procesos)} proceso(s)**:\n\n" + "\n".join(lines) + "\n\n¿Quieres analizar alguno?")

        if any(w in msg for w in ["automatiz", "automatización"]):
            if not autos:
                return R("No tienes automatizaciones. Di *\"crea una automatización para [nombre]\"* y la registro.")
            activas = [a for a in autos if a.estado == "activa"]
            horas = sum(a.horas_mes or 0 for a in autos)
            lines = [f"• **{a.nombre}** — {a.estado}" + (f" ({a.herramienta})" if a.herramienta else "") for a in autos]
            return R(
                f"⚡ Tienes **{len(autos)} automatización(es)** ({len(activas)} activas, {horas}h/mes ahorradas):\n\n"
                + "\n".join(lines)
            )

        if any(w in msg for w in ["kpi", "kpis", "indicador", "indicadores", "métrica", "métricas"]):
            if not kpis:
                return R("No tienes KPIs definidos. Di *\"crea un KPI de [nombre]\"* para añadir uno.")
            lines = []
            for k in kpis:
                tend = "↑" if k.tendencia == "up" else "↓" if k.tendencia == "down" else "→"
                lines.append(f"{tend} **{k.nombre}**: {k.valor}{' ' + k.unidad if k.unidad else ''}")
            return R(f"📈 Tus **{len(kpis)} KPI(s)**:\n\n" + "\n".join(lines))

    # ── ANÁLISIS de proceso concreto ──
    analizar_keywords = ["analiza", "análisis", "analisis", "analizar", "cómo está", "como esta",
                         "cuéntame más de", "cuentame mas de", "detalles de", "info de",
                         "información de", "informacion de", "explicame", "háblame de"]
    if any(w in msg for w in analizar_keywords):
        nombre_buscado = None
        for kw in analizar_keywords:
            if kw in msg:
                nombre_buscado = _extract_name(msg, kw)
                if nombre_buscado:
                    break
        if not nombre_buscado and prev_names:
            nombre_buscado = prev_names[0]

        p = _find_proceso(procesos, nombre_buscado) if nombre_buscado else None
        if p:
            score_line = f"• **Score:** {p.score}/100\n" if p.score is not None else "• **Score:** sin asignar\n"
            emoji = "🔴" if (p.score or 0) < 40 else "🟡" if (p.score or 0) < 70 else "🟢"
            recom = ""
            if p.score is not None and p.score < 50:
                recom = "\n\n⚠️ **Este proceso necesita atención urgente.** ¿Quieres que cree una automatización para optimizarlo?"
            elif p.score is not None and p.score < 70:
                recom = "\n\n💡 Hay margen de mejora. ¿Quiero que proponga una automatización?"
            return R(
                f"{emoji} **Análisis de '{p.nombre}':**\n\n"
                + score_line
                + f"• **Estado:** {p.estado}\n"
                + (f"• **Responsable:** {p.responsable}\n" if p.responsable else "")
                + (f"• **Frecuencia:** {p.frecuencia}\n" if p.frecuencia else "")
                + (f"• **Duración estimada:** {p.duracion_h}h\n" if p.duracion_h else "")
                + (f"• **Notas:** {p.descripcion}\n" if p.descripcion else "")
                + recom
            )

        if not procesos:
            return R("No tienes procesos registrados todavía. Puedo crear uno: dime *\"crea un proceso de [nombre]\"*.")
        # Mostrar todos si no encontró uno concreto
        if scores:
            peor = min(scores, key=lambda x: x.score)
            return R(
                f"Dime el nombre exacto del proceso que quieres analizar. "
                f"Tienes **{len(procesos)}** registrados. El más crítico ahora mismo es **{peor.nombre}** (score {peor.score}/100)."
            )
        return R(f"¿De qué proceso quieres el análisis? Tienes {len(procesos)} registrado(s): " + ", ".join(f"*{p.nombre}*" for p in procesos[:4]))

    # ── RESUMEN / DIAGNÓSTICO general ──
    if any(w in msg for w in ["resumen", "resumen empresa", "resumen completo", "overview", "diagnós",
                               "diagnostico", "situación", "situacion", "cómo estamos", "como estamos",
                               "cómo va", "como va", "estado", "qué tal vamos"]):
        activas = [a for a in autos if a.estado == "activa"]
        horas = sum(a.horas_mes or 0 for a in autos)
        criticos = [p for p in scores if p.score < 50]
        score_prom = round(sum(p.score for p in scores) / len(scores), 1) if scores else None

        resumen = f"📊 **Estado de {empresa.nombre}:**\n\n"
        resumen += f"• **Procesos:** {len(procesos)}"
        if score_prom:
            resumen += f" | Score promedio: **{score_prom}/100**"
        if criticos:
            resumen += f" | ⚠️ {len(criticos)} crítico(s)"
        resumen += f"\n• **Automatizaciones:** {len(autos)} ({len(activas)} activas) | Ahorro: **{horas}h/mes**"
        resumen += f"\n• **KPIs:** {len(kpis)}\n"

        if not procesos:
            resumen += "\n▶️ **Primer paso:** Di *\"crea un proceso de [nombre]\"* para empezar a mapear tu empresa."
        elif criticos:
            resumen += f"\n⚠️ **Urgente:** **{criticos[0].nombre}** tiene score crítico ({criticos[0].score}/100)."
        elif not kpis:
            resumen += "\n💡 **Siguiente paso:** Define KPIs para medir la mejora. Di *\"crea un KPI de [nombre]\"*."
        elif not autos:
            resumen += "\n💡 **Oportunidad:** Puedes crear automatizaciones para ahorrar tiempo. Di *\"crea una automatización\"*."
        else:
            resumen += f"\n✅ Todo en marcha. Estás ahorrando {horas}h/mes."
        return R(resumen)

    # ── PROCESOS (pregunta genérica) ──
    if any(w in msg for w in ["proceso", "procesos", "mapear"]):
        if not procesos:
            return R(
                "Aún no tienes procesos registrados.\n\nPuedo crearlos directamente: "
                "di *\"crea un proceso de facturación\"*, *\"crea un proceso de atención al cliente\"*, etc."
            )
        if scores:
            peor = min(scores, key=lambda x: x.score)
            mejor = max(scores, key=lambda x: x.score)
            criticos = [p for p in scores if p.score < 50]
            lines = []
            for p in sorted(scores, key=lambda x: x.score)[:5]:
                emoji = "🔴" if p.score < 40 else "🟡" if p.score < 70 else "🟢"
                lines.append(f"{emoji} **{p.nombre}** — {p.score}/100")
            reply = f"📋 **Tus {len(procesos)} proceso(s):**\n\n" + "\n".join(lines)
            if criticos:
                reply += f"\n\n⚠️ {len(criticos)} proceso(s) crítico(s). ¿Analizo **{criticos[0].nombre}** en detalle?"
            else:
                reply += f"\n\n✅ Ninguno en estado crítico. El más mejorable es **{peor.nombre}** ({peor.score}/100)."
            return R(reply)
        lines = [f"• **{p.nombre}** ({p.estado})" for p in procesos[:5]]
        return R(
            f"Tienes **{len(procesos)} proceso(s)** registrado(s):\n\n" + "\n".join(lines) +
            "\n\nNinguno tiene score asignado. Edítalos en **Procesos** o dime *\"actualiza el score de [proceso] a [número]\"*."
        )

    # ── AUTOMATIZACIONES (pregunta genérica) ──
    if any(w in msg for w in ["automatiz", "automatización", "workflow", "n8n", "zapier"]):
        if not autos:
            sugerencias = []
            for p in procesos[:3]:
                nl = p.nombre.lower()
                if "factur" in nl:
                    sugerencias.append(f"• *Automatización de facturación* con n8n + Google Sheets")
                elif "email" in nl or "correo" in nl:
                    sugerencias.append(f"• *Envío automático de emails* con Gmail API")
                elif "client" in nl or "onboard" in nl:
                    sugerencias.append(f"• *Alta de clientes* con n8n + Drive + Gmail")
                elif "inventar" in nl:
                    sugerencias.append(f"• *Control de inventario* con hoja de cálculo automatizada")
                else:
                    sugerencias.append(f"• *Notificaciones automáticas* para {p.nombre}")
            reply = "Todavía no tienes automatizaciones configuradas.\n\n"
            if sugerencias:
                reply += "Basándome en tus procesos, te propongo:\n\n" + "\n".join(sugerencias[:3])
                reply += "\n\n¿Quieres que cree alguna? Di *\"crea una automatización de [nombre]\"*."
            else:
                reply += "Di *\"crea una automatización de [nombre]\"* y la registro en el sistema al momento."
            return R(reply)
        activas = [a for a in autos if a.estado == "activa"]
        horas = sum(a.horas_mes or 0 for a in autos)
        return R(
            f"⚡ Tienes **{len(autos)} automatización(es)** ({len(activas)} activas).\n"
            f"Ahorro estimado: **{horas}h/mes**.\n\n"
            + ("".join(f"• **{a.nombre}** — {a.estado}\n" for a in autos[:5]))
            + "\n¿Quieres crear una nueva o activar alguna pendiente?"
        )

    # ── KPIs (pregunta genérica) ──
    if any(w in msg for w in ["kpi", "indicador", "métrica", "rendimiento", "performance", "objetivo"]):
        if not kpis:
            return R(
                "Aún no tienes KPIs definidos.\n\n"
                "Los más útiles para BPA son:\n"
                "• *Tiempo de resolución de procesos*\n• *Coste por proceso (€)*\n"
                "• *Satisfacción del cliente (%)*\n• *Errores por ciclo*\n\n"
                "Di *\"crea un KPI de [nombre]\"* y lo añado ahora."
            )
        lines = []
        for k in kpis[:6]:
            tend = "↑" if k.tendencia == "up" else "↓" if k.tendencia == "down" else "→"
            obj = f" (obj: {k.objetivo})" if k.objetivo else ""
            lines.append(f"{tend} **{k.nombre}**: {k.valor}{' ' + k.unidad if k.unidad else ''}{obj}")
        return R(f"📈 **Tus {len(kpis)} KPI(s):**\n\n" + "\n".join(lines))

    # ── PROPUESTAS / RECOMENDACIONES ──
    if any(w in msg for w in ["propuesta", "suger", "recomend", "mejora", "optimiz", "qué me recomiendas", "que me recomiendas"]):
        props = []
        if not procesos:
            props.append("▶️ **Mapea tus procesos:** di *\"crea un proceso de [nombre]\"* para cada proceso clave.")
        else:
            criticos = sorted([p for p in scores if p.score < 60], key=lambda x: x.score)
            for p in criticos[:2]:
                props.append(
                    f"🔴 **Optimizar '{p.nombre}'** (score {p.score}/100)\n"
                    f"   → ¿Quieres que cree una automatización para este proceso?"
                )
        if not autos and procesos:
            props.append(
                f"⚡ **Crear tu primera automatización** — Di *\"crea una automatización para {procesos[0].nombre}\"*\n"
                f"   → Ahorro estimado: 4-8h/mes"
            )
        if not kpis:
            props.append("📊 **Definir KPIs** — Di *\"crea un KPI de [nombre]\"* para medir el progreso.")
        if not props:
            horas = sum(a.horas_mes or 0 for a in autos)
            props = [
                f"✅ Tu empresa está bien encaminada con {len(procesos)} procesos y {horas}h/mes ahorradas.\n"
                "→ Siguiente nivel: incrementa el score de los procesos con más margen de mejora."
            ]
        return R("💡 **Mis recomendaciones:**\n\n" + "\n\n".join(props))

    # ── AYUDA ──
    if any(w in msg for w in ["ayuda", "help", "qué puedes", "que puedes", "cómo funciona", "que haces",
                               "qué haces", "comandos", "instrucciones", "para qué sirves", "para que sirves"]):
        return R(
            "Puedo hacer bastante más que responder preguntas 😄\n\n"
            "**Crear cosas:**\n"
            "• *\"Crea un proceso de facturación mensual\"*\n"
            "• *\"Crea una automatización para enviar emails con n8n\"*\n"
            "• *\"Crea un KPI de satisfacción del cliente\"*\n\n"
            "**Analizar y consultar:**\n"
            "• *\"Analiza el proceso de control de inventario\"*\n"
            "• *\"Muéstrame mis KPIs\"* / *\"Lista mis automatizaciones\"*\n"
            "• *\"Dame un resumen de la empresa\"*\n\n"
            "**Actualizar y eliminar:**\n"
            "• *\"Actualiza el score de facturación a 75\"*\n"
            "• *\"Elimina el proceso X\"*\n\n"
            "Todo se guarda en tiempo real en la base de datos."
        )

    # ── SEGUIMIENTO CONTEXTUAL (peor/mejor proceso) ──
    if any(w in msg for w in ["peor", "más bajo", "mas bajo", "menor score", "crítico", "critico"]):
        if scores:
            peor = min(scores, key=lambda p: p.score)
            return R(
                f"🔴 El proceso con **peor score** es **{peor.nombre}** con **{peor.score}/100**.\n\n"
                f"Estado: {peor.estado or 'pendiente'}."
                + (f" Responsable: {peor.responsable}." if peor.responsable else "")
                + f"\n\n¿Quiero que analice cómo mejorarlo o cree una automatización para ese proceso?"
            )
        return R("Ninguno de tus procesos tiene score asignado. Edítalos en **Procesos** para asignar uno.")

    if any(w in msg for w in ["mejor", "más alto", "mas alto", "mayor score", "el mejor"]):
        if scores:
            mejor = max(scores, key=lambda p: p.score)
            return R(
                f"🟢 El proceso con **mejor score** es **{mejor.nombre}** con **{mejor.score}/100**.\n\n"
                + (f"Responsable: {mejor.responsable}." if mejor.responsable else "")
            )
        return R("Ninguno de tus procesos tiene score asignado todavía.")

    # ── RESPUESTA GRACIAS / POSITIVA ──
    if any(w in msg for w in ["gracias", "perfecto", "genial", "bien", "ok", "vale", "entendido", "de acuerdo"]):
        return R(_r(
            "¡De nada! ¿Hay algo más que quieras hacer?",
            "¡Perfecto! ¿Qué más necesitas?",
            "¡Encantado de ayudar! ¿Seguimos con algo?",
        ))

    # ═══════════════════════════════════════════════════════════
    # 5. FALLBACK INTELIGENTE Y VARIADO
    # ═══════════════════════════════════════════════════════════

    # Si hay contexto previo, responder contextualmente
    if prev_names:
        p = _find_proceso(procesos, prev_names[0])
        if p:
            return R(
                f"No he entendido del todo tu pregunta. ¿Sigues hablando de **{p.nombre}**? "
                f"Puedo analizarlo, actualizar su score o crear una automatización para él. ¿Qué prefieres?"
            )

    # Fallbacks variados con datos reales
    opciones_fallback = []

    if scores:
        peor = min(scores, key=lambda p: p.score)
        opciones_fallback.append(
            f"No he captado bien eso. Ten en cuenta que tienes el proceso **{peor.nombre}** con score crítico "
            f"({peor.score}/100). ¿Quieres que lo analice?"
        )

    opciones_fallback.append(
        f"No he entendido tu mensaje. Recuerda que puedes pedirme que **cree** procesos, KPIs o automatizaciones, "
        f"o que **analice** cualquier dato de {empresa.nombre}. ¿Qué necesitas?"
    )

    if not procesos:
        opciones_fallback.append(
            "No tengo claro qué quieres decir. Para empezar, podría crear tus primeros procesos. "
            "Di algo como: *\"crea un proceso de atención al cliente\"*."
        )

    opciones_fallback.append(
        "Hmm, no he podido interpretar eso. Prueba a ser más concreto: "
        "*\"crea un proceso de [nombre]\"*, *\"analiza [proceso]\"* o *\"muéstrame mis KPIs\"*."
    )

    return R(random.choice(opciones_fallback))


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

    # Buscar o crear conversación
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

    # Cargar historial
    try:
        historial = json.loads(conv.historial or "[]")
    except Exception:
        historial = []

    historial.append({"role": "user", "content": body.mensaje})

    # ── Usar Claude si hay API key, si no smart_response ──
    accion = None
    entidad = None

    if settings.ANTHROPIC_API_KEY:
        try:
            import anthropic
            from app.agents.safety import limpiar_input, REGLA_ANTI_CREDENCIALES
            from app.agents.prompts.analisis import SYSTEM_ANALISIS

            client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
            mensaje_limpio = limpiar_input(body.mensaje)
            respuesta_texto = ""
            with client.messages.stream(
                model="claude-3-5-haiku-20241022",
                max_tokens=1024,
                system=SYSTEM_ANALISIS + "\n\n" + REGLA_ANTI_CREDENCIALES,
                messages=[{"role": m["role"], "content": m["content"]} for m in historial],
            ) as stream:
                for text in stream.text_stream:
                    respuesta_texto += text
        except Exception:
            result_dict = await _smart_response(body.mensaje, empresa, db, historial)
            respuesta_texto = result_dict["respuesta"]
            accion = result_dict.get("accion")
            entidad = result_dict.get("entidad")
    else:
        result_dict = await _smart_response(body.mensaje, empresa, db, historial)
        respuesta_texto = result_dict["respuesta"]
        accion = result_dict.get("accion")
        entidad = result_dict.get("entidad")

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
