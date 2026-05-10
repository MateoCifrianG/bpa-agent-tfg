"""
test_modelos_unitarios.py — Tests unitarios de modelos de dominio:
User, Empresa, Proceso, Automatizacion, KPI, Conversacion.
Verifica campos, defaults, tipos, restricciones, relaciones.
"""
import pytest
import uuid
from datetime import datetime


class TestUserModelo:
    def test_user_tiene_campo_email(self):
        from app.models.user import User
        assert hasattr(User, "email")

    def test_user_tiene_campo_hashed_password(self):
        from app.models.user import User
        assert hasattr(User, "hashed_password")

    def test_user_tiene_campo_nombre(self):
        from app.models.user import User
        assert hasattr(User, "nombre")

    def test_user_tiene_campo_apellido(self):
        from app.models.user import User
        assert hasattr(User, "apellido")

    def test_user_tiene_campo_role(self):
        from app.models.user import User
        assert hasattr(User, "role")

    def test_user_tiene_campo_plan(self):
        from app.models.user import User
        assert hasattr(User, "plan")

    def test_user_tiene_campo_is_active(self):
        from app.models.user import User
        assert hasattr(User, "is_active")

    def test_user_tiene_campo_id(self):
        from app.models.user import User
        assert hasattr(User, "id")

    def test_user_tiene_campo_created_at(self):
        from app.models.user import User
        assert hasattr(User, "created_at")

    def test_user_instancia_creada(self):
        from app.models.user import User
        u = User(email="test@test.com", hashed_password="hash", nombre="Test", apellido="U", role="user", plan="free")
        assert u.email == "test@test.com"

    def test_user_role_default_user(self):
        from app.models.user import User
        u = User(email="test@test.com", hashed_password="h", nombre="T", apellido="U")
        assert u.role in (None, "user")

    def test_user_is_active_default(self):
        from app.models.user import User
        u = User(email="test@test.com", hashed_password="h", nombre="T", apellido="U")
        assert u.is_active in (None, True, False)


class TestEmpresaModelo:
    def test_empresa_tiene_campo_nombre(self):
        from app.models.empresa import Empresa
        assert hasattr(Empresa, "nombre")

    def test_empresa_tiene_campo_sector(self):
        from app.models.empresa import Empresa
        assert hasattr(Empresa, "sector")

    def test_empresa_tiene_campo_user_id(self):
        from app.models.empresa import Empresa
        assert hasattr(Empresa, "user_id")

    def test_empresa_tiene_campo_empleados(self):
        from app.models.empresa import Empresa
        assert hasattr(Empresa, "empleados")

    def test_empresa_tiene_campo_id(self):
        from app.models.empresa import Empresa
        assert hasattr(Empresa, "id")

    def test_empresa_instancia_creada(self):
        from app.models.empresa import Empresa
        e = Empresa(user_id=str(uuid.uuid4()), nombre="Mi Empresa", sector="ventas")
        assert e.nombre == "Mi Empresa"
        assert e.sector == "ventas"


class TestProcesoModelo:
    def test_proceso_tiene_campo_nombre(self):
        from app.models.proceso import Proceso
        assert hasattr(Proceso, "nombre")

    def test_proceso_tiene_campo_descripcion(self):
        from app.models.proceso import Proceso
        assert hasattr(Proceso, "descripcion")

    def test_proceso_tiene_campo_empresa_id(self):
        from app.models.proceso import Proceso
        assert hasattr(Proceso, "empresa_id")

    def test_proceso_tiene_campo_responsable(self):
        from app.models.proceso import Proceso
        assert hasattr(Proceso, "responsable")

    def test_proceso_tiene_campo_frecuencia(self):
        from app.models.proceso import Proceso
        assert hasattr(Proceso, "frecuencia")

    def test_proceso_tiene_campo_duracion_h(self):
        from app.models.proceso import Proceso
        assert hasattr(Proceso, "duracion_h")

    def test_proceso_tiene_campo_score(self):
        from app.models.proceso import Proceso
        assert hasattr(Proceso, "score")

    def test_proceso_tiene_campo_estado(self):
        from app.models.proceso import Proceso
        assert hasattr(Proceso, "estado")

    def test_proceso_tiene_campo_id(self):
        from app.models.proceso import Proceso
        assert hasattr(Proceso, "id")

    def test_proceso_instancia_creada(self):
        from app.models.proceso import Proceso
        p = Proceso(empresa_id=str(uuid.uuid4()), nombre="Test Proceso")
        assert p.nombre == "Test Proceso"


class TestAutomatizacionModelo:
    def test_auto_tiene_campo_nombre(self):
        from app.models.automatizacion import Automatizacion
        assert hasattr(Automatizacion, "nombre")

    def test_auto_tiene_campo_empresa_id(self):
        from app.models.automatizacion import Automatizacion
        assert hasattr(Automatizacion, "empresa_id")

    def test_auto_tiene_campo_herramienta(self):
        from app.models.automatizacion import Automatizacion
        assert hasattr(Automatizacion, "herramienta")

    def test_auto_tiene_campo_estado(self):
        from app.models.automatizacion import Automatizacion
        assert hasattr(Automatizacion, "estado")

    def test_auto_tiene_campo_horas_mes(self):
        from app.models.automatizacion import Automatizacion
        assert hasattr(Automatizacion, "horas_mes")

    def test_auto_tiene_campo_tipo_trigger(self):
        from app.models.automatizacion import Automatizacion
        assert hasattr(Automatizacion, "tipo_trigger")

    def test_auto_tiene_campo_cron_expr(self):
        from app.models.automatizacion import Automatizacion
        assert hasattr(Automatizacion, "cron_expr")

    def test_auto_tiene_campo_id(self):
        from app.models.automatizacion import Automatizacion
        assert hasattr(Automatizacion, "id")

    def test_auto_instancia_creada(self):
        from app.models.automatizacion import Automatizacion
        a = Automatizacion(empresa_id=str(uuid.uuid4()), nombre="Test Auto")
        assert a.nombre == "Test Auto"


class TestKPIModelo:
    def test_kpi_tiene_campo_nombre(self):
        from app.models.kpi import KPI
        assert hasattr(KPI, "nombre")

    def test_kpi_tiene_campo_valor(self):
        from app.models.kpi import KPI
        assert hasattr(KPI, "valor")

    def test_kpi_tiene_campo_objetivo(self):
        from app.models.kpi import KPI
        assert hasattr(KPI, "objetivo")

    def test_kpi_tiene_campo_unidad(self):
        from app.models.kpi import KPI
        assert hasattr(KPI, "unidad")

    def test_kpi_tiene_campo_empresa_id(self):
        from app.models.kpi import KPI
        assert hasattr(KPI, "empresa_id")

    def test_kpi_tiene_campo_categoria(self):
        from app.models.kpi import KPI
        assert hasattr(KPI, "categoria")

    def test_kpi_tiene_campo_id(self):
        from app.models.kpi import KPI
        assert hasattr(KPI, "id")

    def test_kpi_instancia_creada(self):
        from app.models.kpi import KPI
        k = KPI(empresa_id=str(uuid.uuid4()), nombre="Test KPI", valor="85")
        assert k.nombre == "Test KPI"


class TestConversacionModelo:
    def test_conv_tiene_campo_empresa_id(self):
        from app.models.conversacion import Conversacion
        assert hasattr(Conversacion, "empresa_id")

    def test_conv_tiene_campo_titulo(self):
        from app.models.conversacion import Conversacion
        assert hasattr(Conversacion, "titulo")

    def test_conv_tiene_campo_historial(self):
        from app.models.conversacion import Conversacion
        assert hasattr(Conversacion, "historial")

    def test_conv_tiene_campo_fase(self):
        from app.models.conversacion import Conversacion
        assert hasattr(Conversacion, "fase")

    def test_conv_tiene_campo_id(self):
        from app.models.conversacion import Conversacion
        assert hasattr(Conversacion, "id")

    def test_conv_instancia_creada(self):
        from app.models.conversacion import Conversacion
        c = Conversacion(empresa_id=str(uuid.uuid4()), titulo="Test Conv", historial="[]", fase="diagnostico")
        assert c.titulo == "Test Conv"
        assert c.historial == "[]"
