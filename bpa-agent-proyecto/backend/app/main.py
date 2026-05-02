from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.config import settings
from app.database import create_tables
from app.routers import auth, credenciales, empresas, procesos, kpis, automatizaciones, agente, users


@asynccontextmanager
async def lifespan(app: FastAPI):
    await create_tables()
    yield


app = FastAPI(
    title=settings.APP_NAME,
    version=settings.APP_VERSION,
    lifespan=lifespan,
)

if settings.DEBUG:
    # En desarrollo: aceptar cualquier origen (localhost, file://, etc.)
    app.add_middleware(
        CORSMiddleware,
        allow_origin_regex=r".*",   # cualquier origen en dev
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


@app.get("/health")
async def health():
    return {"status": "ok", "version": settings.APP_VERSION}
