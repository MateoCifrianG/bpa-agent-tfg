import re
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, field_validator
from typing import Optional
from datetime import datetime
from app.database import get_db
from app.models.kpi import KPI
from app.models.empresa import Empresa
from app.models.user import User
from app.auth.jwt import get_current_user

router = APIRouter(prefix="/api/kpis", tags=["kpis"])

_XSS_RE = re.compile(r"<script|javascript:", re.IGNORECASE)


def _sanitize_str(v: str | None, max_len: int = 255) -> str | None:
    if v is None:
        return None
    v = v.strip()
    if len(v) > max_len:
        raise ValueError(f"El campo no puede superar los {max_len} caracteres")
    if _XSS_RE.search(v):
        raise ValueError("El campo contiene contenido no permitido")
    return v


class KPIOut(BaseModel):
    id: str
    nombre: str
    valor: str
    objetivo: Optional[str] = None
    unidad: Optional[str] = None
    tendencia: str
    categoria: Optional[str] = None
    updated_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class KPICreate(BaseModel):
    nombre: str
    valor: str
    objetivo: Optional[str] = None
    unidad: Optional[str] = None
    tendencia: str = "up"
    categoria: Optional[str] = None

    @field_validator("nombre", "valor", "objetivo", "unidad", "tendencia", "categoria")
    @classmethod
    def validate_strings(cls, v: Optional[str]) -> Optional[str]:
        return _sanitize_str(v, 255)


class KPIUpdate(BaseModel):
    nombre: Optional[str] = None
    valor: Optional[str] = None
    objetivo: Optional[str] = None
    unidad: Optional[str] = None
    tendencia: Optional[str] = None
    categoria: Optional[str] = None

    @field_validator("nombre", "valor", "objetivo", "unidad", "tendencia", "categoria")
    @classmethod
    def validate_strings(cls, v: Optional[str]) -> Optional[str]:
        return _sanitize_str(v, 255)


async def _get_empresa_id(db: AsyncSession, user: User) -> str:
    result = await db.execute(select(Empresa).where(Empresa.user_id == user.id))
    empresa = result.scalars().first()
    if not empresa:
        raise HTTPException(status_code=404, detail="No tienes empresa registrada")
    return empresa.id


@router.get("", response_model=list[KPIOut])
async def list_kpis(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    empresa_id = await _get_empresa_id(db, user)
    result = await db.execute(
        select(KPI).where(KPI.empresa_id == empresa_id).order_by(KPI.created_at.desc())
    )
    return result.scalars().all()


@router.post("", response_model=KPIOut, status_code=201)
async def create_kpi(
    body: KPICreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    empresa_id = await _get_empresa_id(db, user)
    kpi = KPI(empresa_id=empresa_id, **body.model_dump())
    db.add(kpi)
    await db.commit()
    await db.refresh(kpi)
    return kpi


@router.put("/{kpi_id}", response_model=KPIOut)
async def update_kpi(
    kpi_id: str,
    body: KPIUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    empresa_id = await _get_empresa_id(db, user)
    result = await db.execute(
        select(KPI).where(KPI.id == kpi_id, KPI.empresa_id == empresa_id)
    )
    kpi = result.scalar_one_or_none()
    if not kpi:
        raise HTTPException(status_code=404, detail="KPI no encontrado")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(kpi, field, value)
    await db.commit()
    await db.refresh(kpi)
    return kpi


@router.delete("/{kpi_id}", status_code=204)
async def delete_kpi(
    kpi_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    empresa_id = await _get_empresa_id(db, user)
    result = await db.execute(
        select(KPI).where(KPI.id == kpi_id, KPI.empresa_id == empresa_id)
    )
    kpi = result.scalar_one_or_none()
    if not kpi:
        raise HTTPException(status_code=404, detail="KPI no encontrado")
    await db.delete(kpi)
    await db.commit()
