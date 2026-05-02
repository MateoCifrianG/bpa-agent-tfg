"""
agente.py — BPA-Agent v3: IA con estado de conversación, NLP preciso y BD rica.

Mejoras v3:
  • State machine: rastrea qué preguntó el bot en el turno anterior
  • NLP defensivo: no crea si el mensaje es una RESPUESTA a la pregunta anterior
  • Extracción de intención segura: require verbo de creación explícito
  • Respuestas afirmativas/negativas detectadas correctamente
  • KB dinámica: el agente aprende el contexto de la empresa de la BD
  • Variaciones de lenguaje naturales en todas las respuestas
"""

from __future__ import annotations

import json
import random
import re
from datetime import datetime
from typing import Any, Optional

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


# ──────────────────────── Helpers BD ─────────────────────────────

async def _get_empresa(db: AsyncSession, user: User) -> Empresa:
    result = await db.execute(select(Empresa).where(Empresa.user_id == user.id))
    empresa = result.scalars().first()
    if not empresa:
        raise HTTPException(status_code=404, detail="No tienes empresa registrada")
    return empresa


async def _load_all(db: AsyncSession, empresa_id: str):
    proc_res = await db.execute(select(Proceso).where(Proceso.empresa_id == empresa_id))
    kpi_res  = await db.execute(select(KPI).where(KPI.empresa_id == empresa_id))
    auto_res = await db.execute(select(Automatizacion).where(Automatizacion.empresa_id == empresa_id))
    return proc_res.scalars().all(), kpi_res.scalars().all(), auto_res.scalars().all()


# ──────────────────────── Análisis del historial ─────────────────

def _last_bot(historial: list) -> str:
    """Último mensaje del asistente."""
    for m in reversed(historial):
        if m.get("role") == "assistant":
            return m.get("content", "")
    return ""


def _last_user(historial: list, skip_last: bool = True) -> str:
    """Penúltimo mensaje del usuario (el anterior al actual)."""
    users = [m for m in historial if m.get("role") == "user"]
    if skip_last and len(users) >= 2:
        return users[-2].get("content", "")
    if users:
        return users[-1].get("content", "")
    return ""


def _bold_names(text: str) -> list[str]:
    return re.findall(r"\*\*([^*\n]{2,80})\*\*", text)


class ConvState:
    """
    Estado inferido de la última respuesta del bot.
    Permite saber si el bot hizo una pregunta y de qué tipo.
    """
    IDLE            = "idle"
    ASKED_SCORE     = "asked_score"        # "¿Le asigno un score?"
    ASKED_CREATE    = "asked_create"       # "¿Creo X?"
    ASKED_ANALYZE   = "asked_analyze"      # "¿Analizo X?"
    ASKED_AUTO      = "asked_auto"         # "¿Creo automatización para X?"
    JUST_CREATED    = "just_created"       # acaba de crear algo
    JUST_ANALYZED   = "just_analyzed"      # acaba de analizar


def _detect_state(last_bot: str) -> tuple[str, str]:
    """
    Detecta el estado de la conversación y el nombre de entidad en contexto.
    Returns (state, entity_name_or_empty).
    """
    lb = last_bot.lower()
    names = _bold_names(last_bot)
    entity = names[0] if names else ""

    if any(w in lb for w in ["asigno un score", "le asigne un score", "añadimos el score", "ponemos el score", "score inicial", "lo hacemos"]):
        return ConvState.ASKED_SCORE, entity
    if any(w in lb for w in ["¿creo", "¿lo creo", "¿quieres que cree", "¿creamos"]):
        return ConvState.ASKED_CREATE, entity
    if any(w in lb for w in ["¿analizo", "¿quieres que analice", "¿empezamos por", "análisis en detalle"]):
        return ConvState.ASKED_ANALYZE, entity
    if any(w in lb for w in ["automatización para", "¿quiero que cree una automatiz", "propongo una automatiz"]):
        return ConvState.ASKED_AUTO, entity
    if "he registrado" in lb or "he creado" in lb or "✅" in lb:
        return ConvState.JUST_CREATED, entity
    if "análisis de" in lb or "🔍" in lb or "score:" in lb:
        return ConvState.JUST_ANALYZED, entity

    return ConvState.IDLE, entity


# ──────────────────────── Detección de intención ─────────────────

# Palabras que señalan CLARAMENTE intención de crear
_STRONG_CREATE = re.compile(
    r"\b(crea(?:r|me|nos)?|añade?(?:r|me|nos)?|agrega?(?:r|me|nos)?|"
    r"registra?(?:r|me|nos)?|da(?:me|nos)\s+de\s+alta|quiero\s+(?:crear|añadir|un nuevo|una nueva))\b",
    re.IGNORECASE,
)

# Palabras que señalan que el mensaje es una RESPUESTA, no un comando
_IS_REPLY = re.compile(
    r"^(pero|no|sí|si|claro|ok|vale|espera|después|depues|ahora no|no puedo|"
    r"todavía no|aún no|aun no|ya lo|no he|no lo|ni idea|más tarde|luego|bueno|"
    r"lo que sea|eso|no creo|ya|de momento|tampoco|nada|eso no|no es así|"
    r"no entiendes|perdona|me refiero|lo que dije|quería decir)\b",
    re.IGNORECASE,
)

# Palabras de afirmación
_YES = re.compile(r"\b(sí|si|sip|dale|claro|venga|hazlo|confirmo|ok|okay|por favor|porfavor|perfecto|adelante|genial)\b", re.IGNORECASE)
_NO  = re.compile(r"\b(no|nope|paso|mejor no|ahora no|no quiero|no gracias|déjalo|dejalo|no hace falta|no es necesario)\b", re.IGNORECASE)


def _is_strong_create(msg: str) -> bool:
    """True si el mensaje tiene un verbo de creación explícito."""
    return bool(_STRONG_CREATE.search(msg))


def _is_reply_not_command(msg: str) -> bool:
    """True si el mensaje parece una respuesta conversacional, no un comando."""
    msg_strip = msg.strip().lower()
    # Corto y empieza por palabra de respuesta
    if _IS_REPLY.match(msg_strip):
        return True
    # Mensaje corto sin verbo de acción fuerte
    if len(msg_strip) < 60 and not _is_strong_create(msg_strip):
        # Tiene "proceso" pero también "no" o frase negativa → respuesta
        if re.search(r"\bno\b|\bno\s", msg_strip) and any(w in msg_strip for w in ["proceso", "score", "kpi", "auto"]):
            return True
    return False


def _extract_name_from(msg: str, after_kws: list[str]) -> Optional[str]:
    """Extrae el nombre de la entidad después de una lista de keywords."""
    text = msg

    # 1. Comillas
    m = re.search(r'["\'«»]([^"\'«»]{2,80})["\'«»]', text)
    if m:
        return m.group(1).strip()

    # 2. Después de keywords
    for kw in after_kws:
        idx = text.lower().find(kw.lower())
        if idx >= 0:
            remainder = text[idx + len(kw):].strip(" ,.:·-")
            # quitar stop words al inicio
            remainder = re.sub(r"^(de|un|una|el|la|para|nuevo|nueva|llamado|llamada)\s+", "", remainder, flags=re.IGNORECASE)
            # tomar hasta un separador
            chunk = re.split(r"\s+(?:con|para|en|y|,|que|a|por)\s+", remainder, maxsplit=1)[0]
            chunk = chunk.strip(" ,.")
            if 2 < len(chunk) <= 100:
                return chunk.capitalize()

    # 3. Todo el texto sin stop words iniciales (si es corto)
    cleaned = re.sub(r"^(el|la|los|las|un|una|unos|unas|mi|mis|de|para)\s+", "", text.lower()).strip()
    if 3 <= len(cleaned) <= 80:
        return cleaned.capitalize()

    return None


def _extract_score(msg: str) -> Optional[int]:
    m = re.search(r"\b([0-9]{1,3})\b", msg)
    if m:
        v = int(m.group(1))
        if 0 <= v <= 100:
            return v
    return None


def _find_proceso(procesos, name: str) -> Optional[Proceso]:
    if not name:
        return None
    n = name.lower().strip()
    for p in procesos:
        if p.nombre.lower() == n:
            return p
    for p in procesos:
        if n in p.nombre.lower() or p.nombre.lower().startswith(n[:min(6, len(n))]):
            return p
    return None


def _find_kpi(kpis, name: str) -> Optional[KPI]:
    if not name:
        return None
    n = name.lower().strip()
    for k in kpis:
        if k.nombre.lower() == n:
            return k
    for k in kpis:
        if n in k.nombre.lower():
            return k
    return None


def _find_auto(autos, name: str) -> Optional[Automatizacion]:
    if not name:
        return None
    n = name.lower().strip()
    for a in autos:
        if a.nombre.lower() == n:
            return a
    for a in autos:
        if n in a.nombre.lower():
            return a
    return None


# ──────────────────────── Variaciones de respuesta ───────────────

def _r(*options: str) -> str:
    return random.choice(options)


# ──────────────────────── Smart response ─────────────────────────

async def _smart_response(
    mensaje: str,
    empresa: Empresa,
    db: AsyncSession,
    historial: list,
) -> dict[str, Any]:

    msg  = mensaje.strip()
    msgL = msg.lower()
    n_turns = len([m for m in historial if m["role"] == "user"])

    procesos, kpis, autos = await _load_all(db, empresa.id)
    scores = [p for p in procesos if p.score is not None]

    last_bot   = _last_bot(historial[:-1]) if len(historial) > 1 else ""
    prev_state, prev_entity = _detect_state(last_bot)
    prev_names = _bold_names(last_bot)
    context_proceso = _find_proceso(procesos, prev_entity) if prev_entity else None

    def R(texto: str, accion: str = None, entidad: dict = None):
        return {"respuesta": texto, "accion": accion, "entidad": entidad}

    # ═══════════════════════════════════════════════════════════════
    # NIVEL 0 — Respuestas contextuales a preguntas previas del bot
    # ═══════════════════════════════════════════════════════════════

    is_yes = bool(_YES.search(msgL))
    is_no  = bool(_NO.search(msgL)) and not is_yes  # "no sé" → no, pero "no sé, sí quiero" → ambiguo

    if prev_state == ConvState.ASKED_SCORE and n_turns > 1:
        if is_yes:
            score_val = _extract_score(msgL)
            if score_val is None and context_proceso:
                return R(
                    f"¡Perfecto! ¿Qué score le ponemos a **{context_proceso.nombre}**? (0 = muy ineficiente, 100 = óptimo)"
                )
            if score_val is not None and context_proceso:
                context_proceso.score = score_val
                await db.commit()
                emoji = "🔴" if score_val < 40 else "🟡" if score_val < 70 else "🟢"
                return R(
                    f"{emoji} Score de **{context_proceso.nombre}** actualizado a **{score_val}/100**. ¡Guardado!",
                    "updated_proceso",
                    {"id": context_proceso.id, "score": score_val},
                )
            return R("Dime el número de score que quieres asignar (0-100).")

        if is_no or _is_reply_not_command(msg):
            return R(_r(
                "Entendido, sin score de momento. Puedes asignarlo más tarde desde la sección **Procesos** o diciéndome *«actualiza el score de [proceso] a [número]»*.",
                "De acuerdo, lo dejamos sin score. Cuando lo tengas claro, dímelo.",
                "Sin problema. Puedes editarlo manualmente en **Procesos** cuando quieras.",
            ))

    if prev_state == ConvState.ASKED_ANALYZE and n_turns > 1:
        if is_yes and context_proceso:
            p = context_proceso
            score_line = f"• **Score:** {p.score}/100\n" if p.score is not None else "• **Score:** sin asignar\n"
            emoji = "🔴" if (p.score or 0) < 40 else "🟡" if (p.score or 0) < 70 else "🟢"
            return R(
                f"{emoji} **Análisis de '{p.nombre}':**\n\n"
                + score_line
                + f"• **Estado:** {p.estado}\n"
                + (f"• **Responsable:** {p.responsable}\n" if p.responsable else "")
                + (f"• **Frecuencia:** {p.frecuencia}\n" if p.frecuencia else "")
                + (f"• **Duración:** {p.duracion_h}h\n" if p.duracion_h else "")
                + (f"• **Notas:** {p.descripcion}\n" if p.descripcion else "")
                + "\n¿Quieres que proponga una automatización para este proceso?"
            )
        if is_no:
            return R("De acuerdo. ¿Qué quieres hacer entonces?")

    if prev_state == ConvState.ASKED_AUTO and n_turns > 1:
        if is_yes and context_proceso:
            nuevo = Automatizacion(
                empresa_id=empresa.id,
                nombre=f"Automatización de {context_proceso.nombre}",
                estado="pendiente",
                ejecuciones=0,
            )
            db.add(nuevo)
            await db.commit()
            await db.refresh(nuevo)
            return R(
                f"⚡ ¡Hecho! He creado la automatización **{nuevo.nombre}** en estado *pendiente*.\n\n"
                f"Ve a **Automatizaciones** para configurarla con tu herramienta preferida (n8n, Zapier, etc.).",
                "created_auto",
                {"id": nuevo.id, "nombre": nuevo.nombre},
            )
        if is_no:
            return R("Entendido. Si en algún momento quieres crearla, dímelo.")

    if prev_state == ConvState.JUST_CREATED and n_turns > 1:
        # El usuario responde a algo después de que el bot creó una entidad
        if _is_reply_not_command(msg) and not _is_strong_create(msg):
            # Es un comentario o corrección, no un nuevo comando de crear
            entity_name = prev_names[0] if prev_names else "el elemento"
            if is_no or any(w in msgL for w in ["no quería", "no era", "no es", "me equivoqué", "error", "equivocado"]):
                return R(
                    f"Entiendo, parece que fue un malentendido. ¿Quieres que elimine **{entity_name}**? "
                    f"Di *«sí, elimínalo»* o dime qué querías crear exactamente."
                )
            # Score-related reply after create
            if any(w in msgL for w in ["score", "no puedo", "no he", "todavía", "aún", "después", "más tarde", "no empezado"]):
                return R(_r(
                    f"Sin problema, el score lo puedes añadir cuando quieras. Ve a **Procesos** y edítalo, o dime *«actualiza el score de {entity_name} a [número]»* cuando lo tengas.",
                    f"Tranquilo, puedes asignar el score más tarde desde **Procesos**. No hay prisa.",
                    f"Entendido. El proceso está creado y puedes ponerle score cuando lo conozcas mejor.",
                ))

    # ═══════════════════════════════════════════════════════════════
    # NIVEL 1 — Detectar si es respuesta conversacional (no comando)
    # ═══════════════════════════════════════════════════════════════

    if _is_reply_not_command(msg) and not _is_strong_create(msg) and n_turns > 1:
        # Respuesta genérica de seguimiento
        if any(w in msgL for w in ["no sé", "no se", "no lo sé", "ni idea", "no tengo claro"]):
            return R(_r(
                "Sin problema. Cuéntame más sobre tu empresa y yo te voy guiando. ¿A qué se dedica principalmente?",
                "Tranquilo. ¿Qué tipo de tareas son las más repetitivas en tu empresa?",
                "No pasa nada. Para empezar, ¿cuántas personas trabajan en la empresa y cuál es el proceso más lento?",
            ))
        if is_no and len(msgL) < 30:
            return R(_r(
                "De acuerdo. ¿Qué quieres hacer entonces?",
                "Entendido. ¿En qué te puedo ayudar?",
                "Ok. ¿Qué necesitas?",
            ))
        if is_yes and len(msgL) < 20:
            # "sí" aislado sin contexto claro
            return R("¡Perfecto! ¿De qué proceso o tarea quieres que me ocupe?")

        # Comentario o pregunta no reconocida
        return R(_r(
            f"Entendido. ¿Quieres que analice algo concreto, o que cree algún proceso o automatización?",
            f"De acuerdo. ¿En qué te puedo ayudar ahora?",
        ))

    # ═══════════════════════════════════════════════════════════════
    # NIVEL 2 — Saludo
    # ═══════════════════════════════════════════════════════════════

    _SALUDOS = ["hola", "buenas", "hey", "hi", "hello", "ola", "qué tal", "buenas tardes", "buenos días", "buenas noches"]
    if any(msgL == s or msgL.startswith(s + " ") or msgL.startswith(s + ",") for s in _SALUDOS):
        if n_turns <= 1:
            intro = _r(
                f"¡Hola! Soy **BPA-Agent** 👋, tu asistente de procesos para **{empresa.nombre}**.",
                f"¡Buenas! Soy el agente de **{empresa.nombre}**. Encantado.",
                f"¡Hola! Conectado a **{empresa.nombre}**. ¿En qué te ayudo?",
            )
            if not procesos:
                return R(
                    intro + "\n\n"
                    "Veo que aún no tienes procesos. Puedo crearlos directamente desde aquí: "
                    "di *«crea un proceso de [nombre]»* y lo registro al instante.\n\n"
                    "También puedo crear KPIs, automatizaciones y analizar tu empresa."
                )
            criticos = [p for p in scores if p.score < 50]
            resumen = f"Tienes **{len(procesos)} proceso(s)**, **{len(autos)} automatización(es)** y **{len(kpis)} KPI(s)**"
            if criticos:
                resumen += f". ⚠️ **{len(criticos)} proceso(s) crítico(s)** necesitan atención"
            return R(intro + "\n\n" + resumen + ".\n\n¿Qué quieres hacer hoy?")
        return R(_r("¡Hola de nuevo! ¿En qué te ayudo?", "¿Qué tal? ¿Qué necesitas?", "¡Buenas! Dime."))

    # ═══════════════════════════════════════════════════════════════
    # NIVEL 3 — Meta: el bot se queja / el usuario critica
    # ═══════════════════════════════════════════════════════════════

    if any(w in msgL for w in ["siempre lo mismo", "misma respuesta", "siempre eso", "repetitivo",
                                "no me entiendes", "no entiendes", "mal", "inútil", "inutil",
                                "no sirves", "para qué sirves", "para que sirves", "no funciona",
                                "no me ayudas", "error", "equivocado", "te has equivocado",
                                "no era eso", "no quería eso"]):
        return R(_r(
            "Tienes razón, me he equivocado. ¿Qué querías hacer exactamente? Dímelo con más detalle y lo hago bien.",
            "Lo siento. ¿Puedes decirme exactamente qué necesitas? Intenta ser concreto: *«crea X»*, *«analiza Y»*, etc.",
            "Pido disculpas. ¿Qué esperabas que hiciera? Te lo corrijo ahora mismo.",
        ))

    # ═══════════════════════════════════════════════════════════════
    # NIVEL 4 — Acciones de CREACIÓN (solo con verbo explícito)
    # ═══════════════════════════════════════════════════════════════

    if _is_strong_create(msg):

        # Crear PROCESO
        if any(w in msgL for w in ["proceso", "flujo", "tarea", "actividad", "procedimiento"]):
            nombre = _extract_name_from(msg, ["proceso", "flujo", "tarea", "actividad", "procedimiento"])
            if not nombre or len(nombre.strip()) < 3:
                return R("¿Cómo se llama el proceso que quieres crear? Dime el nombre.")
            nombre = nombre[:100]
            nuevo = Proceso(empresa_id=empresa.id, nombre=nombre, estado="pendiente")
            db.add(nuevo)
            await db.commit()
            await db.refresh(nuevo)
            return R(
                _r(
                    f"✅ ¡Proceso **{nuevo.nombre}** creado y guardado!\n\nAparece en **Procesos** con estado *pendiente*.\n\n"
                    f"Para que pueda analizarlo mejor, ¿le asignamos un score ahora? (0 = muy ineficiente, 100 = óptimo)",
                    f"✅ He registrado **{nuevo.nombre}** en el sistema. Lo tienes en la sección **Procesos**.\n\n"
                    f"¿Le ponemos un score inicial para poder priorizar análisis?",
                ),
                "created_proceso",
                {"id": nuevo.id, "nombre": nuevo.nombre},
            )

        # Crear KPI
        if any(w in msgL for w in ["kpi", "indicador", "métrica", "metrica", "objetivo", "medida"]):
            nombre = _extract_name_from(msg, ["kpi", "indicador", "métrica", "metrica", "objetivo"])
            if not nombre or len(nombre.strip()) < 3:
                return R("¿Cómo se llama el KPI que quieres crear? Por ejemplo: *«crea un KPI de satisfacción del cliente»*.")
            valor = "0"
            m_val = re.search(r"(?:valor|de|a|en)\s+([\d,.]+\s*%?)", msgL)
            if m_val:
                valor = m_val.group(1).strip()
            nuevo = KPI(empresa_id=empresa.id, nombre=nombre[:100], valor=valor, tendencia="up")
            db.add(nuevo)
            await db.commit()
            await db.refresh(nuevo)
            return R(
                f"✅ KPI **{nuevo.nombre}** creado con valor inicial `{valor}`.\n\n"
                f"Puedes editarlo en **KPIs** para añadir unidad, objetivo y ajustar la tendencia.",
                "created_kpi",
                {"id": nuevo.id, "nombre": nuevo.nombre},
            )

        # Crear AUTOMATIZACIÓN
        if any(w in msgL for w in ["automatiz", "workflow", "flujo automático", "bot", "script", "n8n", "zapier", "make"]):
            nombre = _extract_name_from(msg, ["automatización", "automatizacion", "automatiz", "workflow", "bot", "para"])
            if not nombre or len(nombre.strip()) < 3:
                return R("¿Cómo se llama la automatización? Por ejemplo: *«crea una automatización de envío de emails»*.")
            herramienta = None
            for tool in ["n8n", "zapier", "make", "gmail", "sheets", "drive", "slack", "python", "power automate"]:
                if tool in msgL:
                    herramienta = tool.capitalize()
                    break
            nuevo = Automatizacion(
                empresa_id=empresa.id,
                nombre=nombre[:100],
                estado="pendiente",
                herramienta=herramienta,
                ejecuciones=0,
            )
            db.add(nuevo)
            await db.commit()
            await db.refresh(nuevo)
            tool_str = f" con **{herramienta}**" if herramienta else ""
            return R(
                _r(
                    f"⚡ Automatización **{nuevo.nombre}** creada{tool_str}.\n\n"
                    f"Aparece en **Automatizaciones** con estado *pendiente*. Actívala cuando la tengas configurada para que cuente en las estadísticas.",
                    f"⚡ Registrada la automatización **{nuevo.nombre}**{tool_str}. La tienes en **Automatizaciones**.\n\n"
                    f"¿Quieres que te ayude a estimar cuántas horas al mes podría ahorrarte?",
                ),
                "created_auto",
                {"id": nuevo.id, "nombre": nuevo.nombre},
            )

    # ═══════════════════════════════════════════════════════════════
    # NIVEL 5 — Acciones de ELIMINACIÓN
    # ═══════════════════════════════════════════════════════════════

    _DELETE_RE = re.compile(r"\b(elimina(?:r)?|borra(?:r)?|quita(?:r)?|suprime?(?:r)?|borrar?|delete)\b", re.I)
    if _DELETE_RE.search(msgL):
        if any(w in msgL for w in ["proceso"]):
            nombre = _extract_name_from(msg, ["proceso"])
            p = _find_proceso(procesos, nombre) if nombre else (context_proceso if context_proceso else None)
            if p:
                await db.delete(p)
                await db.commit()
                return R(f"🗑️ El proceso **{p.nombre}** ha sido eliminado.", "deleted_proceso")
            if not procesos:
                return R("No tienes procesos registrados.")
            return R(f"No encontré ese proceso. Tus procesos son: " + ", ".join(f"*{p.nombre}*" for p in procesos[:5]))
        if any(w in msgL for w in ["kpi", "indicador"]):
            nombre = _extract_name_from(msg, ["kpi", "indicador"])
            k = _find_kpi(kpis, nombre) if nombre else None
            if k:
                await db.delete(k)
                await db.commit()
                return R(f"🗑️ KPI **{k.nombre}** eliminado.", "deleted_kpi")
            return R("¿Qué KPI quieres eliminar? Dime el nombre exacto.")
        if any(w in msgL for w in ["automatiz"]):
            nombre = _extract_name_from(msg, ["automatización", "automatiz"])
            a = _find_auto(autos, nombre) if nombre else None
            if a:
                await db.delete(a)
                await db.commit()
                return R(f"🗑️ Automatización **{a.nombre}** eliminada.", "deleted_auto")
            return R("¿Qué automatización quieres eliminar? Dime el nombre.")

    # ═══════════════════════════════════════════════════════════════
    # NIVEL 6 — Actualización de SCORE
    # ═══════════════════════════════════════════════════════════════

    if re.search(r"\b(actualiz|cambia|pon(?:le)?|asigna|establece|sube|baja)\b.*\bscore\b|\bscore\b.*\b(actualiz|cambia|pon(?:le)?|asigna)\b", msgL):
        score_val = _extract_score(msgL)
        nombre = _extract_name_from(msg, ["proceso", "de", "score"]) or (prev_entity if prev_entity else None)
        p = _find_proceso(procesos, nombre) if nombre else None
        if not p and context_proceso:
            p = context_proceso
        if p and score_val is not None:
            p.score = score_val
            await db.commit()
            emoji = "🔴" if score_val < 40 else "🟡" if score_val < 70 else "🟢"
            return R(
                f"{emoji} Score de **{p.nombre}** actualizado a **{score_val}/100**.",
                "updated_proceso",
                {"id": p.id, "score": score_val},
            )
        if not p:
            if not procesos:
                return R("No tienes procesos. Primero crea uno.")
            return R("¿De qué proceso quieres cambiar el score? Dime el nombre exacto.")
        if score_val is None:
            return R(f"¿A qué valor quieres cambiar el score de **{p.nombre}**? (0-100)")

    # ═══════════════════════════════════════════════════════════════
    # NIVEL 7 — CONSULTAS (mostrar / analizar / listar)
    # ═══════════════════════════════════════════════════════════════

    # Analizar proceso concreto
    _ANALYZE_KW = ["analiza", "análisis", "analisis", "cómo está", "como esta", "cuéntame",
                   "cuentame", "detalles", "info", "información", "informacion",
                   "háblame", "hablame", "explícame", "explicame", "revisar", "revisar"]
    if any(w in msgL for w in _ANALYZE_KW):
        nombre = None
        for kw in _ANALYZE_KW:
            if kw in msgL:
                nombre = _extract_name_from(msg, [kw])
                if nombre:
                    break
        if not nombre and prev_names:
            nombre = prev_names[0]
        p = _find_proceso(procesos, nombre) if nombre else None
        if p:
            score_line = f"• **Score:** {p.score}/100\n" if p.score is not None else "• **Score:** sin asignar\n"
            emoji = "🔴" if (p.score or 0) < 40 else "🟡" if (p.score or 0) < 70 else "🟢"
            recom = ""
            if p.score is not None and p.score < 60:
                recom = "\n\n¿Quieres que proponga una automatización para optimizarlo?"
            return R(
                f"{emoji} **Análisis de '{p.nombre}':**\n\n"
                + score_line
                + f"• **Estado:** {p.estado}\n"
                + (f"• **Responsable:** {p.responsable}\n" if p.responsable else "")
                + (f"• **Frecuencia:** {p.frecuencia}\n" if p.frecuencia else "")
                + (f"• **Duración:** {p.duracion_h}h\n" if p.duracion_h else "")
                + (f"• **Notas:** {p.descripcion}\n" if p.descripcion else "")
                + recom
            )
        if procesos:
            return R(
                f"¿Qué proceso quieres analizar? Tus procesos: "
                + ", ".join(f"*{p.nombre}*" for p in procesos[:6])
            )
        return R("No tienes procesos aún. Di *«crea un proceso de [nombre]»* para empezar.")

    # Listar / mostrar
    if any(w in msgL for w in ["muestra", "lista", "ver", "tengo", "cuántos", "cuantos", "qué tengo", "que tengo", "dame"]):
        if any(w in msgL for w in ["proceso", "procesos"]):
            if not procesos:
                return R("No tienes procesos. Di *«crea un proceso de [nombre]»* para añadir el primero.")
            lines = []
            for p in sorted(procesos, key=lambda x: (x.score is None, x.score or 999)):
                e = "🔴" if (p.score or 0) < 40 else "🟡" if (p.score or 0) < 70 else "🟢"
                s = f" — {p.score}/100" if p.score is not None else " — sin score"
                lines.append(f"{e} **{p.nombre}**{s}")
            return R(f"📋 Tus **{len(procesos)} proceso(s)**:\n\n" + "\n".join(lines) + "\n\n¿Quieres analizar alguno?")

        if any(w in msgL for w in ["automatiz"]):
            if not autos:
                return R("No tienes automatizaciones. Di *«crea una automatización de [nombre]»*.")
            activas = [a for a in autos if a.estado == "activa"]
            horas = sum(a.horas_mes or 0 for a in autos)
            lines = [f"• **{a.nombre}** — {a.estado}" + (f" ({a.herramienta})" if a.herramienta else "") for a in autos]
            return R(f"⚡ **{len(autos)} automatización(es)** ({len(activas)} activas, {horas}h/mes):\n\n" + "\n".join(lines))

        if any(w in msgL for w in ["kpi", "indicador", "indicadores"]):
            if not kpis:
                return R("No tienes KPIs. Di *«crea un KPI de [nombre]»*.")
            lines = []
            for k in kpis[:8]:
                t = "↑" if k.tendencia == "up" else "↓" if k.tendencia == "down" else "→"
                lines.append(f"{t} **{k.nombre}**: {k.valor}{' ' + k.unidad if k.unidad else ''}")
            return R(f"📈 **{len(kpis)} KPI(s)**:\n\n" + "\n".join(lines))

    # Resumen / diagnóstico
    if any(w in msgL for w in ["resumen", "overview", "diagnós", "diagnostico", "situación",
                                "situacion", "cómo estamos", "como estamos", "cómo va", "como va",
                                "estado", "qué tal vamos", "que tal vamos"]):
        activas = [a for a in autos if a.estado == "activa"]
        horas = sum(a.horas_mes or 0 for a in autos)
        criticos = [p for p in scores if p.score < 50]
        score_prom = round(sum(p.score for p in scores) / len(scores), 1) if scores else None

        res = f"📊 **{empresa.nombre} — Estado actual:**\n\n"
        res += f"• **Procesos:** {len(procesos)}"
        if score_prom is not None:
            res += f" | Score promedio: **{score_prom}/100**"
        if criticos:
            res += f" | ⚠️ {len(criticos)} crítico(s)"
        res += f"\n• **Automatizaciones:** {len(autos)} ({len(activas)} activas) | Ahorro: **{horas}h/mes**"
        res += f"\n• **KPIs:** {len(kpis)}\n"

        if not procesos:
            res += "\n▶️ **Paso 1:** Di *«crea un proceso de [nombre]»* para mapear tu empresa."
        elif criticos:
            res += f"\n⚠️ **Urgente:** **{criticos[0].nombre}** tiene score {criticos[0].score}/100. ¿Lo analizo?"
        elif not kpis:
            res += "\n💡 **Siguiente:** Define KPIs para medir la mejora. Di *«crea un KPI de [nombre]»*."
        elif not autos:
            res += "\n💡 **Oportunidad:** Crea automatizaciones para ahorrar tiempo."
        else:
            res += f"\n✅ Todo en marcha. Ahorrando **{horas}h/mes** con automatizaciones."
        return R(res)

    # Propuestas
    if any(w in msgL for w in ["propuesta", "suger", "recomend", "mejora", "optimiz", "qué hago", "que hago", "por dónde", "por donde"]):
        props = []
        if not procesos:
            props.append("▶️ **Mapear procesos:** di *«crea un proceso de [nombre]»* para cada proceso clave.")
        else:
            criticos = sorted([p for p in scores if p.score < 60], key=lambda x: x.score)
            for p in criticos[:2]:
                props.append(
                    f"🔴 **Optimizar '{p.nombre}'** (score {p.score}/100)\n"
                    f"   → Revisar cuellos de botella y considerar automatización"
                )
        if not autos and procesos:
            props.append(f"⚡ **Primera automatización** para *{procesos[0].nombre}*\n   → Ahorro estimado: 4-8h/mes")
        if not kpis:
            props.append("📊 **Definir KPIs** → di *«crea un KPI de [nombre]»*.")
        if not props:
            horas = sum(a.horas_mes or 0 for a in autos)
            props = [f"✅ Empresa bien encaminada ({horas}h/mes ahorradas). Para seguir mejorando: sube el score de los procesos con más margen."]
        return R("💡 **Mis recomendaciones:**\n\n" + "\n\n".join(props))

    # Ayuda
    if any(w in msgL for w in ["ayuda", "help", "qué puedes", "que puedes", "cómo funciona",
                                "que haces", "qué haces", "comandos"]):
        return R(
            "Puedo **crear**, **analizar**, **actualizar** y **eliminar** datos de tu empresa directamente desde el chat:\n\n"
            "**Crear:**\n"
            "• *«Crea un proceso de facturación mensual»*\n"
            "• *«Crea una automatización de envío de emails con n8n»*\n"
            "• *«Crea un KPI de satisfacción del cliente»*\n\n"
            "**Consultar:**\n"
            "• *«Muéstrame mis procesos»* / *«Muéstrame mis KPIs»*\n"
            "• *«Analiza el proceso de [nombre]»*\n"
            "• *«Dame un resumen de la empresa»*\n\n"
            "**Modificar:**\n"
            "• *«Actualiza el score de [proceso] a 75»*\n"
            "• *«Elimina el proceso [nombre]»*\n\n"
            "Todo se guarda en la base de datos en tiempo real. ¿Qué quieres hacer?"
        )

    # Peor/mejor proceso
    if any(w in msgL for w in ["peor", "más bajo", "mas bajo", "menor", "crítico", "critico", "urgente"]):
        if scores:
            peor = min(scores, key=lambda p: p.score)
            return R(
                f"🔴 Proceso con **peor score**: **{peor.nombre}** ({peor.score}/100).\n\n"
                + (f"Responsable: {peor.responsable}. " if peor.responsable else "")
                + "¿Quieres que lo analice en detalle?"
            )
        return R("Ningún proceso tiene score asignado todavía. Edítalos en **Procesos** para añadir uno.")

    if any(w in msgL for w in ["mejor", "más alto", "mas alto", "mayor", "óptimo", "optimo"]):
        if scores:
            mejor = max(scores, key=lambda p: p.score)
            return R(f"🟢 Proceso con **mejor score**: **{mejor.nombre}** ({mejor.score}/100).")
        return R("Sin scores asignados aún.")

    # Gracias / positivo
    if any(w in msgL for w in ["gracias", "perfecto", "genial", "bien", "ok", "vale", "entendido", "de acuerdo", "👍"]):
        return R(_r(
            "¡De nada! ¿Algo más?",
            "¡Perfecto! ¿Qué más necesitas?",
            "¡Encantado de ayudar! ¿Seguimos?",
        ))

    # Procesos (genérico)
    if any(w in msgL for w in ["proceso", "procesos"]):
        if not procesos:
            return R("Aún no tienes procesos. Di *«crea un proceso de [nombre]»* para añadir el primero.")
        if scores:
            peor = min(scores, key=lambda x: x.score)
            lines = [f"{'🔴' if p.score<40 else '🟡' if p.score<70 else '🟢'} **{p.nombre}** — {p.score}/100"
                     for p in sorted(scores, key=lambda x: x.score)[:5]]
            criticos = [p for p in scores if p.score < 50]
            reply = f"📋 **{len(procesos)} proceso(s):**\n\n" + "\n".join(lines)
            if criticos:
                reply += f"\n\n⚠️ {len(criticos)} crítico(s). ¿Analizo **{criticos[0].nombre}**?"
            else:
                reply += f"\n\n✅ Ninguno crítico. El más mejorable: **{peor.nombre}** ({peor.score}/100)."
            return R(reply)
        lines = [f"• **{p.nombre}** ({p.estado})" for p in procesos[:5]]
        return R(f"Tienes **{len(procesos)} proceso(s)**:\n\n" + "\n".join(lines) + "\n\nNinguno tiene score asignado aún.")

    # Automatizaciones (genérico)
    if any(w in msgL for w in ["automatiz", "n8n", "zapier", "workflow"]):
        if not autos:
            sugs = []
            for p in procesos[:3]:
                nl = p.nombre.lower()
                if "factur" in nl:
                    sugs.append(f"• *Automatizar facturación* con n8n + Google Sheets")
                elif "email" in nl or "correo" in nl:
                    sugs.append(f"• *Envío automático de emails* con Gmail API")
                else:
                    sugs.append(f"• *Notificaciones automáticas* para {p.nombre}")
            reply = "No tienes automatizaciones todavía.\n\n"
            if sugs:
                reply += "Basándome en tus procesos, podría crear:\n\n" + "\n".join(sugs[:3])
                reply += "\n\n¿Te interesa alguna? Di *«crea una automatización de [nombre]»*."
            else:
                reply += "Di *«crea una automatización de [nombre]»* para empezar."
            return R(reply)
        activas = [a for a in autos if a.estado == "activa"]
        horas = sum(a.horas_mes or 0 for a in autos)
        return R(
            f"⚡ **{len(autos)} automatización(es)** ({len(activas)} activas, **{horas}h/mes** ahorradas):\n\n"
            + "".join(f"• **{a.nombre}** — {a.estado}\n" for a in autos[:5])
        )

    # KPIs (genérico)
    if any(w in msgL for w in ["kpi", "indicador", "métrica", "metrica", "rendimiento"]):
        if not kpis:
            return R(
                "No tienes KPIs definidos.\n\n"
                "Los más útiles son:\n• *Tiempo de resolución*\n• *Coste por proceso*\n"
                "• *Satisfacción del cliente (%)*\n• *Errores por ciclo*\n\n"
                "Di *«crea un KPI de [nombre]»* para añadir uno."
            )
        lines = [
            f"{'↑' if k.tendencia=='up' else '↓' if k.tendencia=='down' else '→'} **{k.nombre}**: {k.valor}"
            + (f" {k.unidad}" if k.unidad else "")
            + (f" (obj: {k.objetivo})" if k.objetivo else "")
            for k in kpis[:6]
        ]
        return R(f"📈 **{len(kpis)} KPI(s):**\n\n" + "\n".join(lines))

    # ═══════════════════════════════════════════════════════════════
    # NIVEL 8 — FALLBACK inteligente y variado
    # ═══════════════════════════════════════════════════════════════

    # Si hay contexto previo, aprovecharlo
    if context_proceso:
        return R(
            f"No he entendido del todo. ¿Sigues hablando de **{context_proceso.nombre}**? "
            f"Puedo analizarlo, actualizar su score o crear una automatización para él. ¿Qué prefieres?"
        )

    fallbacks = [
        "No he captado bien eso. Prueba con algo como: *«crea un proceso de [nombre]»*, "
        "*«muéstrame mis KPIs»* o *«dame un resumen»*. ¿Qué necesitas?",
        "Hmm, no estoy seguro de entender. ¿Quieres crear algo, analizar un proceso o ver estadísticas?",
        f"No lo he interpretado bien. Cuéntame qué quieres hacer con tu empresa **{empresa.nombre}** y te ayudo.",
    ]
    if scores:
        peor = min(scores, key=lambda p: p.score)
        fallbacks.append(
            f"No he entendido tu mensaje. Recuerda que tienes **{peor.nombre}** con score crítico "
            f"({peor.score}/100). ¿Te ayudo a mejorarlo?"
        )
    return R(random.choice(fallbacks))


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

    historial.append({"role": "user", "content": body.mensaje})

    accion  = None
    entidad = None

    if settings.ANTHROPIC_API_KEY:
        try:
            import anthropic
            from app.agents.safety import limpiar_input, REGLA_ANTI_CREDENCIALES
            from app.agents.prompts.analisis import SYSTEM_ANALISIS
            client = anthropic.Anthropic(api_key=settings.ANTHROPIC_API_KEY)
            msg_limpio = limpiar_input(body.mensaje)
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
            result_d = await _smart_response(body.mensaje, empresa, db, historial)
            respuesta_texto = result_d["respuesta"]
            accion  = result_d.get("accion")
            entidad = result_d.get("entidad")
    else:
        result_d = await _smart_response(body.mensaje, empresa, db, historial)
        respuesta_texto = result_d["respuesta"]
        accion  = result_d.get("accion")
        entidad = result_d.get("entidad")

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
