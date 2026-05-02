"""
Endpoint de credenciales MCP.
REGLA DE SEGURIDAD: Nunca devuelve el valor de la credencial en la respuesta.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from pydantic import BaseModel
from app.database import get_db
from app.auth.jwt import get_current_user
from app.models.user import User
from app.models.empresa import Empresa
from app.services import credenciales_service
from sqlalchemy import select

router = APIRouter(prefix="/api/credenciales", tags=["credenciales"])


class CredencialIn(BaseModel):
    servicio: str
    token: str


class CredencialOut(BaseModel):
    servicio: str
    empresa_id: str
    mensaje: str = "Credencial guardada correctamente"
    # NUNCA incluir el token aquí


@router.post("", response_model=CredencialOut, status_code=status.HTTP_201_CREATED)
async def guardar_credencial(
    data: CredencialIn,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    # Obtener empresa del usuario
    result = await db.execute(
        select(Empresa).where(Empresa.user_id == current_user.id)
    )
    empresa = result.scalars().first()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")

    await credenciales_service.guardar_credencial(db, empresa.id, data.servicio, data.token)

    return CredencialOut(servicio=data.servicio, empresa_id=empresa.id)


@router.delete("/{servicio}", status_code=status.HTTP_204_NO_CONTENT)
async def eliminar_credencial(
    servicio: str,
    current_user: User = Depends(get_current_user),
    db: AsyncSession = Depends(get_db),
):
    result = await db.execute(
        select(Empresa).where(Empresa.user_id == current_user.id)
    )
    empresa = result.scalars().first()
    if not empresa:
        raise HTTPException(status_code=404, detail="Empresa no encontrada")

    deleted = await credenciales_service.eliminar_credencial(db, empresa.id, servicio)
    if not deleted:
        raise HTTPException(status_code=404, detail="Credencial no encontrada")
