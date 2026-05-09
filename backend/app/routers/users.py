from fastapi import APIRouter, Depends, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from sqlalchemy.orm import selectinload
from pydantic import BaseModel
from typing import Optional
from app.database import get_db
from app.models.user import User
from app.auth.jwt import get_current_user, hash_password, verify_password
from app.schemas.auth import UserOut
from fastapi import HTTPException

router = APIRouter(prefix="/api/users", tags=["users"])


class UserUpdate(BaseModel):
    nombre: Optional[str] = None
    apellido: Optional[str] = None
    telefono: Optional[str] = None
    ciudad: Optional[str] = None


class PasswordChange(BaseModel):
    password_actual: str
    password_nuevo: str


class DeleteAccountRequest(BaseModel):
    password: str


@router.get("/me", response_model=UserOut)
async def get_me(user: User = Depends(get_current_user)):
    return UserOut.model_validate(user)


@router.put("/me", response_model=UserOut)
async def update_me(
    body: UserUpdate,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    for field, value in body.model_dump(exclude_none=True).items():
        setattr(user, field, value)
    await db.commit()
    await db.refresh(user)
    return UserOut.model_validate(user)


@router.post("/me/password")
async def change_password(
    body: PasswordChange,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not verify_password(body.password_actual, user.hashed_password):
        raise HTTPException(status_code=400, detail="Contraseña actual incorrecta")
    user.hashed_password = hash_password(body.password_nuevo)
    await db.commit()
    return {"ok": True}


@router.post("/me/deactivate")
async def deactivate_me(
    body: DeleteAccountRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=403, detail="Contraseña incorrecta")
    user.is_active = False
    await db.commit()
    response.delete_cookie("refresh_token")
    return {"ok": True}


@router.delete("/me", status_code=204)
async def delete_me(
    body: DeleteAccountRequest,
    response: Response,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    if not verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=403, detail="Contraseña incorrecta")
    result = await db.execute(
        select(User).where(User.id == user.id).options(selectinload(User.empresas))
    )
    full_user = result.scalar_one()
    await db.delete(full_user)
    await db.commit()
    response.delete_cookie("refresh_token")
