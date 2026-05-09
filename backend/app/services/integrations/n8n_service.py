"""
n8n Service — conecta con n8n self-hosted (100% gratuito, open source).
n8n es la alternativa gratuita a Zapier/Make que corre en tu propio servidor.

Cómo instalar n8n (gratis, 2 minutos):
  npx n8n                          → corre en http://localhost:5678
  docker run -p 5678:5678 n8nio/n8n → con Docker

Funcionalidades:
- Disparar workflows via webhook
- Listar workflows
- Ejecutar workflows por ID
- Obtener historial de ejecuciones
"""
from __future__ import annotations

import logging
from typing import Optional

import httpx

log = logging.getLogger(__name__)

DEFAULT_N8N_URL = "http://localhost:5678"


async def trigger_webhook(
    webhook_path: str,
    payload: dict,
    n8n_url: str = DEFAULT_N8N_URL,
) -> dict:
    """
    Dispara un workflow de n8n via Webhook trigger.
    En n8n: añadir nodo 'Webhook' → copiar la URL → pegarla aquí.
    """
    url = f"{n8n_url}/webhook/{webhook_path.lstrip('/')}"
    try:
        async with httpx.AsyncClient(timeout=30) as client:
            r = await client.post(url, json=payload)
        if r.status_code < 400:
            try:
                data = r.json()
            except Exception:
                data = {"raw": r.text[:500]}
            return {"ok": True, "mensaje": f"Workflow n8n disparado (HTTP {r.status_code})", "respuesta": data}
        return {"ok": False, "error": f"n8n respondió HTTP {r.status_code}: {r.text[:200]}"}
    except httpx.ConnectError:
        return {"ok": False, "error": f"No se pudo conectar con n8n en {n8n_url}. ¿Está corriendo? (npx n8n)"}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


async def listar_workflows(
    api_key: str,
    n8n_url: str = DEFAULT_N8N_URL,
) -> dict:
    """Lista todos los workflows de n8n via REST API."""
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.get(
                f"{n8n_url}/api/v1/workflows",
                headers={"X-N8N-API-KEY": api_key},
            )
        if r.status_code == 200:
            data = r.json()
            workflows = [
                {"id": w["id"], "nombre": w["name"], "activo": w.get("active", False)}
                for w in data.get("data", [])
            ]
            return {"ok": True, "workflows": workflows}
        return {"ok": False, "error": f"n8n API error {r.status_code}"}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


async def ejecutar_workflow(
    workflow_id: str,
    api_key: str,
    n8n_url: str = DEFAULT_N8N_URL,
    datos: Optional[dict] = None,
) -> dict:
    """Ejecuta un workflow específico de n8n por ID."""
    try:
        async with httpx.AsyncClient(timeout=60) as client:
            r = await client.post(
                f"{n8n_url}/api/v1/workflows/{workflow_id}/execute",
                headers={"X-N8N-API-KEY": api_key, "Content-Type": "application/json"},
                json={"workflowData": datos or {}},
            )
        if r.status_code < 400:
            return {"ok": True, "mensaje": f"Workflow {workflow_id} ejecutado", "resultado": r.json()}
        return {"ok": False, "error": f"Error ejecutando workflow: {r.text[:200]}"}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


async def historial_ejecuciones(
    workflow_id: str,
    api_key: str,
    n8n_url: str = DEFAULT_N8N_URL,
    limit: int = 10,
) -> dict:
    """Obtiene el historial de ejecuciones de un workflow."""
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.get(
                f"{n8n_url}/api/v1/executions",
                headers={"X-N8N-API-KEY": api_key},
                params={"workflowId": workflow_id, "limit": limit},
            )
        if r.status_code == 200:
            data  = r.json()
            items = [
                {
                    "id":       e["id"],
                    "estado":   e.get("status", "unknown"),
                    "inicio":   e.get("startedAt"),
                    "fin":      e.get("stoppedAt"),
                    "modo":     e.get("mode", ""),
                }
                for e in data.get("data", [])
            ]
            return {"ok": True, "ejecuciones": items}
        return {"ok": False, "error": f"n8n error {r.status_code}"}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}


async def verificar_conexion(n8n_url: str = DEFAULT_N8N_URL) -> dict:
    """Verifica que n8n está corriendo y accesible."""
    try:
        async with httpx.AsyncClient(timeout=5) as client:
            r = await client.get(f"{n8n_url}/healthz")
        if r.status_code == 200:
            return {"ok": True, "mensaje": f"n8n online en {n8n_url}"}
        return {"ok": False, "error": f"n8n respondió {r.status_code}"}
    except httpx.ConnectError:
        return {"ok": False, "error": f"n8n no disponible en {n8n_url}. Ejecuta: npx n8n"}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}
