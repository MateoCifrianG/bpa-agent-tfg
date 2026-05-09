"""
Gmail Service — Lee y envía emails reales via Gmail API (OAuth2).
Completamente gratuito con cuenta Google.

Capacidades:
- Enviar emails con HTML, adjuntos, CC, BCC
- Leer bandeja de entrada / búsqueda
- Listar threads y mensajes
- Marcar como leído / archivar
- Crear borradores
"""
from __future__ import annotations

import base64
import logging
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.oauth2.credentials import Credentials

log = logging.getLogger(__name__)


def _build_service(access_token: str, refresh_token: Optional[str] = None):
    """Construye el cliente de Gmail API."""
    creds = Credentials(
        token=access_token,
        refresh_token=refresh_token,
        token_uri="https://oauth2.googleapis.com/token",
    )
    return build("gmail", "v1", credentials=creds, cache_discovery=False)


def _crear_mensaje(
    remitente: str,
    destinatario: str,
    asunto: str,
    cuerpo: str,
    cuerpo_html: Optional[str] = None,
    cc: Optional[str] = None,
) -> dict:
    msg = MIMEMultipart("alternative")
    msg["Subject"] = asunto
    msg["From"]    = remitente
    msg["To"]      = destinatario
    if cc:
        msg["Cc"] = cc
    msg.attach(MIMEText(cuerpo, "plain", "utf-8"))
    if cuerpo_html:
        msg.attach(MIMEText(cuerpo_html, "html", "utf-8"))
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    return {"raw": raw}


async def enviar_email(
    access_token: str,
    destinatario: str,
    asunto: str,
    cuerpo: str,
    cuerpo_html: Optional[str] = None,
    cc: Optional[str] = None,
    refresh_token: Optional[str] = None,
) -> dict:
    """Envía un email real via Gmail API."""
    try:
        service = _build_service(access_token, refresh_token)
        perfil = service.users().getProfile(userId="me").execute()
        remitente = perfil["emailAddress"]
        mensaje = _crear_mensaje(remitente, destinatario, asunto, cuerpo, cuerpo_html, cc)
        sent = service.users().messages().send(userId="me", body=mensaje).execute()
        log.info("Gmail: email enviado a %s, id=%s", destinatario, sent.get("id"))
        return {"ok": True, "mensaje": f"Email enviado a {destinatario}", "message_id": sent.get("id"), "remitente": remitente}
    except HttpError as e:
        return {"ok": False, "error": f"Gmail API error: {e.reason}"}
    except Exception as exc:
        log.exception("Gmail enviar_email")
        return {"ok": False, "error": str(exc)}


async def listar_emails(
    access_token: str,
    query: str = "is:unread",
    max_results: int = 10,
    refresh_token: Optional[str] = None,
) -> dict:
    """Lista emails de Gmail con filtro de búsqueda."""
    try:
        service = _build_service(access_token, refresh_token)
        result = service.users().messages().list(
            userId="me", q=query, maxResults=max_results
        ).execute()
        messages = result.get("messages", [])
        emails = []
        for m in messages[:max_results]:
            msg = service.users().messages().get(
                userId="me", id=m["id"], format="metadata",
                metadataHeaders=["Subject", "From", "Date"]
            ).execute()
            headers = {h["name"]: h["value"] for h in msg.get("payload", {}).get("headers", [])}
            emails.append({
                "id":      m["id"],
                "asunto":  headers.get("Subject", "(sin asunto)"),
                "de":      headers.get("From", ""),
                "fecha":   headers.get("Date", ""),
                "snippet": msg.get("snippet", ""),
            })
        return {"ok": True, "emails": emails, "total": result.get("resultSizeEstimate", len(emails))}
    except HttpError as e:
        return {"ok": False, "error": f"Gmail API error: {e.reason}"}
    except Exception as exc:
        log.exception("Gmail listar_emails")
        return {"ok": False, "error": str(exc)}


async def buscar_emails(
    access_token: str,
    query: str,
    max_results: int = 20,
    refresh_token: Optional[str] = None,
) -> dict:
    """Busca emails con cualquier query de Gmail (from:, subject:, after:, etc.)"""
    return await listar_emails(access_token, query=query, max_results=max_results, refresh_token=refresh_token)


async def crear_borrador(
    access_token: str,
    destinatario: str,
    asunto: str,
    cuerpo: str,
    refresh_token: Optional[str] = None,
) -> dict:
    """Crea un borrador en Gmail."""
    try:
        service = _build_service(access_token, refresh_token)
        perfil  = service.users().getProfile(userId="me").execute()
        mensaje = _crear_mensaje(perfil["emailAddress"], destinatario, asunto, cuerpo)
        draft   = service.users().drafts().create(userId="me", body={"message": mensaje}).execute()
        return {"ok": True, "mensaje": "Borrador creado en Gmail", "draft_id": draft.get("id")}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}
