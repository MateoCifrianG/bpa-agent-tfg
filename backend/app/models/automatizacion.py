from sqlalchemy import String, Integer, Text, ForeignKey, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column, relationship
from uuid import uuid4
from app.database import Base


class Automatizacion(Base):
    __tablename__ = "automatizaciones"

    id:           Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    empresa_id:   Mapped[str] = mapped_column(String(36), ForeignKey("empresas.id"), nullable=False, index=True)
    proceso_id:   Mapped[str | None] = mapped_column(String(36), ForeignKey("procesos.id", ondelete="SET NULL"))
    nombre:       Mapped[str] = mapped_column(String(255), nullable=False)
    descripcion:  Mapped[str | None] = mapped_column(Text)
    herramienta:  Mapped[str | None] = mapped_column(String(100))   # n8n, Gmail, Drive, etc.
    estado:       Mapped[str]        = mapped_column(String(30), default="pendiente")  # activa | pendiente | pausada | error
    ejecuciones:  Mapped[int]        = mapped_column(Integer, default=0)
    horas_mes:    Mapped[int | None] = mapped_column(Integer)        # horas ahorradas/mes
    config_json:  Mapped[str | None] = mapped_column(Text)           # JSON cifrado con parámetros MCP
    created_at:   Mapped[DateTime]   = mapped_column(DateTime(timezone=True), server_default=func.now())
    last_run_at:  Mapped[DateTime | None] = mapped_column(DateTime(timezone=True))

    # ── Trigger (cómo se dispara) ──────────────────────────────────
    tipo_trigger: Mapped[str] = mapped_column(String(30), default="manual")   # manual | cron | webhook_in
    cron_expr:    Mapped[str | None] = mapped_column(String(100))              # "0 9 * * 1" = lunes 9h
    webhook_token: Mapped[str | None] = mapped_column(String(64))             # token único para webhook entrante

    # ── Acción (qué hace) ──────────────────────────────────────────
    tipo_accion:  Mapped[str] = mapped_column(String(30), default="webhook_out")  # email | telegram | slack | webhook_out | script
    # config_json ya existía — almacena params cifrados de la acción

    empresa: Mapped["Empresa"]     = relationship(back_populates="automatizaciones")
    proceso: Mapped["Proceso | None"] = relationship(back_populates="automatizaciones")
    logs:    Mapped[list["EjecucionLog"]] = relationship(back_populates="automatizacion", cascade="all, delete-orphan", order_by="EjecucionLog.created_at.desc()")
