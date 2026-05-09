"""
Filtros de seguridad para inputs/outputs del agente IA.
REGLA: Nunca persistir ni loguear credenciales.
"""
import re

# Patrones que nunca deben llegar al agente ni persistirse
INJECTION_PATTERNS = [
    r"(?i)(password|contraseña|passwd|pwd)\s*[:=]\s*\S+",
    r"(?i)(api[_-]?key|apikey|api_token)\s*[:=]\s*\S+",
    r"(?i)(bearer\s+)[A-Za-z0-9\-_\.]+",
    r"(?i)(secret|token|credential)\s*[:=]\s*\S+",
    r"[A-Za-z0-9+/]{40,}={0,2}",           # base64 largo (posible token)
    r"ghp_[A-Za-z0-9]{36}",                 # GitHub token
    r"sk-[A-Za-z0-9]{32,}",                 # OpenAI/Anthropic key
    r"<<BPA_FASE:",                          # inyección de token de fase
]

# Token interno para cambio de fase — no reproducible por el usuario
FASE_TOKEN = "<<BPA_FASE:ANALISIS>>"

_compiled = [re.compile(p) for p in INJECTION_PATTERNS]


def limpiar_input(texto: str) -> str:
    """Elimina credenciales del input del usuario antes de enviarlo al agente."""
    for patron in _compiled:
        texto = patron.sub("[CREDENCIAL_ELIMINADA]", texto)
    return texto


def limpiar_historial(mensajes: list[dict]) -> list[dict]:
    """Sanitiza el historial completo antes de persistir en BD."""
    limpios = []
    for msg in mensajes:
        msg_limpio = dict(msg)
        if isinstance(msg_limpio.get("content"), str):
            msg_limpio["content"] = limpiar_input(msg_limpio["content"])
        limpios.append(msg_limpio)
    return limpios


def contiene_credenciales(texto: str) -> bool:
    """Detecta si un texto contiene posibles credenciales."""
    return any(p.search(texto) for p in _compiled)
