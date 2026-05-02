import re
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel, field_validator
from typing import Optional
from datetime import datetime
from app.database import get_db
from app.models.proceso import Proceso
from app.models.empresa import Empresa
from app.models.user import User
from app.auth.jwt import get_current_user

router = APIRouter(prefix="/api/procesos", tags=["procesos"])

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


class ProcesoOut(BaseModel):
    id: str
    nombre: str
    descripcion: Optional[str] = None
    responsable: Optional[str] = None
    frecuencia: Optional[str] = None
    duracion_h: Optional[int] = None
    score: Optional[int] = None
    estado: str
    notas: Optional[str] = None
    created_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


class ProcesoCreate(BaseModel):
    nombre: str
    descripcion: Optional[str] = None
    responsable: Optional[str] = None
    frecuencia: Optional[str] = None
    duracion_h: Optional[int] = None
    score: Optional[int] = None
    estado: str = "pendiente"
    notas: Optional[str] = None

    @field_validator("nombre")
    @classmethod
    def validate_nombre(cls, v: str) -> str:
        result = _sanitize_str(v, 255)
        if not result:
            raise ValueError("El nombre no puede estar vacío")
        return result

    @field_validator("descripcion", "notas")
    @classmethod
    def validate_long_text(cls, v: Optional[str]) -> Optional[str]:
        return _sanitize_str(v, 1000)

    @field_validator("responsable", "frecuencia", "estado")
    @classmethod
    def validate_short_str(cls, v: Optional[str]) -> Optional[str]:
        return _sanitize_str(v, 255)


class ProcesoUpdate(BaseModel):
    nombre: Optional[str] = None
    descripcion: Optional[str] = None
    responsable: Optional[str] = None
    frecuencia: Optional[str] = None
    duracion_h: Optional[int] = None
    score: Optional[int] = None
    estado: Optional[str] = None
    notas: Optional[str] = None

    @field_validator("nombre")
    @classmethod
    def validate_nombre(cls, v: Optional[str]) -> Optional[str]:
        return _sanitize_str(v, 255)

    @field_validator("descripcion", "notas")
    @classmethod
    def validate_long_text(cls, v: Optional[str]) -> Optional[str]:
        return _sanitize_str(v, 1000)

    @field_validator("responsable", "frecuencia", "estado")
    @classmethod
    def validate_short_str(cls, v: Optional[str]) -> Optional[str]:
        return _sanitize_str(v, 255)


async def _get_empresa_id(db: AsyncSession, user: User) -> str:
    result = await db.execute(select(Empresa).where(Empresa.user_id == user.id))
    empresa = result.scalars().first()
    if not empresa:
        raise HTTPException(status_code=404, detail="No tienes empresa registrada")
    return empresa.id


@router.get("", response_model=list[ProcesoOut])
async def list_procesos(
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    empresa_id = await _get_empresa_id(db, user)
    result = await db.execute(
        select(Proceso).where(Proceso.empresa_id == empresa_id).order_by(Proceso.created_at.desc())
    )
    return result.scalars().all()


@router.post("", response_model=ProcesoOut, status_code=201)
async def create_proceso(
    body: ProcesoCreate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    empresa_id = await _get_empresa_id(db, user)
    proceso = Proceso(empresa_id=empresa_id, **body.model_dump())
    db.add(proceso)
    await db.commit()
    await db.refresh(proceso)
    return proceso


@router.put("/{proceso_id}", response_model=ProcesoOut)
async def update_proceso(
    proceso_id: str,
    body: ProcesoUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    empresa_id = await _get_empresa_id(db, user)
    result = await db.execute(
        select(Proceso).where(Proceso.id == proceso_id, Proceso.empresa_id == empresa_id)
    )
    proceso = result.scalar_one_or_none()
    if not proceso:
        raise HTTPException(status_code=404, detail="Proceso no encontrado")
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(proceso, field, value)
    await db.commit()
    await db.refresh(proceso)
    return proceso


@router.delete("/{proceso_id}", status_code=204)
async def delete_proceso(
    proceso_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    empresa_id = await _get_empresa_id(db, user)
    result = await db.execute(
        select(Proceso).where(Proceso.id == proceso_id, Proceso.empresa_id == empresa_id)
    )
    proceso = result.scalar_one_or_none()
    if not proceso:
        raise HTTPException(status_code=404, detail="Proceso no encontrado")
    await db.delete(proceso)
    await db.commit()
