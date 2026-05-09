"""
Rate limiting middleware — sin dependencias externas.
Almacena intentos en memoria: { endpoint_key: { ip: (count, window_start) } }
"""
import time
import threading
from fastapi import Request, Response
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import JSONResponse

# Configuración por ruta (prefijo o exacto)
_RULES: dict[str, dict] = {
    "/api/auth/login":    {"max_requests": 10,  "window_seconds": 60},
    "/api/auth/register": {"max_requests": 5,   "window_seconds": 300},
    "/api/agente/chat":   {"max_requests": 60,  "window_seconds": 60},   # 1 msg/seg max
    "/api/admin":         {"max_requests": 120, "window_seconds": 60},
}

# Almacén compartido: { route_key: { ip: [count, window_start] } }
_store: dict[str, dict[str, list]] = {k: {} for k in _RULES}


def _match_rule(path: str) -> tuple[str, dict] | None:
    """Busca la regla más específica que coincida con el path (prefijo)."""
    best: tuple[str, dict] | None = None
    best_len = 0
    for rule_path, rule in _RULES.items():
        if path == rule_path or path.startswith(rule_path + "/") or path.startswith(rule_path):
            if len(rule_path) > best_len:
                best = (rule_path, rule)
                best_len = len(rule_path)
    return best
_lock = threading.Lock()


def _get_client_ip(request: Request) -> str:
    """Obtiene la IP real del cliente, teniendo en cuenta proxies."""
    forwarded_for = request.headers.get("X-Forwarded-For")
    if forwarded_for:
        return forwarded_for.split(",")[0].strip()
    if request.client:
        return request.client.host
    return "unknown"


def _cleanup(bucket: dict[str, list], window_seconds: int) -> None:
    """Elimina entradas caducadas para no acumular memoria indefinidamente."""
    now = time.monotonic()
    expired = [ip for ip, (_, start) in bucket.items() if now - start >= window_seconds]
    for ip in expired:
        del bucket[ip]


class RateLimitMiddleware(BaseHTTPMiddleware):
    async def dispatch(self, request: Request, call_next) -> Response:
        path = request.url.path

        matched = _match_rule(path)
        if matched is None:
            return await call_next(request)

        rule_path, rule = matched
        if rule_path not in _store:
            _store[rule_path] = {}

        ip = _get_client_ip(request)
        max_req = rule["max_requests"]
        window = rule["window_seconds"]
        now = time.monotonic()

        with _lock:
            bucket = _store[rule_path]
            _cleanup(bucket, window)

            if ip in bucket:
                count, start = bucket[ip]
                if now - start < window:
                    if count >= max_req:
                        return JSONResponse(
                            status_code=429,
                            content={"detail": "Demasiadas solicitudes, espera un momento"},
                        )
                    bucket[ip] = [count + 1, start]
                else:
                    # Ventana caducada, reiniciar
                    bucket[ip] = [1, now]
            else:
                bucket[ip] = [1, now]

        return await call_next(request)
