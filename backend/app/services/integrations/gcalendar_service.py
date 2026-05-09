"""
Google Calendar Service — crea, lista y gestiona eventos reales.
100% gratuito con cuenta Google.
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta, timezone
from typing import Optional

from googleapiclient.discovery import build
from googleapiclient.errors import HttpError
from google.oauth2.credentials import Credentials

log = logging.getLogger(__name__)


def _build_service(access_token: str, refresh_token: Optional[str] = None):
    creds = Credentials(token=access_token, refresh_token=refresh_token,
                        token_uri="https://oauth2.googleapis.com/token")
    return build("calendar", "v3", credentials=creds, cache_discovery=False)


async def crear_evento(
    access_token: str,
    titulo: str,
    inicio: str,           # ISO 8601: "2025-05-12T09:00:00"
    fin: Optional[str] = None,
    descripcion: Optional[str] = None,
    invitados: Optional[list[str]] = None,
    duracion_minutos: int = 60,
    refresh_token: Optional[str] = None,
) -> dict:
    """Crea un evento en Google Calendar."""
    try:
        service = _build_service(access_token, refresh_token)
        dt_inicio = datetime.fromisoformat(inicio)
        dt_fin    = datetime.fromisoformat(fin) if fin else dt_inicio + timedelta(minutes=duracion_minutos)
        evento = {
            "summary":     titulo,
            "description": descripcion or "",
            "start":  {"dateTime": dt_inicio.isoformat(), "timeZone": "Europe/Madrid"},
            "end":    {"dateTime": dt_fin.isoformat(),    "timeZone": "Europe/Madrid"},
        }
        if invitados:
            evento["attendees"] = [{"email": e} for e in invitados]
        creado = service.events().insert(calendarId="primary", body=evento, sendUpdates="all").execute()
        log.info("Evento creado: %s → %s", titulo, creado.get("id"))
        return {
            "ok": True,
            "mensaje": f"Evento '{titulo}' creado en Google Calendar",
            "event_id": creado.get("id"),
            "link": creado.get("htmlLink"),
        }
    except HttpError as e:
        return {"ok": False, "error": f"Calendar API error: {e.reason}"}
    except Exception as exc:
        log.exception("Calendar crear_evento")
        return {"ok": False, "error": str(exc)}


async def listar_eventos(
    access_token: str,
    dias: int = 7,
    max_results: int = 20,
    refresh_token: Optional[str] = None,
) -> dict:
    """Lista los próximos eventos del calendario."""
    try:
        service = _build_service(access_token, refresh_token)
        ahora   = datetime.now(timezone.utc).isoformat()
        limite  = (datetime.now(timezone.utc) + timedelta(days=dias)).isoformat()
        result  = service.events().list(
            calendarId="primary",
            timeMin=ahora,
            timeMax=limite,
            maxResults=max_results,
            singleEvents=True,
            orderBy="startTime",
        ).execute()
        eventos = []
        for e in result.get("items", []):
            start = e["start"].get("dateTime") or e["start"].get("date")
            eventos.append({
                "id":     e["id"],
                "titulo": e.get("summary", "(sin título)"),
                "inicio": start,
                "link":   e.get("htmlLink"),
            })
        return {"ok": True, "eventos": eventos}
    except HttpError as e:
        return {"ok": False, "error": f"Calendar API error: {e.reason}"}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}
