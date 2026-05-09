import time
import logging
from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from app.config import settings
from app.database import create_tables
from app.routers import auth, credenciales, empresas, procesos, kpis, automatizaciones, agente, users, admin, ejecutar, integraciones
from app.middleware.rate_limit import RateLimitMiddleware
from app.logging_config import setup_logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, text
from app.database import AsyncSessionLocal

_START_TIME: float = time.monotonic()
logger = logging.getLogger("bpa.main")

MAX_BODY_BYTES = 1 * 1024 * 1024  # 1 MB


class RequestLoggingMiddleware(BaseHTTPMiddleware):
    """Logs method, path, status code and latency for every request."""

    async def dispatch(self, request: Request, call_next) -> Response:
        t0 = time.monotonic()
        response = await call_next(request)
        ms = round((time.monotonic() - t0) * 1000)
        # Skip health spam in production
        if request.url.path != "/health":
            logger.info(
                "%s %s %d",
                request.method,
                request.url.path,
                response.status_code,
                extra={
                    "method": request.method,
                    "path": request.url.path,
                    "status": response.status_code,
                    "ms": ms,
                    "ip": request.client.host if request.client else None,
                },
            )
        return response


class BodySizeLimitMiddleware(BaseHTTPMiddleware):
    """Rechaza peticiones cuyo body supere MAX_BODY_BYTES."""

    async def dispatch(self, request: Request, call_next) -> Response:
        content_length = request.headers.get("content-length")
        if content_length and int(content_length) > MAX_BODY_BYTES:
            return JSONResponse(
                status_code=413,
                content={"detail": "El cuerpo de la solicitud supera el límite permitido (1 MB)"},
            )
        return await call_next(request)


class SecurityHeadersMiddleware(BaseHTTPMiddleware):
    """Añade cabeceras de seguridad HTTP a todas las respuestas."""

    _CSP = (
        "default-src 'self'; "
        "script-src 'self' 'unsafe-inline'; "   # unsafe-inline necesario para dashboard.html inline scripts
        "style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; "
        "font-src 'self' https://fonts.gstatic.com; "
        "img-src 'self' data: blob:; "
        "connect-src 'self' http://localhost:8002; "
        "frame-ancestors 'none';"
    )

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Content-Security-Policy"] = self._CSP
        response.headers["Permissions-Policy"] = "geolocation=(), microphone=(), camera=()"
        return response


async def _bootstrap_admin():
    """Create the default admin user and its empresa if they don't exist yet."""
    from app.models.user import User
    from app.models.empresa import Empresa
    from app.auth.jwt import hash_password

    async with AsyncSessionLocal() as db:
        result = await db.execute(select(User).where(User.email == settings.ADMIN_EMAIL))
        existing = result.scalar_one_or_none()
        if existing:
            return

        admin_user = User(
            email=settings.ADMIN_EMAIL,
            hashed_password=hash_password(settings.ADMIN_PASSWORD),
            nombre="Admin",
            apellido="BPA",
            role="admin",
            plan="enterprise",
            is_active=True,
        )
        db.add(admin_user)
        await db.flush()

        empresa = Empresa(
            user_id=admin_user.id,
            nombre="BPA-Agent",
        )
        db.add(empresa)
        await db.commit()


async def _migrate_db():
    """Apply incremental schema changes to existing DB without losing data."""
    async with AsyncSessionLocal() as db:
        migrations = [
            "ALTER TABLE kpis ADD COLUMN proceso_id VARCHAR(36) REFERENCES procesos(id) ON DELETE SET NULL",
            "ALTER TABLE automatizaciones ADD COLUMN tipo_trigger VARCHAR(30) DEFAULT 'manual'",
            "ALTER TABLE automatizaciones ADD COLUMN cron_expr VARCHAR(100)",
            "ALTER TABLE automatizaciones ADD COLUMN webhook_token VARCHAR(64)",
            "ALTER TABLE automatizaciones ADD COLUMN tipo_accion VARCHAR(30) DEFAULT 'webhook_out'",
        ]
        for sql in migrations:
            try:
                await db.execute(text(sql))
                await db.commit()
            except Exception:
                await db.rollback()


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging(level="INFO", json_logs=not settings.DEBUG)
    logger.info("BPA-Agent arrancando", extra={"version": settings.APP_VERSION})
    await create_tables()
    await _migrate_db()
    await _bootstrap_admin()
    from app.services.scheduler import start_scheduler, stop_scheduler
    await start_scheduler()
    logger.info("BPA-Agent listo")
    yield
    await stop_scheduler()
    logger.info("BPA-Agent detenido")


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan,
)

# ---- Middlewares (orden: de fuera hacia dentro) ----
app.add_middleware(SecurityHeadersMiddleware)
app.add_middleware(RequestLoggingMiddleware)
app.add_middleware(BodySizeLimitMiddleware)
app.add_middleware(RateLimitMiddleware)

if settings.DEBUG:
    app.add_middleware(
        CORSMiddleware,
        allow_origin_regex=r".*",
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )
else:
    app.add_middleware(
        CORSMiddleware,
        allow_origins=settings.ALLOWED_ORIGINS,
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

@app.exception_handler(RequestValidationError)
async def validation_exception_handler(request: Request, exc: RequestValidationError):
    errors = [
        {"field": " → ".join(str(l) for l in e["loc"][1:]), "msg": e["msg"]}
        for e in exc.errors()
    ]
    logger.warning("Validación fallida %s %s", request.method, request.url.path,
                   extra={"errors": errors})
    return JSONResponse(status_code=422, content={"detail": "Datos inválidos", "errors": errors})


@app.exception_handler(Exception)
async def unhandled_exception_handler(request: Request, exc: Exception):
    logger.error("Error no controlado %s %s: %s", request.method, request.url.path, exc,
                 exc_info=True)
    return JSONResponse(status_code=500, content={"detail": "Error interno del servidor"})


app.include_router(auth.router)
app.include_router(users.router)
app.include_router(empresas.router)
app.include_router(procesos.router)
app.include_router(kpis.router)
app.include_router(automatizaciones.router)
app.include_router(agente.router)
app.include_router(credenciales.router)
app.include_router(admin.router)
app.include_router(ejecutar.router)
app.include_router(integraciones.router)


@app.get("/health")
async def health():
    """Enriched health check: DB ping, motor version, uptime."""
    uptime_s = round(time.monotonic() - _START_TIME)
    db_ok = False
    try:
        async with AsyncSessionLocal() as db:
            await db.execute(text("SELECT 1"))
        db_ok = True
    except Exception:
        pass

    # Detect which motor version is active
    motor_version = "v6"
    try:
        from app.agents import motor_v6  # noqa: F401
    except ImportError:
        try:
            from app.agents import motor_v5  # noqa: F401
            motor_version = "v5"
        except ImportError:
            motor_version = "v4"

    status = "ok" if db_ok else "degraded"
    return {
        "status": status,
        "version": settings.APP_VERSION,
        "motor": motor_version,
        "db": "ok" if db_ok else "error",
        "uptime_s": uptime_s,
    }
