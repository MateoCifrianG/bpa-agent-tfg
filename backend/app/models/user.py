from sqlalchemy import String, Boolean, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from uuid import uuid4
from app.database import Base


class User(Base):
    __tablename__ = "users"

    id:               Mapped[str]  = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    email:            Mapped[str]  = mapped_column(String(255), unique=True, nullable=False, index=True)
    hashed_password:  Mapped[str]  = mapped_column(String(255), nullable=False)
    nombre:           Mapped[str]  = mapped_column(String(100), nullable=False)
    apellido:         Mapped[str]  = mapped_column(String(100), nullable=False, default="")
    telefono:         Mapped[str | None] = mapped_column(String(20))
    ciudad:           Mapped[str | None] = mapped_column(String(100))
    role:             Mapped[str]  = mapped_column(String(20), nullable=False, default="user")
    plan:             Mapped[str]  = mapped_column(String(20), nullable=False, default="free")
    is_active:        Mapped[bool] = mapped_column(Boolean, default=True)
    created_at:       Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at:       Mapped[DateTime] = mapped_column(DateTime(timezone=True), onupdate=func.now(), nullable=True)

    empresas:         Mapped[list["Empresa"]] = relationship(back_populates="user", cascade="all, delete-orphan")

    @property
    def avatar(self) -> str:
        return (self.nombre[0] + self.apellido[0]).upper() if self.apellido else self.nombre[:2].upper()
