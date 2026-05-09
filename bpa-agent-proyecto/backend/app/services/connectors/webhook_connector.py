"""
Conector de Webhooks salientes — envía datos a cualquier URL externa vía HTTP.
Sirve para conectar con n8n, Make, Zapier, Slack Incoming Webhooks, o cualquier app.
100% gratuito.
"""
import httpx
import json
import logging
from typing import Any, Optional

log = logging.getLogger(__name__)


async def enviar_webhook(
    *,
    url: str,
    payload: dict[str, Any],
    method: str = "POST",
    headers: Optional[dict] = None,
    timeout: int = 30,
) -> dict:
    """
    Envía una petición HTTP a la URL indicada con el payload dado.
    Útil para disparar flujos en n8n, Make, Zapier, etc.
    """
    _headers = {"Content-Type": "application/json"}
    if headers:
        _headers.update(headers)

    try:
        async with httpx.AsyncClient(timeout=timeout) as client:
            if method.upper() == "POST":
                r = await client.post(url, json=payload, headers=_headers)
            elif method.upper() == "PUT":
                r = await client.put(url, json=payload, headers=_headers)
            elif method.upper() == "GET":
                r = await client.get(url, params=payload, headers=_headers)
            else:
                return {"ok": False, "error": f"Método HTTP no soportado: {method}"}

        log.info("Webhook enviado a %s → HTTP %s", url, r.status_code)
        if r.status_code < 400:
            try:
                resp_data = r.json()
            except Exception:
                resp_data = r.text[:500]
            return {"ok": True, "mensaje": f"Webhook enviado (HTTP {r.status_code})", "respuesta": resp_data}
        else:
            return {"ok": False, "error": f"El servidor respondió HTTP {r.status_code}: {r.text[:200]}"}
    except httpx.TimeoutException:
        return {"ok": False, "error": f"Timeout enviando webhook a {url}"}
    except httpx.ConnectError:
        return {"ok": False, "error": f"No se pudo conectar con {url}"}
    except Exception as exc:
        log.exception("Error en webhook connector")
        return {"ok": False, "error": str(exc)}


async def enviar_slack(
    *,
    webhook_url: str,
    mensaje: str,
    titulo: Optional[str] = None,
    color: str = "#4CAF50",  # verde por defecto
) -> dict:
    """
    Envía un mensaje a un canal de Slack vía Incoming Webhook.
    Para obtener la URL: api.slack.com/apps → Incoming Webhooks
    """
    payload: dict[str, Any] = {
        "text": titulo or "BPA-Agent",
        "attachments": [
            {
                "color": color,
                "text": mensaje,
                "footer": "BPA-Agent",
            }
        ],
    }
    return await enviar_webhook(url=webhook_url, payload=payload)


async def enviar_teams(
    *,
    webhook_url: str,
    titulo: str,
    mensaje: str,
) -> dict:
    """
    Envía un mensaje a Microsoft Teams vía Incoming Webhook.
    Formato: Adaptive Card simplificada.
    """
    payload = {
        "@type": "MessageCard",
        "@context": "http://schema.org/extensions",
        "themeColor": "0078D4",
        "summary": titulo,
        "sections": [{"activityTitle": titulo, "activityText": mensaje}],
    }
    return await enviar_webhook(url=webhook_url, payload=payload)
