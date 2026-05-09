"""
motor_v5.py — BPA-Agent Motor Razonador v5
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
Agente de IA completo con razonamiento LLM via Ollama (gratuito, 100% local).

Arquitectura idéntica a la de los mejores agentes comerciales:
  [1] ContextBuilder  → system prompt rico con estado real de la empresa
  [2] OllamaClient    → LLM local (llama3.1, mistral, qwen2.5, phi4...)
  [3] AgentLoop       → razona → llama herramientas → razona → responde
  [4] ToolExecutor    → ejecuta 11 herramientas BPA en BD async
  [5] ResponseSynth   → respuesta final natural en español

Modelos recomendados (en orden de calidad para este caso de uso):
  ollama pull llama3.1:8b       → mejor calidad (requiere ~8GB RAM)
  ollama pull qwen2.5:7b        → excelente en español (7GB RAM)
  ollama pull mistral:7b-instruct → rápido y capaz (5GB RAM)
  ollama pull phi4:mini          → muy ligero (2GB RAM)
"""

from __future__ import annotations

import json
from typing import Any, Optional

import httpx
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.automatizacion import Automatizacion
from app.models.empresa import Empresa
from app.models.kpi import KPI
from app.models.proceso import Proceso

# ─────────────────────────────────────────────────────────────────
# CONFIGURACIÓN
# ─────────────────────────────────────────────────────────────────

OLLAMA_BASE   = "http://localhost:11434"
OLLAMA_MODEL  = "llama3.1:8b"   # Cambia según tu hardware
OLLAMA_TIMEOUT = 120             # segundos máximos de espera
MAX_ITERATIONS = 8               # máximas llamadas a herramientas por turno
COSTE_HORA     = 25              # €/hora benchmark pyme española

# ─────────────────────────────────────────────────────────────────
# KNOWLEDGE BASE BPM
# ─────────────────────────────────────────────────────────────────

_BPM_KB = {
    "facturación":      {"ahorro_h": 8,  "coste_impl": 500,  "herramienta": "n8n + Google Sheets"},
    "facturacion":      {"ahorro_h": 8,  "coste_impl": 500,  "herramienta": "n8n + Google Sheets"},
    "rrhh":             {"ahorro_h": 6,  "coste_impl": 800,  "herramienta": "Zapier + HR tool"},
    "recursos humanos": {"ahorro_h": 6,  "coste_impl": 800,  "herramienta": "Zapier + HR tool"},
    "email":            {"ahorro_h": 5,  "coste_impl": 200,  "herramienta": "n8n + Gmail API"},
    "correo":           {"ahorro_h": 5,  "coste_impl": 200,  "herramienta": "n8n + Gmail API"},
    "onboarding":       {"ahorro_h": 10, "coste_impl": 1200, "herramienta": "Make + Notion"},
    "inventario":       {"ahorro_h": 7,  "coste_impl": 600,  "herramienta": "n8n + ERP API"},
    "reportes":         {"ahorro_h": 6,  "coste_impl": 400,  "herramienta": "Python + cron"},
    "informes":         {"ahorro_h": 6,  "coste_impl": 400,  "herramienta": "Python + cron"},
    "atención al cliente": {"ahorro_h": 4, "coste_impl": 700, "herramienta": "n8n + CRM"},
    "ventas":           {"ahorro_h": 5,  "coste_impl": 900,  "herramienta": "Zapier + CRM"},
    "contabilidad":     {"ahorro_h": 9,  "coste_impl": 1000, "herramienta": "n8n + ERP"},
    "logística":        {"ahorro_h": 7,  "coste_impl": 800,  "herramienta": "n8n + WMS"},
    "logistica":        {"ahorro_h": 7,  "coste_impl": 800,  "herramienta": "n8n + WMS"},
    "compras":          {"ahorro_h": 5,  "coste_impl": 600,  "herramienta": "Zapier + ERP"},
    "pedidos":          {"ahorro_h": 6,  "coste_impl": 500,  "herramienta": "n8n + e-commerce"},
    "soporte":          {"ahorro_h": 4,  "coste_impl": 700,  "herramienta": "n8n + Zendesk"},
    "marketing":        {"ahorro_h": 5,  "coste_impl": 600,  "herramienta": "Make + Meta API"},
    "nóminas":          {"ahorro_h": 5,  "coste_impl": 500,  "herramienta": "n8n + Sage"},
    "nominas":          {"ahorro_h": 5,  "coste_impl": 500,  "herramienta": "n8n + Sage"},
}

def _kb_lookup(nombre: str) -> Optional[dict]:
    nl = nombre.lower()
    for kw, data in _BPM_KB.items():
        if kw in nl:
            return data
    return None


# ─────────────────────────────────────────────────────────────────
# DEFINICIÓN DE HERRAMIENTAS (formato OpenAI tool use)
# ─────────────────────────────────────────────────────────────────

TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "listar_procesos",
            "description": "Lista todos los procesos de negocio de la empresa con score, estado y responsable. Úsalo cuando el usuario pregunte qué procesos hay o quiera ver el listado.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "crear_proceso",
            "description": "Crea y registra un nuevo proceso de negocio en la base de datos. Úsalo siempre que el usuario pida crear, añadir o registrar un proceso.",
            "parameters": {
                "type": "object",
                "properties": {
                    "nombre":      {"type": "string", "description": "Nombre del proceso (requerido)"},
                    "descripcion": {"type": "string", "description": "Descripción opcional del proceso"},
                    "responsable": {"type": "string", "description": "Nombre de la persona responsable"},
                    "estado":      {"type": "string", "enum": ["pendiente", "activo", "completado"], "description": "Estado inicial (por defecto: pendiente)"},
                    "frecuencia":  {"type": "string", "description": "Frecuencia del proceso: diario, semanal, mensual, etc."},
                },
                "required": ["nombre"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "actualizar_proceso",
            "description": "Actualiza un campo específico de un proceso existente. Úsalo para cambiar score, responsable, estado, descripcion, frecuencia o duracion_h.",
            "parameters": {
                "type": "object",
                "properties": {
                    "nombre": {"type": "string", "description": "Nombre del proceso a actualizar"},
                    "campo":  {"type": "string", "enum": ["score", "responsable", "estado", "descripcion", "frecuencia", "duracion_h"], "description": "Campo a modificar"},
                    "valor":  {"type": "string", "description": "Nuevo valor para el campo"},
                },
                "required": ["nombre", "campo", "valor"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "eliminar_proceso",
            "description": "Elimina permanentemente un proceso de la base de datos. Solo úsalo cuando el usuario confirme explícitamente que quiere eliminar.",
            "parameters": {
                "type": "object",
                "properties": {
                    "nombre": {"type": "string", "description": "Nombre exacto del proceso a eliminar"},
                },
                "required": ["nombre"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "analizar_proceso",
            "description": "Análisis completo de un proceso: score, KPIs vinculados, automatizaciones, benchmark vs otros procesos y recomendaciones de mejora.",
            "parameters": {
                "type": "object",
                "properties": {
                    "nombre": {"type": "string", "description": "Nombre del proceso a analizar"},
                },
                "required": ["nombre"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "calcular_roi",
            "description": "Calcula el ROI (retorno de inversión) de automatizar un proceso. Devuelve ahorro mensual/anual, payback y ROI a 12 meses con herramienta recomendada.",
            "parameters": {
                "type": "object",
                "properties": {
                    "nombre": {"type": "string", "description": "Nombre del proceso para calcular el ROI"},
                },
                "required": ["nombre"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "crear_kpi",
            "description": "Crea un nuevo KPI (indicador de rendimiento) para medir la evolución de un proceso.",
            "parameters": {
                "type": "object",
                "properties": {
                    "nombre":   {"type": "string", "description": "Nombre descriptivo del KPI"},
                    "valor":    {"type": "string", "description": "Valor inicial del KPI"},
                    "unidad":   {"type": "string", "description": "Unidad de medida: %, €, días, unidades, etc."},
                    "proceso":  {"type": "string", "description": "Nombre del proceso al que vincular el KPI (opcional)"},
                    "objetivo": {"type": "string", "description": "Valor objetivo a alcanzar (opcional)"},
                },
                "required": ["nombre"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "listar_kpis",
            "description": "Lista todos los KPIs definidos con su valor actual, tendencia y objetivo.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "crear_automatizacion",
            "description": "Registra una nueva automatización para un proceso. Especifica la herramienta (n8n, Zapier, Make, Python, etc.) y el ahorro en horas/mes.",
            "parameters": {
                "type": "object",
                "properties": {
                    "nombre":    {"type": "string", "description": "Nombre descriptivo de la automatización"},
                    "herramienta": {"type": "string", "description": "Herramienta: n8n, Zapier, Make, Python, Power Automate, etc."},
                    "proceso":   {"type": "string", "description": "Nombre del proceso que automatiza (opcional)"},
                    "horas_mes": {"type": "number", "description": "Horas/mes que ahorra esta automatización"},
                },
                "required": ["nombre"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "listar_automatizaciones",
            "description": "Lista todas las automatizaciones con su estado, herramienta y ahorro en horas.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "resumen_empresa",
            "description": "Resumen ejecutivo completo: métricas de procesos, KPIs, automatizaciones, ahorro total y situación crítica.",
            "parameters": {"type": "object", "properties": {}, "required": []},
        },
    },
    {
        "type": "function",
        "function": {
            "name": "ejecutar_automatizacion",
            "description": "Ejecuta AHORA MISMO una automatización real: envía emails, mensajes de Telegram, webhooks a n8n/Make/Zapier, etc. Úsalo cuando el usuario diga 'ejecuta', 'lanza', 'corre', 'envía ahora', 'manda el email', etc.",
            "parameters": {
                "type": "object",
                "properties": {
                    "nombre": {"type": "string", "description": "Nombre de la automatización a ejecutar"},
                },
                "required": ["nombre"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "configurar_automatizacion_email",
            "description": "Configura una automatización para enviar emails reales. Guarda los parámetros SMTP y el contenido del email en la automatización.",
            "parameters": {
                "type": "object",
                "properties": {
                    "nombre":         {"type": "string", "description": "Nombre de la automatización"},
                    "smtp_preset":    {"type": "string", "enum": ["gmail", "outlook", "yahoo"], "description": "Servidor de correo a usar"},
                    "smtp_user":      {"type": "string", "description": "Email del remitente"},
                    "smtp_password":  {"type": "string", "description": "Contraseña de aplicación SMTP"},
                    "destinatario":   {"type": "string", "description": "Email del destinatario"},
                    "asunto":         {"type": "string", "description": "Asunto del email"},
                    "cuerpo":         {"type": "string", "description": "Cuerpo del email"},
                    "proceso":        {"type": "string", "description": "Proceso asociado (opcional)"},
                },
                "required": ["nombre", "smtp_user", "smtp_password", "destinatario", "asunto", "cuerpo"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "configurar_automatizacion_telegram",
            "description": "Configura una automatización para enviar mensajes de Telegram automáticos. Necesita bot_token y chat_id.",
            "parameters": {
                "type": "object",
                "properties": {
                    "nombre":     {"type": "string", "description": "Nombre de la automatización"},
                    "bot_token":  {"type": "string", "description": "Token del bot de Telegram (de @BotFather)"},
                    "chat_id":    {"type": "string", "description": "ID del chat o canal de Telegram"},
                    "mensaje":    {"type": "string", "description": "Mensaje a enviar (puede incluir HTML)"},
                    "proceso":    {"type": "string", "description": "Proceso asociado (opcional)"},
                },
                "required": ["nombre", "bot_token", "chat_id", "mensaje"],
            },
        },
    },
    # ── INTEGRACIONES EXTERNAS REALES ─────────────────────────────────────
    {
        "type": "function",
        "function": {
            "name": "gmail_enviar",
            "description": "Envía un email REAL via la cuenta Gmail conectada del usuario. Úsalo cuando el usuario diga 'manda un email', 'envía un correo', 'escribe a...', 'notifica a...'. Requiere que Gmail esté conectado en Integraciones.",
            "parameters": {
                "type": "object",
                "properties": {
                    "destinatario": {"type": "string", "description": "Email del destinatario"},
                    "asunto":       {"type": "string", "description": "Asunto del email"},
                    "cuerpo":       {"type": "string", "description": "Cuerpo del email en texto plano"},
                    "cc":           {"type": "string", "description": "Email en CC (opcional)"},
                },
                "required": ["destinatario", "asunto", "cuerpo"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "gmail_leer_bandeja",
            "description": "Lee los emails de la bandeja de Gmail del usuario. Úsalo cuando pregunten '¿tengo emails nuevos?', 'qué hay en mi bandeja', 'emails de hoy', etc.",
            "parameters": {
                "type": "object",
                "properties": {
                    "query":       {"type": "string", "description": "Filtro Gmail: 'is:unread', 'from:cliente@empresa.com', 'subject:factura', etc. Default: 'is:unread'"},
                    "max_results": {"type": "number", "description": "Máximo emails a devolver (default 10)"},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "calendar_crear_evento",
            "description": "Crea un evento REAL en Google Calendar. Úsalo para 'pon una reunión', 'crea un evento', 'agenda una cita', 'bloquea tiempo para...'",
            "parameters": {
                "type": "object",
                "properties": {
                    "titulo":            {"type": "string", "description": "Título del evento"},
                    "inicio":            {"type": "string", "description": "Fecha/hora inicio ISO 8601: '2025-05-15T09:00:00'"},
                    "duracion_minutos":  {"type": "number", "description": "Duración en minutos (default 60)"},
                    "descripcion":       {"type": "string", "description": "Descripción del evento"},
                    "invitados":         {"type": "array", "items": {"type": "string"}, "description": "Lista de emails de invitados"},
                },
                "required": ["titulo", "inicio"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "calendar_ver_eventos",
            "description": "Muestra los próximos eventos del Google Calendar del usuario.",
            "parameters": {
                "type": "object",
                "properties": {
                    "dias": {"type": "number", "description": "Número de días hacia adelante (default 7)"},
                },
                "required": [],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "n8n_trigger_webhook",
            "description": "Dispara un workflow de n8n via webhook. Úsalo para lanzar automatizaciones complejas en n8n cuando el usuario las solicite.",
            "parameters": {
                "type": "object",
                "properties": {
                    "webhook_path": {"type": "string", "description": "Ruta del webhook en n8n (ej: 'mi-flujo', 'facturacion/enviar')"},
                    "datos":        {"type": "object", "description": "Datos a enviar al workflow (opcional)"},
                },
                "required": ["webhook_path"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "notion_crear_pagina",
            "description": "Crea una página en Notion. Úsalo para documentar procesos, guardar informes o añadir registros a bases de datos de Notion.",
            "parameters": {
                "type": "object",
                "properties": {
                    "parent_id":  {"type": "string", "description": "ID de la página/BD padre en Notion"},
                    "titulo":     {"type": "string", "description": "Título de la nueva página"},
                    "contenido":  {"type": "string", "description": "Contenido de la página (opcional)"},
                },
                "required": ["parent_id", "titulo"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "programar_automatizacion",
            "description": "Programa una automatización para ejecutarse automáticamente con un horario (cron). Por ejemplo: cada lunes a las 9h, cada día a las 8:30, el primer día de mes, etc.",
            "parameters": {
                "type": "object",
                "properties": {
                    "nombre":     {"type": "string", "description": "Nombre de la automatización a programar"},
                    "cron_expr":  {"type": "string", "description": "Expresión cron: '0 9 * * 1' (lunes 9h), '30 8 * * *' (cada día 8:30), '0 9 1 * *' (día 1 del mes)"},
                    "descripcion_horario": {"type": "string", "description": "Descripción legible del horario, ej: 'cada lunes a las 9:00'"},
                },
                "required": ["nombre", "cron_expr"],
            },
        },
    },
]


# ─────────────────────────────────────────────────────────────────
# CAPA 1 — SYSTEM PROMPT (contexto rico de la empresa)
# ─────────────────────────────────────────────────────────────────

def _build_system_prompt(empresa: Empresa, procesos: list, kpis: list, autos: list) -> str:
    scores  = [p for p in procesos if p.score is not None]
    criticos = [p for p in scores if p.score < 40]
    activas = [a for a in autos if a.estado == "activa"]
    horas_mes = sum(a.horas_mes or 0 for a in activas)
    score_prom = round(sum(p.score for p in scores) / len(scores), 1) if scores else None

    # Resumen ejecutivo de la empresa
    resumen_lines = [
        f"**Empresa:** {empresa.nombre}",
        f"**Sector:** {empresa.sector or 'General'} | **Empleados:** {empresa.empleados or 'N/A'}",
        f"**Procesos:** {len(procesos)} registrados" +
        (f" | Score medio: {score_prom}/100" if score_prom else "") +
        (f" | ⚠️ {len(criticos)} críticos" if criticos else ""),
        f"**Automatizaciones:** {len(autos)} ({len(activas)} activas, {horas_mes}h/mes ahorradas, ~{horas_mes * COSTE_HORA}€/mes)",
        f"**KPIs:** {len(kpis)} definidos",
    ]

    # Lista de procesos actuales (máximo 20)
    proc_section = ""
    if procesos:
        proc_lines = []
        for p in sorted(procesos, key=lambda x: (x.score is None, x.score or 999)):
            emoji = "🔴" if (p.score or 0) < 40 else "🟡" if (p.score or 0) < 70 else "🟢"
            score_s = f"{p.score}/100" if p.score is not None else "sin score"
            resp_s = f", resp: {p.responsable}" if p.responsable else ""
            proc_lines.append(f"  {emoji} {p.nombre} — {score_s}{resp_s} — {p.estado}")
        proc_section = "\n**Procesos:**\n" + "\n".join(proc_lines[:20])

    if criticos:
        proc_section += f"\n\n⚠️ **CRÍTICOS (score<40):** {', '.join(p.nombre for p in criticos)}"

    context_block = "\n".join(resumen_lines) + proc_section

    return f"""Eres **BPA-Agent**, un consultor de IA senior especializado en Business Process Automation (BPA/BPM).
Tu cliente es la empresa **{empresa.nombre}**.

## Estado actual de la empresa
{context_block}

## Tu personalidad y estilo
- Responde SIEMPRE en español, con tono directo y profesional (como un consultor de confianza)
- Sé conciso: respuestas claras, sin rodeos innecesarios
- Usa Markdown (tablas, listas, negritas) cuando ayude a la claridad
- Varía tus expresiones — no empieces dos respuestas consecutivas igual
- Al final de cada respuesta, sugiere siempre el siguiente paso lógico (una sola frase)
- Si el usuario te da un número entre 0-100 después de hablar de un proceso, asume que es el score
- Si el usuario menciona un nombre de persona en contexto de un proceso, asume que es el responsable

## Cómo usar las herramientas
- Para CUALQUIER operación con datos (crear, listar, analizar, calcular ROI...) usa las herramientas disponibles
- Puedes llamar VARIAS herramientas en secuencia para responder preguntas complejas
- Antes de eliminar algo, confirma con el usuario si no lo ha pedido explícitamente
- Cuando crees o actualices algo, confirma brevemente con una sola frase y propón el siguiente paso

## Capacidades completas
1. **Procesos**: crear, listar, analizar en profundidad, actualizar (score, responsable, estado...), eliminar
2. **ROI**: calcular retorno de inversión de automatizar cualquier proceso
3. **KPIs**: crear indicadores de rendimiento vinculados a procesos
4. **Automatizaciones**: registrar, gestionar y EJECUTAR automatizaciones reales
5. **Email real**: configurar y enviar emails automáticos via SMTP (Gmail, Outlook, etc.)
6. **Telegram real**: configurar y enviar mensajes de Telegram automáticos via Bot API
7. **Scheduler**: programar automatizaciones con horario (cron) — "cada lunes a las 9h", etc.
8. **Ejecución inmediata**: lanzar cualquier automatización configurada con un comando
9. **Diagnóstico**: identificar cuellos de botella, procesos críticos y prioridades de mejora
10. **Resumen ejecutivo**: estado completo de la empresa en un vistazo

## Automatizaciones reales — ejemplos de uso
- "Configura un email automático que mande el informe de ventas a director@empresa.com cada lunes"
- "Manda un mensaje de Telegram al canal de operaciones cuando un proceso sea crítico"
- "Ejecuta la automatización de facturación ahora"
- "Programa el email semanal para los lunes a las 9:00"

## Conocimiento de benchmarks BPM
Tienes acceso a benchmarks del sector para facturación, RRHH, onboarding, inventario, ventas,
contabilidad, logística, compras, soporte, marketing y más. Úsalos al dar recomendaciones de ROI.
"""


# ─────────────────────────────────────────────────────────────────
# CAPA 2 — OLLAMA CLIENT
# ─────────────────────────────────────────────────────────────────

async def _ollama_chat(messages: list, tools: list = None, model: str = OLLAMA_MODEL) -> dict:
    payload: dict = {
        "model": model,
        "messages": messages,
        "stream": False,
        "options": {
            "temperature": 0.7,
            "num_predict": 2048,
        },
    }
    if tools:
        payload["tools"] = tools

    async with httpx.AsyncClient(timeout=OLLAMA_TIMEOUT) as client:
        r = await client.post(f"{OLLAMA_BASE}/api/chat", json=payload)
        r.raise_for_status()
        return r.json()


async def _ollama_available() -> tuple[bool, str]:
    """Comprueba si Ollama está corriendo Y si el modelo configurado está instalado."""
    try:
        async with httpx.AsyncClient(timeout=3) as client:
            r = await client.get(f"{OLLAMA_BASE}/api/tags")
            if r.status_code != 200:
                return False, ""
            data = r.json()
            model_names = [m["name"] for m in data.get("models", [])]
            # Check model with and without tag (e.g. "llama3.1:8b" or "llama3.1")
            model_base = OLLAMA_MODEL.split(":")[0]
            model_ready = any(
                n == OLLAMA_MODEL or n.startswith(model_base + ":") or n.startswith(model_base)
                for n in model_names
            )
            if not model_ready:
                return False, ", ".join(model_names) if model_names else "ninguno"
            return True, ", ".join(model_names)
    except Exception:
        return False, ""


# ─────────────────────────────────────────────────────────────────
# CAPA 3 — TOOL EXECUTOR
# ─────────────────────────────────────────────────────────────────

def _find_proceso(procesos: list, nombre: str) -> Optional[Proceso]:
    if not nombre:
        return None
    n = nombre.lower().strip()
    for p in procesos:
        if p.nombre.lower() == n:
            return p
    for p in procesos:
        if n in p.nombre.lower() or p.nombre.lower().startswith(n[:min(6, len(n))]):
            return p
    return None


async def _execute_tool(
    name: str,
    args: dict,
    db: AsyncSession,
    empresa: Empresa,
    procesos: list,
    kpis: list,
    autos: list,
) -> str:
    """Ejecuta una herramienta BPA y devuelve el resultado como string."""

    # ── listar_procesos ──────────────────────────────────────────────────────
    if name == "listar_procesos":
        if not procesos:
            return "No hay procesos registrados todavía."
        lines = []
        for p in sorted(procesos, key=lambda x: (x.score is None, x.score or 999)):
            e = "🔴" if (p.score or 0) < 40 else "🟡" if (p.score or 0) < 70 else "🟢"
            s = f"Score {p.score}/100" if p.score is not None else "Sin score"
            r = f" | Resp: {p.responsable}" if p.responsable else ""
            lines.append(f"{e} {p.nombre} — {s} — {p.estado}{r}")
        criticos = [p for p in procesos if p.score is not None and p.score < 40]
        result = f"**{len(procesos)} procesos:**\n" + "\n".join(lines)
        if criticos:
            result += f"\n\n⚠️ {len(criticos)} proceso(s) crítico(s) requieren atención."
        return result

    # ── crear_proceso ────────────────────────────────────────────────────────
    if name == "crear_proceso":
        nombre = str(args.get("nombre", "")).strip()[:100]
        if not nombre:
            return "ERROR: el campo 'nombre' es obligatorio para crear un proceso."
        nuevo = Proceso(
            empresa_id=empresa.id,
            nombre=nombre.capitalize(),
            descripcion=args.get("descripcion"),
            responsable=args.get("responsable"),
            estado=args.get("estado", "pendiente"),
            frecuencia=args.get("frecuencia"),
        )
        db.add(nuevo)
        await db.commit()
        await db.refresh(nuevo)
        procesos.append(nuevo)
        kb = _kb_lookup(nombre)
        extra = (
            f" Benchmark del sector: ahorro estimado {kb['ahorro_h']}h/mes automatizando con {kb['herramienta']}."
            if kb else ""
        )
        return f"✅ Proceso '{nuevo.nombre}' creado (id={nuevo.id}, estado={nuevo.estado}).{extra}"

    # ── actualizar_proceso ───────────────────────────────────────────────────
    if name == "actualizar_proceso":
        p = _find_proceso(procesos, str(args.get("nombre", "")))
        if not p:
            disponibles = ", ".join(x.nombre for x in procesos[:8]) or "ninguno"
            return f"ERROR: proceso '{args.get('nombre')}' no encontrado. Disponibles: {disponibles}"
        campo = str(args.get("campo", ""))
        valor = str(args.get("valor", ""))
        if campo == "score":
            try:
                v = int(float(valor))
                if not 0 <= v <= 100:
                    return "ERROR: el score debe ser un número entre 0 y 100."
                p.score = v
            except (ValueError, TypeError):
                return "ERROR: el score debe ser un número entero."
        elif campo == "duracion_h":
            try:
                p.duracion_h = float(valor.replace(",", "."))
            except (ValueError, TypeError):
                return "ERROR: duracion_h debe ser un número."
        elif campo in ("responsable", "estado", "descripcion", "frecuencia"):
            setattr(p, campo, valor)
        else:
            return f"ERROR: campo '{campo}' no válido. Campos permitidos: score, responsable, estado, descripcion, frecuencia, duracion_h."
        await db.commit()
        return f"✅ Proceso '{p.nombre}' actualizado: {campo} = {valor}."

    # ── eliminar_proceso ─────────────────────────────────────────────────────
    if name == "eliminar_proceso":
        p = _find_proceso(procesos, str(args.get("nombre", "")))
        if not p:
            return f"ERROR: proceso '{args.get('nombre')}' no encontrado."
        nombre_bak = p.nombre
        await db.delete(p)
        await db.commit()
        procesos[:] = [x for x in procesos if x.id != p.id]
        return f"🗑️ Proceso '{nombre_bak}' eliminado permanentemente."

    # ── analizar_proceso ─────────────────────────────────────────────────────
    if name == "analizar_proceso":
        p = _find_proceso(procesos, str(args.get("nombre", "")))
        if not p:
            disponibles = ", ".join(x.nombre for x in procesos[:8]) or "ninguno"
            return f"ERROR: proceso '{args.get('nombre')}' no encontrado. Disponibles: {disponibles}"

        s = p.score
        emoji = "🔴" if (s or 0) < 40 else "🟡" if (s or 0) < 70 else "🟢"

        p_kpis = [k for k in kpis if getattr(k, "proceso_id", None) == p.id]
        p_autos = [a for a in autos if getattr(a, "proceso_id", None) == p.id]
        scores_rest = [x.score for x in procesos if x.score is not None and x.id != p.id]

        lines = [f"{emoji} Análisis de '{p.nombre}':"]
        lines.append(f"Score: {s if s is not None else 'sin asignar'}/100")
        lines.append(f"Estado: {p.estado}")
        if p.responsable: lines.append(f"Responsable: {p.responsable}")
        if p.frecuencia:  lines.append(f"Frecuencia: {p.frecuencia}")
        if p.duracion_h:  lines.append(f"Duración: {p.duracion_h}h")
        if p.descripcion: lines.append(f"Descripción: {p.descripcion}")

        if scores_rest and s is not None:
            avg = sum(scores_rest) / len(scores_rest)
            delta = s - avg
            lines.append(
                f"Benchmark: {abs(delta):.0f}pts {'por encima' if delta >= 0 else 'por debajo'} "
                f"de la media interna ({avg:.0f}/100)"
            )

        if p_kpis:
            lines.append(f"KPIs vinculados: {', '.join(k.nombre for k in p_kpis)}")
        if p_autos:
            lines.append(f"Automatizaciones: {', '.join(a.nombre for a in p_autos)}")

        kb = _kb_lookup(p.nombre)
        if kb:
            lines.append(f"Potencial ROI: ~{kb['ahorro_h']}h/mes ahorradas con {kb['herramienta']}")

        # Recomendación
        if s is not None and s < 40:
            lines.append("⚡ Recomendación: score crítico, prioridad máxima — automatizar da ROI positivo en <6 meses.")
        elif s is not None and s < 70:
            lines.append("💡 Recomendación: margen de mejora significativo — revisar cuellos de botella y asignar responsable.")
        elif s is not None:
            lines.append("✅ Proceso bien optimizado — mantener monitorización con KPIs.")
        else:
            lines.append("ℹ️ Asigna un score para poder hacer benchmarking y seguimiento.")

        return "\n".join(lines)

    # ── calcular_roi ─────────────────────────────────────────────────────────
    if name == "calcular_roi":
        nombre_hint = str(args.get("nombre", "el proceso"))
        p = _find_proceso(procesos, nombre_hint)
        nombre = p.nombre if p else nombre_hint

        kb = _kb_lookup(nombre)
        if kb:
            ahorro_h   = kb["ahorro_h"]
            coste_impl = kb["coste_impl"]
            herramienta = kb["herramienta"]
        else:
            ahorro_h   = p.duracion_h * 0.7 if p and p.duracion_h else 5
            coste_impl = 800
            herramienta = "n8n / Zapier"

        ahorro_mes = round(ahorro_h * COSTE_HORA)
        ahorro_ano = ahorro_mes * 12
        payback    = round(coste_impl / ahorro_mes, 1) if ahorro_mes > 0 else "∞"
        roi_12m    = round(((ahorro_ano - coste_impl) / coste_impl) * 100) if coste_impl > 0 else 0

        score_ctx = ""
        if p and p.score is not None:
            if p.score < 40:
                score_ctx = f"\n(Score actual {p.score}/100 — proceso crítico, automatizar es PRIORITARIO)"
            else:
                score_ctx = f"\n(Score actual {p.score}/100)"

        return (
            f"ROI de automatizar '{nombre}':{score_ctx}\n"
            f"- Ahorro estimado: {ahorro_h:.0f}h/mes × {COSTE_HORA}€/h = {ahorro_mes}€/mes\n"
            f"- Ahorro anual: {ahorro_ano}€\n"
            f"- Inversión inicial: {coste_impl}€\n"
            f"- Payback: {payback} meses\n"
            f"- ROI a 12 meses: {roi_12m}%\n"
            f"- Herramienta recomendada: {herramienta}"
        )

    # ── crear_kpi ────────────────────────────────────────────────────────────
    if name == "crear_kpi":
        nombre = str(args.get("nombre", "")).strip()[:100]
        if not nombre:
            return "ERROR: el campo 'nombre' es obligatorio para crear un KPI."
        proceso_id = None
        proceso_nombre = ""
        if args.get("proceso"):
            p = _find_proceso(procesos, str(args["proceso"]))
            if p:
                proceso_id = p.id
                proceso_nombre = p.nombre
        nuevo = KPI(
            empresa_id=empresa.id,
            nombre=nombre.capitalize(),
            valor=str(args.get("valor", "0")),
            tendencia="up",
            proceso_id=proceso_id,
            unidad=args.get("unidad"),
            objetivo=args.get("objetivo"),
        )
        db.add(nuevo)
        await db.commit()
        await db.refresh(nuevo)
        kpis.append(nuevo)
        extra_parts = []
        if nuevo.unidad: extra_parts.append(f"unidad={nuevo.unidad}")
        if proceso_nombre: extra_parts.append(f"vinculado a '{proceso_nombre}'")
        if nuevo.objetivo: extra_parts.append(f"objetivo={nuevo.objetivo}")
        extra = f" ({', '.join(extra_parts)})" if extra_parts else ""
        return f"✅ KPI '{nuevo.nombre}' creado con valor inicial {nuevo.valor}{extra}."

    # ── listar_kpis ──────────────────────────────────────────────────────────
    if name == "listar_kpis":
        if not kpis:
            return "No hay KPIs definidos. Puedo crear uno ahora si me dices qué medir."
        lines = []
        for k in kpis:
            t = "↑" if k.tendencia == "up" else "↓" if k.tendencia == "down" else "→"
            u = f" {k.unidad}" if k.unidad else ""
            obj = f" (obj: {k.objetivo})" if k.objetivo else ""
            lines.append(f"{t} {k.nombre}: {k.valor}{u}{obj}")
        return f"**{len(kpis)} KPIs:**\n" + "\n".join(lines)

    # ── crear_automatizacion ─────────────────────────────────────────────────
    if name == "crear_automatizacion":
        nombre = str(args.get("nombre", "")).strip()[:100]
        if not nombre:
            return "ERROR: el campo 'nombre' es obligatorio."
        proceso_id = None
        proceso_nombre = ""
        if args.get("proceso"):
            p = _find_proceso(procesos, str(args["proceso"]))
            if p:
                proceso_id = p.id
                proceso_nombre = p.nombre
        nuevo = Automatizacion(
            empresa_id=empresa.id,
            nombre=nombre.capitalize(),
            estado="pendiente",
            herramienta=args.get("herramienta"),
            horas_mes=args.get("horas_mes"),
            ejecuciones=0,
            proceso_id=proceso_id,
        )
        db.add(nuevo)
        await db.commit()
        await db.refresh(nuevo)
        autos.append(nuevo)
        tool_s = f" con {nuevo.herramienta}" if nuevo.herramienta else ""
        h_s = f", ahorro estimado: {nuevo.horas_mes}h/mes" if nuevo.horas_mes else ""
        proc_s = f", vinculada a '{proceso_nombre}'" if proceso_nombre else ""
        return f"⚡ Automatización '{nuevo.nombre}' creada{tool_s}{h_s}{proc_s} (estado: pendiente)."

    # ── listar_automatizaciones ──────────────────────────────────────────────
    if name == "listar_automatizaciones":
        if not autos:
            return "No hay automatizaciones registradas todavía."
        activas = [a for a in autos if a.estado == "activa"]
        horas = sum(a.horas_mes or 0 for a in activas)
        lines = []
        for a in autos:
            icon = "⚡" if a.estado == "activa" else "⏸️"
            tool = f" ({a.herramienta})" if a.herramienta else ""
            h = f" · {a.horas_mes}h/mes" if a.horas_mes else ""
            lines.append(f"{icon} {a.nombre}{tool} — {a.estado}{h}")
        return (
            f"**{len(autos)} automatizaciones** ({len(activas)} activas, {horas}h/mes ahorradas):\n"
            + "\n".join(lines)
        )

    # ── resumen_empresa ──────────────────────────────────────────────────────
    if name == "resumen_empresa":
        scores   = [p for p in procesos if p.score is not None]
        criticos = [p for p in scores if p.score < 40]
        activas  = [a for a in autos if a.estado == "activa"]
        horas    = sum(a.horas_mes or 0 for a in activas)
        score_prom = round(sum(p.score for p in scores) / len(scores), 1) if scores else None

        lines = [
            f"📊 Resumen ejecutivo — {empresa.nombre}",
            f"Procesos: {len(procesos)}" +
            (f" | Score medio: {score_prom}/100" if score_prom else "") +
            (f" | ⚠️ {len(criticos)} críticos" if criticos else " | sin críticos"),
            f"Automatizaciones: {len(autos)} ({len(activas)} activas) | Ahorro: {horas}h/mes (~{horas*COSTE_HORA}€/mes)",
            f"KPIs: {len(kpis)} definidos",
        ]
        if criticos:
            lines.append(
                "⚠️ Procesos críticos: "
                + ", ".join(f"{p.nombre} ({p.score}/100)" for p in criticos)
            )
        if not procesos:
            lines.append("💡 Próximo paso recomendado: registra los procesos clave de tu empresa.")
        elif not kpis:
            lines.append("💡 Próximo paso: define KPIs para medir la evolución de tus procesos.")
        elif not autos:
            lines.append("💡 Oportunidad: automatizar procesos puede ahorrar 4-10h/mes. ¿Analizo el ROI?")
        else:
            lines.append(f"✅ Empresa bien gestionada. Ahorrando {horas}h/mes con automatizaciones.")
        return "\n".join(lines)

    # ── ejecutar_automatizacion ──────────────────────────────────────────────
    if name == "ejecutar_automatizacion":
        nombre_buscar = str(args.get("nombre", "")).strip()
        auto = next((a for a in autos if nombre_buscar.lower() in a.nombre.lower()), None)
        if not auto:
            disponibles = ", ".join(a.nombre for a in autos[:5]) or "ninguna"
            return f"ERROR: automatización '{nombre_buscar}' no encontrada. Disponibles: {disponibles}"
        from app.services.automation_executor import ejecutar_automatizacion as _exec
        result = await _exec(auto.id, empresa.id, db, triggered_by="agente")
        if result.get("ok"):
            return f"✅ Automatización '{auto.nombre}' ejecutada correctamente. {result.get('mensaje', '')} (duración: {result.get('duracion_ms', '?')}ms)"
        else:
            return f"❌ Error ejecutando '{auto.nombre}': {result.get('mensaje', 'error desconocido')}"

    # ── configurar_automatizacion_email ─────────────────────────────────────
    if name == "configurar_automatizacion_email":
        from app.services.connectors.email_connector import SMTP_PRESETS
        nombre = str(args.get("nombre", "")).strip()[:100]
        preset = SMTP_PRESETS.get(args.get("smtp_preset", "gmail"), SMTP_PRESETS["gmail"])
        config = {
            "smtp_host":     preset["smtp_host"],
            "smtp_port":     preset["smtp_port"],
            "smtp_user":     args.get("smtp_user", ""),
            "smtp_password": args.get("smtp_password", ""),
            "destinatario":  args.get("destinatario", ""),
            "asunto":        args.get("asunto", "Notificación BPA-Agent"),
            "cuerpo":        args.get("cuerpo", ""),
        }
        proceso_id = None
        if args.get("proceso"):
            p = _find_proceso(procesos, str(args["proceso"]))
            if p:
                proceso_id = p.id
        nuevo = Automatizacion(
            empresa_id=empresa.id,
            nombre=nombre.capitalize() or "Email automático",
            estado="activa",
            herramienta="Email SMTP",
            tipo_accion="email",
            tipo_trigger="manual",
            config_json=json.dumps(config),
            proceso_id=proceso_id,
        )
        db.add(nuevo)
        await db.commit()
        await db.refresh(nuevo)
        autos.append(nuevo)
        return (
            f"⚡ Automatización de email '{nuevo.nombre}' configurada y lista.\n"
            f"Enviará emails desde {config['smtp_user']} a {config['destinatario']}.\n"
            f"Ejecuta con: 'lanza {nuevo.nombre}' o prográmala con un horario."
        )

    # ── configurar_automatizacion_telegram ──────────────────────────────────
    if name == "configurar_automatizacion_telegram":
        nombre = str(args.get("nombre", "")).strip()[:100]
        config = {
            "bot_token": args.get("bot_token", ""),
            "chat_id":   args.get("chat_id", ""),
            "mensaje":   args.get("mensaje", "Notificación de BPA-Agent"),
        }
        proceso_id = None
        if args.get("proceso"):
            p = _find_proceso(procesos, str(args["proceso"]))
            if p:
                proceso_id = p.id
        nuevo = Automatizacion(
            empresa_id=empresa.id,
            nombre=nombre.capitalize() or "Alerta Telegram",
            estado="activa",
            herramienta="Telegram Bot",
            tipo_accion="telegram",
            tipo_trigger="manual",
            config_json=json.dumps(config),
            proceso_id=proceso_id,
        )
        db.add(nuevo)
        await db.commit()
        await db.refresh(nuevo)
        autos.append(nuevo)
        return (
            f"⚡ Automatización de Telegram '{nuevo.nombre}' configurada.\n"
            f"Enviará mensajes al chat {config['chat_id']}.\n"
            f"Ejecuta ahora con: 'lanza {nuevo.nombre}'"
        )

    # ── programar_automatizacion ─────────────────────────────────────────────
    if name == "programar_automatizacion":
        nombre_buscar = str(args.get("nombre", "")).strip()
        auto = next((a for a in autos if nombre_buscar.lower() in a.nombre.lower()), None)
        if not auto:
            disponibles = ", ".join(a.nombre for a in autos[:5]) or "ninguna"
            return f"ERROR: automatización '{nombre_buscar}' no encontrada. Disponibles: {disponibles}"
        cron_expr = str(args.get("cron_expr", "")).strip()
        desc_horario = args.get("descripcion_horario", cron_expr)
        auto.tipo_trigger = "cron"
        auto.cron_expr    = cron_expr
        auto.estado       = "activa"
        await db.commit()
        from app.services.scheduler import programar_automatizacion as _programar
        _programar(auto.id, empresa.id, cron_expr)
        return (
            f"🕐 Automatización '{auto.nombre}' programada: {desc_horario} ({cron_expr}).\n"
            f"Se ejecutará automáticamente según el horario configurado."
        )

    # ── gmail_enviar ─────────────────────────────────────────────────────────
    if name == "gmail_enviar":
        from app.services import credenciales_service
        from app.services.integrations import gmail_service
        import json as _json
        raw = await credenciales_service.obtener_credencial(db, empresa.id, "google_tokens")
        if not raw:
            return "❌ Gmail no está conectado. Ve a **Integraciones** → Google para conectar tu cuenta Google."
        tokens = _json.loads(raw)
        resultado = await gmail_service.enviar_email(
            access_token=tokens["access_token"],
            refresh_token=tokens.get("refresh_token"),
            destinatario=str(args.get("destinatario", "")),
            asunto=str(args.get("asunto", "")),
            cuerpo=str(args.get("cuerpo", "")),
            cc=args.get("cc"),
        )
        if resultado.get("ok"):
            return f"✅ Email enviado desde {resultado.get('remitente', 'tu Gmail')} a **{args.get('destinatario')}**\nAsunto: {args.get('asunto')}"
        return f"❌ Error enviando email: {resultado.get('error')}"

    # ── gmail_leer_bandeja ────────────────────────────────────────────────────
    if name == "gmail_leer_bandeja":
        from app.services import credenciales_service
        from app.services.integrations import gmail_service
        import json as _json
        raw = await credenciales_service.obtener_credencial(db, empresa.id, "google_tokens")
        if not raw:
            return "❌ Gmail no está conectado. Ve a **Integraciones** para conectar tu cuenta Google."
        tokens = _json.loads(raw)
        query  = str(args.get("query", "is:unread"))
        mx     = int(args.get("max_results", 10))
        resultado = await gmail_service.listar_emails(tokens["access_token"], query=query, max_results=mx, refresh_token=tokens.get("refresh_token"))
        if not resultado.get("ok"):
            return f"❌ Error leyendo Gmail: {resultado.get('error')}"
        emails = resultado.get("emails", [])
        if not emails:
            return f"No hay emails con el filtro '{query}'."
        lines = [f"📬 **{len(emails)} email(s)** (filtro: {query}):"]
        for e in emails:
            lines.append(f"- **{e['asunto']}** — De: {e['de']}\n  _{e['snippet'][:100]}_")
        return "\n".join(lines)

    # ── calendar_crear_evento ────────────────────────────────────────────────
    if name == "calendar_crear_evento":
        from app.services import credenciales_service
        from app.services.integrations import gcalendar_service
        import json as _json
        raw = await credenciales_service.obtener_credencial(db, empresa.id, "google_tokens")
        if not raw:
            return "❌ Google Calendar no está conectado. Ve a **Integraciones** → Google."
        tokens   = _json.loads(raw)
        resultado = await gcalendar_service.crear_evento(
            access_token=tokens["access_token"],
            refresh_token=tokens.get("refresh_token"),
            titulo=str(args.get("titulo", "")),
            inicio=str(args.get("inicio", "")),
            descripcion=args.get("descripcion"),
            invitados=args.get("invitados"),
            duracion_minutos=int(args.get("duracion_minutos", 60)),
        )
        if resultado.get("ok"):
            return f"📅 Evento creado: **{args.get('titulo')}**\nInicio: {args.get('inicio')}\nVer en Calendar: {resultado.get('link', '')}"
        return f"❌ Error creando evento: {resultado.get('error')}"

    # ── calendar_ver_eventos ─────────────────────────────────────────────────
    if name == "calendar_ver_eventos":
        from app.services import credenciales_service
        from app.services.integrations import gcalendar_service
        import json as _json
        raw = await credenciales_service.obtener_credencial(db, empresa.id, "google_tokens")
        if not raw:
            return "❌ Google Calendar no está conectado. Ve a **Integraciones** → Google."
        tokens   = _json.loads(raw)
        dias     = int(args.get("dias", 7))
        resultado = await gcalendar_service.listar_eventos(tokens["access_token"], dias=dias, refresh_token=tokens.get("refresh_token"))
        if not resultado.get("ok"):
            return f"❌ Error leyendo Calendar: {resultado.get('error')}"
        eventos = resultado.get("eventos", [])
        if not eventos:
            return f"No hay eventos en los próximos {dias} días."
        lines = [f"📅 **Próximos {len(eventos)} eventos ({dias} días):**"]
        for e in eventos:
            lines.append(f"- **{e['titulo']}** — {e['inicio']}")
        return "\n".join(lines)

    # ── n8n_trigger_webhook ──────────────────────────────────────────────────
    if name == "n8n_trigger_webhook":
        from app.services import credenciales_service
        from app.services.integrations import n8n_service
        n8n_url = await credenciales_service.obtener_credencial(db, empresa.id, "n8n_url") or n8n_service.DEFAULT_N8N_URL
        path    = str(args.get("webhook_path", ""))
        datos   = args.get("datos") or {}
        resultado = await n8n_service.trigger_webhook(path, datos, n8n_url)
        if resultado.get("ok"):
            return f"⚡ Workflow n8n disparado: `{path}`\nRespuesta: {str(resultado.get('respuesta', ''))[:200]}"
        return f"❌ Error en n8n: {resultado.get('error')}"

    # ── notion_crear_pagina ──────────────────────────────────────────────────
    if name == "notion_crear_pagina":
        from app.services import credenciales_service
        from app.services.integrations import notion_service
        token = await credenciales_service.obtener_credencial(db, empresa.id, "notion_token")
        if not token:
            return "❌ Notion no está conectado. Ve a **Integraciones** y añade tu token de Notion."
        resultado = await notion_service.crear_pagina(
            token=token,
            parent_id=str(args.get("parent_id", "")),
            titulo=str(args.get("titulo", "")),
            contenido=args.get("contenido"),
        )
        if resultado.get("ok"):
            return f"📝 Página Notion creada: **{args.get('titulo')}**\n{resultado.get('url', '')}"
        return f"❌ Error en Notion: {resultado.get('error')}"

    return f"ERROR: herramienta desconocida '{name}'."


# ─────────────────────────────────────────────────────────────────
# CAPA 4 — AGENT LOOP
# ─────────────────────────────────────────────────────────────────

async def _run_agent_loop(
    messages: list,
    db: AsyncSession,
    empresa: Empresa,
    procesos: list,
    kpis: list,
    autos: list,
) -> str:
    """
    Bucle agente principal:
    LLM → ¿hay tool_calls? → ejecutar herramientas → volver al LLM → respuesta final.
    Soporta múltiples llamadas en cadena (ej: crear proceso → calcular ROI → crear auto).
    """
    for iteration in range(MAX_ITERATIONS):
        response = await _ollama_chat(messages, TOOLS)
        msg = response.get("message", {})
        tool_calls = msg.get("tool_calls") or []

        if not tool_calls:
            # Sin tool calls → respuesta final del LLM
            content = msg.get("content", "")
            if not content:
                content = "No he podido generar una respuesta. Por favor, reformula tu pregunta."
            return content

        # ── Hay herramientas que llamar ──────────────────────────────────────
        # Añadir respuesta del asistente al historial de mensajes
        assistant_msg: dict[str, Any] = {
            "role": "assistant",
            "content": msg.get("content") or "",
            "tool_calls": tool_calls,
        }
        messages.append(assistant_msg)

        # Ejecutar cada herramienta y añadir resultado
        for tc in tool_calls:
            fn   = tc.get("function", {})
            t_name = fn.get("name", "")
            t_args = fn.get("arguments", {})

            # Algunos modelos devuelven arguments como string JSON
            if isinstance(t_args, str):
                try:
                    t_args = json.loads(t_args)
                except json.JSONDecodeError:
                    t_args = {}

            result = await _execute_tool(t_name, t_args, db, empresa, procesos, kpis, autos)

            messages.append({
                "role": "tool",
                "content": result,
            })

    # Si llegamos aquí sin respuesta final, pedimos una síntesis
    synthesis = await _ollama_chat(messages)
    return synthesis.get("message", {}).get("content", "Operación completada.")


# ─────────────────────────────────────────────────────────────────
# PUNTO DE ENTRADA PRINCIPAL
# ─────────────────────────────────────────────────────────────────

async def responder(
    mensaje: str,
    empresa: Empresa,
    db: AsyncSession,
    historial: list,
) -> dict[str, Any]:
    """
    Entry point — misma firma que motor_v4.responder() para compatibilidad total.
    """

    # ── Verificar disponibilidad de Ollama ───────────────────────────────────
    disponible, modelos = await _ollama_available()
    if not disponible:
        raise RuntimeError("Ollama no disponible — usando motor_v4 como fallback")

    # ── Cargar datos de la empresa ───────────────────────────────────────────
    proc_res = await db.execute(select(Proceso).where(Proceso.empresa_id == empresa.id))
    kpi_res  = await db.execute(select(KPI).where(KPI.empresa_id == empresa.id))
    auto_res = await db.execute(select(Automatizacion).where(Automatizacion.empresa_id == empresa.id))
    procesos = list(proc_res.scalars().all())
    kpis     = list(kpi_res.scalars().all())
    autos    = list(auto_res.scalars().all())

    # ── Construir mensajes para el LLM ───────────────────────────────────────
    system_prompt = _build_system_prompt(empresa, procesos, kpis, autos)
    messages: list[dict] = [{"role": "system", "content": system_prompt}]

    # Incluir historial reciente (últimos 40 turnos = 20 pares usuario/asistente)
    history_msgs = [
        {"role": m["role"], "content": m["content"]}
        for m in historial[-40:]
        if m.get("role") in ("user", "assistant") and m.get("content")
    ]
    messages.extend(history_msgs)

    # Asegurar que el mensaje actual está al final
    if not messages or messages[-1].get("content") != mensaje or messages[-1].get("role") != "user":
        messages.append({"role": "user", "content": mensaje})

    # ── Ejecutar el bucle agente ─────────────────────────────────────────────
    try:
        respuesta_texto = await _run_agent_loop(messages, db, empresa, procesos, kpis, autos)
    except httpx.TimeoutException as e:
        # Re-raise so agente.py fallback to motor_v4 kicks in
        raise RuntimeError(f"Ollama timeout — modelo {OLLAMA_MODEL}") from e
    except httpx.HTTPStatusError as e:
        # Model not found or any HTTP error → let agente.py fall back to v4
        raise RuntimeError(f"Ollama HTTP {e.response.status_code} — modelo {OLLAMA_MODEL}") from e
    except httpx.ConnectError as e:
        raise RuntimeError("Ollama no disponible (conexión rechazada)") from e
    except Exception as e:
        raise RuntimeError(f"motor_v5 error: {str(e)[:200]}") from e

    return {
        "respuesta": respuesta_texto,
        "accion":    None,
        "entidad":   None,
    }
