from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.security import OAuth2PasswordBearer
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
    decode_token, get_current_user, revoke_token,
)
from app.schemas.auth import LoginRequest, RegisterRequest, TokenResponse, UserOut
from app.config import settings
from app.security.sanitize import limpiar_email, limpiar_nombre, validar_password
from app.security.audit import log_event

router = APIRouter(prefix="/api/auth", tags=["auth"])

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login", auto_error=False)


class RefreshBody(BaseModel):
    refresh_token: Optional[str] = None


def _set_refresh_cookie(response: Response, token: str):
    response.set_cookie(
        key="refresh_token", value=token,
        httponly=True, secure=False, samesite="lax",
        max_age=60 * 60 * 24 * settings.REFRESH_TOKEN_EXPIRE_DAYS,
    )


@router.post("/login")
async def login(
    body: LoginRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    email = limpiar_email(body.email)
    result = await db.execute(select(User).where(User.email == email))
    user = result.scalar_one_or_none()

    if not user or not verify_password(body.password, user.hashed_password):
        await log_event(db, "login_fail", request=request,
                        detail={"email": email}, status="fail")
        await db.commit()
        raise HTTPException(status_code=401, detail="Credenciales incorrectas")
    if not user.is_active:
        await log_event(db, "login_blocked", user_id=user.id, request=request, status="fail")
        await db.commit()
        raise HTTPException(status_code=403, detail="Cuenta desactivada")

    access_token  = create_access_token({"sub": user.id, "role": user.role})
    refresh_token = create_refresh_token({"sub": user.id})

    await log_event(db, "login", user_id=user.id, request=request)
    await db.commit()

    _set_refresh_cookie(response, refresh_token)
    return {
        "access_token": access_token,
        "refresh_token": refresh_token,
        "token_type": "bearer",
        "user": UserOut.model_validate(user).model_dump(),
    }


@router.post("/register", status_code=201)
async def register(
    body: RegisterRequest,
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
):
    email = limpiar_email(body.email)
    nombre = limpiar_nombre(body.nombre)
    apellido = limpiar_nombre(body.apellido or "")
    empresa_nombre = limpiar_nombre(body.empresa)

    # Validar contraseña
    pwd_errors = validar_password(body.password)
    if pwd_errors:
        raise HTTPException(status_code=422, detail={"password": pwd_errors})

    existing = await db.execute(select(User).where(User.email == email))
    if existing.scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Ya existe una cuenta con ese correo")

    user = User(
        email=email,
        hashed_password=hash_password(body.password),
        nombre=nombre,
        apellido=apellido,
        plan=body.plan,
    )
    db.add(user)
    await db.flush()

    empresa = Empresa(
        user_id=user.id,
        nombre=empresa_nombre,
        sector=body.sector,
        empleados=body.empleados,
    )
    db.add(empresa)

    access_token  = create_access_token({"sub": user.id, "role": user.role})
    refresh_token = create_refresh_token({"sub": user.id})

    await log_event(db, "register", user_id=user.id, request=request,
                    detail={"email": email, "plan": body.plan})
    await db.commit()
    await db.refresh(user)

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
async def refresh_token(
    request: Request,
    body: RefreshBody = RefreshBody(),
    db: AsyncSession = Depends(get_db),
):
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
async def logout(
    request: Request,
    response: Response,
    db: AsyncSession = Depends(get_db),
    token: Optional[str] = Depends(oauth2_scheme),
):
    # Revocar access token si se envía en la cabecera
    if token:
        try:
            payload = decode_token(token)
            revoke_token(token)
            await log_event(db, "logout", user_id=payload.get("sub"), request=request)
            await db.commit()
        except Exception:
            pass  # token ya inválido, no hay problema

    response.delete_cookie("refresh_token")
    return {"ok": True}
