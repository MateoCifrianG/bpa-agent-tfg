import re
from typing import Optional
from pydantic import BaseModel, EmailStr, field_validator, model_validator


_HTML_RE = re.compile(r"<[^>]+>", re.IGNORECASE)


def _reject_html(value: str, field_name: str) -> str:
    if _HTML_RE.search(value):
        raise ValueError(f"El campo '{field_name}' contiene etiquetas HTML no permitidas")
    return value


class LoginRequest(BaseModel):
    email: EmailStr
    password: str

    @field_validator("email")
    @classmethod
    def email_max_len(cls, v: str) -> str:
        if len(v) > 255:
            raise ValueError("El email no puede superar los 255 caracteres")
        return v

    @field_validator("password")
    @classmethod
    def password_limits(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("La contraseña debe tener al menos 8 caracteres")
        if len(v) > 128:
            raise ValueError("La contraseña no puede superar los 128 caracteres")
        return v


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    nombre: str
    apellido: str = ""
    empresa: str
    sector: str = ""
    empleados: int = 0
    plan: str = "free"

    @field_validator("email")
    @classmethod
    def email_max_len(cls, v: str) -> str:
        if len(v) > 255:
            raise ValueError("El email no puede superar los 255 caracteres")
        return v

    @field_validator("password")
    @classmethod
    def password_limits(cls, v: str) -> str:
        if len(v) < 8:
            raise ValueError("La contraseña debe tener al menos 8 caracteres")
        if len(v) > 128:
            raise ValueError("La contraseña no puede superar los 128 caracteres")
        _reject_html(v, "password")
        return v

    @field_validator("nombre", "apellido")
    @classmethod
    def nombre_apellido(cls, v: str) -> str:
        v = v.strip()
        if len(v) > 100:
            raise ValueError("El nombre/apellido no puede superar los 100 caracteres")
        _reject_html(v, "nombre/apellido")
        return v

    @field_validator("empresa", "sector")
    @classmethod
    def empresa_sector(cls, v: str) -> str:
        v = v.strip()
        if len(v) > 255:
            raise ValueError("El campo no puede superar los 255 caracteres")
        _reject_html(v, "empresa/sector")
        return v


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: Optional[str] = None
    token_type: str = "bearer"
    user: "UserOut"


class UserOut(BaseModel):
    id: str
    email: str
    nombre: str
    apellido: str
    role: str
    plan: str
    is_active: bool
    avatar: str

    model_config = {"from_attributes": True}


TokenResponse.model_rebuild()
