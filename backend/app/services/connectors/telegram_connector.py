"""
Conector de Telegram — envía mensajes y alertas vía Telegram Bot API.
100% gratuito. Solo necesita un bot de Telegram (se crea en 1 minuto con @BotFather).

Cómo crear el bot:
1. Abrir Telegram y buscar @BotFather
2. Enviar /newbot → elegir nombre y username
3. BotFather te da el TOKEN
4. Abrir el bot en Telegram y enviar cualquier mensaje
5. Obtener el chat_id con: https://api.telegram.org/bot{TOKEN}/getUpdates
"""
import httpx
import logging
from typing import Optional

log = logging.getLogger(__name__)

TELEGRAM_API = "https://api.telegram.org"


async def enviar_mensaje(
    *,
    bot_token: str,
    chat_id: str,
    mensaje: str,
    parse_mode: str = "HTML",
    disable_preview: bool = True,
) -> dict:
    """
    Envía un mensaje de Telegram.
    Soporta HTML: <b>negrita</b>, <i>cursiva</i>, <code>código</code>
    """
    url = f"{TELEGRAM_API}/bot{bot_token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": mensaje,
        "parse_mode": parse_mode,
        "disable_web_page_preview": disable_preview,
    }
    try:
        async with httpx.AsyncClient(timeout=15) as client:
            r = await client.post(url, json=payload)
            data = r.json()
        if r.status_code == 200 and data.get("ok"):
            log.info("Telegram enviado a chat_id %s", chat_id)
            return {"ok": True, "mensaje": f"Mensaje enviado a Telegram chat {chat_id}"}
        else:
            err = data.get("description", f"HTTP {r.status_code}")
            return {"ok": False, "error": f"Telegram error: {err}"}
    except httpx.TimeoutException:
        return {"ok": False, "error": "Timeout conectando con la API de Telegram."}
    except Exception as exc:
        log.exception("Error en Telegram connector")
        return {"ok": False, "error": str(exc)}


async def enviar_alerta_proceso(
    *,
    bot_token: str,
    chat_id: str,
    nombre_proceso: str,
    score: Optional[int],
    empresa: str,
    tipo_alerta: str = "critico",  # critico | bajo | mejora
) -> dict:
    """Envía una alerta formateada sobre un proceso empresarial."""
    iconos = {"critico": "🔴", "bajo": "🟡", "mejora": "🟢"}
    icono = iconos.get(tipo_alerta, "⚪")
    score_text = f"Score: <b>{score}/100</b>" if score is not None else "Sin score asignado"

    mensaje = (
        f"{icono} <b>Alerta BPA-Agent</b>\n\n"
        f"🏢 Empresa: <b>{empresa}</b>\n"
        f"⚙️ Proceso: <b>{nombre_proceso}</b>\n"
        f"📊 {score_text}\n\n"
        f"{'⚠️ Este proceso necesita atención urgente.' if tipo_alerta == 'critico' else '📈 Oportunidad de mejora detectada.'}"
    )
    return await enviar_mensaje(bot_token=bot_token, chat_id=chat_id, mensaje=mensaje)


async def verificar_bot(*, bot_token: str) -> dict:
    """Verifica que el token del bot es válido."""
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            r = await client.get(f"{TELEGRAM_API}/bot{bot_token}/getMe")
        data = r.json()
        if data.get("ok"):
            bot = data["result"]
            return {"ok": True, "bot_nombre": bot.get("first_name"), "bot_username": bot.get("username")}
        return {"ok": False, "error": "Token inválido"}
    except Exception as exc:
        return {"ok": False, "error": str(exc)}
