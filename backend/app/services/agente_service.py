"""
Servicio principal del agente IA BPA-Agent.
Gestiona el flujo de conversación y la integración con Claude API.
"""
import re
from sqlalchemy.ext.asyncio import AsyncSession
from app.agents.safety import limpiar_input, limpiar_historial, FASE_TOKEN
from app.agents.prompts.analisis import SYSTEM_PROMPT_ANALISIS
from app.agents.prompts.propuesta import SYSTEM_PROMPT_PROPUESTA
from app.agents.prompts.automatizacion import SYSTEM_PROMPT_AUTOMATIZACION
from app.agents.prompts.kpi import SYSTEM_PROMPT_KPI

SYSTEM_PROMPTS = {
    "analisis":       SYSTEM_PROMPT_ANALISIS,
    "propuesta":      SYSTEM_PROMPT_PROPUESTA,
    "automatizacion": SYSTEM_PROMPT_AUTOMATIZACION,
    "kpi":            SYSTEM_PROMPT_KPI,
}


def _limpiar_credenciales(texto: str) -> str:
    """
    Elimina cualquier credencial del texto antes de persistir en BD.
    REGLA DE SEGURIDAD: Nunca almacenar tokens/passwords en el historial.
    """
    return limpiar_input(texto)


def obtener_system_prompt(fase: str) -> str:
    return SYSTEM_PROMPTS.get(fase, SYSTEM_PROMPT_ANALISIS)


async def procesar_mensaje(
    mensaje_usuario: str,
    historial: list[dict],
    fase: str,
    empresa_id: str,
    db: AsyncSession,
) -> dict:
    """
    Procesa un mensaje del usuario y devuelve la respuesta del agente.
    TODO: Integrar con Anthropic Claude API cuando ANTHROPIC_API_KEY esté configurada.
    """
    # 1. Sanitizar input antes de procesar
    mensaje_limpio = _limpiar_credenciales(mensaje_usuario)

    # 2. Sanitizar historial antes de usarlo
    historial_limpio = limpiar_historial(historial)

    # 3. TODO: Llamar a Claude API
    # from anthropic import AsyncAnthropic
    # client = AsyncAnthropic(api_key=settings.ANTHROPIC_API_KEY)
    # response = await client.messages.create(...)

    # Placeholder hasta integrar Claude
    respuesta = f"[Agente en fase '{fase}'] Recibido: {mensaje_limpio[:100]}... (Claude API pendiente de integración)"
    nueva_fase = fase

    # 4. Detectar cambio de fase por token seguro
    if FASE_TOKEN in respuesta:
        nueva_fase = "propuesta"
        respuesta = respuesta.replace(FASE_TOKEN, "").strip()

    # 5. Sanitizar respuesta antes de devolver/persistir
    respuesta_limpia = _limpiar_credenciales(respuesta)

    return {
        "respuesta": respuesta_limpia,
        "fase": nueva_fase,
        "historial_actualizado": historial_limpio + [
            {"role": "user", "content": mensaje_limpio},
            {"role": "assistant", "content": respuesta_limpia},
        ],
    }
