from sqlalchemy import String, ForeignKey, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from uuid import uuid4
from app.database import Base

class Credencial(Base):
    __tablename__ = "credenciales"

    id:         Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    empresa_id: Mapped[str] = mapped_column(String(36), ForeignKey("empresas.id"), nullable=False, index=True)
    servicio:   Mapped[str] = mapped_column(String(100), nullable=False)   # "gmail", "drive", "n8n", etc.
    valor_cifrado: Mapped[str] = mapped_column(String(500), nullable=False)  # token cifrado con Fernet
    created_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at: Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now())

    empresa: Mapped["Empresa"] = relationship(back_populates="credenciales")
