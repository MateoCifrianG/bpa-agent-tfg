from sqlalchemy import String, Float, ForeignKey, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from uuid import uuid4
from app.database import Base


class KPI(Base):
    __tablename__ = "kpis"

    id:          Mapped[str]   = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    empresa_id:  Mapped[str]   = mapped_column(String(36), ForeignKey("empresas.id"), nullable=False, index=True)
    nombre:      Mapped[str]   = mapped_column(String(255), nullable=False)
    valor:       Mapped[str]   = mapped_column(String(100))   # string para soportar "2.1 días", "68%", etc.
    objetivo:    Mapped[str | None] = mapped_column(String(100))
    unidad:      Mapped[str | None] = mapped_column(String(50))
    tendencia:   Mapped[str]   = mapped_column(String(10), default="up")   # up | down | flat
    categoria:   Mapped[str | None] = mapped_column(String(50))            # tiempo | coste | calidad | volumen
    created_at:  Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at:  Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), onupdate=func.now())

    empresa: Mapped["Empresa"] = relationship(back_populates="kpis")
