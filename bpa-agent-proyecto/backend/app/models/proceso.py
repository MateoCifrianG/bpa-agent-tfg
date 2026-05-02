from sqlalchemy import String, Integer, Text, ForeignKey, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from uuid import uuid4
from app.database import Base


class Proceso(Base):
    __tablename__ = "procesos"

    id:          Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    empresa_id:  Mapped[str] = mapped_column(String(36), ForeignKey("empresas.id"), nullable=False, index=True)
    nombre:      Mapped[str] = mapped_column(String(255), nullable=False)
    descripcion: Mapped[str | None] = mapped_column(Text)
    responsable: Mapped[str | None] = mapped_column(String(150))
    frecuencia:  Mapped[str | None] = mapped_column(String(50))   # diario, semanal, mensual
    duracion_h:  Mapped[int | None] = mapped_column(Integer)       # horas invertidas/mes
    score:       Mapped[int | None] = mapped_column(Integer)       # 0-100
    estado:      Mapped[str]        = mapped_column(String(30), default="pendiente")  # pendiente | analizado | critico | optimizado
    notas:       Mapped[str | None] = mapped_column(Text)
    created_at:  Mapped[DateTime]   = mapped_column(DateTime(timezone=True), server_default=func.now())
    updated_at:  Mapped[DateTime | None] = mapped_column(DateTime(timezone=True), onupdate=func.now())

    empresa:         Mapped["Empresa"]          = relationship(back_populates="procesos")
    automatizaciones: Mapped[list["Automatizacion"]] = relationship(back_populates="proceso")
