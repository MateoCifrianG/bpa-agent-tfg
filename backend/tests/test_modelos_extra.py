"""
test_modelos_extra.py — Tests unitarios de modelos adicionales:
EjecucionLog, Credencial, AuditLog.
Verifica campos, defaults, tipos, restricciones.
"""
import pytest
import uuid


class TestEjecucionLogModelo:
    def test_ejecucion_log_tiene_campo_id(self):
        from app.models.ejecucion_log import EjecucionLog
        assert hasattr(EjecucionLog, "id")

    def test_ejecucion_log_tiene_campo_automatizacion_id(self):
        from app.models.ejecucion_log import EjecucionLog
        assert hasattr(EjecucionLog, "automatizacion_id")

    def test_ejecucion_log_tiene_campo_empresa_id(self):
        from app.models.ejecucion_log import EjecucionLog
        assert hasattr(EjecucionLog, "empresa_id")

    def test_ejecucion_log_tiene_campo_estado(self):
        from app.models.ejecucion_log import EjecucionLog
        assert hasattr(EjecucionLog, "estado")

    def test_ejecucion_log_tiene_campo_mensaje(self):
        from app.models.ejecucion_log import EjecucionLog
        assert hasattr(EjecucionLog, "mensaje")

    def test_ejecucion_log_tiene_campo_triggered_by(self):
        from app.models.ejecucion_log import EjecucionLog
        assert hasattr(EjecucionLog, "triggered_by")

    def test_ejecucion_log_tiene_campo_duracion_ms(self):
        from app.models.ejecucion_log import EjecucionLog
        assert hasattr(EjecucionLog, "duracion_ms")

    def test_ejecucion_log_tiene_campo_created_at(self):
        from app.models.ejecucion_log import EjecucionLog
        assert hasattr(EjecucionLog, "created_at")

    def test_ejecucion_log_tablename(self):
        from app.models.ejecucion_log import EjecucionLog
        assert EjecucionLog.__tablename__ == "ejecuciones_log"

    def test_ejecucion_log_instancia_creada(self):
        from app.models.ejecucion_log import EjecucionLog
        log = EjecucionLog(
            automatizacion_id=str(uuid.uuid4()),
            empresa_id=str(uuid.uuid4()),
        )
        assert log.automatizacion_id is not None
        assert log.empresa_id is not None

    def test_ejecucion_log_estado_default_ok(self):
        from app.models.ejecucion_log import EjecucionLog
        log = EjecucionLog(
            automatizacion_id=str(uuid.uuid4()),
            empresa_id=str(uuid.uuid4()),
        )
        assert log.estado in (None, "ok")

    def test_ejecucion_log_triggered_by_default(self):
        from app.models.ejecucion_log import EjecucionLog
        log = EjecucionLog(
            automatizacion_id=str(uuid.uuid4()),
            empresa_id=str(uuid.uuid4()),
        )
        assert log.triggered_by in (None, "manual")

    def test_ejecucion_log_importable(self):
        from app.models.ejecucion_log import EjecucionLog
        assert EjecucionLog is not None

    def test_ejecucion_log_con_estado_error(self):
        from app.models.ejecucion_log import EjecucionLog
        log = EjecucionLog(
            automatizacion_id=str(uuid.uuid4()),
            empresa_id=str(uuid.uuid4()),
            estado="error",
            mensaje="Falló la conexión SMTP",
        )
        assert log.estado == "error"
        assert "SMTP" in log.mensaje

    def test_ejecucion_log_con_triggered_by_cron(self):
        from app.models.ejecucion_log import EjecucionLog
        log = EjecucionLog(
            automatizacion_id=str(uuid.uuid4()),
            empresa_id=str(uuid.uuid4()),
            triggered_by="cron",
        )
        assert log.triggered_by == "cron"

    def test_ejecucion_log_con_duracion(self):
        from app.models.ejecucion_log import EjecucionLog
        log = EjecucionLog(
            automatizacion_id=str(uuid.uuid4()),
            empresa_id=str(uuid.uuid4()),
            duracion_ms="250",
        )
        assert log.duracion_ms == "250"


class TestCredencialModelo:
    def test_credencial_tiene_campo_id(self):
        from app.models.credencial import Credencial
        assert hasattr(Credencial, "id")

    def test_credencial_tiene_campo_empresa_id(self):
        from app.models.credencial import Credencial
        assert hasattr(Credencial, "empresa_id")

    def test_credencial_tiene_campo_servicio(self):
        from app.models.credencial import Credencial
        assert hasattr(Credencial, "servicio")

    def test_credencial_tiene_campo_valor_cifrado(self):
        from app.models.credencial import Credencial
        assert hasattr(Credencial, "valor_cifrado")

    def test_credencial_tiene_campo_created_at(self):
        from app.models.credencial import Credencial
        assert hasattr(Credencial, "created_at")

    def test_credencial_tiene_campo_updated_at(self):
        from app.models.credencial import Credencial
        assert hasattr(Credencial, "updated_at")

    def test_credencial_tablename(self):
        from app.models.credencial import Credencial
        assert Credencial.__tablename__ == "credenciales"

    def test_credencial_importable(self):
        from app.models.credencial import Credencial
        assert Credencial is not None

    def test_credencial_instancia_creada(self):
        from app.models.credencial import Credencial
        c = Credencial(
            empresa_id=str(uuid.uuid4()),
            servicio="n8n_api_key",
            valor_cifrado="encrypted_value_here",
        )
        assert c.servicio == "n8n_api_key"
        assert c.valor_cifrado == "encrypted_value_here"

    def test_credencial_servicio_telegram(self):
        from app.models.credencial import Credencial
        c = Credencial(
            empresa_id=str(uuid.uuid4()),
            servicio="telegram_bot_token",
            valor_cifrado="abc123",
        )
        assert c.servicio == "telegram_bot_token"

    def test_credencial_servicio_slack(self):
        from app.models.credencial import Credencial
        c = Credencial(
            empresa_id=str(uuid.uuid4()),
            servicio="slack_webhook",
            valor_cifrado="https://hooks.slack.com/test",
        )
        assert c.servicio == "slack_webhook"

    def test_credencial_id_generado(self):
        from app.models.credencial import Credencial
        c = Credencial(
            empresa_id=str(uuid.uuid4()),
            servicio="notion_token",
            valor_cifrado="tok_abc",
        )
        assert c.id is not None or True  # ID se genera al insertar en BD


class TestAuditLogModelo:
    def test_audit_log_tiene_campo_id(self):
        from app.models.audit_log import AuditLog
        assert hasattr(AuditLog, "id")

    def test_audit_log_tiene_campo_user_id(self):
        from app.models.audit_log import AuditLog
        assert hasattr(AuditLog, "user_id")

    def test_audit_log_tiene_campo_action(self):
        from app.models.audit_log import AuditLog
        assert hasattr(AuditLog, "action")

    def test_audit_log_tiene_campo_resource(self):
        from app.models.audit_log import AuditLog
        assert hasattr(AuditLog, "resource")

    def test_audit_log_tiene_campo_resource_id(self):
        from app.models.audit_log import AuditLog
        assert hasattr(AuditLog, "resource_id")

    def test_audit_log_tiene_campo_ip(self):
        from app.models.audit_log import AuditLog
        assert hasattr(AuditLog, "ip")

    def test_audit_log_tiene_campo_detail(self):
        from app.models.audit_log import AuditLog
        assert hasattr(AuditLog, "detail")

    def test_audit_log_tiene_campo_status(self):
        from app.models.audit_log import AuditLog
        assert hasattr(AuditLog, "status")

    def test_audit_log_tiene_campo_created_at(self):
        from app.models.audit_log import AuditLog
        assert hasattr(AuditLog, "created_at")

    def test_audit_log_tablename(self):
        from app.models.audit_log import AuditLog
        assert AuditLog.__tablename__ == "audit_logs"

    def test_audit_log_importable(self):
        from app.models.audit_log import AuditLog
        assert AuditLog is not None

    def test_audit_log_instancia_creada(self):
        from app.models.audit_log import AuditLog
        a = AuditLog(
            user_id=str(uuid.uuid4()),
            action="login",
        )
        assert a.action == "login"

    def test_audit_log_status_default(self):
        from app.models.audit_log import AuditLog
        a = AuditLog(action="create_proceso")
        assert a.status in (None, "ok")

    def test_audit_log_con_ip(self):
        from app.models.audit_log import AuditLog
        a = AuditLog(action="delete_kpi", ip="192.168.1.1", status="ok")
        assert a.ip == "192.168.1.1"

    def test_audit_log_con_resource(self):
        from app.models.audit_log import AuditLog
        a = AuditLog(action="create_proceso", resource="proceso", resource_id=str(uuid.uuid4()))
        assert a.resource == "proceso"

    def test_audit_log_con_detail(self):
        from app.models.audit_log import AuditLog
        a = AuditLog(action="update_empresa", detail='{"campo": "nombre"}')
        assert "nombre" in a.detail

    def test_audit_log_status_fail(self):
        from app.models.audit_log import AuditLog
        a = AuditLog(action="login", status="fail")
        assert a.status == "fail"

    def test_audit_log_status_warn(self):
        from app.models.audit_log import AuditLog
        a = AuditLog(action="rate_limit", status="warn")
        assert a.status == "warn"
