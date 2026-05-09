"""
audit.py — Servicio de auditoría: registra eventos de seguridad y acciones críticas.
"""

import json
import logging
from typing import Any, Optional

from fastapi import Request
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.audit_log import AuditLog

log = logging.getLogger(__name__)


def _get_ip(request: Request | None) -> str | None:
    if request is None:
        return None
    fwd = request.headers.get("X-Forwarded-For")
    if fwd:
        return fwd.split(",")[0].strip()
    return request.client.host if request.client else None


async def log_event(
    db: AsyncSession,
    action: str,
    *,
    user_id: str | None = None,
    resource: str | None = None,
    resource_id: str | None = None,
    request: Request | None = None,
    detail: dict[str, Any] | None = None,
    status: str = "ok",
) -> None:
    """
    Registra un evento de auditoría en la BD.
    No lanza excepciones — el fallo de auditoría no debe romper el flujo principal.
    """
    try:
        entry = AuditLog(
            user_id=user_id,
            action=action,
            resource=resource,
            resource_id=resource_id,
            ip=_get_ip(request),
            detail=json.dumps(detail, ensure_ascii=False) if detail else None,
            status=status,
        )
        db.add(entry)
        # No hacemos commit aquí — se commitea junto con la transacción principal
    except Exception as exc:
        log.warning("audit log error (non-fatal): %s", exc)
