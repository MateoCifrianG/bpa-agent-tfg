from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from pydantic import BaseModel
from typing import Optional
from app.database import get_db
from app.models.empresa import Empresa
from app.models.proceso import Proceso
from app.models.kpi import KPI
from app.models.automatizacion import Automatizacion
from app.models.user import User
from app.auth.jwt import get_current_user

router = APIRouter(prefix="/api/empresa", tags=["empresa"])


class EmpresaOut(BaseModel):
    id: str
    nombre: str
    sector: Optional[str] = None
    empleados: Optional[int] = None
    ciudad: Optional[str] = None
    descripcion: Optional[str] = None

    model_config = {"from_attributes": True}


class EmpresaUpdate(BaseModel):
    nombre: Optional[str] = None
    sector: Optional[str] = None
    empleados: Optional[int] = None
    ciudad: Optional[str] = None
    descripcion: Optional[str] = None


class EmpresaStats(BaseModel):
    procesos_count: int
    autos_count: int
    kpis_count: int
    horas_ahorradas: int
    score_promedio: Optional[float]
    autos_activas: int


async def _get_empresa(db: AsyncSession, user: User) -> Empresa:
    result = await db.execute(select(Empresa).where(Empresa.user_id == user.id))
    empresa = result.scalars().first()
    if not empresa:
        raise HTTPException(status_code=404, detail="No tienes empresa registrada")
    return empresa


@router.get("/mia", response_model=EmpresaOut)
async def get_mi_empresa(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    return await _get_empresa(db, user)


@router.put("/mia", response_model=EmpresaOut)
async def update_mi_empresa(
    body: EmpresaUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    empresa = await _get_empresa(db, user)
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(empresa, field, value)
    await db.commit()
    await db.refresh(empresa)
    return empresa


@router.get("/mia/stats", response_model=EmpresaStats)
async def get_stats(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    empresa = await _get_empresa(db, user)
    eid = empresa.id

    # Conteos en paralelo con consultas individuales
    procesos_res = await db.execute(
        select(func.count()).select_from(Proceso).where(Proceso.empresa_id == eid)
    )
    procesos_count: int = procesos_res.scalar_one()

    autos_res = await db.execute(
        select(func.count()).select_from(Automatizacion).where(Automatizacion.empresa_id == eid)
    )
    autos_count: int = autos_res.scalar_one()

    kpis_res = await db.execute(
        select(func.count()).select_from(KPI).where(KPI.empresa_id == eid)
    )
    kpis_count: int = kpis_res.scalar_one()

    horas_res = await db.execute(
        select(func.coalesce(func.sum(Automatizacion.horas_mes), 0))
        .where(Automatizacion.empresa_id == eid)
    )
    horas_ahorradas: int = horas_res.scalar_one()

    score_res = await db.execute(
        select(func.avg(Proceso.score))
        .where(Proceso.empresa_id == eid, Proceso.score.isnot(None))
    )
    score_promedio_raw = score_res.scalar_one()
    score_promedio: Optional[float] = round(float(score_promedio_raw), 1) if score_promedio_raw is not None else None

    activas_res = await db.execute(
        select(func.count())
        .select_from(Automatizacion)
        .where(Automatizacion.empresa_id == eid, Automatizacion.estado == "activa")
    )
    autos_activas: int = activas_res.scalar_one()

    return EmpresaStats(
        procesos_count=procesos_count,
        autos_count=autos_count,
        kpis_count=kpis_count,
        horas_ahorradas=horas_ahorradas,
        score_promedio=score_promedio,
        autos_activas=autos_activas,
    )
