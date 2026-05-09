"""
motor_v4.py — BPA-Agent Motor Razonador v4

Pipeline de 5 capas:
  [1] PreProcessor      → normalizar, segmentar multi-intención
  [2] ContextAnalyzer   → memoria completa de conversación (todos los turnos)
  [3] IntentClassifier  → 18 intenciones con score de confianza
  [4] ActionExecutor    → BD async, ROI engine, KB de BPM
  [5] ResponseSynthesizer → register formal/conversacional
"""

from __future__ import annotations

import random
import re
from dataclasses import dataclass, field as dataclasses_field
from typing import Any, Optional

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.automatizacion import Automatizacion
from app.models.empresa import Empresa
from app.models.kpi import KPI
from app.models.proceso import Proceso

# ─────────────────────────────────────────────────────────────────
# CAPA 1 — PRE-PROCESSOR
# ─────────────────────────────────────────────────────────────────

def pre_process(mensaje: str) -> dict:
    """
    Normaliza el texto y detecta si hay múltiples intenciones (batch).
    Devuelve: {text, lower, segments, is_batch, batch_items}
    """
    text  = mensaje.strip()
    lower = text.lower()

    # Detectar operación en lote: "crea X, Y y Z" / "crea: A, B, C"
    batch_items: list[str] = []
    is_batch = False

    # Patrón 1: "crea tres procesos: A, B, C"  (con dos puntos explícito)
    batch_m = re.search(
        r"\b(crea(?:r|me|nos)?|añade?|agrega?|registra?)\b[^:]+:\s*"
        r"([A-Za-záéíóúüñÁÉÍÓÚÜÑ][\w\s,yYáéíóúüñ]{2,})",
        text, re.IGNORECASE
    )
    # Patrón 2: "crea A, B y C"  (sin dos puntos)
    if not batch_m:
        batch_m = re.search(
            r"\b(crea(?:r|me|nos)?|añade?|agrega?|registra?)\b\s+"
            r"([A-Za-záéíóúüñÁÉÍÓÚÜÑ][\w\s]{1,30}"
            r"(?:\s*,\s*[\w\sáéíóúüñ]{1,30})+"
            r"(?:\s+[yYeE]\s+[\w\sáéíóúüñ]{1,30})?)",
            text, re.IGNORECASE
        )
    if batch_m:
        raw_list = batch_m.group(2)
        # Separar por coma, "y", "e"
        parts = re.split(r"\s*[,;]\s*|\s+[yYeE]\s+", raw_list)
        parts = [p.strip(" .\"'") for p in parts if len(p.strip()) > 2]
        if len(parts) >= 2:
            is_batch = True
            batch_items = parts

    return {
        "text": text,
        "lower": lower,
        "is_batch": is_batch,
        "batch_items": batch_items,
    }


# ─────────────────────────────────────────────────────────────────
# CAPA 2 — CONTEXT ANALYZER
# ─────────────────────────────────────────────────────────────────

# Estados de la máquina de conversación
class ConvState:
    IDLE          = "idle"
    ASKED_SCORE   = "asked_score"
    ASKED_CREATE  = "asked_create"
    ASKED_ANALYZE = "asked_analyze"
    ASKED_AUTO    = "asked_auto"
    ASKED_FIELD   = "asked_field"
    ASKED_ROI     = "asked_roi"
    JUST_CREATED  = "just_created"
    JUST_ANALYZED = "just_analyzed"
    JUST_UPDATED  = "just_updated"


@dataclass
class ConversationMemory:
    """
    Memoria completa de la conversación.
    Procesa TODOS los turnos, no solo los últimos N.
    """
    # Estado del último turno del bot
    state: str = ConvState.IDLE
    pending_field: str = ""

    # Entidad activa (la más reciente mencionada por el bot)
    active_entity: str = ""
    active_entity_type: str = ""

    # Registro completo de la sesión
    all_created: list[dict] = dataclasses_field(default_factory=list)      # [{type, name, turn}]
    all_analyzed: list[str] = dataclasses_field(default_factory=list)      # nombres de procesos analizados
    all_updated: list[dict] = dataclasses_field(default_factory=list)      # [{name, field, value}]
    all_deleted: list[str] = dataclasses_field(default_factory=list)       # nombres eliminados
    roi_calcs_done: list[str] = dataclasses_field(default_factory=list)    # procesos con ROI calculado
    suggestions_made: list[str] = dataclasses_field(default_factory=list)  # sugerencias ya hechas

    # Todos los nombres mencionados a lo largo de la conversación
    all_mentioned: list[str] = dataclasses_field(default_factory=list)

    # Patrones detectados en el usuario
    user_style: str = "neutral"        # "formal" | "informal" | "neutral"
    user_domain: str = ""              # dominio principal detectado
    pending_topics: list[str] = dataclasses_field(default_factory=list)    # temas sin resolver

    # Resumen de lo hablado (para respuestas contextuales ricas)
    session_actions_count: int = 0
    n_turns: int = 0


def _bold_names(text: str) -> list[str]:
    return re.findall(r"\*\*([^*\n]{2,80})\*\*", text)


_ACTION_PATTERNS = {
    # Coincide con: "Proceso **X** registrado" / "He incorporado **X** al sistema"
    "created_proceso": re.compile(
        r"(?:(?:proceso|tarea|flujo)\s+\*\*([^*\n]{2,80})\*\*\s+(?:creado|registrado)"
        r"|incorporado\s+\*\*([^*\n]{2,80})\*\*\s+al\s+sistema"
        r"|✅\s+\*\*([^*\n]{2,80})\*\*\s+(?:creado|registrado))",
        re.I
    ),
    # Batch: "He registrado **N procesos**" + líneas "✅ **Nombre**"
    "batch_proceso":   re.compile(r"He registrado\s+\*\*\d+\s+procesos?\*\*", re.I),
    "batch_item":      re.compile(r"✅\s+\*\*([^*\n]{2,60})\*\*", re.I),
    "created_kpi":     re.compile(r"kpi\s+\*\*([^*\n]{2,80})\*\*\s+creado", re.I),
    "created_auto":    re.compile(r"automatización\s+\*\*([^*\n]{2,80})\*\*\s+creada?", re.I),
    "updated":         re.compile(r"\*\*([^*\n]{2,80})\*\*\s+actualizado", re.I),
    "deleted":         re.compile(r"\*\*([^*\n]{2,80})\*\*\s+(?:ha sido\s+)?eliminad", re.I),
    "analyzed":        re.compile(r"(?:diagnóstico|análisis)\s+completo\s+[—–-]\s+\*\*([^*\n]{2,80})\*\*", re.I),
    "roi":             re.compile(r"(?:análisis\s+)?roi\s+[—–*\-]+\s+\*{1,2}([^*\n]{2,80})\*{1,2}", re.I),
}

# Detección de estilo del usuario
_FORMAL_MARKERS = re.compile(r"\b(podría|quisiera|le agradecería|por favor|sería posible|disculpe|cuál sería|¿podría)\b", re.I)
_INFORMAL_MARKERS = re.compile(r"\b(tío|joder|venga|dale|oye|mira|a ver|pon|dame|crea|dime)\b", re.I)


def analyze_context(historial: list) -> ConversationMemory:
    """
    Analiza el historial COMPLETO de la conversación para construir
    una memoria rica con todos los eventos, entidades y patrones detectados.
    """
    mem = ConversationMemory()
    mem.n_turns = len([m for m in historial if m.get("role") == "user"])

    formal_score = 0
    informal_score = 0
    all_names: set[str] = set()

    for i, msg in enumerate(historial):
        role    = msg.get("role", "")
        content = msg.get("content", "")
        lower   = content.lower()

        if role == "user":
            # Detectar estilo de escritura acumulado
            if _FORMAL_MARKERS.search(lower):
                formal_score += 1
            if _INFORMAL_MARKERS.search(lower):
                informal_score += 1

            # Detectar dominio
            for domain_kw in ["facturación", "rrhh", "logística", "ventas", "marketing", "soporte", "compras"]:
                if domain_kw in lower and not mem.user_domain:
                    mem.user_domain = domain_kw

        elif role == "assistant":
            names = _bold_names(content)
            all_names.update(names)

            # Extraer acciones realizadas por el bot
            m_cp = _ACTION_PATTERNS["created_proceso"].search(content)
            if m_cp:
                # Puede tener hasta 3 grupos de captura alternativos
                name = next((g for g in m_cp.groups() if g), None)
                if name:
                    mem.all_created.append({"type": "proceso", "name": name, "turn": i})
                    mem.session_actions_count += 1

            # Batch de procesos: extraer cada ítem "✅ **Nombre**"
            if _ACTION_PATTERNS["batch_proceso"].search(content):
                for m_bi in _ACTION_PATTERNS["batch_item"].finditer(content):
                    item_name = m_bi.group(1).strip()
                    if len(item_name) > 1:
                        mem.all_created.append({"type": "proceso", "name": item_name, "turn": i})
                mem.session_actions_count += 1

            m_ck = _ACTION_PATTERNS["created_kpi"].search(content)
            if m_ck:
                mem.all_created.append({"type": "kpi", "name": m_ck.group(1), "turn": i})
                mem.session_actions_count += 1

            m_ca = _ACTION_PATTERNS["created_auto"].search(content)
            if m_ca:
                mem.all_created.append({"type": "auto", "name": m_ca.group(1), "turn": i})
                mem.session_actions_count += 1

            m_upd = _ACTION_PATTERNS["updated"].search(content)
            if m_upd:
                mem.all_updated.append({"name": m_upd.group(1)})
                mem.session_actions_count += 1

            m_del = _ACTION_PATTERNS["deleted"].search(content)
            if m_del:
                mem.all_deleted.append(m_del.group(1))
                mem.session_actions_count += 1

            m_ana = _ACTION_PATTERNS["analyzed"].search(content)
            if m_ana and m_ana.group(1) not in mem.all_analyzed:
                mem.all_analyzed.append(m_ana.group(1))

            m_roi = _ACTION_PATTERNS["roi"].search(content)
            if m_roi and m_roi.group(1) not in mem.roi_calcs_done:
                mem.roi_calcs_done.append(m_roi.group(1))

    # Estilo del usuario
    if formal_score > informal_score + 1:
        mem.user_style = "formal"
    elif informal_score > formal_score:
        mem.user_style = "informal"

    # Todos los nombres mencionados
    mem.all_mentioned = list(all_names)

    # ── Estado del último turno del bot (para respuestas contextuales) ──
    for msg in reversed(historial):
        if msg.get("role") != "assistant":
            continue
        lb = msg["content"].lower()
        names = _bold_names(msg["content"])
        if names:
            mem.active_entity = names[0]

        if any(w in lb for w in ["asigno un score", "le asignamos", "ponemos el score", "score inicial", "qué score"]):
            mem.state = ConvState.ASKED_SCORE
        elif any(w in lb for w in ["¿creo", "¿lo creo", "¿quieres que cree", "¿creamos", "¿creo el"]):
            mem.state = ConvState.ASKED_CREATE
        elif any(w in lb for w in ["¿analizo", "¿quieres que analice", "análisis en detalle", "¿empezamos por"]):
            mem.state = ConvState.ASKED_ANALYZE
        elif any(w in lb for w in ["automatización para", "propongo una automatiz", "¿creo la automatiz"]):
            mem.state = ConvState.ASKED_AUTO
        elif any(w in lb for w in ["¿a qué valor", "¿cuál es el nuevo", "dime el valor", "¿qué valor"]):
            mem.state = ConvState.ASKED_FIELD
            for fkw in ["responsable", "frecuencia", "duración", "descripción", "estado"]:
                if fkw in lb:
                    mem.pending_field = fkw
                    break
        elif any(w in lb for w in ["estimación de roi", "roi estimado", "análisis de rentabilidad", "ahorro estimado", "## 📊 análisis roi"]):
            mem.state = ConvState.ASKED_ROI
        elif "he registrado" in lb or "he creado" in lb or "✅" in lb:
            mem.state = ConvState.JUST_CREATED
        elif "diagnóstico completo" in lb or "🔍" in lb:
            mem.state = ConvState.JUST_ANALYZED
        elif "actualizado a" in lb or "he cambiado" in lb or "modificado" in lb:
            mem.state = ConvState.JUST_UPDATED
        break

    return mem


# ─────────────────────────────────────────────────────────────────
# CAPA 3 — INTENT CLASSIFIER
# ─────────────────────────────────────────────────────────────────

class Intent:
    CREATE_PROCESO  = "create_proceso"
    CREATE_KPI      = "create_kpi"
    CREATE_AUTO     = "create_auto"
    BATCH_CREATE    = "batch_create"
    DELETE          = "delete"
    UPDATE_SCORE    = "update_score"
    UPDATE_FIELD    = "update_field"
    ANALYZE         = "analyze"
    LIST            = "list"
    SUMMARY         = "summary"
    ROI_CALC        = "roi_calc"
    RECOMMENDATIONS = "recommendations"
    HELP            = "help"
    GREETING        = "greeting"
    AFFIRMATIVE     = "affirmative"
    NEGATIVE        = "negative"
    COMPLAINT       = "complaint"
    UNKNOWN         = "unknown"


_CREATE_RE = re.compile(
    r"\b(crea(?:r|me|nos)?|añade?(?:r|me|nos)?|agrega?(?:r|me|nos)?|"
    r"registra?(?:r|me|nos)?|da(?:me|nos)\s+de\s+alta|"
    r"quiero\s+(?:crear|añadir|un\s+nuevo|una\s+nueva)|"
    r"necesito\s+(?:crear|añadir|un\s+nuevo|una\s+nueva)|"
    r"introduce|incluye|incorpora)\b",
    re.IGNORECASE,
)
_DELETE_RE  = re.compile(r"\b(elimina(?:r)?|borra(?:r)?|quita(?:r)?|suprime?|delete|descarta?|remueve?)\b", re.IGNORECASE)
_UPDATE_RE  = re.compile(r"\b(actualiza?(?:r)?|cambia(?:r)?|modifica?(?:r)?|pon(?:le)?|asigna?(?:r)?|edita?(?:r)?|establece?)\b", re.IGNORECASE)
_ANALYZE_RE = re.compile(r"\b(analiza?(?:r)?|análisis|diagnosis|diagnós|revisa?(?:r)?|evalúa?(?:r)?|evalua?(?:r)?|inspecciona?(?:r)?|cómo\s+está|detalles\s+de|informe\s+de)\b", re.IGNORECASE)
_LIST_RE    = re.compile(r"\b(muestra?|lista?(?:r)?|ver|dame|cuántos|cuantos|qué\s+tengo|que\s+tengo|enumera?(?:r)?|dime\s+los?|dime\s+las?|visualiza?)\b", re.IGNORECASE)
_SUMMARY_RE = re.compile(r"\b(resumen|overview|panorama|diagnóstico\s+general|situación\s+general|cómo\s+estamos|como\s+estamos|estado\s+general|qué\s+tal\s+vamos|balance)\b", re.IGNORECASE)
_ROI_RE     = re.compile(r"\b(roi|retorno|ahorro|rentabil|cuánto\s+(me\s+)?ahorra|cuanto\s+(me\s+)?ahorra|tiempo\s+ahorra|horas?\s+ahorra|vale\s+la\s+pena|merece\s+la\s+pena|beneficio\s+económico|impacto\s+económico)\b", re.IGNORECASE)
_RECOM_RE   = re.compile(r"\b(recomend|sugier|propón|propone?|mejora?(?:r)?|optimiza?(?:r)?|qué\s+hago|por\s+dónde\s+empiezo|próximo\s+paso|siguiente\s+paso|prioridad|priorizar)\b", re.IGNORECASE)
_SCORE_RE   = re.compile(r"\bscore\b", re.IGNORECASE)
_HELP_RE    = re.compile(r"\b(ayuda|help|qué\s+puedes|que\s+puedes|cómo\s+funciona|comandos|capacidades|instrucciones)\b", re.IGNORECASE)
_GREETING   = re.compile(r"^(hola|buenas|hey|hi|hello|buenos\s+días|buenas\s+tardes|buenas\s+noches|qué\s+tal|como\s+estás)\b", re.IGNORECASE)
_YES_RE     = re.compile(r"\b(sí|si|sip|dale|claro|venga|hazlo|confirmo|ok|okay|por\s+favor|perfecto|adelante|genial|afirmativo|correcto|exacto)\b", re.IGNORECASE)
_NO_RE      = re.compile(r"\b(no|nope|paso|mejor\s+no|ahora\s+no|no\s+quiero|no\s+gracias|déjalo|dejalo|no\s+hace\s+falta|tampoco|negativo)\b", re.IGNORECASE)
_COMPLAINT  = re.compile(r"\b(siempre\s+lo\s+mismo|no\s+me\s+entiendes|inútil|inutil|no\s+sirves|no\s+funciona|mal|error|equivocado|no\s+era\s+eso|no\s+quería\s+eso|repites?)\b", re.IGNORECASE)

_PROCESO_KW = ["proceso", "flujo", "tarea", "actividad", "procedimiento", r"workflow\s+manual", r"proceso\s+de"]
_KPI_KW     = ["kpi", "indicador", "métrica", "metrica", "objetivo", "medida", "rendimiento"]
_AUTO_KW    = ["automatiz", "bot", "script", "n8n", "zapier", "make", r"power\s+automate", r"workflow\s+auto"]

_FIELD_MAP = {
    "responsable": "responsable",
    "dueño": "responsable",
    "owner": "responsable",
    "responsabilidad": "responsable",
    "estado": "estado",
    "status": "estado",
    "frecuencia": "frecuencia",
    "periodicidad": "frecuencia",
    "duración": "duracion_h",
    "duracion": "duracion_h",
    "tiempo": "duracion_h",
    "descripción": "descripcion",
    "descripcion": "descripcion",
    "detalle": "descripcion",
    "notas": "descripcion",
    "nota": "descripcion",
}


@dataclass
class ClassifiedIntent:
    intent: str
    confidence: float
    entity_type: str = ""   # "proceso" | "kpi" | "auto" | ""
    campo: str = ""         # campo a actualizar
    score_value: Optional[int] = None
    field_value: Optional[str] = None
    entity_name: Optional[str] = None
    batch_type: str = ""
    batch_items: list = dataclasses_field(default_factory=list)


def classify_intent(pre: dict, ctx: "ConversationMemory") -> ClassifiedIntent:
    text  = pre["text"]
    lower = pre["lower"]

    # Batch
    if pre["is_batch"] and _CREATE_RE.search(lower):
        etype = "proceso"
        for kw in _KPI_KW:
            if kw in lower:
                etype = "kpi"; break
        for kw in _AUTO_KW:
            if re.search(kw, lower):
                etype = "auto"; break
        return ClassifiedIntent(
            Intent.BATCH_CREATE, 0.95, batch_type=etype, batch_items=pre["batch_items"]
        )

    # Respuestas contextuales (afirmativas / negativas)
    is_yes = bool(_YES_RE.search(lower))
    is_no  = bool(_NO_RE.search(lower)) and not is_yes
    is_short = len(lower.split()) <= 5

    if is_yes and is_short:
        return ClassifiedIntent(Intent.AFFIRMATIVE, 0.95)
    if is_no and is_short:
        return ClassifiedIntent(Intent.NEGATIVE, 0.95)

    # Quejas
    if _COMPLAINT.search(lower):
        return ClassifiedIntent(Intent.COMPLAINT, 0.9)

    # Saludo
    if _GREETING.search(lower):
        return ClassifiedIntent(Intent.GREETING, 0.95)

    # Ayuda
    if _HELP_RE.search(lower):
        return ClassifiedIntent(Intent.HELP, 0.95)

    # ROI
    if _ROI_RE.search(lower):
        etype = "proceso"
        name = _extract_entity_name(text, ["proceso", "automatiz", "de"])
        return ClassifiedIntent(Intent.ROI_CALC, 0.88, entity_type=etype, entity_name=name)

    # Resumen
    if _SUMMARY_RE.search(lower):
        return ClassifiedIntent(Intent.SUMMARY, 0.92)

    # Análisis
    if _ANALYZE_RE.search(lower):
        etype = _detect_entity_type(lower)
        name = _extract_entity_name(text, ["analiza", "análisis", "proceso", "cómo está", "detalles de"])
        return ClassifiedIntent(Intent.ANALYZE, 0.90, entity_type=etype, entity_name=name)

    # Listar
    if _LIST_RE.search(lower):
        etype = _detect_entity_type(lower)
        return ClassifiedIntent(Intent.LIST, 0.88, entity_type=etype)

    # Recomendaciones
    if _RECOM_RE.search(lower):
        return ClassifiedIntent(Intent.RECOMMENDATIONS, 0.85)

    # Creación
    if _CREATE_RE.search(lower):
        etype = _detect_entity_type(lower)
        kws = {"proceso": _PROCESO_KW, "kpi": _KPI_KW, "auto": _AUTO_KW}.get(etype, [])
        flat_kws = [k.split(r"\s+")[0] for k in kws]
        name = _extract_entity_name(text, flat_kws + ["crear", "crea", "añadir", "añade", "nuevo", "nueva"])
        return ClassifiedIntent(Intent.CREATE_PROCESO if etype=="proceso" else Intent.CREATE_KPI if etype=="kpi" else Intent.CREATE_AUTO,
                                0.90, entity_type=etype, entity_name=name)

    # Eliminación
    if _DELETE_RE.search(lower):
        etype = _detect_entity_type(lower)
        name = _extract_entity_name(text, ["proceso", "kpi", "indicador", "automatización", "automatiz"])
        return ClassifiedIntent(Intent.DELETE, 0.88, entity_type=etype, entity_name=name)

    # Actualización de score
    if _UPDATE_RE.search(lower) and _SCORE_RE.search(lower):
        score = _extract_score(lower)
        name = _extract_entity_name(text, ["proceso", "de"])
        return ClassifiedIntent(Intent.UPDATE_SCORE, 0.90, entity_type="proceso",
                                score_value=score, entity_name=name)

    # Actualización de campo
    if _UPDATE_RE.search(lower):
        etype = _detect_entity_type(lower)
        detected_field = ""
        field_val = None
        for kw, fname in _FIELD_MAP.items():
            if kw in lower:
                detected_field = fname
                # Extraer el valor: "cambia el responsable de X a VALOR"
                m = re.search(rf"\b{kw}\b.*?\ba\b\s+(.+?)(?:\s+(?:y|,|$))", lower)
                if m:
                    field_val = m.group(1).strip()
                break
        name = _extract_entity_name(text, ["proceso", "de", "kpi", "automatiz"])
        return ClassifiedIntent(Intent.UPDATE_FIELD, 0.85, entity_type=etype,
                                campo=detected_field, field_value=field_val, entity_name=name)

    # Menciones genéricas de entidades
    if any(kw in lower for kw in ["proceso", "procesos"]):
        return ClassifiedIntent(Intent.LIST, 0.60, entity_type="proceso")
    if any(re.search(kw, lower) for kw in _AUTO_KW):
        return ClassifiedIntent(Intent.LIST, 0.60, entity_type="auto")
    if any(kw in lower for kw in _KPI_KW):
        return ClassifiedIntent(Intent.LIST, 0.60, entity_type="kpi")

    return ClassifiedIntent(Intent.UNKNOWN, 0.30)


def _detect_entity_type(lower: str) -> str:
    for kw in _KPI_KW:
        if kw in lower:
            return "kpi"
    for kw in _AUTO_KW:
        if re.search(kw, lower):
            return "auto"
    return "proceso"


def _extract_entity_name(text: str, keywords: list[str]) -> Optional[str]:
    # 1. Comillas
    m = re.search(r'["\'«»]([^"\'«»]{2,80})["\'«»]', text)
    if m:
        return m.group(1).strip()
    # 2. Después de keywords
    for kw in keywords:
        idx = text.lower().find(kw.lower())
        if idx >= 0:
            # Asegurar que el keyword está al principio de una palabra (no es sufijo)
            start = idx
            if start > 0 and text[start - 1].isalpha():
                continue  # es sufijo de otra palabra (ej: "automatizarlo" contiene "auto")
            rest = text[idx + len(kw):].strip(" ,.:·-")
            rest = re.sub(r"^(de|un|una|el|la|para|nuevo|nueva|llamado|llamada|este|esta)\s+", "", rest, flags=re.IGNORECASE)
            chunk = re.split(r"\s+(?:con|para|en|y|,|que|a|por|al)\s+", rest, maxsplit=1)[0]
            chunk = chunk.strip(" ,.")
            if 2 < len(chunk) <= 100:
                return chunk.capitalize()
    # 3. Texto corto — solo si parece un nombre de entidad (no una pregunta)
    if not re.search(r"\b(cuánto|cuanto|cómo|como|qué|que|dónde|cuando|me|ahorra|vale)\b", text.lower()):
        cleaned = re.sub(r"^(el|la|los|las|un|una|mi|de|para)\s+", "", text.lower()).strip()
        if 3 <= len(cleaned) <= 80:
            return cleaned.capitalize()
    return None


def _extract_score(text: str) -> Optional[int]:
    m = re.search(r"\b([0-9]{1,3})\b", text)
    if m:
        v = int(m.group(1))
        if 0 <= v <= 100:
            return v
    return None


# ─────────────────────────────────────────────────────────────────
# CAPA 4 — ACTION EXECUTOR (incluye ROI engine y KB de BPM)
# ─────────────────────────────────────────────────────────────────

# Base de conocimiento de benchmarks BPM
_BPM_KB = {
    "facturación":       {"ahorro_h": 8,  "coste_impl": 500,  "complejidad": "baja",  "herramienta": "n8n + Google Sheets"},
    "facturacion":       {"ahorro_h": 8,  "coste_impl": 500,  "complejidad": "baja",  "herramienta": "n8n + Google Sheets"},
    "rrhh":              {"ahorro_h": 6,  "coste_impl": 800,  "complejidad": "media", "herramienta": "Zapier + HR tool"},
    "recursos humanos":  {"ahorro_h": 6,  "coste_impl": 800,  "complejidad": "media", "herramienta": "Zapier + HR tool"},
    "email":             {"ahorro_h": 5,  "coste_impl": 200,  "complejidad": "baja",  "herramienta": "n8n + Gmail API"},
    "correo":            {"ahorro_h": 5,  "coste_impl": 200,  "complejidad": "baja",  "herramienta": "n8n + Gmail API"},
    "onboarding":        {"ahorro_h": 10, "coste_impl": 1200, "complejidad": "alta",  "herramienta": "Make + Notion"},
    "inventario":        {"ahorro_h": 7,  "coste_impl": 600,  "complejidad": "media", "herramienta": "n8n + ERP API"},
    "reportes":          {"ahorro_h": 6,  "coste_impl": 400,  "complejidad": "baja",  "herramienta": "Python + cron"},
    "informes":          {"ahorro_h": 6,  "coste_impl": 400,  "complejidad": "baja",  "herramienta": "Python + cron"},
    "atención al cliente": {"ahorro_h": 4, "coste_impl": 700, "complejidad": "media", "herramienta": "n8n + CRM"},
    "ventas":            {"ahorro_h": 5,  "coste_impl": 900,  "complejidad": "media", "herramienta": "Zapier + CRM"},
    "contabilidad":      {"ahorro_h": 9,  "coste_impl": 1000, "complejidad": "alta",  "herramienta": "n8n + ERP"},
    "logística":         {"ahorro_h": 7,  "coste_impl": 800,  "complejidad": "media", "herramienta": "n8n + WMS"},
    "compras":           {"ahorro_h": 5,  "coste_impl": 600,  "complejidad": "media", "herramienta": "Zapier + ERP"},
    "pedidos":           {"ahorro_h": 6,  "coste_impl": 500,  "complejidad": "baja",  "herramienta": "n8n + e-commerce"},
    "soporte":           {"ahorro_h": 4,  "coste_impl": 700,  "complejidad": "media", "herramienta": "n8n + Zendesk"},
    "marketing":         {"ahorro_h": 5,  "coste_impl": 600,  "complejidad": "media", "herramienta": "Make + Meta API"},
}

_COSTE_HORA_DEFAULT = 25  # €/hora, benchmark pyme española


def _kb_lookup(nombre: str) -> Optional[dict]:
    nl = nombre.lower()
    for kw, data in _BPM_KB.items():
        if kw in nl:
            return data
    return None


def _roi_analysis(proceso: Optional[Proceso], nombre_hint: str) -> str:
    """
    Genera análisis ROI detallado basado en datos reales + KB de benchmarks.
    """
    # Datos base
    duracion_h = None
    frecuencia_mes = 4   # default: semanal
    nombre = nombre_hint

    if proceso:
        nombre = proceso.nombre
        duracion_h = proceso.duracion_h
        if proceso.frecuencia:
            f = proceso.frecuencia.lower()
            if "diario" in f or "día" in f:
                frecuencia_mes = 22
            elif "semana" in f:
                frecuencia_mes = 4
            elif "quincenal" in f:
                frecuencia_mes = 2
            elif "mensual" in f:
                frecuencia_mes = 1

    kb = _kb_lookup(nombre)
    ahorro_h_mes = (kb["ahorro_h"] if kb else (duracion_h * 0.7 if duracion_h else 5))
    coste_impl   = kb["coste_impl"] if kb else 800
    herramienta  = kb["herramienta"] if kb else "n8n / Zapier"
    complejidad  = kb["complejidad"] if kb else "media"
    coste_hora   = _COSTE_HORA_DEFAULT

    ahorro_mensual = round(ahorro_h_mes * coste_hora, 0)
    ahorro_anual   = ahorro_mensual * 12
    payback_meses  = round(coste_impl / ahorro_mensual, 1) if ahorro_mensual > 0 else "∞"
    roi_12m        = round(((ahorro_anual - coste_impl) / coste_impl) * 100, 0) if coste_impl > 0 else 0

    score_str = ""
    if proceso and proceso.score is not None:
        s = proceso.score
        if s < 40:
            score_str = f"\n> ⚠️ Score actual {s}/100 — proceso **crítico**, automatizar es **prioritario**."
        elif s < 70:
            score_str = f"\n> 🟡 Score actual {s}/100 — mejora moderada esperada tras automatizar."
        else:
            score_str = f"\n> 🟢 Score actual {s}/100 — proceso ya eficiente, automatizar amplifica el rendimiento."

    intro = _r(
        f"He calculado el potencial de automatizar **{nombre}**. Aquí están los números:",
        f"Estos son los números para **{nombre}** si lo automatizamos:",
        f"Análisis listo. El impacto económico de automatizar **{nombre}** es este:",
        f"Buenas noticias para **{nombre}**: los números son favorables.",
        f"El ROI de automatizar **{nombre}** habla por sí solo:",
    )

    cierre = _r(
        "¿Quieres que cree la automatización para empezar?",
        "¿Lo ponemos en marcha? Puedo crear la automatización ahora mismo.",
        "¿Damos el siguiente paso y creamos la automatización?",
        "Con estos números, merece la pena. ¿Arrancamos con la automatización?",
    )

    lines = [
        f"## 📊 Análisis ROI — *{nombre}*{score_str}",
        "",
        intro,
        "",
        f"| Parámetro | Estimación |",
        f"|---|---|",
        f"| Ahorro de horas/mes | **{ahorro_h_mes:.0f} h** |",
        f"| Coste hora evitada | {coste_hora} €/h |",
        f"| **Ahorro mensual** | **{ahorro_mensual:.0f} €** |",
        f"| **Ahorro anual** | **{ahorro_anual:.0f} €** |",
        f"| Inversión estimada | {coste_impl} € |",
        f"| **Payback** | **{payback_meses} meses** |",
        f"| **ROI a 12 meses** | **{roi_12m:.0f}%** |",
        "",
        f"**Herramienta recomendada:** {herramienta} · Complejidad: {complejidad}",
        "",
        cierre,
    ]
    return "\n".join(lines)


def _deep_analysis(proceso: Proceso, procesos: list, kpis: list, autos: list) -> str:
    """
    Análisis profundo de un proceso: score, contexto, KPIs vinculados, automatizaciones, recomendaciones.
    """
    s = proceso.score
    emoji = "🔴" if (s or 0) < 40 else "🟡" if (s or 0) < 70 else "🟢"
    score_str = f"{s}/100" if s is not None else "sin asignar"

    # KPIs vinculados
    p_kpis = [k for k in kpis if getattr(k, "proceso_id", None) == proceso.id]
    kpi_str = ""
    if p_kpis:
        kpi_lines = [f"  · **{k.nombre}**: {k.valor}{' ' + k.unidad if k.unidad else ''}" for k in p_kpis]
        kpi_str = "\n\n**KPIs vinculados:**\n" + "\n".join(kpi_lines)

    # Automatizaciones vinculadas
    p_autos = [a for a in autos if getattr(a, "proceso_id", None) == proceso.id]
    auto_str = ""
    if p_autos:
        auto_lines = [f"  · **{a.nombre}** ({a.estado})" for a in p_autos]
        auto_str = "\n\n**Automatizaciones activas:**\n" + "\n".join(auto_lines)

    # Score comparativo con el resto
    scores_rest = [p.score for p in procesos if p.score is not None and p.id != proceso.id]
    bench_str = ""
    if scores_rest:
        avg = sum(scores_rest) / len(scores_rest)
        delta = (s or 0) - avg
        comp = "por encima" if delta > 0 else "por debajo"
        bench_str = f"\n\n**Benchmark interno:** {abs(delta):.0f} puntos {comp} de la media de tus procesos ({avg:.0f}/100)."

    # Recomendación
    recom = ""
    if s is not None and s < 40:
        kb = _kb_lookup(proceso.nombre)
        tool = kb["herramienta"] if kb else "n8n"
        recom = f"\n\n**⚡ Recomendación:** Score crítico. Prioridad máxima de mejora. Considera automatizar con **{tool}** — ROI estimado positivo en menos de 6 meses."
    elif s is not None and s < 70:
        recom = f"\n\n**💡 Recomendación:** Margen de mejora significativo. Revisa cuellos de botella y asigna responsable si no lo tiene."
    elif s is not None:
        recom = f"\n\n**✅ Evaluación:** Proceso bien optimizado. Mantener monitorización con KPIs para detectar degradación."

    lines = [
        f"{emoji} **Diagnóstico completo — {proceso.nombre}**",
        "",
        f"| Campo | Valor |",
        f"|---|---|",
        f"| Score | **{score_str}** |",
        f"| Estado | {proceso.estado} |",
    ]
    if proceso.responsable:
        lines.append(f"| Responsable | {proceso.responsable} |")
    if proceso.frecuencia:
        lines.append(f"| Frecuencia | {proceso.frecuencia} |")
    if proceso.duracion_h:
        lines.append(f"| Duración | {proceso.duracion_h} h |")
    if proceso.descripcion:
        lines.append(f"| Descripción | {proceso.descripcion} |")

    result = "\n".join(lines)
    result += kpi_str + auto_str + bench_str + recom

    if not p_autos:
        result += f"\n\n¿Quieres que calcule el ROI de automatizar **{proceso.nombre}**?"

    return result


# ─────────────────────────────────────────────────────────────────
# CAPA 5 — RESPONSE SYNTHESIZER
# ─────────────────────────────────────────────────────────────────

def _r(*options: str) -> str:
    return random.choice(options)


def _ack() -> str:
    """Acuse de recibo aleatorio para confirmar acciones completadas."""
    return random.choice([
        "Hecho.",
        "Listo.",
        "En el sistema.",
        "Perfecto.",
        "Registrado.",
        "Entendido.",
        "De acuerdo, queda guardado.",
    ])


def _next_step(procesos, kpis, autos, mem_proceso=None, mem=None) -> str:
    """
    Sugiere el siguiente paso natural basado en el estado actual.
    Devuelve UNA frase corta de sugerencia.
    """
    # Procesos sin score
    sin_score = [p for p in procesos if p.score is None]
    if sin_score:
        candidato = sin_score[0]
        # Si hay un proceso recién creado, priorizarlo
        if mem_proceso and mem_proceso.score is None:
            candidato = mem_proceso
        return f"¿Le ponemos un score a **{candidato.nombre}**? (0 = crítico, 100 = óptimo)"

    # Procesos críticos
    criticos = [p for p in procesos if p.score is not None and p.score < 40]
    if criticos:
        peor = min(criticos, key=lambda p: p.score)
        return f"⚠️ **{peor.nombre}** tiene score {peor.score}/100. ¿Lo analizamos?"

    # Hay procesos pero ninguna automatización
    if procesos and not autos:
        return "¿Automatizamos alguno? Puedo calcular el ROI en segundos."

    # Automatizaciones inactivas/pendientes
    pendientes = [a for a in autos if a.estado == "pendiente"]
    if pendientes:
        return f"Tienes {len(pendientes)} automatización(es) en *pendiente*. ¿Las revisamos?"

    # Sin KPIs
    if procesos and not kpis:
        return "Sin KPIs no hay forma de medir el progreso. ¿Creamos uno?"

    return "¿En qué más puedo ayudarte?"


def _formal(msg: str) -> str:
    """Marca el mensaje como de registro formal consultivo."""
    return msg


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


# ─────────────────────────────────────────────────────────────────
# PUNTO DE ENTRADA PRINCIPAL
# ─────────────────────────────────────────────────────────────────

async def _resolve_contextual_short(
    lower: str,
    text: str,
    mem: ConversationMemory,
    mem_proceso,
    procesos: list,
    kpis: list,
    autos: list,
    db: AsyncSession,
    empresa: Empresa,
) -> Optional[dict]:
    """
    Resuelve inputs cortos/ambiguos usando el contexto de la conversación.
    Se llama ANTES del clasificador de intents para inputs de ≤4 palabras.
    Devuelve {respuesta, accion, entidad} o None si no puede resolver.
    """
    stripped = lower.strip()

    # Input vacío o solo signos de pregunta → no resolver
    if not stripped or stripped in ("?", "??", "???"):
        return None

    def R(texto: str, accion: str = None, entidad: dict = None):
        return {"respuesta": texto, "accion": accion, "entidad": entidad}

    # ── Número puro 0-100 ───────────────────────────────────────
    num_match = re.fullmatch(r"\s*([0-9]{1,3})\s*", stripped)
    if num_match:
        v = int(num_match.group(1))
        if 0 <= v <= 100:
            if mem.state == ConvState.ASKED_SCORE and mem_proceso:
                mem_proceso.score = v
                await db.commit()
                emoji = "🔴" if v < 40 else "🟡" if v < 70 else "🟢"
                ns = _next_step(procesos, kpis, autos, mem_proceso, mem)
                return R(
                    f"{_ack()} {emoji} Score de **{mem_proceso.nombre}** fijado a **{v}/100**.\n\n{ns}",
                    "updated_proceso", {"id": mem_proceso.id, "score": v},
                )
            # No hay proceso activo, pero hay procesos sin score
            sin_score = [p for p in procesos if p.score is None]
            if sin_score:
                nombres = ", ".join(f"*{p.nombre}*" for p in sin_score[:4])
                return R(
                    f"¿A qué proceso le asigno el score de **{v}**? "
                    f"Procesos sin score: {nombres}."
                )
        return None

    # ── Solo nombre de proceso conocido ─────────────────────────
    p_match = _find_proceso(procesos, text.strip())
    # Verificar que el input sea realmente solo el nombre (no una frase larga)
    if p_match and len(lower.split()) <= 3:
        s = p_match.score
        score_txt = f"**{s}/100**" if s is not None else "*sin score*"
        emoji = "🔴" if (s or 0) < 40 else "🟡" if (s or 0) < 70 else "🟢"
        return R(
            f"Aquí tienes {emoji} **{p_match.nombre}**: score {score_txt}, estado *{p_match.estado}*. "
            f"¿Qué quieres hacer — analizar, calcular ROI, o actualizar algo?"
        )

    # ── Nombre de herramienta solo ──────────────────────────────
    _TOOLS = ["n8n", "zapier", "make", "python", "power automate"]
    herramienta_detectada = None
    for tool in _TOOLS:
        if tool in stripped:
            herramienta_detectada = tool
            break

    if herramienta_detectada and mem.state == ConvState.ASKED_AUTO and mem_proceso:
        nombre_auto = f"Automatización de {mem_proceso.nombre}"
        nuevo = Automatizacion(
            empresa_id=empresa.id,
            nombre=nombre_auto,
            estado="pendiente",
            herramienta=herramienta_detectada.capitalize(),
            ejecuciones=0,
        )
        db.add(nuevo)
        await db.commit()
        await db.refresh(nuevo)
        ns = _next_step(procesos, kpis, autos, mem_proceso, mem)
        return R(
            f"{_ack()} ⚡ Automatización **{nuevo.nombre}** creada con **{herramienta_detectada}** "
            f"en estado *pendiente*.\n\n{ns}",
            "created_auto", {"id": nuevo.id, "nombre": nuevo.nombre},
        )

    return None


async def responder(
    mensaje: str,
    empresa: Empresa,
    db: AsyncSession,
    historial: list,
) -> dict[str, Any]:
    """
    Orquesta el pipeline de 5 capas y devuelve {respuesta, accion, entidad}.
    """

    def R(texto: str, accion: str = None, entidad: dict = None):
        return {"respuesta": texto, "accion": accion, "entidad": entidad}

    # ── Carga de datos ────────────────────────────────────────────
    proc_res = await db.execute(select(Proceso).where(Proceso.empresa_id == empresa.id))
    kpi_res  = await db.execute(select(KPI).where(KPI.empresa_id == empresa.id))
    auto_res = await db.execute(select(Automatizacion).where(Automatizacion.empresa_id == empresa.id))
    procesos = proc_res.scalars().all()
    kpis     = kpi_res.scalars().all()
    autos    = auto_res.scalars().all()
    scores   = [p for p in procesos if p.score is not None]

    n_turns = len([m for m in historial if m.get("role") == "user"])

    # ── [1] Pre-process ───────────────────────────────────────────
    pre = pre_process(mensaje)
    lower = pre["lower"]

    # ── [2] Context (memoria completa de la conversación) ─────────
    mem = analyze_context(historial[:-1])  # excluir el mensaje actual
    mem_proceso = _find_proceso(procesos, mem.active_entity) if mem.active_entity else None

    # Helper de saludo con memoria acumulada
    def _session_summary_line() -> str:
        parts = []
        if mem.all_created:
            tipos = {}
            for c in mem.all_created:
                tipos[c["type"]] = tipos.get(c["type"], 0) + 1
            _tipo_label = {"proceso": "proceso(s)", "kpi": "KPI(s)", "auto": "automatización(es)"}
            desc = ", ".join(
                f"{v} {_tipo_label.get(k, k)}"
                for k, v in tipos.items()
            )
            parts.append(f"hemos creado {desc}")
        if mem.all_analyzed:
            parts.append(f"analizado {', '.join(mem.all_analyzed[:2])}")
        if mem.roi_calcs_done:
            parts.append(f"calculado ROI de {mem.roi_calcs_done[0]}")
        if not parts:
            return ""
        return "En esta sesión " + " y ".join(parts) + "."

    # ── [2.5] Resolver inputs cortos en contexto ──────────────────
    if len(lower.split()) <= 4:
        resolved = await _resolve_contextual_short(
            lower, pre["text"], mem, mem_proceso, procesos, kpis, autos, db, empresa
        )
        if resolved:
            return resolved

    # ── [3] Intent ────────────────────────────────────────────────
    ci = classify_intent(pre, mem)

    # ══════════════════════════════════════════════════════════════
    # RESPUESTAS CONTEXTUALES (estado de la máquina)
    # ══════════════════════════════════════════════════════════════

    if n_turns > 1 and ci.intent in (Intent.AFFIRMATIVE, Intent.NEGATIVE):

        if mem.state == ConvState.ASKED_SCORE:
            if ci.intent == Intent.AFFIRMATIVE:
                sv = _extract_score(lower)
                if sv is None and mem_proceso:
                    return R(f"¿Qué score le asignamos a **{mem_proceso.nombre}**? Indique un valor entre 0 y 100.")
                if sv is not None and mem_proceso:
                    mem_proceso.score = sv
                    await db.commit()
                    emoji = "🔴" if sv < 40 else "🟡" if sv < 70 else "🟢"
                    ns = _next_step(procesos, kpis, autos, mem_proceso, mem)
                    return R(
                        f"{_ack()} {emoji} Score de **{mem_proceso.nombre}** actualizado a **{sv}/100**.\n\n{ns}",
                        "updated_proceso", {"id": mem_proceso.id, "score": sv},
                    )
                return R("Indique el número de score que desea asignar (0–100).")
            return R(_r(
                "Entendido, sin score por ahora. Puede asignarlo en cualquier momento desde **Procesos** o indicándomelo directamente.",
                "De acuerdo. Cuando disponga del dato, dígamelo y lo registro al instante.",
                "Sin problema. Lo dejamos sin score por ahora — dime cuando quieras asignarlo.",
            ))

        if mem.state == ConvState.ASKED_ANALYZE and mem_proceso:
            if ci.intent == Intent.AFFIRMATIVE:
                return R(_deep_analysis(mem_proceso, procesos, kpis, autos))
            return R(_r(
                "De acuerdo. ¿En qué puedo asistirle?",
                "Sin problema. ¿Qué quieres hacer ahora?",
                "Entendido. Dime en qué puedo ayudarte.",
            ))

        if mem.state == ConvState.ASKED_AUTO and mem_proceso:
            if ci.intent == Intent.AFFIRMATIVE:
                nuevo = Automatizacion(
                    empresa_id=empresa.id,
                    nombre=f"Automatización de {mem_proceso.nombre}",
                    estado="pendiente", ejecuciones=0,
                )
                db.add(nuevo)
                await db.commit()
                await db.refresh(nuevo)
                ns = _next_step(procesos, kpis, autos, mem_proceso, mem)
                return R(
                    f"{_ack()} ⚡ Automatización **{nuevo.nombre}** creada y registrada en estado *pendiente*.\n\n"
                    f"Acceda a **Automatizaciones** para configurar la herramienta y activarla.\n\n{ns}",
                    "created_auto", {"id": nuevo.id, "nombre": nuevo.nombre},
                )
            return R(_r(
                "Entendido. Si en el futuro desea crearla, no dude en pedírmelo.",
                "De acuerdo, lo dejamos para más adelante.",
                "Sin problema. Cuando quieras, dímelo y la creamos.",
            ))

        if mem.state == ConvState.ASKED_ROI and mem_proceso:
            if ci.intent == Intent.AFFIRMATIVE:
                return R(_roi_analysis(mem_proceso, mem_proceso.nombre))
            return R(_r(
                "De acuerdo. ¿Hay algo más en lo que pueda ayudarle?",
                "Entendido. ¿En qué más puedo asistirte?",
                "Sin problema. Aquí estoy si necesitas algo.",
            ))

        if mem.state == ConvState.JUST_CREATED:
            entity_name = mem.all_mentioned[0] if mem.all_mentioned else "el registro"
            if ci.intent == Intent.NEGATIVE and any(w in lower for w in ["no quería", "no era", "error", "equivocado"]):
                return R(
                    f"Entendido, puede haber sido un malentendido. ¿Desea que elimine **{entity_name}**? "
                    f"Confirme con *«sí, elimínalo»* o indíqueme qué quería crear exactamente."
                )

    # ══════════════════════════════════════════════════════════════
    # INTENT: GREETING
    # ══════════════════════════════════════════════════════════════

    if ci.intent == Intent.GREETING:
        if n_turns <= 1:
            intro = _r(
                f"Buenas. Soy **BPA-Agent**, el asistente de optimización de procesos de **{empresa.nombre}**.",
                f"¡Hola! Conectado a **{empresa.nombre}**. ¿En qué puedo ayudarle?",
                f"Bienvenido. Soy el agente de **{empresa.nombre}**. ¿Por dónde empezamos?",
                f"¡Hola! Estoy listo para trabajar en **{empresa.nombre}**. Cuéntame qué necesitas.",
                f"Buenas. **BPA-Agent** al servicio de **{empresa.nombre}**. ¿Qué gestionamos hoy?",
            )
            if not procesos:
                return R(
                    intro + "\n\n"
                    "Observo que no hay procesos registrados todavía. Puedo crearlos directamente: "
                    "dígame *«crea un proceso de [nombre]»* y lo registro en el acto.\n\n"
                    "También gestiono KPIs, automatizaciones y realizo diagnósticos y análisis ROI."
                )
            criticos = [p for p in scores if p.score < 50]
            resumen = (
                f"Su empresa cuenta con **{len(procesos)} proceso(s)**, "
                f"**{len(autos)} automatización(es)** y **{len(kpis)} KPI(s)**"
            )
            if criticos:
                resumen += f". ⚠️ **{len(criticos)} proceso(s) en estado crítico** requieren atención inmediata"
            return R(intro + "\n\n" + resumen + ".\n\n¿Qué desea hacer hoy?")

        # Saludo en mitad de conversación — usar memoria de sesión
        session_line = _session_summary_line()
        if mem.session_actions_count > 0 and session_line:
            ns = _next_step(procesos, kpis, autos, mem_proceso, mem)
            return R(_r(
                f"Aquí sigo. {session_line} {ns}",
                f"¡Hola de nuevo! {session_line} {ns}",
                f"Sigo contigo. {session_line} {ns}",
                f"Por aquí estoy. {session_line} {ns}",
                f"De vuelta. {session_line} {ns}",
            ))
        return R(_r(
            "¡Hola de nuevo! ¿En qué puedo asistirle?",
            "¿Qué tal? ¿Qué necesitas?",
            "¡Buenas! Dígame.",
            "Aquí estoy. ¿Qué necesitas?",
            "¡Hola! ¿Seguimos trabajando?",
        ))

    # ══════════════════════════════════════════════════════════════
    # INTENT: COMPLAINT
    # ══════════════════════════════════════════════════════════════

    if ci.intent == Intent.COMPLAINT:
        return R(_r(
            "Tiene razón, lo he gestionado incorrectamente. ¿Podría indicarme exactamente qué necesita? "
            "Con más detalle podré ejecutarlo con precisión.",
            "Le pido disculpas. Dígame qué esperaba que hiciera y lo corrijo de inmediato.",
            "Entendido el error. ¿Puede reformularlo? Intente ser específico: *«crea X»*, *«analiza Y»*, *«actualiza Z a valor»*.",
        ))

    # ══════════════════════════════════════════════════════════════
    # INTENT: HELP
    # ══════════════════════════════════════════════════════════════

    if ci.intent == Intent.HELP:
        return R(
            "## 🤖 Capacidades del agente BPA\n\n"
            "**📋 Gestión de procesos**\n"
            "• *«Crea un proceso de facturación mensual»*\n"
            "• *«Analiza el proceso de [nombre]»*\n"
            "• *«Muéstrame mis procesos»*\n"
            "• *«Actualiza el score de [proceso] a 75»*\n"
            "• *«Cambia el responsable de [proceso] a [persona]»*\n"
            "• *«Elimina el proceso [nombre]»*\n\n"
            "**⚡ Automatizaciones**\n"
            "• *«Crea una automatización de envío de emails con n8n»*\n"
            "• *«¿Cuánto me ahorra automatizar [proceso]?»* — análisis ROI\n\n"
            "**📈 KPIs**\n"
            "• *«Crea un KPI de satisfacción del cliente para [proceso]»*\n"
            "• *«Muéstrame mis KPIs»*\n\n"
            "**📊 Análisis y reportes**\n"
            "• *«Dame un resumen de la empresa»*\n"
            "• *«¿Cuáles son mis recomendaciones?»*\n\n"
            "**🚀 Operaciones en lote**\n"
            "• *«Crea tres procesos: Facturación, RRHH, Logística»*\n\n"
            "Todo se persiste en base de datos en tiempo real."
        )

    # ══════════════════════════════════════════════════════════════
    # INTENT: BATCH_CREATE
    # ══════════════════════════════════════════════════════════════

    if ci.intent == Intent.BATCH_CREATE:
        items = ci.batch_items
        etype = ci.batch_type
        creados = []
        for nombre in items[:10]:  # máximo 10 en lote
            nombre = nombre[:100].strip()
            if len(nombre) < 2:
                continue
            if etype == "proceso":
                obj = Proceso(empresa_id=empresa.id, nombre=nombre.capitalize(), estado="pendiente")
            elif etype == "kpi":
                obj = KPI(empresa_id=empresa.id, nombre=nombre.capitalize(), valor="0", tendencia="up")
            else:
                obj = Automatizacion(empresa_id=empresa.id, nombre=nombre.capitalize(), estado="pendiente", ejecuciones=0)
            db.add(obj)
            creados.append(nombre.capitalize())

        await db.commit()
        tipo_label = {"proceso": "procesos", "kpi": "KPIs", "auto": "automatizaciones"}.get(etype, "elementos")
        lines = "\n".join(f"  ✅ **{n}**" for n in creados)
        ns = _next_step(procesos, kpis, autos, None, mem)
        batch_intro = _r(
            f"He registrado **{len(creados)} {tipo_label}** en el sistema:",
            f"Listo. Los **{len(creados)} {tipo_label}** ya están en la base de datos:",
            f"En el sistema. Aquí están los **{len(creados)} {tipo_label}** registrados:",
            f"Hecho. He dado de alta **{len(creados)} {tipo_label}**:",
        )
        return R(
            f"{batch_intro}\n\n{lines}\n\n{ns}",
            f"batch_created_{etype}", {"count": len(creados), "nombres": creados},
        )

    # ══════════════════════════════════════════════════════════════
    # INTENT: CREATE_PROCESO / CREATE_KPI / CREATE_AUTO
    # ══════════════════════════════════════════════════════════════

    if ci.intent == Intent.CREATE_PROCESO:
        nombre = ci.entity_name
        if not nombre or len(nombre.strip()) < 2:
            return R("¿Cuál es el nombre del proceso que desea crear?")
        nuevo = Proceso(empresa_id=empresa.id, nombre=nombre[:100], estado="pendiente")
        db.add(nuevo)
        await db.commit()
        await db.refresh(nuevo)
        kb = _kb_lookup(nombre)
        sugerencia = ""
        if kb:
            sugerencia = (
                f"\n\n**Nota consultiva:** Procesos similares a *{nombre}* tienen un ahorro medio de "
                f"**{kb['ahorro_h']}h/mes** al automatizarse con {kb['herramienta']}. "
                f"¿Calculo el ROI si lo automatizamos?"
            )
        # Actualizar procesos con el nuevo para _next_step correcto
        procesos_actualizados = list(procesos) + [nuevo]
        ns = _next_step(procesos_actualizados, kpis, autos, nuevo, mem)
        return R(
            _ack() + " " + _r(
                f"Proceso **{nuevo.nombre}** listo en el sistema.",
                f"He registrado **{nuevo.nombre}** en **Procesos**.",
                f"**{nuevo.nombre}** ya está en la lista de procesos.",
                f"Proceso **{nuevo.nombre}** dado de alta con estado *pendiente*.",
                f"He incorporado **{nuevo.nombre}** al sistema.",
                f"**{nuevo.nombre}** registrado y visible en **Procesos**.",
            )
            + sugerencia
            + "\n\n" + ns,
            "created_proceso", {"id": nuevo.id, "nombre": nuevo.nombre},
        )

    if ci.intent == Intent.CREATE_KPI:
        nombre = ci.entity_name
        if not nombre or len(nombre.strip()) < 2:
            return R(
                "¿Cómo se denominará el KPI? Por ejemplo: *«crea un KPI de tasa de resolución en primer contacto»*."
            )
        valor = "0"
        m_val = re.search(r"(?:valor|de|a|en)\s+([\d,.]+\s*%?)", lower)
        if m_val:
            valor = m_val.group(1).strip()

        # Vincular a proceso si se menciona
        proceso_id = None
        proceso_link_str = ""
        for kw in ["para el proceso", "del proceso", "proceso de", "para"]:
            m_p = re.search(rf"\b{kw}\b\s+(.{{3,60}}?)(?:\s*$|\s*,|\s*\.)", pre["text"], re.IGNORECASE)
            if m_p:
                pname = m_p.group(1).strip()
                p_obj = _find_proceso(procesos, pname)
                if p_obj:
                    proceso_id = p_obj.id
                    proceso_link_str = f" vinculado al proceso **{p_obj.nombre}**"
                    break

        nuevo = KPI(
            empresa_id=empresa.id, nombre=nombre[:100], valor=valor,
            tendencia="up", proceso_id=proceso_id,
        )
        db.add(nuevo)
        await db.commit()
        await db.refresh(nuevo)
        ns = _next_step(procesos, list(kpis) + [nuevo], autos, None, mem)
        return R(
            f"{_ack()} KPI **{nuevo.nombre}** creado con valor inicial `{valor}`{proceso_link_str}.\n\n"
            f"Puede editarlo en **KPIs** para definir unidad, objetivo y tendencia.\n\n{ns}",
            "created_kpi", {"id": nuevo.id, "nombre": nuevo.nombre},
        )

    if ci.intent == Intent.CREATE_AUTO:
        nombre = ci.entity_name
        if not nombre or len(nombre.strip()) < 2:
            return R(
                "¿Cómo se denominará la automatización? Por ejemplo: *«crea una automatización de envío de facturas con n8n»*."
            )
        herramienta = None
        for tool in ["n8n", "zapier", "make", "gmail", "sheets", "slack", "python", "power automate", "airtable", "notion"]:
            if tool in lower:
                herramienta = tool.capitalize()
                break
        nuevo = Automatizacion(
            empresa_id=empresa.id, nombre=nombre[:100],
            estado="pendiente", herramienta=herramienta, ejecuciones=0,
        )
        db.add(nuevo)
        await db.commit()
        await db.refresh(nuevo)
        tool_str = f" con **{herramienta}**" if herramienta else ""
        kb = _kb_lookup(nombre)
        ahorro_hint = f"\n\nAhorro estimado según benchmarks del sector: **{kb['ahorro_h']}h/mes** (~{kb['ahorro_h']*_COSTE_HORA_DEFAULT}€/mes)." if kb else ""
        ns = _next_step(procesos, kpis, list(autos) + [nuevo], None, mem)
        return R(
            f"{_ack()} ⚡ Automatización **{nuevo.nombre}** creada{tool_str} en estado *pendiente*."
            + ahorro_hint
            + f"\n\nActívela en **Automatizaciones** cuando esté configurada para que compute en las estadísticas.\n\n{ns}",
            "created_auto", {"id": nuevo.id, "nombre": nuevo.nombre},
        )

    # ══════════════════════════════════════════════════════════════
    # INTENT: DELETE
    # ══════════════════════════════════════════════════════════════

    if ci.intent == Intent.DELETE:
        etype = ci.entity_type
        nombre = ci.entity_name
        if etype == "proceso":
            p = _find_proceso(procesos, nombre) or mem_proceso
            if p:
                nombre_eliminado = p.nombre
                await db.delete(p)
                await db.commit()
                procesos_restantes = [x for x in procesos if x.id != p.id]
                ns = _next_step(procesos_restantes, kpis, autos, None, mem)
                return R(
                    f"{_ack()} 🗑️ El proceso **{nombre_eliminado}** ha sido eliminado del sistema.\n\n{ns}",
                    "deleted_proceso",
                )
            if not procesos:
                return R("No hay procesos registrados.")
            return R("No he localizado ese proceso. Sus procesos son: " + ", ".join(f"*{p.nombre}*" for p in procesos[:6]))
        if etype == "kpi":
            k = _find_kpi(kpis, nombre)
            if k:
                nombre_eliminado = k.nombre
                await db.delete(k)
                await db.commit()
                ns = _next_step(procesos, [x for x in kpis if x.id != k.id], autos, None, mem)
                return R(
                    f"{_ack()} 🗑️ KPI **{nombre_eliminado}** eliminado.\n\n{ns}",
                    "deleted_kpi",
                )
            return R("¿Qué KPI desea eliminar? Indique el nombre exacto.")
        if etype == "auto":
            a = _find_auto(autos, nombre)
            if a:
                nombre_eliminado = a.nombre
                await db.delete(a)
                await db.commit()
                ns = _next_step(procesos, kpis, [x for x in autos if x.id != a.id], None, mem)
                return R(
                    f"{_ack()} 🗑️ Automatización **{nombre_eliminado}** eliminada.\n\n{ns}",
                    "deleted_auto",
                )
            return R("¿Qué automatización desea eliminar? Indique el nombre.")
        return R("¿Qué desea eliminar? Indique si es un proceso, KPI o automatización.")

    # ══════════════════════════════════════════════════════════════
    # INTENT: UPDATE_SCORE
    # ══════════════════════════════════════════════════════════════

    if ci.intent == Intent.UPDATE_SCORE:
        sv = ci.score_value or _extract_score(lower)
        p = _find_proceso(procesos, ci.entity_name) or mem_proceso
        if p and sv is not None:
            p.score = sv
            await db.commit()
            emoji = "🔴" if sv < 40 else "🟡" if sv < 70 else "🟢"
            ns = _next_step(procesos, kpis, autos, p, mem)
            return R(
                f"{_ack()} {emoji} Score de **{p.nombre}** actualizado a **{sv}/100**.\n\n{ns}",
                "updated_proceso", {"id": p.id, "score": sv},
            )
        if not p:
            return R("¿A qué proceso desea modificar el score? Indique el nombre.")
        return R(f"¿A qué valor quiere fijar el score de **{p.nombre}**? (0–100)")

    # ══════════════════════════════════════════════════════════════
    # INTENT: UPDATE_FIELD (multi-campo)
    # ══════════════════════════════════════════════════════════════

    if ci.intent == Intent.UPDATE_FIELD:
        p = _find_proceso(procesos, ci.entity_name) or mem_proceso
        fname = ci.campo
        fval  = ci.field_value

        if not p:
            return R("¿A qué proceso desea modificar el campo? Indique el nombre.")
        if not fname:
            return R(
                f"¿Qué campo de **{p.nombre}** desea actualizar? "
                f"Opciones: responsable, estado, frecuencia, duración, descripción."
            )
        if not fval:
            label = {"responsable": "responsable", "estado": "estado (pendiente/activo/completado)",
                     "frecuencia": "frecuencia (diario/semanal/mensual)",
                     "duracion_h": "duración en horas", "descripcion": "descripción"}.get(fname, fname)
            return R(f"¿Cuál es el nuevo valor para **{label}** de **{p.nombre}**?")

        # Validar estado
        if fname == "estado" and fval not in ["pendiente", "activo", "completado", "activa", "inactivo"]:
            fval = "activo" if any(w in fval for w in ["activ", "en curso"]) else "pendiente"

        # Aplicar cambio
        setattr(p, fname, fval if fname != "duracion_h" else _parse_float(fval))
        await db.commit()
        field_label = fname.replace("_", " ").capitalize()
        ns = _next_step(procesos, kpis, autos, p, mem)
        return R(
            f"{_ack()} **{field_label}** de **{p.nombre}** actualizado a *{fval}*.\n\n{ns}",
            "updated_proceso", {"id": p.id, "field": fname, "value": fval},
        )

    # ══════════════════════════════════════════════════════════════
    # INTENT: ANALYZE
    # ══════════════════════════════════════════════════════════════

    if ci.intent == Intent.ANALYZE:
        p = _find_proceso(procesos, ci.entity_name) or mem_proceso
        if p:
            return R(_deep_analysis(p, procesos, kpis, autos))
        if procesos:
            names = ", ".join(f"*{p.nombre}*" for p in procesos[:6])
            return R(f"¿Qué proceso desea analizar? Sus procesos: {names}")
        return R("No hay procesos registrados. Créelos con *«crea un proceso de [nombre]»*.")

    # ══════════════════════════════════════════════════════════════
    # INTENT: ROI_CALC
    # ══════════════════════════════════════════════════════════════

    if ci.intent == Intent.ROI_CALC:
        p = _find_proceso(procesos, ci.entity_name) or mem_proceso
        nombre_hint = (p.nombre if p else ci.entity_name) or "el proceso"
        return R(_formal(_roi_analysis(p, nombre_hint)))

    # ══════════════════════════════════════════════════════════════
    # INTENT: LIST
    # ══════════════════════════════════════════════════════════════

    if ci.intent == Intent.LIST:
        etype = ci.entity_type

        if etype in ("proceso", "") or any(w in lower for w in ["proceso", "procesos"]):
            if not procesos:
                return R("No hay procesos registrados. Diga *«crea un proceso de [nombre]»* para comenzar.")
            lines = []
            for p in sorted(procesos, key=lambda x: (x.score is None, x.score or 999)):
                e = "🔴" if (p.score or 0) < 40 else "🟡" if (p.score or 0) < 70 else "🟢"
                s = f" — **{p.score}/100**" if p.score is not None else " — *sin score*"
                resp = f" _(resp. {p.responsable})_" if p.responsable else ""
                lines.append(f"{e} **{p.nombre}**{s}{resp}")
            criticos = [p for p in scores if p.score < 50]
            footer = ""
            if criticos:
                footer = f"\n\n⚠️ **{len(criticos)} proceso(s) crítico(s)**. ¿Analizo **{criticos[0].nombre}**?"
            return R(f"📋 **{len(procesos)} proceso(s):**\n\n" + "\n".join(lines) + footer)

        if etype == "auto" or any(re.search(kw, lower) for kw in _AUTO_KW):
            if not autos:
                return R("No hay automatizaciones. Cree la primera con *«crea una automatización de [nombre]»*.")
            activas = [a for a in autos if a.estado == "activa"]
            horas = sum(a.horas_mes or 0 for a in autos)
            lines = [
                f"{'⚡' if a.estado=='activa' else '⏸️'} **{a.nombre}** — {a.estado}"
                + (f" ({a.herramienta})" if a.herramienta else "")
                + (f" · {a.horas_mes}h/mes" if a.horas_mes else "")
                for a in autos
            ]
            return R(
                f"⚡ **{len(autos)} automatización(es)** ({len(activas)} activas · **{horas}h/mes** ahorradas):\n\n"
                + "\n".join(lines)
            )

        if etype == "kpi" or any(kw in lower for kw in _KPI_KW):
            if not kpis:
                return R("No hay KPIs definidos. Créelos con *«crea un KPI de [nombre]»*.")
            lines = []
            for k in kpis[:10]:
                t = "↑" if k.tendencia == "up" else "↓" if k.tendencia == "down" else "→"
                unit = f" {k.unidad}" if k.unidad else ""
                obj  = f" (obj: {k.objetivo})" if k.objetivo else ""
                lines.append(f"{t} **{k.nombre}**: {k.valor}{unit}{obj}")
            return R(f"📈 **{len(kpis)} KPI(s):**\n\n" + "\n".join(lines))

    # ══════════════════════════════════════════════════════════════
    # INTENT: SUMMARY
    # ══════════════════════════════════════════════════════════════

    if ci.intent == Intent.SUMMARY:
        activas = [a for a in autos if a.estado == "activa"]
        horas   = sum(a.horas_mes or 0 for a in autos)
        criticos = [p for p in scores if p.score < 50]
        score_prom = round(sum(p.score for p in scores) / len(scores), 1) if scores else None

        res  = f"## 📊 Estado de {empresa.nombre}\n\n"
        res += f"| Área | Detalle |\n|---|---|\n"
        res += f"| Procesos | **{len(procesos)}**"
        if score_prom is not None:
            res += f" · Score medio: **{score_prom}/100**"
        if criticos:
            res += f" · ⚠️ **{len(criticos)} crítico(s)**"
        res += " |\n"
        res += f"| Automatizaciones | **{len(autos)}** ({len(activas)} activas) · Ahorro: **{horas}h/mes** (~{horas*_COSTE_HORA_DEFAULT}€/mes) |\n"
        res += f"| KPIs | **{len(kpis)}** indicadores definidos |\n\n"

        if not procesos:
            res += "**Paso 1 recomendado:** Mapear los procesos clave de la empresa con *«crea un proceso de [nombre]»*."
        elif criticos:
            res += (
                f"**Acción prioritaria:** El proceso **{criticos[0].nombre}** tiene score **{criticos[0].score}/100**. "
                f"¿Realizo un análisis completo y propongo medidas de mejora?"
            )
        elif not kpis:
            res += "**Siguiente paso:** Defina KPIs para medir la evolución de sus procesos."
        elif not autos:
            res += f"**Oportunidad de mejora:** Automatizar procesos puede ahorrar entre 4–10h/mes. ¿Analizo el ROI del proceso más adecuado?"
        else:
            res += f"**Estado óptimo.** Ahorrando **{horas}h/mes** con automatizaciones. ¿Desea profundizar en algún área?"

        return R(res)

    # ══════════════════════════════════════════════════════════════
    # INTENT: RECOMMENDATIONS
    # ══════════════════════════════════════════════════════════════

    if ci.intent == Intent.RECOMMENDATIONS:
        props = []

        if not procesos:
            props.append(
                "**1. Mapear procesos clave**\n"
                "   → Diga *«crea un proceso de [nombre]»* para cada proceso relevante de su empresa."
            )
        else:
            criticos_ord = sorted([p for p in scores if p.score < 60], key=lambda x: x.score)
            for i, p in enumerate(criticos_ord[:3], 1):
                kb = _kb_lookup(p.nombre)
                rec = f"Revisar cuellos de botella"
                if kb:
                    rec = f"Automatizar con {kb['herramienta']} → ahorro estimado {kb['ahorro_h']}h/mes"
                props.append(
                    f"**{i}. Optimizar proceso *{p.nombre}*** (score {p.score}/100 — {'crítico' if p.score<40 else 'mejorable'})\n"
                    f"   → {rec}"
                )

        if not autos and procesos:
            best = procesos[0]
            kb = _kb_lookup(best.nombre)
            hint = f" Estimación: {kb['ahorro_h']}h/mes con {kb['herramienta']}." if kb else ""
            props.append(
                f"**Primera automatización** → *{best.nombre}*\n"
                f"   →{hint} Diga *«crea una automatización de {best.nombre}»*."
            )

        if not kpis and procesos:
            props.append(
                "**Definir KPIs de control**\n"
                "   → Sin indicadores no hay mejora medible. Diga *«crea un KPI de [nombre]»*."
            )

        if not props:
            horas = sum(a.horas_mes or 0 for a in autos)
            props = [
                f"✅ **Empresa bien gestionada** — {horas}h/mes ahorradas con automatizaciones.\n"
                f"   → Para seguir progresando: asigne scores a todos los procesos y defina objetivos en los KPIs."
            ]

        return R("## 💡 Plan de acción recomendado\n\n" + "\n\n".join(props))

    # ══════════════════════════════════════════════════════════════
    # INTENT: UNKNOWN — fallback inteligente con contexto
    # ══════════════════════════════════════════════════════════════

    # 1. Si el texto menciona un nombre que existe como proceso → actuar sobre él
    for p in procesos:
        if p.nombre.lower() in lower or any(w in lower for w in p.nombre.lower().split()):
            return R(
                f"¿Te refieres a **{p.nombre}**? Puedo: analizarlo, calcular su ROI, "
                f"actualizar el score o crear una automatización. ¿Qué prefieres?"
            )

    # 2. Si hay un mem_proceso activo → preguntar qué hacer con él
    if mem_proceso:
        return R(
            f"No he entendido bien. ¿Qué quieres hacer con **{mem_proceso.nombre}**? "
            f"Opciones: analizar, ROI, actualizar score, o crear automatización."
        )

    # 3. Fallback con next_step y variantes
    ns = _next_step(procesos, kpis, autos, mem_proceso, mem)
    return R(_r(
        f"No he captado la intención. {ns}",
        f"No he interpretado correctamente la solicitud. {ns}",
        f"Disculpe, no he entendido bien. {ns}",
        f"No he captado qué necesitas. {ns}",
        f"No he podido procesar esa instrucción. {ns}",
        f"Hmm, no he entendido eso. {ns}",
    ))


# ─────────────────────────────────────────────────────────────────
# UTILIDADES
# ─────────────────────────────────────────────────────────────────

def _parse_float(s: str) -> Optional[float]:
    try:
        return float(str(s).replace(",", "."))
    except (ValueError, TypeError):
        return None
