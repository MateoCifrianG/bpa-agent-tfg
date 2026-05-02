from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional
from app.database import get_db
from app.models.empresa import Empresa
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
