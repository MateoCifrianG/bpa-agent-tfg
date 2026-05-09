"""
Notion Service — crea páginas, lee bases de datos y actualiza propiedades en Notion.
100% gratuito con cuenta Notion (plan Free soporta la API).

Cómo obtener el token:
1. Ve a https://www.notion.so/my-integrations
2. Crea una integración → copia el "Internal Integration Token"
3. En tu workspace Notion, comparte la BD/página con tu integración
"""
from __future__ import annotations

import logging
from typing import Optional

import httpx

log = logging.getLogger(__name__)

NOTION_API = "https://api.notion.com/v1"
NOTION_VERSION = "2022-06-28"


def _headers(token: str) -> dict:
    return {
        "Authorization":  f"Bearer {token}",
        "Notion-Version": NOTION_VERSION,
        "Content-Type":   "application/json",
    }


async def crear_pagina(
    token: str,
    parent_id: str,  # ID de la página/BD padre
    titulo: str,
    contenido: Optional[str] = None,
    propiedades: Optional[dict] = None,
) -> dict:
    """Crea una nueva página en Notion."""
    body: dict = {
        "parent": {"page_id": parent_id},
        "properties": {
            "title": {"title": [{"text": {"content": titulo}}]},
        },
    }
    if propiedades:
        body["properties"].update(propiedades)
    if contenido:
        body["children"] = [
            {
                "object": "block",
                "type":   "paragraph",
                "paragraph": {"rich_text": [{"text": {"content": contenido}}]},
            }
        ]
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.post(f"{NOTION_API}/pages", headers=_headers(token), json=body)
        data = r.json()
        if r.status_code == 200:
            return {"ok": True, "mensaje": f"Página '{titulo}' creada en Notion", "page_id": data.get("id"), "url": data.get("url")}
        return {"ok": False, "error": data.get("message", f"HTTP {r.status_code}")}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


async def añadir_registro_bd(
    token: str,
    database_id: str,
    propiedades: dict,  # {nombre_campo: valor, ...}
) -> dict:
    """Añade un registro a una base de datos de Notion."""
    props_formateadas = {}
    for key, val in propiedades.items():
        if isinstance(val, str):
            props_formateadas[key] = {"rich_text": [{"text": {"content": val}}]}
        elif isinstance(val, bool):
            props_formateadas[key] = {"checkbox": val}
        elif isinstance(val, (int, float)):
            props_formateadas[key] = {"number": val}
        else:
            props_formateadas[key] = {"rich_text": [{"text": {"content": str(val)}}]}

    body = {
        "parent":     {"database_id": database_id},
        "properties": props_formateadas,
    }
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.post(f"{NOTION_API}/pages", headers=_headers(token), json=body)
        data = r.json()
        if r.status_code == 200:
            return {"ok": True, "mensaje": "Registro añadido a BD de Notion", "page_id": data.get("id")}
        return {"ok": False, "error": data.get("message", f"HTTP {r.status_code}")}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


async def consultar_bd(
    token: str,
    database_id: str,
    filtro: Optional[dict] = None,
    max_results: int = 20,
) -> dict:
    """Consulta registros de una base de datos de Notion."""
    body: dict = {"page_size": max_results}
    if filtro:
        body["filter"] = filtro
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.post(f"{NOTION_API}/databases/{database_id}/query",
                                  headers=_headers(token), json=body)
        data = r.json()
        if r.status_code == 200:
            resultados = []
            for page in data.get("results", []):
                props = page.get("properties", {})
                fila = {"id": page["id"]}
                for key, val in props.items():
                    t = val.get("type")
                    if t == "title":
                        fila[key] = "".join(t["plain_text"] for t in val["title"])
                    elif t == "rich_text":
                        fila[key] = "".join(t["plain_text"] for t in val["rich_text"])
                    elif t == "number":
                        fila[key] = val.get("number")
                    elif t == "checkbox":
                        fila[key] = val.get("checkbox")
                    elif t == "select":
                        fila[key] = val.get("select", {}).get("name") if val.get("select") else None
                    else:
                        fila[key] = str(val)
                resultados.append(fila)
            return {"ok": True, "registros": resultados, "total": len(resultados)}
        return {"ok": False, "error": data.get("message", f"HTTP {r.status_code}")}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


async def verificar_conexion(token: str) -> dict:
    """Verifica que el token de Notion es válido."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(f"{NOTION_API}/users/me", headers=_headers(token))
        data = r.json()
        if r.status_code == 200:
            return {"ok": True, "mensaje": "Notion conectado", "usuario": data.get("name")}
        return {"ok": False, "error": data.get("message", "Token inválido")}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}
