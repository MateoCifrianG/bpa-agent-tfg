"""
integraciones.py — Gestión completa de integraciones externas.

Endpoints:
  GET  /api/integraciones/                → lista integraciones disponibles + estado
  GET  /api/integraciones/oauth/google    → inicia flujo OAuth2 de Google
  GET  /api/integraciones/oauth/google/callback → callback de Google
  DELETE /api/integraciones/{servicio}    → desconectar integración

  POST /api/integraciones/n8n/webhook/{path}   → disparar webhook n8n
  GET  /api/integraciones/n8n/workflows        → listar workflows n8n
  POST /api/integraciones/n8n/verificar        → verificar conexión n8n

  POST /api/integraciones/gmail/enviar         → enviar email via Gmail
  GET  /api/integraciones/gmail/bandeja        → listar emails
  POST /api/integraciones/gmail/buscar         → buscar emails

  POST /api/integraciones/calendar/crear       → crear evento
  GET  /api/integraciones/calendar/eventos     → listar próximos eventos

  POST /api/integraciones/notion/verificar     → verificar token Notion
  POST /api/integraciones/notion/pagina        → crear página
  POST /api/integraciones/notion/bd/añadir     → añadir registro a BD
"""
from __future__ import annotations

import json
import secrets
from typing import Optional
from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import RedirectResponse, JSONResponse
from pydantic import BaseModel
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.auth.jwt import get_current_user
from app.config import settings
from app.database import get_db
from app.models.empresa import Empresa
from app.models.user import User
from app.services import credenciales_service
from app.services.integrations import (
    google_oauth, gmail_service, gcalendar_service, n8n_service, notion_service
)

router = APIRouter(prefix="/api/integraciones", tags=["integraciones"])

REDIRECT_URI = "http://localhost:8002/api/integraciones/oauth/google/callback"

# Tokens de estado temporales para OAuth (en memoria, TTL corto)
_oauth_states: dict[str, str] = {}  # state → empresa_id


async def _get_empresa(db: AsyncSession, user: User) -> Empresa:
    r = await db.execute(select(Empresa).where(Empresa.user_id == user.id))
    emp = r.scalars().first()
    if not emp:
        raise HTTPException(404, "No tienes empresa registrada")
    return emp


# ── Estado de integraciones ─────────────────────────────────────────────────

@router.get("")
async def listar_integraciones(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Devuelve todas las integraciones disponibles con su estado de conexión."""
    empresa = await _get_empresa(db, user)

    async def _conectado(servicio: str) -> bool:
        try:
            token = await credenciales_service.obtener_credencial(db, empresa.id, servicio)
            return bool(token)
        except Exception:
            return False

    google  = await _conectado("google_tokens")
    n8n_key = await _conectado("n8n_api_key")
    notion  = await _conectado("notion_token")
    tg      = await _conectado("telegram_bot_token")
    slack   = await _conectado("slack_webhook")

    return {
        "integraciones": [
            {
                "id":          "google",
                "nombre":      "Google (Gmail + Calendar)",
                "descripcion": "Envía emails, crea eventos y gestiona Drive con tu cuenta Google",
                "icono":       "google",
                "conectado":   google,
                "tipo":        "oauth2",
                "gratis":      True,
                "oauth_url":   "/api/integraciones/oauth/google" if not google else None,
            },
            {
                "id":          "n8n",
                "nombre":      "n8n",
                "descripcion": "Automatización open-source. Conecta con +400 apps. Corre local gratis.",
                "icono":       "n8n",
                "conectado":   n8n_key,
                "tipo":        "api_key",
                "gratis":      True,
                "setup_url":   "https://n8n.io/",
            },
            {
                "id":          "notion",
                "nombre":      "Notion",
                "descripcion": "Crea páginas, añade registros a bases de datos y automatiza documentación",
                "icono":       "notion",
                "conectado":   notion,
                "tipo":        "api_key",
                "gratis":      True,
                "setup_url":   "https://www.notion.so/my-integrations",
            },
            {
                "id":          "telegram",
                "nombre":      "Telegram Bot",
                "descripcion": "Envía notificaciones y alertas a chats o canales de Telegram",
                "icono":       "telegram",
                "conectado":   tg,
                "tipo":        "api_key",
                "gratis":      True,
                "setup_url":   "https://t.me/BotFather",
            },
            {
                "id":          "slack",
                "nombre":      "Slack",
                "descripcion": "Notificaciones en canales de Slack via Incoming Webhooks",
                "icono":       "slack",
                "conectado":   slack,
                "tipo":        "webhook",
                "gratis":      True,
                "setup_url":   "https://api.slack.com/apps",
            },
        ]
    }


# ── Google OAuth2 ───────────────────────────────────────────────────────────

@router.get("/oauth/google")
async def iniciar_google_oauth(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not settings.GOOGLE_CLIENT_ID:
        raise HTTPException(400, detail=(
            "GOOGLE_CLIENT_ID no configurado. "
            "Crea credenciales OAuth2 en https://console.cloud.google.com y añádelas al .env"
        ))
    empresa = await _get_empresa(db, user)
    state   = secrets.token_urlsafe(24)
    _oauth_states[state] = empresa.id
    url = google_oauth.build_auth_url(settings.GOOGLE_CLIENT_ID, REDIRECT_URI, state)
    return RedirectResponse(url)


@router.get("/oauth/google/callback")
async def google_oauth_callback(
    code: Optional[str] = None,
    state: Optional[str] = None,
    error: Optional[str] = None,
    db: AsyncSession = Depends(get_db),
):
    if error:
        return RedirectResponse(f"http://localhost/integraciones.html?error={error}")
    if not code or not state or state not in _oauth_states:
        raise HTTPException(400, "OAuth callback inválido")

    empresa_id = _oauth_states.pop(state)

    tokens = await google_oauth.exchange_code(
        code, settings.GOOGLE_CLIENT_ID, settings.GOOGLE_CLIENT_SECRET, REDIRECT_URI
    )

    # Guardar tokens cifrados en BD
    tokens_json = json.dumps(tokens)
    await credenciales_service.guardar_credencial(db, empresa_id, "google_tokens", tokens_json)

    # Obtener info del usuario
    user_info = await google_oauth.get_user_info(tokens["access_token"])

    return RedirectResponse(
        f"http://localhost/integraciones.html?google_ok=1&email={user_info.get('email', '')}"
    )


@router.delete("/{servicio}")
async def desconectar(
    servicio: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    empresa = await _get_empresa(db, user)
    await credenciales_service.eliminar_credencial(db, empresa.id, servicio)
    return {"ok": True, "mensaje": f"Integración '{servicio}' desconectada"}


# ── Helpers para obtener tokens ─────────────────────────────────────────────

async def _get_google_tokens(db: AsyncSession, empresa_id: str) -> dict:
    raw = await credenciales_service.obtener_credencial(db, empresa_id, "google_tokens")
    if not raw:
        raise HTTPException(400, detail=(
            "Google no está conectado. Ve a Integraciones y conecta tu cuenta Google."
        ))
    return json.loads(raw)


# ── Gmail ───────────────────────────────────────────────────────────────────

class GmailEnviarBody(BaseModel):
    destinatario: str
    asunto: str
    cuerpo: str
    cuerpo_html: Optional[str] = None
    cc: Optional[str] = None


@router.post("/gmail/enviar")
async def gmail_enviar(
    body: GmailEnviarBody,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    empresa  = await _get_empresa(db, user)
    tokens   = await _get_google_tokens(db, empresa.id)
    resultado = await gmail_service.enviar_email(
        access_token=tokens["access_token"],
        refresh_token=tokens.get("refresh_token"),
        destinatario=body.destinatario,
        asunto=body.asunto,
        cuerpo=body.cuerpo,
        cuerpo_html=body.cuerpo_html,
        cc=body.cc,
    )
    if not resultado["ok"]:
        raise HTTPException(400, detail=resultado["error"])
    return resultado


@router.get("/gmail/bandeja")
async def gmail_bandeja(
    query: str = "is:unread",
    max_results: int = 10,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    empresa = await _get_empresa(db, user)
    tokens  = await _get_google_tokens(db, empresa.id)
    return await gmail_service.listar_emails(
        tokens["access_token"], query=query, max_results=max_results,
        refresh_token=tokens.get("refresh_token")
    )


class GmailBuscarBody(BaseModel):
    query: str
    max_results: int = 20


@router.post("/gmail/buscar")
async def gmail_buscar(
    body: GmailBuscarBody,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    empresa = await _get_empresa(db, user)
    tokens  = await _get_google_tokens(db, empresa.id)
    return await gmail_service.buscar_emails(
        tokens["access_token"], query=body.query, max_results=body.max_results,
        refresh_token=tokens.get("refresh_token")
    )


# ── Google Calendar ─────────────────────────────────────────────────────────

class CalendarEventoBody(BaseModel):
    titulo: str
    inicio: str       # ISO: "2025-05-15T09:00:00"
    fin: Optional[str] = None
    descripcion: Optional[str] = None
    invitados: Optional[list[str]] = None
    duracion_minutos: int = 60


@router.post("/calendar/crear")
async def calendar_crear(
    body: CalendarEventoBody,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    empresa  = await _get_empresa(db, user)
    tokens   = await _get_google_tokens(db, empresa.id)
    resultado = await gcalendar_service.crear_evento(
        access_token=tokens["access_token"],
        refresh_token=tokens.get("refresh_token"),
        titulo=body.titulo,
        inicio=body.inicio,
        fin=body.fin,
        descripcion=body.descripcion,
        invitados=body.invitados,
        duracion_minutos=body.duracion_minutos,
    )
    if not resultado["ok"]:
        raise HTTPException(400, detail=resultado["error"])
    return resultado


@router.get("/calendar/eventos")
async def calendar_eventos(
    dias: int = 7,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    empresa = await _get_empresa(db, user)
    tokens  = await _get_google_tokens(db, empresa.id)
    return await gcalendar_service.listar_eventos(
        tokens["access_token"], dias=dias, refresh_token=tokens.get("refresh_token")
    )


# ── n8n ──────────────────────────────────────────────────────────────────────

class N8nWebhookBody(BaseModel):
    payload: dict = {}


@router.post("/n8n/webhook/{webhook_path:path}")
async def n8n_webhook(
    webhook_path: str,
    body: N8nWebhookBody,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    empresa  = await _get_empresa(db, user)
    n8n_url_raw = await credenciales_service.obtener_credencial(db, empresa.id, "n8n_url")
    n8n_url  = n8n_url_raw or n8n_service.DEFAULT_N8N_URL
    resultado = await n8n_service.trigger_webhook(webhook_path, body.payload, n8n_url)
    if not resultado["ok"]:
        raise HTTPException(400, detail=resultado["error"])
    return resultado


@router.get("/n8n/workflows")
async def n8n_listar_workflows(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    empresa  = await _get_empresa(db, user)
    api_key  = await credenciales_service.obtener_credencial(db, empresa.id, "n8n_api_key")
    n8n_url  = await credenciales_service.obtener_credencial(db, empresa.id, "n8n_url") or n8n_service.DEFAULT_N8N_URL
    if not api_key:
        raise HTTPException(400, "n8n API key no configurada. Añádela en Integraciones.")
    return await n8n_service.listar_workflows(api_key, n8n_url)


class N8nVerificarBody(BaseModel):
    url: str = n8n_service.DEFAULT_N8N_URL


@router.post("/n8n/verificar")
async def n8n_verificar(body: N8nVerificarBody, user: User = Depends(get_current_user)):
    return await n8n_service.verificar_conexion(body.url)


# ── Notion ───────────────────────────────────────────────────────────────────

class NotionPaginaBody(BaseModel):
    parent_id: str
    titulo: str
    contenido: Optional[str] = None


@router.post("/notion/pagina")
async def notion_crear_pagina(
    body: NotionPaginaBody,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    empresa = await _get_empresa(db, user)
    token   = await credenciales_service.obtener_credencial(db, empresa.id, "notion_token")
    if not token:
        raise HTTPException(400, "Notion no conectado. Añade tu token en Integraciones.")
    resultado = await notion_service.crear_pagina(token, body.parent_id, body.titulo, body.contenido)
    if not resultado["ok"]:
        raise HTTPException(400, detail=resultado["error"])
    return resultado


class NotionVerificarBody(BaseModel):
    token: str


@router.post("/notion/verificar")
async def notion_verificar(body: NotionVerificarBody, user: User = Depends(get_current_user)):
    return await notion_service.verificar_conexion(body.token)


# ── Guardar credenciales de integraciones ───────────────────────────────────

class GuardarCredencialBody(BaseModel):
    servicio: str
    valor: str


@router.post("/credencial")
async def guardar_credencial_integracion(
    body: GuardarCredencialBody,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """Guarda una API key o token de integración (cifrado en BD)."""
    empresa = await _get_empresa(db, user)
    servicios_validos = {"n8n_api_key", "n8n_url", "notion_token", "telegram_bot_token",
                         "telegram_chat_id", "slack_webhook", "teams_webhook"}
    if body.servicio not in servicios_validos:
        raise HTTPException(400, f"Servicio no válido. Opciones: {', '.join(servicios_validos)}")
    await credenciales_service.guardar_credencial(db, empresa.id, body.servicio, body.valor)
    return {"ok": True, "mensaje": f"Credencial '{body.servicio}' guardada correctamente"}
