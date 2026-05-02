from sqlalchemy import String, Integer, ForeignKey, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from uuid import uuid4
from app.database import Base


class Empresa(Base):
    __tablename__ = "empresas"

    id:          Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id:     Mapped[str] = mapped_column(String(36), ForeignKey("users.id"), nullable=False, index=True)
    nombre:      Mapped[str] = mapped_column(String(255), nullable=False)
    sector:      Mapped[str | None] = mapped_column(String(100))
    empleados:   Mapped[int | None] = mapped_column(Integer)
    ciudad:      Mapped[str | None] = mapped_column(String(100))
    descripcion: Mapped[str | None] = mapped_column(String(500))
    created_at:  Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now())

    user:            Mapped["User"]            = relationship(back_populates="empresas")
    procesos:        Mapped[list["Proceso"]]   = relationship(back_populates="empresa", cascade="all, delete-orphan")
    automatizaciones: Mapped[list["Automatizacion"]] = relationship(back_populates="empresa", cascade="all, delete-orphan")
    conversaciones:  Mapped[list["Conversacion"]] = relationship(back_populates="empresa", cascade="all, delete-orphan")
    kpis:            Mapped[list["KPI"]]       = relationship(back_populates="empresa", cascade="all, delete-orphan")
