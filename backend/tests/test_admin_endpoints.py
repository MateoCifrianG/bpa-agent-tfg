"""
test_admin_endpoints.py — Tests de endpoints de admin:
/api/admin/users, /api/admin/stats, /api/admin/activity, /api/admin/sistema.
Verifica permisos, estructura de respuesta, campos, autorización.
"""
import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


class TestAdminStats:
    async def test_stats_requiere_auth(self, client: AsyncClient):
        r = await client.get("/api/admin/stats")
        assert r.status_code in (401, 403)

    async def test_stats_requiere_admin(self, client: AsyncClient, auth_headers):
        r = await client.get("/api/admin/stats", headers=auth_headers)
        assert r.status_code == 403

    async def test_stats_admin_ok(self, client: AsyncClient, admin_headers):
        r = await client.get("/api/admin/stats", headers=admin_headers)
        assert r.status_code == 200

    async def test_stats_tiene_total_users(self, client: AsyncClient, admin_headers):
        r = await client.get("/api/admin/stats", headers=admin_headers)
        data = r.json()
        assert "total_users" in data

    async def test_stats_tiene_total_procesos(self, client: AsyncClient, admin_headers):
        r = await client.get("/api/admin/stats", headers=admin_headers)
        data = r.json()
        assert "total_procesos" in data

    async def test_stats_tiene_total_autos(self, client: AsyncClient, admin_headers):
        r = await client.get("/api/admin/stats", headers=admin_headers)
        data = r.json()
        assert "total_autos" in data

    async def test_stats_tiene_total_kpis(self, client: AsyncClient, admin_headers):
        r = await client.get("/api/admin/stats", headers=admin_headers)
        data = r.json()
        assert "total_kpis" in data

    async def test_stats_total_users_numerico(self, client: AsyncClient, admin_headers):
        r = await client.get("/api/admin/stats", headers=admin_headers)
        data = r.json()
        assert isinstance(data["total_users"], int)
        assert data["total_users"] >= 0

    async def test_stats_tiene_score_promedio(self, client: AsyncClient, admin_headers):
        r = await client.get("/api/admin/stats", headers=admin_headers)
        data = r.json()
        assert "score_promedio" in data

    async def test_stats_tiene_users_activos(self, client: AsyncClient, admin_headers):
        r = await client.get("/api/admin/stats", headers=admin_headers)
        data = r.json()
        assert "users_activos" in data

    async def test_stats_tiene_horas_totales(self, client: AsyncClient, admin_headers):
        r = await client.get("/api/admin/stats", headers=admin_headers)
        data = r.json()
        assert "horas_totales" in data


class TestAdminUsers:
    async def test_users_requiere_auth(self, client: AsyncClient):
        r = await client.get("/api/admin/users")
        assert r.status_code in (401, 403)

    async def test_users_requiere_admin(self, client: AsyncClient, auth_headers):
        r = await client.get("/api/admin/users", headers=auth_headers)
        assert r.status_code == 403

    async def test_users_admin_ok(self, client: AsyncClient, admin_headers):
        r = await client.get("/api/admin/users", headers=admin_headers)
        assert r.status_code == 200

    async def test_users_devuelve_lista(self, client: AsyncClient, admin_user, admin_headers):
        r = await client.get("/api/admin/users", headers=admin_headers)
        data = r.json()
        assert isinstance(data, list)

    async def test_users_tiene_al_menos_admin(self, client: AsyncClient, admin_user, admin_headers):
        r = await client.get("/api/admin/users", headers=admin_headers)
        data = r.json()
        assert len(data) >= 1

    async def test_users_campos_ok(self, client: AsyncClient, admin_user, admin_headers):
        r = await client.get("/api/admin/users", headers=admin_headers)
        data = r.json()
        if data:
            user = data[0]
            for campo in ["id", "email", "nombre", "apellido", "role", "plan", "is_active"]:
                assert campo in user

    async def test_users_procesos_count_numerico(self, client: AsyncClient, admin_user, admin_headers):
        r = await client.get("/api/admin/users", headers=admin_headers)
        data = r.json()
        if data:
            assert isinstance(data[0]["procesos_count"], int)

    async def test_users_autos_count_numerico(self, client: AsyncClient, admin_user, admin_headers):
        r = await client.get("/api/admin/users", headers=admin_headers)
        data = r.json()
        if data:
            assert isinstance(data[0]["autos_count"], int)


class TestAdminActivity:
    async def test_activity_requiere_auth(self, client: AsyncClient):
        r = await client.get("/api/admin/activity")
        assert r.status_code in (401, 403)

    async def test_activity_requiere_admin(self, client: AsyncClient, auth_headers):
        r = await client.get("/api/admin/activity", headers=auth_headers)
        assert r.status_code == 403

    async def test_activity_admin_ok(self, client: AsyncClient, admin_headers):
        r = await client.get("/api/admin/activity", headers=admin_headers)
        assert r.status_code == 200

    async def test_activity_devuelve_dict_o_lista(self, client: AsyncClient, admin_headers):
        r = await client.get("/api/admin/activity", headers=admin_headers)
        data = r.json()
        assert isinstance(data, (dict, list))


class TestAdminSistema:
    async def test_sistema_requiere_auth(self, client: AsyncClient):
        r = await client.get("/api/admin/sistema")
        assert r.status_code in (401, 403)

    async def test_sistema_requiere_admin(self, client: AsyncClient, auth_headers):
        r = await client.get("/api/admin/sistema", headers=auth_headers)
        assert r.status_code == 403

    async def test_sistema_admin_ok(self, client: AsyncClient, admin_headers):
        r = await client.get("/api/admin/sistema", headers=admin_headers)
        assert r.status_code == 200

    async def test_sistema_devuelve_datos(self, client: AsyncClient, admin_headers):
        r = await client.get("/api/admin/sistema", headers=admin_headers)
        data = r.json()
        assert isinstance(data, (dict, list))


class TestAdminCrearUsuario:
    async def test_crear_usuario_requiere_admin(self, client: AsyncClient, auth_headers):
        r = await client.post("/api/admin/users", headers=auth_headers, json={
            "email": "nuevo@test.com", "password": "Test1234!",
            "nombre": "Nuevo", "apellido": "Usuario",
            "empresa": "TestEmp", "sector": "ventas", "empleados": 5, "plan": "free",
        })
        assert r.status_code == 403

    async def test_crear_usuario_admin_ok(self, client: AsyncClient, admin_headers):
        import uuid
        r = await client.post("/api/admin/users", headers=admin_headers, json={
            "email": f"adm_{uuid.uuid4().hex[:6]}@test.com",
            "password": "Test1234!", "nombre": "Admin", "apellido": "Created",
            "empresa": "AdminEmp", "sector": "ventas", "empleados": 5, "plan": "free",
        })
        assert r.status_code in (201, 200)

    async def test_crear_usuario_email_duplicado_falla(self, client: AsyncClient, admin_user, admin_headers):
        r = await client.post("/api/admin/users", headers=admin_headers, json={
            "email": admin_user.email,
            "password": "Test1234!", "nombre": "Dup", "apellido": "User",
            "empresa": "Dup", "sector": "ventas", "empleados": 1, "plan": "free",
        })
        assert r.status_code in (400, 409, 422)
