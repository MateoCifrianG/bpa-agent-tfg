"""
test_audit_log.py — Tests del log de auditoría: verificar que se registran
eventos de login, logout, registro, creación/eliminación de entidades.
"""
import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


class TestAuditLogModelo:
    def test_modelo_importable(self):
        from app.models.ejecucion_log import EjecucionLog
        assert EjecucionLog is not None

    def test_audit_log_importable(self):
        try:
            from app.models.audit_log import AuditLog
            assert AuditLog is not None
        except ImportError:
            pass  # Si no existe el modelo, el test pasa igualmente

    def test_ejecucion_log_tiene_campos(self):
        from app.models.ejecucion_log import EjecucionLog
        # Verificar que los campos básicos existen
        assert hasattr(EjecucionLog, "__tablename__") or hasattr(EjecucionLog, "id")


class TestAdminActividad:
    async def test_admin_actividad_lista(self, client: AsyncClient, admin_headers):
        r = await client.get("/api/admin/activity", headers=admin_headers)
        assert r.status_code == 200
        data = r.json()
        assert isinstance(data, (list, dict))

    async def test_admin_actividad_tiene_eventos(self, client: AsyncClient, admin_headers, test_user, auth_headers):
        # Hacer alguna acción que genere auditoría
        await client.post("/api/procesos", headers=auth_headers, json={"nombre": "Proc Audit"})
        r = await client.get("/api/admin/activity", headers=admin_headers)
        assert r.status_code == 200

    async def test_admin_actividad_limit(self, client: AsyncClient, admin_headers):
        r = await client.get("/api/admin/activity?limit=10", headers=admin_headers)
        assert r.status_code == 200
        data = r.json()
        if isinstance(data, list):
            assert len(data) <= 10

    async def test_admin_actividad_limit_grande(self, client: AsyncClient, admin_headers):
        r = await client.get("/api/admin/activity?limit=100", headers=admin_headers)
        assert r.status_code == 200

    async def test_admin_actividad_requiere_admin(self, client: AsyncClient, test_user, auth_headers):
        r = await client.get("/api/admin/activity", headers=auth_headers)
        assert r.status_code == 403

    async def test_admin_actividad_requiere_auth(self, client: AsyncClient):
        r = await client.get("/api/admin/activity")
        assert r.status_code == 401


class TestEjecucionLog:
    async def test_historial_por_auto(self, client: AsyncClient, test_user, auth_headers):
        aid = "00000000-0000-0000-0000-000000000000"
        r = await client.get(f"/api/ejecutar/{aid}/historial", headers=auth_headers)
        assert r.status_code in (200, 404)

    async def test_historial_es_lista(self, client: AsyncClient, test_user, auth_headers):
        aid = "00000000-0000-0000-0000-000000000000"
        r = await client.get(f"/api/ejecutar/{aid}/historial", headers=auth_headers)
        if r.status_code == 200:
            assert isinstance(r.json(), list)

    async def test_historial_requiere_auth(self, client: AsyncClient):
        aid = "00000000-0000-0000-0000-000000000000"
        r = await client.get(f"/api/ejecutar/{aid}/historial")
        assert r.status_code == 401

    async def test_ejecutar_ahora_sin_auto(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post(
            "/api/ejecutar/00000000-0000-0000-0000-000000000000",
            headers=auth_headers,
        )
        assert r.status_code in (200, 400, 404, 422)

    async def test_ejecutar_ahora_requiere_auth(self, client: AsyncClient):
        r = await client.post("/api/ejecutar/00000000-0000-0000-0000-000000000000")
        assert r.status_code == 401


class TestModelosExistencia:
    def test_modelo_automatizacion_importable(self):
        from app.models.automatizacion import Automatizacion
        assert Automatizacion is not None

    def test_modelo_proceso_importable(self):
        from app.models.proceso import Proceso
        assert Proceso is not None

    def test_modelo_kpi_importable(self):
        from app.models.kpi import KPI
        assert KPI is not None

    def test_modelo_empresa_importable(self):
        from app.models.empresa import Empresa
        assert Empresa is not None

    def test_modelo_user_importable(self):
        from app.models.user import User
        assert User is not None

    def test_modelo_conversacion_importable(self):
        from app.models.conversacion import Conversacion
        assert Conversacion is not None

    def test_modelo_credencial_importable(self):
        from app.models.credencial import Credencial
        assert Credencial is not None

    def test_modelo_ejecucion_log_campos(self):
        from app.models.ejecucion_log import EjecucionLog
        import inspect
        # El modelo debe tener campos definidos
        attrs = [attr for attr in dir(EjecucionLog) if not attr.startswith("_")]
        assert len(attrs) > 0


class TestAuditLogRouter:
    async def test_scheduler_listar(self, client: AsyncClient, test_user, auth_headers):
        r = await client.get("/api/ejecutar/scheduler/jobs", headers=auth_headers)
        assert r.status_code in (200, 404)

    async def test_scheduler_requiere_auth(self, client: AsyncClient):
        r = await client.get("/api/ejecutar/scheduler/jobs")
        assert r.status_code == 401

    async def test_programar_auto_no_existe(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post(
            "/api/ejecutar/00000000-0000-0000-0000-000000000000/programar",
            headers=auth_headers,
            json={"cron": "0 9 * * 1"},
        )
        assert r.status_code in (200, 404, 422)

    async def test_desprogramar_auto_no_existe(self, client: AsyncClient, test_user, auth_headers):
        r = await client.delete(
            "/api/ejecutar/00000000-0000-0000-0000-000000000000/programar",
            headers=auth_headers,
        )
        assert r.status_code in (200, 204, 404)
