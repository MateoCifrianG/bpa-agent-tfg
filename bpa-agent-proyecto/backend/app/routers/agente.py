from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional
from datetime import datetime
from app.database import get_db
from app.models.conversacion import Conversacion
from app.models.empresa import Empresa
from app.models.proceso import Proceso
from app.models.kpi import KPI
from app.models.automatizacion import Automatizacion
from app.models.user import User
from app.auth.jwt import get_current_user
from app.config import settings
import json
import random

router = APIRouter(prefix="/api/agente", tags=["agente"])


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


async def _get_empresa(db: AsyncSession, user: User) -> Empresa:
    result = await db.execute(select(Empresa).where(Empresa.user_id == user.id))
    empresa = result.scalars().first()
    if not empresa:
        raise HTTPException(status_code=404, detail="No tienes empresa registrada")
    return empresa


async def _smart_response(mensaje: str, empresa: Empresa, db: AsyncSession, historial: list) -> str:
    """Genera respuestas inteligentes basadas en los datos reales de la empresa.
    No requiere API key. Analiza el contexto y responde de forma contextual."""

    msg = mensaje.lower().strip()
    n_turns = len([m for m in historial if m["role"] == "user"])

    # Cargar datos reales de la empresa
    proc_res = await db.execute(select(Proceso).where(Proceso.empresa_id == empresa.id))
    procesos = proc_res.scalars().all()

    kpi_res = await db.execute(select(KPI).where(KPI.empresa_id == empresa.id))
    kpis = kpi_res.scalars().all()

    auto_res = await db.execute(select(Automatizacion).where(Automatizacion.empresa_id == empresa.id))
    autos = auto_res.scalars().all()

    # --- Respuestas contextuales según palabras clave ---

    # Saludo inicial
    saludos = ["hola", "buenas", "hey", "qué tal", "buenos días", "buenas tardes"]
    if any(msg.startswith(s) for s in saludos) and n_turns <= 1:
        nombre = empresa.nombre
        intro = f"¡Hola! Soy **BPA-Agent**, tu asistente de automatización de procesos para **{nombre}**.\n\n"
        if not procesos:
            return intro + ("Veo que aún no tienes procesos registrados. Te recomiendo empezar mapeando los procesos más críticos de tu empresa.\n\n"
                            "**Para empezar puedes decirme:**\n"
                            "• \"Quiero analizar el proceso de [nombre]\"\n"
                            "• \"¿Qué procesos debo priorizar?\"\n"
                            "• \"Muéstrame propuestas de automatización\"")
        else:
            criticos = [p for p in procesos if p.score is not None and p.score < 50]
            return intro + (f"Tienes **{len(procesos)} proceso(s)** registrado(s)"
                            + (f", de los cuales **{len(criticos)} tienen score crítico** (<50)." if criticos else ".") + "\n\n"
                            "¿Quieres que analice algún proceso en concreto, o prefieres ver un resumen completo?")

    # Procesos
    if any(w in msg for w in ["proceso", "procesos", "mapear", "mapeo"]):
        if not procesos:
            return ("Aún no tienes procesos registrados en el sistema.\n\n"
                    "Ve a la sección **Procesos** del menú lateral y añade tus procesos más importantes. "
                    "Necesito al menos el nombre, responsable y frecuencia para poder analizarlos correctamente.")
        scores_validos = [p for p in procesos if p.score is not None]
        if scores_validos:
            peor = min(scores_validos, key=lambda p: p.score)
            mejor = max(scores_validos, key=lambda p: p.score)
            criticos = [p for p in scores_validos if p.score < 50]
            respuesta = f"📊 **Análisis de tus {len(procesos)} procesos:**\n\n"
            for p in sorted(scores_validos, key=lambda x: x.score)[:5]:
                emoji = "🔴" if p.score < 40 else "🟡" if p.score < 70 else "🟢"
                respuesta += f"{emoji} **{p.nombre}** — Score: {p.score}/100\n"
            respuesta += f"\n**Proceso más crítico:** {peor.nombre} (score {peor.score})"
            if criticos:
                respuesta += f"\n\n⚠️ Tienes **{len(criticos)} proceso(s) crítico(s)** que necesitan atención inmediata. ¿Empezamos por {criticos[0].nombre}?"
            else:
                respuesta += f"\n\n✅ Ningún proceso en estado crítico. El más optimizable es **{peor.nombre}** (score {peor.score})."
            return respuesta
        else:
            lista = "\n".join(f"• {p.nombre} ({p.estado})" for p in procesos[:5])
            return (f"Tienes {len(procesos)} proceso(s) registrado(s), pero ninguno tiene score asignado aún:\n\n{lista}\n\n"
                    "Edita cada proceso y añade un score del 0 al 100 para que pueda priorizar los análisis.")

    # Automatizaciones
    if any(w in msg for w in ["automatiz", "automatización", "automatizar", "robot", "n8n", "workflow"]):
        if not autos:
            if procesos:
                sugerencias = []
                for p in procesos[:3]:
                    if "factur" in p.nombre.lower():
                        sugerencias.append(f"• **Facturación automática** con n8n + Google Sheets para {p.nombre}")
                    elif "email" in p.nombre.lower() or "correo" in p.nombre.lower():
                        sugerencias.append(f"• **Envío automático de emails** con Gmail para {p.nombre}")
                    elif "cliente" in p.nombre.lower() or "onboard" in p.nombre.lower():
                        sugerencias.append(f"• **Alta de cliente** con n8n + Drive + Gmail para {p.nombre}")
                    else:
                        sugerencias.append(f"• **Notificaciones automáticas** con n8n para {p.nombre}")
                if sugerencias:
                    return ("Basándome en tus procesos, te propongo estas automatizaciones:\n\n"
                            + "\n".join(sugerencias[:3])
                            + "\n\n¿Quieres que profundice en alguna de ellas? Ve a **Automatizaciones** para crearlas.")
            return ("Aún no tienes automatizaciones configuradas.\n\n"
                    "Las herramientas más usadas son:\n• **n8n** — para flujos de trabajo complejos\n"
                    "• **Gmail** — envío automático de emails\n• **Google Drive** — gestión de documentos\n\n"
                    "¿Qué proceso te gustaría automatizar primero?")
        activas = [a for a in autos if a.estado == "activa"]
        horas = sum(a.horas_mes or 0 for a in autos)
        return (f"⚡ **Estado de tus automatizaciones:**\n\n"
                f"• Total: {len(autos)} automatizacion(es)\n"
                f"• Activas: {len(activas)}\n"
                f"• Horas ahorradas/mes: {horas}h\n\n"
                + (f"Automatizaciones activas: " + ", ".join(a.nombre for a in activas[:3]) if activas else "Ninguna activa aún.") +
                "\n\nPuedes gestionar todas desde la sección **Automatizaciones**.")

    # KPIs
    if any(w in msg for w in ["kpi", "indicador", "métrica", "métrico", "rendimiento", "performance"]):
        if not kpis:
            return ("No tienes KPIs definidos todavía.\n\n"
                    "Te recomiendo empezar con estos indicadores básicos:\n"
                    "• **Tiempo de resolución** (días)\n• **Coste por proceso** (€)\n"
                    "• **Satisfacción del cliente** (%)\n• **Errores por proceso** (%)\n\n"
                    "Ve a la sección **KPIs** para añadirlos.")
        respuesta = f"📈 **Tus {len(kpis)} KPIs actuales:**\n\n"
        for k in kpis[:6]:
            tend = "↑" if k.tendencia == "up" else "↓" if k.tendencia == "down" else "→"
            respuesta += f"{tend} **{k.nombre}**: {k.valor}{' ' + k.unidad if k.unidad else ''}"
            if k.objetivo:
                respuesta += f" (objetivo: {k.objetivo})"
            respuesta += "\n"
        return respuesta

    # Análisis / diagnóstico
    if any(w in msg for w in ["analiz", "diagnos", "evaluá", "evalua", "revisar", "revisar", "situación"]):
        resumen = f"🔍 **Diagnóstico de {empresa.nombre}:**\n\n"
        resumen += f"• **Procesos:** {len(procesos)}"
        if procesos:
            criticos = [p for p in procesos if p.score is not None and p.score < 50]
            if criticos:
                resumen += f" ({len(criticos)} críticos)"
        resumen += f"\n• **Automatizaciones:** {len(autos)}"
        if autos:
            activas = [a for a in autos if a.estado == "activa"]
            resumen += f" ({len(activas)} activas)"
        resumen += f"\n• **KPIs:** {len(kpis)}\n"
        if not procesos:
            resumen += "\n⚠️ **Prioridad:** Registra tus procesos de negocio para poder hacer un análisis real."
        elif not kpis:
            resumen += "\n⚠️ **Recomendación:** Define KPIs para medir la mejora de tus procesos."
        elif not autos:
            resumen += "\n💡 **Oportunidad:** Con tus procesos mapeados, puedes empezar a crear automatizaciones."
        else:
            horas = sum(a.horas_mes or 0 for a in autos)
            resumen += f"\n✅ **Ahorro estimado:** {horas}h/mes con las automatizaciones actuales."
        return resumen

    # Propuestas / sugerencias
    if any(w in msg for w in ["propuesta", "suger", "recomend", "mejora", "optimiz"]):
        propuestas = []
        if procesos:
            criticos = sorted([p for p in procesos if p.score is not None and p.score < 60], key=lambda x: x.score)
            for p in criticos[:2]:
                propuestas.append(f"1. **Optimizar '{p.nombre}'** (score actual: {p.score}/100)\n   → Revisar puntos de fricción y automatizar tareas repetitivas")
        if not autos and procesos:
            propuestas.append(f"2. **Crear primera automatización** para '{procesos[0].nombre}'\n   → Ahorro estimado: 4-8h/mes")
        if not kpis:
            propuestas.append("3. **Definir KPIs** para medir el rendimiento operacional\n   → Sin métricas no hay mejora medible")
        if not propuestas:
            propuestas = ["✅ Tu empresa está bien encaminada. Para seguir mejorando:\n→ Incrementa el score de procesos existentes\n→ Añade más automatizaciones\n→ Actualiza tus KPIs regularmente"]
        return "💡 **Mis propuestas para ti:**\n\n" + "\n\n".join(propuestas)

    # Ayuda
    if any(w in msg for w in ["ayuda", "help", "qué puedes", "que puedes", "cómo funciona", "funcionalidades"]):
        return ("Puedo ayudarte con:\n\n"
                "🗂️ **Análisis de procesos** — \"Analiza mis procesos\", \"¿Cuál tiene peor score?\"\n"
                "⚡ **Automatizaciones** — \"Propón automatizaciones\", \"¿Qué puedo automatizar?\"\n"
                "📈 **KPIs** — \"Muéstrame mis KPIs\", \"¿Cómo van mis indicadores?\"\n"
                "🔍 **Diagnóstico** — \"Haz un diagnóstico de mi empresa\"\n"
                "💡 **Propuestas** — \"Dame recomendaciones de mejora\"\n\n"
                "También puedes preguntarme directamente sobre cualquier proceso o dato específico.")

    # Respuesta genérica contextual (fallback inteligente)
    fallbacks = []
    if procesos:
        peor = min((p for p in procesos if p.score is not None), key=lambda p: p.score, default=None)
        if peor:
            fallbacks.append(f"A propósito, el proceso **{peor.nombre}** tiene el score más bajo ({peor.score}/100). ¿Te interesa analizarlo?")
    if not procesos:
        fallbacks.append("Recuerda que para que pueda ayudarte mejor, necesito que registres tus procesos en la sección **Procesos**.")
    if not kpis:
        fallbacks.append("¿Tienes definidos tus KPIs? Son clave para medir si las mejoras están funcionando.")

    base = f"He recibido tu mensaje. "
    if fallbacks:
        base += random.choice(fallbacks)
    else:
        base += "¿Quieres que analice tus procesos, revise tus automatizaciones o te dé recomendaciones de mejora?"
    return base


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

    # Usar Claude si hay API key, si no usar respuestas inteligentes
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
        except Exception as e:
            # Si falla Claude, usar respuestas inteligentes
            respuesta_texto = await _smart_response(body.mensaje, empresa, db, historial)
    else:
        # Respuestas inteligentes basadas en datos reales (sin coste de API)
        respuesta_texto = await _smart_response(body.mensaje, empresa, db, historial)

    historial.append({"role": "assistant", "content": respuesta_texto})
    conv.historial = json.dumps(historial, ensure_ascii=False)

    await db.commit()
    await db.refresh(conv)

    return {
        "conversacion_id": conv.id,
        "respuesta": respuesta_texto,
        "fase": conv.fase,
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
