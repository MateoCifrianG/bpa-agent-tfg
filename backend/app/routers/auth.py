from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from pydantic import BaseModel
from typing import Optional
from app.database import get_db
from app.models.user import User
from app.models.empresa import Empresa
from app.auth.jwt import (
    hash_password, verify_password,
    create_access_token, create_refresh_token,
    decode_token, get_current_user,
)
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserOut
from app.config import settings

router = APIRouter(prefix="/api/auth", tags=["auth"])


class RefreshBody(BaseModel):
    refresh_token: Optional[str] = None


def _set_refresh_cookie(response: Response, token: str):
    response.set_cookie(
        key="refresh_token", value=token,
        httponly=True, secure=False, samesite="lax",
        max_age=60 * 60 * 24 * settings.REFRESH_TOKEN_EXPIRE_DAYS,
    )


@router.post("/login")
async def login(body: LoginRequest, response: Response, db: AsyncSession = Depends(get_db)):
    result = await db.execute(select(User).where(User.email == body.email.lower()))
    user = result.scalar_one_or_none()
    if not user or not verify_password(body.password, user.hashed_password):
        raise HTTPException(status_code=401, detail="Credenciales incorrectas")
    if not user.is_active:
        raise HTTPException(status_code=403, detail="Cuenta desactivada")

    access_token  = create_access_token({"sub": user.id, "role": user.role})
    refresh_token = create_refresh_token({"sub": user.id})

    _set_refresh_cookie(response, refresh_token)
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": UserOut.model_validate(user).model_dump(),
    }


@router.post("/register", status_code=201)
async def register(body: RegisterRequest, response: Response, db: AsyncSession = Depends(get_db)):
    existing = await db.execute(select(User).where(User.email == body.email.lower()))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Ya existe una cuenta con ese correo")

    user = User(
        email=body.email.lower(),
        hashed_password=hash_password(body.password),
        nombre=body.nombre,
        apellido=body.apellido,
        plan=body.plan,
    )
    db.add(user)
    await db.flush()

    empresa = Empresa(
        user_id=user.id,
        nombre=body.empresa,
        sector=body.sector,
        empleados=body.empleados,
    )
    db.add(empresa)
    await db.commit()
    await db.refresh(user)

    access_token  = create_access_token({"sub": user.id, "role": user.role})
    refresh_token = create_refresh_token({"sub": user.id})
    _set_refresh_cookie(response, refresh_token)
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": UserOut.model_validate(user).model_dump(),
    }


@router.get("/me", response_model=UserOut)
async def me(user: User = Depends(get_current_user)):
    return UserOut.model_validate(user)


@router.post("/refresh")
async def refresh_token(request: Request, body: RefreshBody = RefreshBody(), db: AsyncSession = Depends(get_db)):
    token = request.cookies.get("refresh_token") or (body.refresh_token if body else None)
    if not token:
        raise HTTPException(status_code=401, detail="No hay refresh token")
    payload = decode_token(token)
    if payload.get("type") != "refresh":
        raise HTTPException(status_code=401, detail="Token inválido")
    user_id = payload.get("sub")
    result = await db.execute(select(User).where(User.id == user_id))
    user = result.scalar_one_or_none()
    if not user or not user.is_active:
        raise HTTPException(status_code=401, detail="Usuario no encontrado o inactivo")
    access_token = create_access_token({"sub": user.id, "role": user.role})
    return {"access_token": access_token, "user": UserOut.model_validate(user)}


@router.post("/logout")
async def logout(response: Response):
    response.delete_cookie("refresh_token")
    return {"ok": True}
