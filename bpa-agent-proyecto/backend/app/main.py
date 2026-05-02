from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from starlette.middleware.base import BaseHTTPMiddleware
from starlette.responses import Response
from app.config import settings
from app.database import create_tables
from app.routers import auth, credenciales, empresas, procesos, kpis, automatizaciones, agente, users, admin
from app.middleware.rate_limit import RateLimitMiddleware
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from app.database import AsyncSessionLocal

MAX_BODY_BYTES = 1 * 1024 * 1024  # 1 MB


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

    async def dispatch(self, request: Request, call_next) -> Response:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["X-Frame-Options"] = "DENY"
        response.headers["X-XSS-Protection"] = "1; mode=block"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
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


@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_tables()
    await _bootstrap_admin()
    yield


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan,
)

# ---- Middlewares (orden: de fuera hacia dentro) ----
app.add_middleware(SecurityHeadersMiddleware)
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

app.include_router(auth.router)
app.include_router(users.router)
app.include_router(empresas.router)
app.include_router(procesos.router)
app.include_router(kpis.router)
app.include_router(automatizaciones.router)
app.include_router(agente.router)
app.include_router(credenciales.router)
app.include_router(admin.router)


@app.get("/health")
async def health():
    return {"status": "ok", "version": settings.APP_VERSION}
