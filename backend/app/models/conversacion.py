from sqlalchemy import String, Text, ForeignKey, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from uuid import uuid4
from app.database import Base


class Conversacion(Base):
    __tablename__ = "conversaciones"

    id:          Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    empresa_id:  Mapped[str] = mapped_column(String(36), ForeignKey("empresas.id"), nullable=False, index=True)
    titulo:      Mapped[str | None] = mapped_column(String(255))
    fase:        Mapped[str]        = mapped_column(String(30), default="diagnostico")  # diagnostico | analisis | propuesta | ejecucion
    historial:   Mapped[str | None] = mapped_column(Text)   # JSON de mensajes (sanitizado)
    tokens_used: Mapped[int]        = mapped_column(default=0)
    created_at:  Mapped[DateTime]   = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at:  Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), onupdate=func.now())

    empresa: Mapped["Empresa"] = relationship(back_populates="conversaciones")
