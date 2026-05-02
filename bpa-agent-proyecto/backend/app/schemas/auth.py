from pydantic import BaseModel, EmailStr


class LoginRequest(BaseModel):
    email: EmailStr
    password: str


class RegisterRequest(BaseModel):
    email: EmailStr
    password: str
    nombre: str
    apellido: str = ""
    empresa: str
    sector: str = ""
    empleados: int = 0
    plan: str = "free"


class TokenResponse(BaseModel):
    access_token: str
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
