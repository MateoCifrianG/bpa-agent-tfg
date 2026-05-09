"""
motor_v6.py — Motor razonador BPA-Agent v6
Motor propio hipercargado con base de conocimiento sectorial.
Ollama solo para peticiones genuinamente creativas/abiertas (~5%).
"""

from __future__ import annotations

import json
import logging
import random
import re
from typing import Any, Optional

from sqlalchemy import select, func
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.proceso import Proceso
from app.models.kpi import KPI
from app.models.automatizacion import Automatizacion
from app.models.empresa import Empresa

from app.agents.motor_v6_kb import (
    SECTORES,
    INTENT_PATTERNS,
    RESPUESTAS,
    ENTITY_PATTERNS,
    ROI_CONFIG,
    calcular_roi,
    calcular_score,
    detectar_sector,
    detectar_nombre_proceso,
)

log = logging.getLogger(__name__)

# ──────────────────────────────────────────────────────────────────────────────
# INTENTS QUE REQUIEREN OLLAMA (solo creativas / ultra-complejas)
# ──────────────────────────────────────────────────────────────────────────────

_OLLAMA_TRIGGERS = [
    r"\bescríbeme\b",
    r"\bredacta\s+(?:un|una|el|la)\b",
    r"\bcrea\s+una?\s+(?:propuesta|presentación|informe\s+completo|plan\s+estratégico)\b",
    r"\bexplícame\s+(?:en\s+detalle|con\s+profundidad|a\s+fondo)\b",
    r"\bqué\s+opinas\b",
    r"\bconsejo\s+estratégico\b",
    r"\bcómo\s+debería\s+(?:enfocar|diseñar|plantear|abordar)\b",
    r"\bcuéntame\s+sobre\b",
    r"\bhistoria\s+de\b",
    r"\bredactar\b.*\b(?:propuesta|email\s+de\s+presentación|informe)\b",
]


def _needs_ollama(texto: str, intent: str, confidence: float) -> bool:
    if confidence < 0.25 and len(texto.split()) > 8:
        for pat in _OLLAMA_TRIGGERS:
            if re.search(pat, texto, re.I):
                return True
    return False


# ──────────────────────────────────────────────────────────────────────────────
# CONTEXT MANAGER
# ──────────────────────────────────────────────────────────────────────────────

class ContextManager:
    """Analiza el historial reciente y extrae el estado de la conversación."""

    _PENDING_MARKERS = {
        "esperando_nombre_proceso": [
            "¿cómo se llama", "¿qué nombre", "dime el nombre", "¿cuál es el nombre",
            "¿cómo quieres llamar",
        ],
        "esperando_confirmacion": [
            "¿confirmas", "¿quieres que", "¿procedo", "¿lo creo", "¿te parece bien",
            "¿confirmar", "¿deseas continuar",
        ],
        "esperando_email_destino": [
            "¿a qué email", "¿cuál es el email", "¿email del destinatario", "¿a quién",
        ],
        "esperando_asunto": [
            "¿cuál es el asunto", "¿qué asunto", "el asunto del email",
        ],
        "esperando_cuerpo_email": [
            "¿qué quieres decirle", "¿qué mensaje", "¿qué le escribo",
            "¿cuál es el cuerpo", "el contenido del email",
        ],
        "esperando_nombre_kpi": [
            "¿qué kpi", "¿cómo se llama el kpi", "¿nombre del indicador",
        ],
        "esperando_valor_kpi": [
            "¿cuál es el valor", "¿valor actual", "el valor del kpi",
        ],
    }

    def __init__(self, historial: list[dict]):
        self.historial = historial
        self.pending = self._detect_pending()
        self.recent_entities = self._extract_recent_entities()

    def _detect_pending(self) -> dict | None:
        for msg in reversed(self.historial[:-1]):
            if msg["role"] == "assistant":
                content = msg["content"].lower()
                for tipo, markers in self._PENDING_MARKERS.items():
                    if any(m in content for m in markers):
                        return {"tipo": tipo, "msg": msg["content"]}
                break
        return None

    def _extract_recent_entities(self) -> dict:
        entities: dict = {}
        window = self.historial[-8:]
        combined = " ".join(m["content"] for m in window)
        m = ENTITY_PATTERNS["email"].search(combined)
        if m:
            entities["email"] = m.group()
        return entities

    def last_assistant(self) -> str | None:
        for m in reversed(self.historial[:-1]):
            if m["role"] == "assistant":
                return m["content"]
        return None

    def recent_user_text(self, n: int = 4) -> str:
        texts = [m["content"] for m in self.historial if m["role"] == "user"][-n:]
        return " ".join(texts)


# ──────────────────────────────────────────────────────────────────────────────
# INTENT CLASSIFIER
# ──────────────────────────────────────────────────────────────────────────────

class IntentClassifier:
    def classify(self, texto: str, ctx: ContextManager) -> tuple[str, float]:
        texto_lower = texto.lower().strip()
        best_intent = "no_entendido"
        best_score = 0.0

        for pdef in INTENT_PATTERNS:
            intent = pdef["intent"]
            peso = pdef["peso"]
            for patron in pdef["patrones"]:
                if re.search(patron, texto_lower, re.I):
                    if peso > best_score:
                        best_score = peso
                        best_intent = intent
                    break

        # Si hay estado pendiente, los confirms/cancels tienen prioridad
        if ctx.pending:
            if best_intent == "confirmar":
                return "confirmar", 1.0
            if best_intent == "cancelar":
                return "cancelar", 1.0
            # Si espera nombre y usuario escribe algo corto sin intent claro → tratar como nombre
            if ctx.pending["tipo"] in ("esperando_nombre_proceso", "esperando_nombre_kpi"):
                if best_intent == "no_entendido" or (best_score < 0.5 and len(texto.split()) <= 6):
                    return "input_nombre", 0.8
            if ctx.pending["tipo"] == "esperando_valor_kpi":
                if re.search(r'\d', texto):
                    return "input_valor", 0.8
            if ctx.pending["tipo"] == "esperando_email_destino":
                if ENTITY_PATTERNS["email"].search(texto):
                    return "input_email_destino", 0.9
            if ctx.pending["tipo"] == "esperando_asunto":
                if best_intent == "no_entendido":
                    return "input_asunto", 0.8
            if ctx.pending["tipo"] == "esperando_cuerpo_email":
                if best_intent == "no_entendido":
                    return "input_cuerpo", 0.8

        # Desambiguación: "cuánto me ahorraría automatizar X" → calcular_roi, no crear_automatizacion
        if best_intent == "crear_automatizacion" and re.search(
            r'\b(?:cu[aá]nto|ahorro|ahorr[aío]\w*|roi|retorno|rentabilidad|compensa|payback)\b',
            texto_lower,
        ):
            best_intent = "calcular_roi"
            best_score = 0.9

        return best_intent, best_score


# ──────────────────────────────────────────────────────────────────────────────
# ENTITY EXTRACTOR
# ──────────────────────────────────────────────────────────────────────────────

class EntityExtractor:
    def extract(self, texto: str, ctx: ContextManager) -> dict:
        entities: dict = {}
        # Email
        m = ENTITY_PATTERNS["email"].search(texto)
        if m:
            entities["email"] = m.group()
        elif ctx.recent_entities.get("email"):
            entities["email_contexto"] = ctx.recent_entities["email"]
        # Hora
        m = ENTITY_PATTERNS["hora"].search(texto)
        if m:
            entities["hora"] = m.group()
        # Fecha
        m = ENTITY_PATTERNS["fecha_relativa"].search(texto)
        if m:
            entities["fecha"] = m.group()
        else:
            m = ENTITY_PATTERNS["fecha_absoluta"].search(texto)
            if m:
                entities["fecha"] = m.group()
        # Número de horas
        m = re.search(r'(\d+(?:[.,]\d+)?)\s*(?:horas?|h)\b', texto, re.I)
        if m:
            entities["horas"] = float(m.group(1).replace(",", "."))
        # Porcentaje
        m = ENTITY_PATTERNS["porcentaje"].search(texto)
        if m:
            entities["porcentaje"] = float(m.group(1).replace(",", "."))
        # Sector
        sector = detectar_sector(texto)
        if sector:
            entities["sector"] = sector
        return entities


# ──────────────────────────────────────────────────────────────────────────────
# ACTION EXECUTOR — operaciones sobre la BD
# ──────────────────────────────────────────────────────────────────────────────

class ActionExecutor:

    async def listar_procesos(self, empresa_id: str, db: AsyncSession) -> list[Proceso]:
        r = await db.execute(
            select(Proceso).where(Proceso.empresa_id == empresa_id).order_by(Proceso.nombre)
        )
        return r.scalars().all()

    async def get_proceso_by_nombre(self, nombre: str, empresa_id: str, db: AsyncSession) -> Proceso | None:
        r = await db.execute(
            select(Proceso).where(
                Proceso.empresa_id == empresa_id,
                func.lower(Proceso.nombre).contains(nombre.lower()),
            )
        )
        return r.scalars().first()

    async def crear_proceso(
        self, nombre: str, empresa_id: str, db: AsyncSession,
        descripcion: str | None = None, responsable: str | None = None,
        duracion_h: int | None = None, sector: str | None = None,
    ) -> Proceso:
        # Auto-descripción desde KB si hay sector y el nombre coincide
        if not descripcion and sector and sector in SECTORES:
            kb = SECTORES[sector]
            for p in kb["procesos_tipicos"]:
                if nombre.lower() in p.lower() or p.lower() in nombre.lower():
                    descripcion = f"Proceso de {p.lower()} del sector {sector}."
                    break
        if not duracion_h and sector and sector in SECTORES:
            duracion_h = SECTORES[sector]["roi_horas_mes"]

        proceso_data = {
            "responsable": responsable,
            "descripcion": descripcion,
            "kpis_count": 0,
            "autos_count": 0,
            "kpis_en_target": False,
        }
        score, _ = calcular_score(proceso_data)

        p = Proceso(
            empresa_id=empresa_id,
            nombre=nombre,
            descripcion=descripcion,
            responsable=responsable,
            duracion_h=duracion_h,
            score=score,
            estado="pendiente",
        )
        db.add(p)
        await db.flush()
        await db.refresh(p)
        return p

    async def listar_kpis(self, empresa_id: str, db: AsyncSession, proceso_id: str | None = None) -> list[KPI]:
        q = select(KPI).where(KPI.empresa_id == empresa_id)
        if proceso_id:
            q = q.where(KPI.proceso_id == proceso_id)
        r = await db.execute(q.order_by(KPI.nombre))
        return r.scalars().all()

    async def crear_kpi(
        self, nombre: str, valor: str, empresa_id: str, db: AsyncSession,
        proceso_id: str | None = None, unidad: str | None = None,
        objetivo: str | None = None, categoria: str | None = None,
    ) -> KPI:
        kpi = KPI(
            empresa_id=empresa_id,
            proceso_id=proceso_id,
            nombre=nombre,
            valor=str(valor),
            objetivo=objetivo,
            unidad=unidad,
            categoria=categoria or "volumen",
            tendencia="flat",
        )
        db.add(kpi)
        await db.flush()
        await db.refresh(kpi)
        return kpi

    async def listar_automatizaciones(self, empresa_id: str, db: AsyncSession) -> list[Automatizacion]:
        r = await db.execute(
            select(Automatizacion).where(Automatizacion.empresa_id == empresa_id)
            .order_by(Automatizacion.nombre)
        )
        return r.scalars().all()

    async def crear_automatizacion(
        self, nombre: str, empresa_id: str, db: AsyncSession,
        descripcion: str | None = None, proceso_id: str | None = None,
        tipo_accion: str = "webhook_out", horas_mes: int | None = None,
    ) -> Automatizacion:
        a = Automatizacion(
            empresa_id=empresa_id,
            proceso_id=proceso_id,
            nombre=nombre,
            descripcion=descripcion,
            tipo_accion=tipo_accion,
            estado="pendiente",
            horas_mes=horas_mes,
        )
        db.add(a)
        await db.flush()
        await db.refresh(a)
        return a

    async def get_stats(self, empresa_id: str, db: AsyncSession) -> dict:
        proc_count = (await db.execute(
            select(func.count()).where(Proceso.empresa_id == empresa_id)
        )).scalar_one()
        kpi_count = (await db.execute(
            select(func.count()).where(KPI.empresa_id == empresa_id)
        )).scalar_one()
        auto_count = (await db.execute(
            select(func.count()).where(Automatizacion.empresa_id == empresa_id)
        )).scalar_one()
        return {"procesos": proc_count, "kpis": kpi_count, "automatizaciones": auto_count}


# ──────────────────────────────────────────────────────────────────────────────
# RESPONSE GENERATOR — respuestas naturales y variadas
# ──────────────────────────────────────────────────────────────────────────────

class ResponseGenerator:

    def pick(self, key: str, **kwargs) -> str:
        options = RESPUESTAS.get(key, RESPUESTAS["no_entendido"])
        template = random.choice(options)
        if kwargs:
            try:
                return template.format(**kwargs)
            except KeyError:
                return template
        return template

    def format_procesos(self, procesos: list[Proceso], empresa: Empresa) -> str:
        if not procesos:
            return (
                "Todavía no tienes procesos registrados. "
                "Dime algo como *\"crea un proceso de facturación\"* y lo registro ahora mismo."
            )
        lines = [f"📋 **Procesos de {empresa.nombre}** ({len(procesos)} registrados)\n"]
        for p in procesos:
            score_str = f"Score: {p.score}/100" if p.score is not None else "Sin puntuar"
            estado_emoji = {"pendiente": "🔵", "analizado": "🟡", "critico": "🔴", "optimizado": "🟢"}.get(p.estado or "", "⚪")
            lines.append(
                f"{estado_emoji} **{p.nombre}** — {score_str}"
                + (f" · Responsable: {p.responsable}" if p.responsable else "")
            )
        lines.append("\n¿Quieres que analice alguno en profundidad o que te recomiende automatizaciones?")
        return "\n".join(lines)

    def format_analisis_proceso(
        self, proceso: Proceso, kpis: list[KPI], autos: list[Automatizacion],
        sector: str | None = None,
    ) -> str:
        score, mejoras = calcular_score({
            "responsable": proceso.responsable,
            "descripcion": proceso.descripcion,
            "kpis_count": len(kpis),
            "autos_count": len(autos),
            "kpis_en_target": False,
        })

        # Actualizar score en el objeto (se guardará fuera)
        proceso.score = score

        estado_emoji = {"pendiente": "🔵", "analizado": "🟡", "critico": "🔴", "optimizado": "🟢"}.get(proceso.estado or "", "⚪")
        lines = [
            f"## 🔍 Análisis: **{proceso.nombre}** {estado_emoji}\n",
            f"**Score:** {score}/100 {'⭐⭐⭐' if score >= 80 else '⭐⭐' if score >= 50 else '⭐'}",
        ]

        if proceso.descripcion:
            lines.append(f"**Descripción:** {proceso.descripcion}")
        if proceso.responsable:
            lines.append(f"**Responsable:** {proceso.responsable}")
        if proceso.duracion_h:
            lines.append(f"**Carga:** ~{proceso.duracion_h}h/mes")

        # KPIs
        if kpis:
            lines.append(f"\n**KPIs ({len(kpis)}):**")
            for k in kpis[:5]:
                lines.append(f"  • {k.nombre}: **{k.valor}** {k.unidad or ''}")
        else:
            lines.append("\n⚠️ Sin KPIs definidos")

        # Benchmarks de sector
        if sector and sector in SECTORES:
            kb = SECTORES[sector]
            nombre_lower = proceso.nombre.lower()
            sector_kpis = kb["kpis"]
            relevant = {k: v for k, v in sector_kpis.items()
                        if any(w in nombre_lower for w in k.lower().split()[:2])}
            if not relevant:
                relevant = dict(list(sector_kpis.items())[:3])
            if relevant:
                lines.append(f"\n**Benchmarks sector {sector}:**")
                lines.append("| KPI | Tu objetivo | Bueno | A mejorar |")
                lines.append("|-----|------------|-------|-----------|")
                for kname, kdata in relevant.items():
                    bueno = f"{kdata['benchmark_bueno']} {kdata['unidad']}"
                    malo = f"{kdata['benchmark_malo']} {kdata['unidad']}"
                    lines.append(f"| {kname} | — | {bueno} | {malo} |")

        # Automatizaciones activas
        if autos:
            lines.append(f"\n**Automatizaciones ({len(autos)}):**")
            for a in autos[:3]:
                est = {"activa": "✅", "pendiente": "🔵", "pausada": "⏸", "error": "❌"}.get(a.estado, "⚪")
                lines.append(f"  {est} {a.nombre}")

        # Mejoras
        if mejoras:
            lines.append("\n**Para mejorar el score:**")
            for m in mejoras:
                lines.append(f"  📌 {m}")

        # Automatizaciones recomendadas del sector
        if sector and sector in SECTORES:
            sugs = SECTORES[sector]["automatizaciones"]
            lines.append(f"\n**Automatizaciones recomendadas para {sector}:**")
            for s in sugs[:4]:
                lines.append(f"  ⚡ {s}")

        lines.append("\n¿Quieres que calcule el ROI de automatizarlo, cree algún KPI o configure una automatización?")
        return "\n".join(lines)

    def format_roi(self, proceso_nombre: str, horas_mes: float, roi: dict, sector: str | None = None) -> str:
        viable_str = "✅ **Viable**" if roi["viable"] else "⚠️ Payback largo"
        lines = [
            f"## 💰 ROI — Automatización de **{proceso_nombre}**\n",
            f"| Concepto | Valor |",
            f"|----------|-------|",
            f"| Horas ahorradas/mes | {horas_mes:.0f} h |",
            f"| Ahorro mensual | {roi['ahorro_mes']:,.0f} € |",
            f"| Ahorro anual | {roi['ahorro_anual']:,.0f} € |",
            f"| Coste implementación | {roi['coste_implementacion']:,.0f} € |",
            f"| Beneficio neto (12 meses) | {roi['beneficio_neto_anual']:,.0f} € |",
            f"| ROI | **{roi['roi_pct']:.1f}%** |",
            f"| Payback | {roi['payback_meses']:.1f} meses |",
            f"\n{viable_str} — Payback en {roi['payback_meses']:.1f} meses.",
        ]
        if sector and sector in SECTORES:
            puntos = SECTORES[sector]["puntos_dolor"]
            lines.append(f"\n**Problemas típicos en {sector} que resuelve:**")
            for p in puntos[:3]:
                lines.append(f"  🔴 {p}")
        lines.append("\n¿Quieres que configure la automatización ahora?")
        return "\n".join(lines)

    def format_kpis_recomendados(self, sector: str, empresa: Empresa) -> str:
        if sector not in SECTORES:
            return f"No tengo benchmarks específicos para el sector '{sector}'. Prueba con: logística, RRHH, finanzas, ventas, tecnología."
        kb = SECTORES[sector]
        lines = [
            f"## 📊 KPIs recomendados — Sector **{sector.capitalize()}**\n",
            f"Basado en benchmarks del sector para {empresa.nombre}:\n",
            "| KPI | Benchmark bueno | A mejorar | Unidad |",
            "|-----|----------------|-----------|--------|",
        ]
        for nombre, datos in kb["kpis"].items():
            lines.append(
                f"| {nombre} | {datos['benchmark_bueno']} | {datos['benchmark_malo']} | {datos['unidad']} |"
            )
        lines.append(f"\n¿Quieres que cree alguno de estos KPIs para tu empresa?")
        return "\n".join(lines)

    def format_automatizaciones(self, autos: list[Automatizacion], empresa: Empresa) -> str:
        if not autos:
            return (
                "No tienes automatizaciones configuradas todavía. "
                "Puedo crear una ahora mismo. ¿Sobre qué proceso?"
            )
        activas = sum(1 for a in autos if a.estado == "activa")
        horas_total = sum(a.horas_mes or 0 for a in autos if a.estado == "activa")
        lines = [
            f"⚡ **Automatizaciones de {empresa.nombre}** — {len(autos)} total ({activas} activas)\n"
        ]
        if horas_total:
            lines.append(f"💰 Ahorro estimado: **{horas_total}h/mes** = **{horas_total * ROI_CONFIG['coste_hora_media']:,.0f}€/mes**\n")
        for a in autos[:8]:
            est = {"activa": "✅", "pendiente": "🔵", "pausada": "⏸", "error": "❌"}.get(a.estado, "⚪")
            lines.append(f"{est} **{a.nombre}**" + (f" · {a.horas_mes}h/mes" if a.horas_mes else ""))
        if len(autos) > 8:
            lines.append(f"... y {len(autos) - 8} más.")
        return "\n".join(lines)

    def format_sector_info(self, sector: str) -> str:
        if sector not in SECTORES:
            sectores_list = ", ".join(SECTORES.keys())
            return f"No tengo datos para '{sector}'. Sectores disponibles: {sectores_list}."
        kb = SECTORES[sector]
        lines = [
            f"## 🏭 Sector **{sector.capitalize()}**\n",
            "**Procesos típicos:**",
        ]
        for p in kb["procesos_tipicos"][:5]:
            lines.append(f"  • {p}")
        lines.append(f"\n**Potencial de ahorro:** ~{kb['roi_horas_mes']}h/mes = "
                     f"**{kb['roi_horas_mes'] * ROI_CONFIG['coste_hora_media']:,.0f}€/mes**\n")
        lines.append("**Principales automatizaciones:**")
        for a in kb["automatizaciones"][:4]:
            lines.append(f"  ⚡ {a}")
        lines.append("\n¿Quieres ver los KPIs de este sector o calcular el ROI de algún proceso?")
        return "\n".join(lines)

    def format_kpis_lista(self, kpis: list[KPI], empresa: Empresa) -> str:
        if not kpis:
            return "No tienes KPIs registrados. ¿Quieres que te recomiende los más importantes para tu sector?"
        lines = [f"📈 **KPIs de {empresa.nombre}** ({len(kpis)} indicadores)\n"]
        for k in kpis[:10]:
            tendencia = {"up": "📈", "down": "📉", "flat": "➡️"}.get(k.tendencia or "flat", "➡️")
            obj_str = f" / obj: {k.objetivo}" if k.objetivo else ""
            lines.append(
                f"{tendencia} **{k.nombre}**: {k.valor} {k.unidad or ''}{obj_str}"
            )
        if len(kpis) > 10:
            lines.append(f"... y {len(kpis) - 10} más.")
        return "\n".join(lines)

    def format_info_empresa(self, empresa: Empresa, stats: dict) -> str:
        sector_info = ""
        if empresa.sector and empresa.sector in SECTORES:
            kb = SECTORES[empresa.sector]
            potencial = kb["roi_horas_mes"] * ROI_CONFIG["coste_hora_media"]
            sector_info = f"\n**Potencial sector {empresa.sector}:** ~{potencial:,.0f}€/mes en ahorro"
        return (
            f"## 🏢 {empresa.nombre}\n\n"
            f"**Sector:** {empresa.sector or 'No definido'}\n"
            f"**Procesos registrados:** {stats['procesos']}\n"
            f"**KPIs:** {stats['kpis']}\n"
            f"**Automatizaciones:** {stats['automatizaciones']}"
            f"{sector_info}\n\n"
            "¿Quieres que analice tu situación actual o te recomiende por dónde empezar?"
        )


# ──────────────────────────────────────────────────────────────────────────────
# OLLAMA CALLER — solo para peticiones realmente complejas
# ──────────────────────────────────────────────────────────────────────────────

async def _llamar_ollama(mensaje: str, historial: list[dict]) -> str | None:
    try:
        import httpx
        messages = [
            {"role": m["role"], "content": m["content"]}
            for m in historial[-6:]
        ]
        payload = {
            "model": "llama3.1:8b",
            "messages": messages,
            "stream": False,
            "options": {"temperature": 0.7, "num_predict": 600},
        }
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post("http://localhost:11434/api/chat", json=payload)
            if r.status_code == 200:
                data = r.json()
                return data.get("message", {}).get("content", "").strip()
    except Exception as e:
        log.debug("Ollama no disponible: %s", e)
    return None


# ──────────────────────────────────────────────────────────────────────────────
# MOTOR PRINCIPAL
# ──────────────────────────────────────────────────────────────────────────────

_classifier = IntentClassifier()
_extractor = EntityExtractor()
_executor = ActionExecutor()
_respgen = ResponseGenerator()


async def responder(
    mensaje: str,
    empresa: Empresa,
    db: AsyncSession,
    historial: list[dict],
) -> dict:
    """
    Punto de entrada principal del motor v6.
    Devuelve dict con: respuesta, accion, entidad
    """
    ctx = ContextManager(historial)
    entities = _extractor.extract(mensaje, ctx)
    intent, confidence = _classifier.classify(mensaje, ctx)

    log.debug("v6 intent=%s conf=%.2f entities=%s", intent, confidence, entities)

    accion: str | None = None
    entidad: Any | None = None
    respuesta = ""

    # ── Carga inicial de datos comunes ────────────────────────────────────────
    empresa_sector = empresa.sector or entities.get("sector")

    try:
        # ── SALUDOS Y META ────────────────────────────────────────────────────
        if intent == "saludo":
            stats = await _executor.get_stats(empresa.id, db)
            if stats["procesos"] > 0:
                respuesta = (
                    f"¡Hola! Tienes {stats['procesos']} procesos y {stats['automatizaciones']} "
                    f"automatizaciones registradas. ¿Qué quieres revisar hoy?"
                )
            else:
                respuesta = _respgen.pick("saludo")

        elif intent == "despedida":
            respuesta = _respgen.pick("despedida")

        elif intent == "agradecimiento":
            respuesta = _respgen.pick("agradecimiento")

        elif intent == "ayuda":
            respuesta = _respgen.pick("ayuda")

        # ── PROCESOS ──────────────────────────────────────────────────────────
        elif intent == "listar_procesos":
            procesos = await _executor.listar_procesos(empresa.id, db)
            respuesta = _respgen.format_procesos(procesos, empresa)
            accion = "listar_procesos"

        elif intent == "crear_proceso":
            # Intenta extraer nombre del mensaje
            procesos_existentes = [p.nombre for p in await _executor.listar_procesos(empresa.id, db)]
            nombre_detectado = _extraer_nombre_proceso(mensaje, entities)

            if nombre_detectado:
                proceso = await _executor.crear_proceso(
                    nombre=nombre_detectado,
                    empresa_id=empresa.id,
                    db=db,
                    sector=empresa_sector,
                )
                await db.commit()
                respuesta = _respgen.pick(
                    "confirmacion_crear_proceso",
                    nombre=proceso.nombre,
                    score=proceso.score or 0,
                )
                accion = "crear_proceso"
                entidad = proceso.id
            else:
                respuesta = "¿Cómo quieres llamar al nuevo proceso? Dime el nombre."

        elif intent == "analizar_proceso":
            procesos = await _executor.listar_procesos(empresa.id, db)
            nombres = [p.nombre for p in procesos]
            nombre_buscado = detectar_nombre_proceso(mensaje, nombres) or detectar_nombre_proceso(
                ctx.recent_user_text(), nombres
            )
            if nombre_buscado:
                proceso = await _executor.get_proceso_by_nombre(nombre_buscado, empresa.id, db)
                if proceso:
                    kpis = await _executor.listar_kpis(empresa.id, db, proceso.id)
                    autos_r = await db.execute(
                        select(Automatizacion).where(
                            Automatizacion.empresa_id == empresa.id,
                            Automatizacion.proceso_id == proceso.id,
                        )
                    )
                    autos = autos_r.scalars().all()
                    sector = empresa_sector or detectar_sector(proceso.nombre + " " + (proceso.descripcion or ""))
                    respuesta = _respgen.format_analisis_proceso(proceso, kpis, autos, sector)
                    await db.commit()
                    accion = "analizar_proceso"
                    entidad = proceso.id
                else:
                    respuesta = f"No encuentro el proceso '{nombre_buscado}'. ¿Cuál quieres analizar?"
            elif procesos:
                lista = "\n".join(f"  • {p.nombre}" for p in procesos[:8])
                respuesta = f"¿Cuál de estos procesos quieres analizar?\n{lista}"
            else:
                respuesta = "No tienes procesos registrados aún. ¿Quieres que creemos uno?"

        # ── KPIs ──────────────────────────────────────────────────────────────
        elif intent == "listar_kpis":
            kpis = await _executor.listar_kpis(empresa.id, db)
            respuesta = _respgen.format_kpis_lista(kpis, empresa)
            accion = "listar_kpis"

        elif intent == "recomendar_kpis":
            sector = entities.get("sector") or empresa_sector
            if sector:
                respuesta = _respgen.format_kpis_recomendados(sector, empresa)
            else:
                sectores_list = ", ".join(list(SECTORES.keys())[:6])
                respuesta = (
                    f"Para recomendarte KPIs necesito saber tu sector. "
                    f"Disponibles: {sectores_list}. ¿Cuál es el tuyo?"
                )

        elif intent == "crear_kpi":
            nombre_kpi = _extraer_nombre_kpi(mensaje)
            if nombre_kpi:
                valor_str = _extraer_valor(mensaje) or "0"
                unidad = _extraer_unidad(mensaje)
                kpi = await _executor.crear_kpi(
                    nombre=nombre_kpi, valor=valor_str,
                    empresa_id=empresa.id, db=db, unidad=unidad,
                )
                await db.commit()
                # Buscar benchmark si hay sector
                bench_str = _benchmark_compare(nombre_kpi, valor_str, unidad, empresa_sector)
                respuesta = _respgen.pick(
                    "confirmacion_crear_kpi",
                    nombre=kpi.nombre,
                    valor=kpi.valor,
                    unidad=kpi.unidad or "",
                    comparativa_benchmark=bench_str,
                )
                accion = "crear_kpi"
                entidad = kpi.id
            else:
                respuesta = "¿Cómo se llama el KPI que quieres crear? (ej: 'Tasa de entrega a tiempo')"

        # ── ROI ───────────────────────────────────────────────────────────────
        elif intent == "calcular_roi":
            procesos = await _executor.listar_procesos(empresa.id, db)
            nombres = [p.nombre for p in procesos]
            nombre_p = detectar_nombre_proceso(mensaje, nombres) or detectar_nombre_proceso(
                ctx.recent_user_text(), nombres
            )
            sector = entities.get("sector") or empresa_sector

            horas = entities.get("horas")
            if not horas:
                # Buscar en proceso o en KB
                if nombre_p:
                    p_obj = await _executor.get_proceso_by_nombre(nombre_p, empresa.id, db)
                    horas = float(p_obj.duracion_h or 0) if p_obj else None
                if not horas and sector and sector in SECTORES:
                    horas = float(SECTORES[sector]["roi_horas_mes"])
                if not horas:
                    horas = 20.0

            roi = calcular_roi(horas)
            proceso_nombre = nombre_p or (sector or "el proceso seleccionado")
            respuesta = _respgen.format_roi(proceso_nombre, horas, roi, sector)
            accion = "calcular_roi"

        # ── AUTOMATIZACIONES ──────────────────────────────────────────────────
        elif intent == "listar_automatizaciones":
            autos = await _executor.listar_automatizaciones(empresa.id, db)
            respuesta = _respgen.format_automatizaciones(autos, empresa)
            accion = "listar_automatizaciones"

        elif intent == "automatizar_proceso":
            sector = entities.get("sector") or empresa_sector
            procesos = await _executor.listar_procesos(empresa.id, db)
            nombres = [p.nombre for p in procesos]
            nombre_p = detectar_nombre_proceso(mensaje, nombres)

            if nombre_p:
                proceso = await _executor.get_proceso_by_nombre(nombre_p, empresa.id, db)
                sector_proc = sector or (detectar_sector(nombre_p) if nombre_p else None)
                sugs = SECTORES.get(sector_proc or "", {}).get("automatizaciones", [])[:4] if sector_proc else []
                lines = [f"⚡ **Automatizaciones recomendadas para {nombre_p}:**\n"]
                if sugs:
                    for s in sugs:
                        lines.append(f"  • {s}")
                else:
                    lines.append("  • Notificación automática de estado")
                    lines.append("  • Informe periódico automatizado")
                    lines.append("  • Alerta ante desviaciones de KPIs")
                lines.append("\n¿Quieres que configure alguna de estas automatizaciones?")
                respuesta = "\n".join(lines)
                accion = "sugerir_automatizaciones"
                entidad = proceso.id if proceso else None
            elif sector and sector in SECTORES:
                sugs = SECTORES[sector]["automatizaciones"]
                lines = [f"⚡ **Automatizaciones recomendadas para {sector}:**\n"]
                for s in sugs:
                    lines.append(f"  • {s}")
                lines.append("\n¿Sobre qué proceso quieres implementarlas?")
                respuesta = "\n".join(lines)
            else:
                respuesta = "¿Para qué proceso o área quieres automatizaciones? (ej: 'facturación', 'RRHH', 'logística')"

        elif intent == "crear_automatizacion":
            nombre_auto = _extraer_nombre_proceso(mensaje, entities) or "Nueva automatización"
            auto = await _executor.crear_automatizacion(
                nombre=nombre_auto, empresa_id=empresa.id, db=db,
            )
            await db.commit()
            respuesta = (
                f"✅ Automatización **{auto.nombre}** creada en estado *pendiente*. "
                "Ahora puedes configurar el trigger y la acción desde el panel. "
                "¿Quieres que la vincule a algún proceso?"
            )
            accion = "crear_automatizacion"
            entidad = auto.id

        # ── EMAIL / CALENDAR / TELEGRAM ───────────────────────────────────────
        elif intent == "enviar_email":
            email_dest = entities.get("email")
            if email_dest:
                respuesta = (
                    f"Para enviar el email a **{email_dest}** necesito el conector de Gmail activo. "
                    "Ve a *Integraciones* en el panel y conecta tu cuenta de Gmail. "
                    "Una vez activo, podré enviar emails directamente desde aquí."
                )
            else:
                respuesta = "¿A qué email quieres enviar el mensaje? (ej: 'envía un email a nombre@empresa.com')"

        elif intent == "crear_evento_calendar":
            fecha = entities.get("fecha", "próximamente")
            hora = entities.get("hora", "")
            respuesta = (
                f"Para agendar la reunión el **{fecha}**{' a las ' + hora if hora else ''}, "
                "necesito el conector de Google Calendar. "
                "Conéctalo en *Integraciones* y podrás crear eventos directamente desde el chat."
            )

        elif intent == "enviar_telegram":
            respuesta = (
                "Para enviar mensajes por Telegram necesitas configurar el bot en *Integraciones*. "
                "Solo tarda 2 minutos: necesitas el token del bot y el chat ID de destino."
            )

        # ── INFO ──────────────────────────────────────────────────────────────
        elif intent == "estado_sistema":
            stats = await _executor.get_stats(empresa.id, db)
            autos = await _executor.listar_automatizaciones(empresa.id, db)
            activas = sum(1 for a in autos if a.estado == "activa")
            horas_mes = sum(a.horas_mes or 0 for a in autos if a.estado == "activa")
            respuesta = (
                f"## 📊 Estado del sistema\n\n"
                f"✅ Backend operativo\n"
                f"📋 Procesos: **{stats['procesos']}**\n"
                f"📈 KPIs: **{stats['kpis']}**\n"
                f"⚡ Automatizaciones: **{stats['automatizaciones']}** ({activas} activas)\n"
            )
            if horas_mes:
                ahorro = horas_mes * ROI_CONFIG["coste_hora_media"]
                respuesta += f"💰 Ahorro mensual estimado: **{ahorro:,.0f}€**"

        elif intent == "info_empresa":
            stats = await _executor.get_stats(empresa.id, db)
            respuesta = _respgen.format_info_empresa(empresa, stats)

        elif intent == "info_sector":
            sector = entities.get("sector") or empresa_sector
            if sector:
                respuesta = _respgen.format_sector_info(sector)
            else:
                respuesta = (
                    "¿De qué sector quieres información? Tengo benchmarks para: "
                    + ", ".join(list(SECTORES.keys()))
                )

        # ── CONFIRMACIÓN DE ACCIÓN PENDIENTE ──────────────────────────────────
        elif intent == "confirmar" and ctx.pending:
            respuesta = "De acuerdo. ¿Qué nombre le pongo? (escríbelo y lo creo enseguida)"

        elif intent == "cancelar":
            respuesta = "Entendido, lo dejamos. ¿En qué más puedo ayudarte?"

        # ── INPUT EN ESPERA ───────────────────────────────────────────────────
        elif intent == "input_nombre" and ctx.pending:
            tipo = ctx.pending["tipo"]
            if tipo == "esperando_nombre_proceso":
                nombre = mensaje.strip()
                proceso = await _executor.crear_proceso(
                    nombre=nombre, empresa_id=empresa.id, db=db,
                    sector=empresa_sector,
                )
                await db.commit()
                respuesta = _respgen.pick(
                    "confirmacion_crear_proceso",
                    nombre=proceso.nombre,
                    score=proceso.score or 0,
                )
                accion = "crear_proceso"
                entidad = proceso.id

        # ── FALLBACK / NO ENTENDIDO ───────────────────────────────────────────
        else:
            # Intentar con Ollama para preguntas complejas
            if _needs_ollama(mensaje, intent, confidence):
                ollama_resp = await _llamar_ollama(mensaje, historial)
                if ollama_resp:
                    respuesta = ollama_resp
                else:
                    respuesta = _respgen.pick("no_entendido")
            else:
                respuesta = _respgen.pick("no_entendido")

    except Exception as exc:
        log.error("motor_v6 error: %s", exc, exc_info=True)
        respuesta = _respgen.pick("error_general", error=str(exc)[:80])

    return {"respuesta": respuesta, "accion": accion, "entidad": entidad}


# ──────────────────────────────────────────────────────────────────────────────
# HELPERS INTERNOS
# ──────────────────────────────────────────────────────────────────────────────

def _extraer_nombre_proceso(texto: str, entities: dict) -> str | None:
    """Extrae el nombre del proceso del mensaje, eliminando el verbo trigger."""
    triggers = [
        r"(?:crea(?:r)?|registra(?:r)?|añade?|agrega(?:r)?|nuevo\s+proceso\s+(?:de|para|llamado)?|proceso\s+(?:de|para|llamado)?)\s+",
    ]
    limpio = texto.strip()
    for t in triggers:
        limpio = re.sub(t, "", limpio, flags=re.I).strip()
    # Quitar preposiciones iniciales sueltas
    limpio = re.sub(r"^(un|una|el|la|de|para)\s+", "", limpio, flags=re.I).strip()
    # Si queda algo razonable (2-60 chars, no solo stopwords)
    stopwords_solas = {"proceso", "nuevo", "crear", "registrar"}
    if limpio and len(limpio) >= 3 and limpio.lower() not in stopwords_solas:
        return limpio[:100].strip(".,!?")
    return None


def _extraer_nombre_kpi(texto: str) -> str | None:
    m = re.search(
        r"(?:kpi|indicador|métrica)\s+(?:de\s+|del?\s+|llamado\s+|con\s+nombre\s+)?[\"']?([A-Za-záéíóúüñÁÉÍÓÚÜÑ\s%\/]+)[\"']?",
        texto, re.I
    )
    if m:
        return m.group(1).strip()[:100]
    # Nombre tras "crea un KPI: X"
    m = re.search(r":\s*(.{3,80})", texto)
    if m:
        return m.group(1).strip()
    return None


def _extraer_valor(texto: str) -> str | None:
    m = re.search(r'(?:valor|actual|es)[\s:=]+(\d+(?:[.,]\d+)?)', texto, re.I)
    if m:
        return m.group(1).replace(",", ".")
    m = re.search(r'\b(\d+(?:[.,]\d+)?)\s*(?:%|horas?|días?|€|min)\b', texto, re.I)
    if m:
        return m.group(1).replace(",", ".")
    m = re.search(r'\b(\d+(?:[.,]\d+)?)\b', texto)
    if m:
        return m.group(1)
    return None


def _extraer_unidad(texto: str) -> str | None:
    m = re.search(r'\b(\d+(?:[.,]\d+)?)\s*(%|horas?|días?|€|euros?|minutos?|unidades?|puntos?)\b', texto, re.I)
    if m:
        return m.group(2)
    return None


def _benchmark_compare(nombre_kpi: str, valor_str: str, unidad: str | None, sector: str | None) -> str:
    if not sector or sector not in SECTORES:
        return ""
    kb_kpis = SECTORES[sector]["kpis"]
    nombre_lower = nombre_kpi.lower()
    for kname, kdata in kb_kpis.items():
        if any(w in nombre_lower for w in kname.lower().split() if len(w) > 3):
            try:
                val = float(valor_str.replace(",", "."))
                bueno = kdata["benchmark_bueno"]
                malo = kdata["benchmark_malo"]
                unidad_kb = kdata["unidad"]
                # Determinar si bueno = bajo o alto según contexto
                if bueno < malo:  # menor es mejor (ej: DSO, coste)
                    if val <= bueno:
                        return f"✅ Estás en zona excelente para el sector (benchmark: {bueno} {unidad_kb})"
                    elif val <= malo:
                        return f"🟡 Dentro del rango aceptable (benchmark bueno: {bueno} {unidad_kb})"
                    else:
                        return f"🔴 Por encima del valor de mejora del sector ({malo} {unidad_kb})"
                else:  # mayor es mejor (ej: tasa de entrega, satisfacción)
                    if val >= bueno:
                        return f"✅ Excelente, superas el benchmark del sector ({bueno} {unidad_kb})"
                    elif val >= malo:
                        return f"🟡 En rango aceptable (objetivo sector: {bueno} {unidad_kb})"
                    else:
                        return f"🔴 Por debajo del benchmark mínimo ({malo} {unidad_kb})"
            except (ValueError, TypeError):
                pass
    return ""
