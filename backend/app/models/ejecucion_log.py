"""
EjecucionLog — registro histórico de cada vez que se ejecuta una automatización.
"""
from sqlalchemy import String, Text, ForeignKey, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from uuid import uuid4
from app.database import Base


class EjecucionLog(Base):
    __tablename__ = "ejecuciones_log"

    id:               Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    automatizacion_id: Mapped[str] = mapped_column(String(36), ForeignKey("automatizaciones.id", ondelete="CASCADE"), nullable=False, index=True)
    empresa_id:       Mapped[str] = mapped_column(String(36), ForeignKey("empresas.id"), nullable=False, index=True)
    estado:           Mapped[str] = mapped_column(String(20), default="ok")   # ok | error | timeout
    mensaje:          Mapped[str | None] = mapped_column(Text)                # resultado o error
    triggered_by:     Mapped[str] = mapped_column(String(30), default="manual")  # manual | cron | webhook | agente
    duracion_ms:      Mapped[int | None] = mapped_column(String(10))
    created_at:       Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)

    automatizacion: Mapped["Automatizacion"] = relationship(back_populates="logs")
