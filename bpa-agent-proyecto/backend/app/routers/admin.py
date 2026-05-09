from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, delete
from sqlalchemy.orm import selectinload
from pydantic import BaseModel, EmailStr
from typing import Optional
from datetime import datetime

from app.database import get_db
from app.auth.jwt import get_current_user, hash_password
from app.models.user import User
from app.models.empresa import Empresa
from app.models.proceso import Proceso
from app.models.kpi import KPI
from app.models.automatizacion import Automatizacion
from app.models.ejecucion_log import EjecucionLog

router = APIRouter(prefix="/api/admin", tags=["admin"])


# ── Admin guard ───────────────────────────────────────────────────────────────

async def require_admin(user: User = Depends(get_current_user)):
    if user.role != "admin":
        raise HTTPException(status_code=403, detail="Admin requerido")
    return user


# ── Schemas ───────────────────────────────────────────────────────────────────

class AdminUserOut(BaseModel):
    id: str
    email: str
    nombre: str
    apellido: str
    role: str
    plan: str
    is_active: bool
    created_at: Optional[datetime]
    empresa_nombre: Optional[str]
    procesos_count: int
    autos_count: int
    kpis_count: int
    horas_ahorradas: int

    model_config = {"from_attributes": True}


class GlobalStats(BaseModel):
    total_users: int
    total_procesos: int
    total_autos: int
    total_kpis: int
    horas_totales: int
    score_promedio: float
    users_activos: int
    users_free: int
    users_pro: int
    users_enterprise: int


class UpdateUserRequest(BaseModel):
    plan: Optional[str] = None
    is_active: Optional[bool] = None
    role: Optional[str] = None


class CreateUserRequest(BaseModel):
    nombre: str
    apellido: str = ""
    email: EmailStr
    password: str
    plan: str = "free"
    empresa_nombre: str = ""


# ── Helpers ───────────────────────────────────────────────────────────────────

async def _build_user_out(user: User, db: AsyncSession) -> AdminUserOut:
    """Build AdminUserOut for a single user with computed fields."""
    # Get empresa name
    emp_res = await db.execute(
        select(Empresa.nombre).where(Empresa.user_id == user.id).limit(1)
    )
    empresa_nombre = emp_res.scalar_one_or_none()

    # Get empresa ids for this user
    emp_ids_res = await db.execute(
        select(Empresa.id).where(Empresa.user_id == user.id)
    )
    emp_ids = [row[0] for row in emp_ids_res.all()]

    if emp_ids:
        proc_res = await db.execute(
            select(func.count(Proceso.id)).where(Proceso.empresa_id.in_(emp_ids))
        )
        procesos_count = proc_res.scalar_one() or 0

        auto_res = await db.execute(
            select(func.count(Automatizacion.id)).where(Automatizacion.empresa_id.in_(emp_ids))
        )
        autos_count = auto_res.scalar_one() or 0

        kpi_res = await db.execute(
            select(func.count(KPI.id)).where(KPI.empresa_id.in_(emp_ids))
        )
        kpis_count = kpi_res.scalar_one() or 0

        horas_res = await db.execute(
            select(func.coalesce(func.sum(Automatizacion.horas_mes), 0))
            .where(Automatizacion.empresa_id.in_(emp_ids))
        )
        horas_ahorradas = horas_res.scalar_one() or 0
    else:
        procesos_count = 0
        autos_count = 0
        kpis_count = 0
        horas_ahorradas = 0

    return AdminUserOut(
        id=user.id,
        email=user.email,
        nombre=user.nombre,
        apellido=user.apellido,
        role=user.role,
        plan=user.plan,
        is_active=user.is_active,
        created_at=user.created_at,
        empresa_nombre=empresa_nombre,
        procesos_count=procesos_count,
        autos_count=autos_count,
        kpis_count=kpis_count,
        horas_ahorradas=horas_ahorradas,
    )


# ── Routes ────────────────────────────────────────────────────────────────────

@router.get("/users", response_model=list[AdminUserOut])
async def list_users(
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).order_by(User.created_at.desc()))
    users = result.scalars().all()
    return [await _build_user_out(u, db) for u in users]


@router.get("/stats", response_model=GlobalStats)
async def global_stats(
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    total_users = (await db.execute(select(func.count(User.id)))).scalar_one() or 0
    users_activos = (await db.execute(select(func.count(User.id)).where(User.is_active == True))).scalar_one() or 0
    users_free = (await db.execute(select(func.count(User.id)).where(User.plan == "free"))).scalar_one() or 0
    users_pro = (await db.execute(select(func.count(User.id)).where(User.plan == "pro"))).scalar_one() or 0
    users_enterprise = (await db.execute(select(func.count(User.id)).where(User.plan == "enterprise"))).scalar_one() or 0

    total_procesos = (await db.execute(select(func.count(Proceso.id)))).scalar_one() or 0
    total_autos = (await db.execute(select(func.count(Automatizacion.id)))).scalar_one() or 0
    total_kpis = (await db.execute(select(func.count(KPI.id)))).scalar_one() or 0
    horas_totales = (await db.execute(select(func.coalesce(func.sum(Automatizacion.horas_mes), 0)))).scalar_one() or 0
    score_raw = (await db.execute(select(func.avg(Proceso.score)).where(Proceso.score.isnot(None)))).scalar_one()
    score_promedio = round(float(score_raw), 1) if score_raw is not None else 0.0

    return GlobalStats(
        total_users=total_users,
        total_procesos=total_procesos,
        total_autos=total_autos,
        total_kpis=total_kpis,
        horas_totales=horas_totales,
        score_promedio=score_promedio,
        users_activos=users_activos,
        users_free=users_free,
        users_pro=users_pro,
        users_enterprise=users_enterprise,
    )


@router.put("/users/{user_id}", response_model=AdminUserOut)
async def update_user(
    user_id: str,
    body: UpdateUserRequest,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    if body.plan is not None:
        user.plan = body.plan
    if body.is_active is not None:
        user.is_active = body.is_active
    if body.role is not None:
        user.role = body.role

    await db.commit()
    await db.refresh(user)
    return await _build_user_out(user, db)


@router.delete("/users/{user_id}", status_code=204)
async def delete_user(
    user_id: str,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    # Cargar usuario con todas las relaciones para que SQLAlchemy pueda hacer cascade
    result = await db.execute(
        select(User)
        .options(selectinload(User.empresas))
        .where(User.id == user_id)
    )
    user = result.scalar_one_or_none()
    if not user:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")
    if user.id == admin.id:
        raise HTTPException(status_code=400, detail="No puedes eliminar tu propia cuenta de admin")

    # Cascade delete: procesos, KPIs, autos, conversaciones, credenciales → via empresa
    # SQLAlchemy maneja el cascade gracias a cascade="all, delete-orphan" en los modelos
    await db.delete(user)
    await db.commit()


@router.get("/activity")
async def global_activity(
    limit: int = 100,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """Global execution log across all automations (admin only)."""
    result = await db.execute(
        select(EjecucionLog, Automatizacion)
        .join(Automatizacion, EjecucionLog.automatizacion_id == Automatizacion.id)
        .order_by(EjecucionLog.created_at.desc())
        .limit(limit)
    )
    rows = result.all()

    # Build empresa→user map for display
    emp_res = await db.execute(select(Empresa.id, Empresa.nombre, Empresa.user_id))
    emp_map = {e.id: {"nombre": e.nombre, "user_id": e.user_id} for e in emp_res.all()}

    user_ids = list({e["user_id"] for e in emp_map.values()})
    usr_res = await db.execute(select(User.id, User.nombre, User.apellido).where(User.id.in_(user_ids)))
    usr_map = {u.id: f"{u.nombre} {u.apellido}".strip() for u in usr_res.all()}

    items = []
    for log, auto in rows:
        emp = emp_map.get(log.empresa_id, {})
        user_name = usr_map.get(emp.get("user_id", ""), "—")
        items.append({
            "id": log.id,
            "auto_id": log.automatizacion_id,
            "auto_nombre": auto.nombre,
            "empresa_nombre": emp.get("nombre", "—"),
            "user_nombre": user_name,
            "estado": log.estado,
            "mensaje": log.mensaje,
            "triggered_by": log.triggered_by,
            "duracion_ms": log.duracion_ms,
            "created_at": log.created_at,
        })
    return items


@router.get("/sistema")
async def sistema_status(
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    """System health check (admin only)."""
    import httpx
    from app.config import settings
    from app.services.scheduler import listar_jobs_activos

    # Ollama health
    ollama_ok = False
    ollama_models: list = []
    try:
        async with httpx.AsyncClient(timeout=3.0) as client:
            r = await client.get(f"{settings.OLLAMA_URL}/api/tags")
            if r.status_code == 200:
                ollama_ok = True
                data = r.json()
                ollama_models = [m["name"] for m in data.get("models", [])]
    except Exception:
        pass

    # DB health
    db_ok = False
    db_users = 0
    db_procesos = 0
    db_autos = 0
    try:
        db_users = (await db.execute(select(func.count(User.id)))).scalar_one() or 0
        db_procesos = (await db.execute(select(func.count(Proceso.id)))).scalar_one() or 0
        db_autos = (await db.execute(select(func.count(Automatizacion.id)))).scalar_one() or 0
        db_ok = True
    except Exception:
        pass

    # Scheduler
    jobs = listar_jobs_activos()

    return {
        "api": {"ok": True, "version": settings.APP_VERSION, "debug": settings.DEBUG},
        "ollama": {
            "ok": ollama_ok,
            "url": settings.OLLAMA_URL,
            "model": settings.OLLAMA_MODEL,
            "models_disponibles": ollama_models,
        },
        "scheduler": {
            "ok": True,
            "jobs_activos": len(jobs),
            "jobs": jobs[:10],
        },
        "database": {
            "ok": db_ok,
            "users": db_users,
            "procesos": db_procesos,
            "automatizaciones": db_autos,
        },
        "motor_activo": "v5 (Ollama LLM)" if ollama_ok else "v4 (NLP local)",
        "seguridad": {
            "cors_modo": "debug (abierto)" if settings.DEBUG else "producción (restringido)",
            "body_limit_mb": 1,
            "jwt_algoritmo": "HS256",
            "rate_limit": "activo",
        },
    }


@router.post("/users", response_model=AdminUserOut, status_code=201)
async def create_user(
    body: CreateUserRequest,
    admin: User = Depends(require_admin),
    db: AsyncSession = Depends(get_db),
):
    existing = await db.execute(select(User).where(User.email == body.email.lower()))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Ya existe una cuenta con ese correo")

    if len(body.password) < 8:
        raise HTTPException(status_code=422, detail="La contraseña debe tener al menos 8 caracteres")

    user = User(
        email=body.email.lower(),
        hashed_password=hash_password(body.password),
        nombre=body.nombre,
        apellido=body.apellido,
        plan=body.plan,
        role="user",
        is_active=True,
    )
    db.add(user)
    await db.flush()

    if body.empresa_nombre:
        empresa = Empresa(
            user_id=user.id,
            nombre=body.empresa_nombre,
        )
        db.add(empresa)

    await db.commit()
    await db.refresh(user)
    return await _build_user_out(user, db)
