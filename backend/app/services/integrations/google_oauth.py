"""
Google OAuth2 — flujo completo para Gmail, Calendar y Drive.
100% gratuito. Solo necesita credenciales de Google Cloud Console (gratis).

Cómo configurarlo (5 minutos):
1. Ve a https://console.cloud.google.com
2. Crea proyecto → APIs & Services → Credentials
3. OAuth 2.0 Client ID → Web application
4. Redirect URI: http://localhost:8002/api/integraciones/oauth/google/callback
5. Copia client_id y client_secret al .env
6. Activa: Gmail API, Calendar API, Drive API
"""
from __future__ import annotations

import json
import logging
from typing import Optional
from urllib.parse import urlencode

import httpx

log = logging.getLogger(__name__)

GOOGLE_AUTH_URL  = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_USERINFO  = "https://www.googleapis.com/oauth2/v2/userinfo"

SCOPES = [
    "https://www.googleapis.com/auth/gmail.send",
    "https://www.googleapis.com/auth/gmail.readonly",
    "https://www.googleapis.com/auth/calendar",
    "https://www.googleapis.com/auth/drive.file",
    "openid",
    "email",
    "profile",
]


def build_auth_url(client_id: str, redirect_uri: str, state: str) -> str:
    """Genera la URL de autorización de Google para redirigir al usuario."""
    params = {
        "client_id":     client_id,
        "redirect_uri":  redirect_uri,
        "response_type": "code",
        "scope":         " ".join(SCOPES),
        "access_type":   "offline",   # para obtener refresh_token
        "prompt":        "consent",   # fuerza mostrar pantalla de permisos
        "state":         state,
    }
    return f"{GOOGLE_AUTH_URL}?{urlencode(params)}"


async def exchange_code(
    code: str,
    client_id: str,
    client_secret: str,
    redirect_uri: str,
) -> dict:
    """Intercambia el código de autorización por access_token + refresh_token."""
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.post(GOOGLE_TOKEN_URL, data={
            "code":          code,
            "client_id":     client_id,
            "client_secret": client_secret,
            "redirect_uri":  redirect_uri,
            "grant_type":    "authorization_code",
        })
        data = r.json()
    if "error" in data:
        raise ValueError(f"Google OAuth error: {data['error']}: {data.get('error_description', '')}")
    return data  # {access_token, refresh_token, expires_in, token_type, scope}


async def refresh_access_token(
    refresh_token: str,
    client_id: str,
    client_secret: str,
) -> dict:
    """Renueva el access_token usando el refresh_token."""
    async with httpx.AsyncClient(timeout=15) as client:
        r = await client.post(GOOGLE_TOKEN_URL, data={
            "refresh_token": refresh_token,
            "client_id":     client_id,
            "client_secret": client_secret,
            "grant_type":    "refresh_token",
        })
        data = r.json()
    if "error" in data:
        raise ValueError(f"Token refresh error: {data['error']}")
    return data


async def get_user_info(access_token: str) -> dict:
    """Obtiene nombre y email del usuario Google autenticado."""
    async with httpx.AsyncClient(timeout=10) as client:
        r = await client.get(
            GOOGLE_USERINFO,
            headers={"Authorization": f"Bearer {access_token}"},
        )
        return r.json()
