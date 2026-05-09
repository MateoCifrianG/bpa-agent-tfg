from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, field_validator
from typing import Optional
from datetime import datetime
from app.database import get_db
from app.models.automatizacion import Automatizacion
from app.models.empresa import Empresa
from app.models.proceso import Proceso
from app.models.user import User
from app.auth.jwt import get_current_user
from app.security.sanitize import limpiar_nombre

router = APIRouter(prefix="/api/automatizaciones", tags=["automatizaciones"])


def _sanitize_str(v: str | None, max_len: int = 255) -> str | None:
    if v is None:
        return None
    return limpiar_nombre(v, max_len=max_len)


class AutomatizacionOut(BaseModel):
    id: str
    nombre: str
    descripcion: Optional[str] = None
    herramienta: Optional[str] = None
    estado: str
    ejecuciones: int
    horas_mes: Optional[int] = None
    proceso_id: Optional[str] = None
    last_run_at: Optional[datetime] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class AutomatizacionCreate(BaseModel):
    nombre: str
    descripcion: Optional[str] = None
    herramienta: Optional[str] = None
    estado: str = "pendiente"
    ejecuciones: int = 0
    horas_mes: Optional[int] = None
    proceso_id: Optional[str] = None

    @field_validator("nombre", "herramienta", "estado")
    @classmethod
    def validate_short_str(cls, v: Optional[str]) -> Optional[str]:
        return _sanitize_str(v, 255)

    @field_validator("descripcion")
    @classmethod
    def validate_descripcion(cls, v: Optional[str]) -> Optional[str]:
        return _sanitize_str(v, 1000)


class AutomatizacionUpdate(BaseModel):
    nombre: Optional[str] = None
    descripcion: Optional[str] = None
    herramienta: Optional[str] = None
    estado: Optional[str] = None
    ejecuciones: Optional[int] = None
    horas_mes: Optional[int] = None

    @field_validator("nombre", "herramienta", "estado")
    @classmethod
    def validate_short_str(cls, v: Optional[str]) -> Optional[str]:
        return _sanitize_str(v, 255)

    @field_validator("descripcion")
    @classmethod
    def validate_descripcion(cls, v: Optional[str]) -> Optional[str]:
        return _sanitize_str(v, 1000)


async def _get_empresa_id(db: AsyncSession, user: User) -> str:
    result = await db.execute(select(Empresa).where(Empresa.user_id == user.id))
    empresa = result.scalars().first()
    if not empresa:
        raise HTTPException(status_code=404, detail="No tienes empresa registrada")
    return empresa.id


@router.get("/{auto_id}", response_model=AutomatizacionOut)
async def get_automatizacion(
    auto_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    empresa_id = await _get_empresa_id(db, user)
    result = await db.execute(
        select(Automatizacion).where(Automatizacion.id == auto_id, Automatizacion.empresa_id == empresa_id)
    )
    auto = result.scalar_one_or_none()
    if not auto:
        raise HTTPException(status_code=404, detail="Automatización no encontrada")
    return auto


@router.get("", response_model=list[AutomatizacionOut])
async def list_automatizaciones(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    empresa_id = await _get_empresa_id(db, user)
    result = await db.execute(
        select(Automatizacion)
        .where(Automatizacion.empresa_id == empresa_id)
        .order_by(Automatizacion.created_at.desc())
    )
    return result.scalars().all()


async def _validate_proceso_ownership(db: AsyncSession, proceso_id: str, empresa_id: str):
    r = await db.execute(select(Proceso).where(Proceso.id == proceso_id, Proceso.empresa_id == empresa_id))
    if not r.scalar_one_or_none():
        raise HTTPException(status_code=403, detail="Proceso no pertenece a tu empresa")


@router.post("", response_model=AutomatizacionOut, status_code=201)
async def create_automatizacion(
    body: AutomatizacionCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    empresa_id = await _get_empresa_id(db, user)
    if body.proceso_id:
        await _validate_proceso_ownership(db, body.proceso_id, empresa_id)
    auto = Automatizacion(empresa_id=empresa_id, **body.model_dump())
    db.add(auto)
    await db.commit()
    await db.refresh(auto)
    return auto


@router.put("/{auto_id}", response_model=AutomatizacionOut)
async def update_automatizacion(
    auto_id: str,
    body: AutomatizacionUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    empresa_id = await _get_empresa_id(db, user)
    result = await db.execute(
        select(Automatizacion).where(
            Automatizacion.id == auto_id,
            Automatizacion.empresa_id == empresa_id
        )
    )
    auto = result.scalar_one_or_none()
    if not auto:
        raise HTTPException(status_code=404, detail="Automatización no encontrada")
    if body.proceso_id:
        await _validate_proceso_ownership(db, body.proceso_id, empresa_id)
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(auto, field, value)
    await db.commit()
    await db.refresh(auto)
    return auto


@router.delete("/{auto_id}", status_code=204)
async def delete_automatizacion(
    auto_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    empresa_id = await _get_empresa_id(db, user)
    result = await db.execute(
        select(Automatizacion).where(
            Automatizacion.id == auto_id,
            Automatizacion.empresa_id == empresa_id
        )
    )
    auto = result.scalar_one_or_none()
    if not auto:
        raise HTTPException(status_code=404, detail="Automatización no encontrada")
    await db.delete(auto)
    await db.commit()
