"""
sanitize.py — Funciones de saneamiento de entrada de usuario.
Protección contra XSS, inyección de control chars y payloads maliciosos.
"""

import re
import html


_CTRL_RE = re.compile(r'[\x00-\x08\x0b\x0c\x0e-\x1f\x7f]')
_SCRIPT_RE = re.compile(r'<\s*script[^>]*>.*?<\s*/\s*script\s*>', re.I | re.S)
_TAG_RE = re.compile(r'<[^>]+>')
_MULTI_SPACE = re.compile(r'[ \t]{3,}')
_MULTI_NL = re.compile(r'\n{4,}')


def limpiar_input(texto: str, max_len: int = 4000) -> str:
    """
    Saneamiento general para cualquier input de texto libre (chat, notas, etc.).
    - Elimina null bytes y caracteres de control
    - Escapa/elimina etiquetas HTML y scripts
    - Colapsa espacios/saltos de línea excesivos
    - Trunca a max_len
    """
    if not isinstance(texto, str):
        return ""
    texto = _CTRL_RE.sub("", texto)
    texto = _SCRIPT_RE.sub("", texto)
    texto = _TAG_RE.sub("", texto)
    texto = html.unescape(texto)          # normaliza &amp; &lt; etc.
    texto = _MULTI_SPACE.sub("  ", texto)
    texto = _MULTI_NL.sub("\n\n\n", texto)
    return texto[:max_len].strip()


def limpiar_nombre(texto: str, max_len: int = 255) -> str:
    """Para nombres de proceso, empresa, KPI — sin HTML ni saltos."""
    if not isinstance(texto, str):
        return ""
    texto = _CTRL_RE.sub("", texto)
    texto = _TAG_RE.sub("", texto)
    texto = html.unescape(texto)
    texto = texto.replace("\n", " ").replace("\r", "")
    texto = _MULTI_SPACE.sub(" ", texto)
    return texto[:max_len].strip()


def limpiar_email(texto: str) -> str:
    """Normaliza email: lowercase, strip, max 254 chars."""
    if not isinstance(texto, str):
        return ""
    return texto.lower().strip()[:254]


def validar_password(password: str) -> list[str]:
    """
    Devuelve lista de errores de validación. Lista vacía = contraseña válida.
    Reglas: ≥8 chars, ≥1 mayúscula, ≥1 minúscula, ≥1 dígito.
    """
    errors: list[str] = []
    if len(password) < 8:
        errors.append("La contraseña debe tener al menos 8 caracteres")
    if not re.search(r'[A-Z]', password):
        errors.append("Debe incluir al menos una mayúscula")
    if not re.search(r'[a-z]', password):
        errors.append("Debe incluir al menos una minúscula")
    if not re.search(r'\d', password):
        errors.append("Debe incluir al menos un número")
    return errors
