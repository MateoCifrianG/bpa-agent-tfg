from sqlalchemy import String, Text, DateTime, func
from sqlalchemy.orm import Mapped, mapped_column
from uuid import uuid4
from app.database import Base


class AuditLog(Base):
    __tablename__ = "audit_logs"

    id:          Mapped[str] = mapped_column(String(36), primary_key=True, default=lambda: str(uuid4()))
    user_id:     Mapped[str | None] = mapped_column(String(36), nullable=True, index=True)
    action:      Mapped[str] = mapped_column(String(100), nullable=False)   # login, logout, create_proceso, delete_kpi…
    resource:    Mapped[str | None] = mapped_column(String(100))            # proceso, kpi, automatizacion…
    resource_id: Mapped[str | None] = mapped_column(String(36))
    ip:          Mapped[str | None] = mapped_column(String(45))             # IPv4 o IPv6
    detail:      Mapped[str | None] = mapped_column(Text)                   # JSON con contexto extra
    status:      Mapped[str] = mapped_column(String(20), default="ok")      # ok | fail | warn
    created_at:  Mapped[DateTime] = mapped_column(DateTime(timezone=True), server_default=func.now(), index=True)
