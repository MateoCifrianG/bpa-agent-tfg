"""
Conector de Email — envía emails reales vía SMTP (Gmail, Outlook, cualquier servidor).
100% gratuito. Solo necesita una cuenta de correo con SMTP habilitado.

Para Gmail: activar "Contraseñas de aplicación" en la cuenta Google.
Para Outlook: usar smtp.office365.com:587
"""
import asyncio
import smtplib
import ssl
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from typing import Optional
import logging

log = logging.getLogger(__name__)


async def enviar_email(
    *,
    smtp_host: str,
    smtp_port: int,
    smtp_user: str,
    smtp_password: str,
    destinatario: str,
    asunto: str,
    cuerpo: str,
    cuerpo_html: Optional[str] = None,
    remitente_nombre: Optional[str] = "BPA-Agent",
) -> dict:
    """
    Envía un email de forma asíncrona usando SMTP estándar.
    Devuelve {"ok": True, "mensaje": "..."} o {"ok": False, "error": "..."}.
    """
    def _send_sync():
        msg = MIMEMultipart("alternative")
        msg["Subject"] = asunto
        msg["From"]    = f"{remitente_nombre} <{smtp_user}>"
        msg["To"]      = destinatario

        msg.attach(MIMEText(cuerpo, "plain", "utf-8"))
        if cuerpo_html:
            msg.attach(MIMEText(cuerpo_html, "html", "utf-8"))

        context = ssl.create_default_context()
        if smtp_port == 465:
            with smtplib.SMTP_SSL(smtp_host, smtp_port, context=context, timeout=15) as server:
                server.login(smtp_user, smtp_password)
                server.sendmail(smtp_user, destinatario, msg.as_string())
        else:
            with smtplib.SMTP(smtp_host, smtp_port, timeout=15) as server:
                server.ehlo()
                server.starttls(context=context)
                server.login(smtp_user, smtp_password)
                server.sendmail(smtp_user, destinatario, msg.as_string())
        return True

    try:
        await asyncio.get_event_loop().run_in_executor(None, _send_sync)
        log.info("Email enviado a %s: %s", destinatario, asunto)
        return {"ok": True, "mensaje": f"Email enviado a {destinatario}"}
    except smtplib.SMTPAuthenticationError:
        return {"ok": False, "error": "Error de autenticación SMTP. Verifica usuario/contraseña."}
    except smtplib.SMTPRecipientsRefused:
        return {"ok": False, "error": f"Destinatario rechazado: {destinatario}"}
    except TimeoutError:
        return {"ok": False, "error": "Timeout conectando al servidor SMTP."}
    except Exception as exc:
        log.exception("Error enviando email")
        return {"ok": False, "error": str(exc)}


# ── Presets de servidores conocidos ──────────────────────────────
SMTP_PRESETS = {
    "gmail": {
        "smtp_host": "smtp.gmail.com",
        "smtp_port": 587,
        "nota": "Necesita Contraseña de Aplicación (no la contraseña normal). Ve a: myaccount.google.com → Seguridad → Contraseñas de aplicación"
    },
    "outlook": {
        "smtp_host": "smtp.office365.com",
        "smtp_port": 587,
        "nota": "Usa tu email y contraseña de Microsoft/Outlook"
    },
    "hotmail": {
        "smtp_host": "smtp.live.com",
        "smtp_port": 587,
        "nota": "Usa tu email y contraseña de Hotmail"
    },
    "yahoo": {
        "smtp_host": "smtp.mail.yahoo.com",
        "smtp_port": 587,
        "nota": "Necesita Contraseña de Aplicación de Yahoo"
    },
    "custom": {
        "smtp_host": "",
        "smtp_port": 587,
        "nota": "Introduce los datos de tu servidor SMTP personalizado"
    },
}
