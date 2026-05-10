"""
test_admin.py — Tests del panel de administración: usuarios, stats, actividad, sistema.
"""
import pytest
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


class TestAdminAcceso:
    async def test_admin_requiere_auth(self, client: AsyncClient):
        r = await client.get("/api/admin/users")
        assert r.status_code == 401

    async def test_admin_bloquea_usuario_normal(self, client: AsyncClient, auth_headers):
        r = await client.get("/api/admin/users", headers=auth_headers)
        assert r.status_code == 403

    async def test_admin_stats_bloquea_normal(self, client: AsyncClient, auth_headers):
        r = await client.get("/api/admin/stats", headers=auth_headers)
        assert r.status_code == 403

    async def test_admin_actividad_bloquea_normal(self, client: AsyncClient, auth_headers):
        r = await client.get("/api/admin/activity", headers=auth_headers)
        assert r.status_code == 403

    async def test_admin_sistema_bloquea_normal(self, client: AsyncClient, auth_headers):
        r = await client.get("/api/admin/sistema", headers=auth_headers)
        assert r.status_code == 403


class TestAdminUsers:
    async def test_listar_usuarios(self, client: AsyncClient, admin_headers, test_user):
        r = await client.get("/api/admin/users", headers=admin_headers)
        assert r.status_code == 200
        assert isinstance(r.json(), list)
        assert len(r.json()) >= 1

    async def test_listar_usuarios_devuelve_campos(self, client: AsyncClient, admin_headers, test_user):
        r = await client.get("/api/admin/users", headers=admin_headers)
        assert r.status_code == 200
        u = r.json()[0]
        for campo in ["id", "email", "nombre", "role", "plan", "is_active"]:
            assert campo in u, f"Campo '{campo}' ausente en admin users"

    async def test_listar_usuarios_no_expone_passwords(self, client: AsyncClient, admin_headers, test_user):
        r = await client.get("/api/admin/users", headers=admin_headers)
        for u in r.json():
            assert "hashed_password" not in u
            assert "password" not in u

    async def test_actualizar_plan_usuario(self, client: AsyncClient, admin_headers, test_user):
        r = await client.put(f"/api/admin/users/{test_user.id}", headers=admin_headers, json={
            "plan": "enterprise",
        })
        assert r.status_code == 200
        assert r.json()["plan"] == "enterprise"

    async def test_actualizar_is_active_usuario(self, client: AsyncClient, admin_headers, test_user):
        r = await client.put(f"/api/admin/users/{test_user.id}", headers=admin_headers, json={
            "is_active": False,
        })
        assert r.status_code == 200
        assert r.json()["is_active"] is False

    async def test_actualizar_role_usuario(self, client: AsyncClient, admin_headers, test_user):
        r = await client.put(f"/api/admin/users/{test_user.id}", headers=admin_headers, json={
            "role": "admin",
        })
        assert r.status_code == 200

    async def test_actualizar_usuario_no_existe(self, client: AsyncClient, admin_headers):
        r = await client.put("/api/admin/users/00000000-0000-0000-0000-000000000000", headers=admin_headers, json={
            "plan": "free",
        })
        assert r.status_code == 404

    async def test_eliminar_usuario(self, client: AsyncClient, admin_headers, client_factory=None):
        import uuid
        # Crear usuario temporal para eliminar
        uid = uuid.uuid4().hex[:8]
        cr = await client.post("/api/auth/register", json={
            "email": f"delete_{uid}@test.com",
            "password": "Delete1234!",
            "nombre": "Delete",
            "apellido": "Me",
            "empresa": "Del Corp",
            "sector": "ventas",
            "empleados": 1,
            "plan": "free",
        })
        assert cr.status_code == 201
        user_id = cr.json()["user"]["id"]
        r = await client.delete(f"/api/admin/users/{user_id}", headers=admin_headers)
        assert r.status_code == 204

    async def test_admin_no_puede_eliminar_su_propia_cuenta(self, client: AsyncClient, admin_user, admin_headers):
        r = await client.delete(f"/api/admin/users/{admin_user.id}", headers=admin_headers)
        assert r.status_code == 400

    async def test_crear_usuario_desde_admin(self, client: AsyncClient, admin_headers):
        import uuid
        uid = uuid.uuid4().hex[:8]
        r = await client.post("/api/admin/users", headers=admin_headers, json={
            "nombre": "Admin",
            "apellido": "Created",
            "email": f"admincreated_{uid}@test.com",
            "password": "Admin1234!",
            "plan": "pro",
            "empresa_nombre": "Admin Corp",
        })
        assert r.status_code == 201
        data = r.json()
        assert data["plan"] == "pro"

    async def test_crear_usuario_email_duplicado(self, client: AsyncClient, admin_headers, test_user):
        r = await client.post("/api/admin/users", headers=admin_headers, json={
            "nombre": "Dup",
            "apellido": "User",
            "email": test_user.email,
            "password": "Admin1234!",
            "plan": "free",
            "empresa_nombre": "Dup Corp",
        })
        assert r.status_code == 409


class TestAdminStats:
    async def test_stats_globales(self, client: AsyncClient, admin_headers, test_user):
        r = await client.get("/api/admin/stats", headers=admin_headers)
        assert r.status_code == 200
        data = r.json()
        campos = ["total_users", "total_procesos", "total_autos", "total_kpis",
                  "horas_totales", "users_activos"]
        for campo in campos:
            assert campo in data, f"Campo '{campo}' ausente en stats"

    async def test_stats_total_users_positivo(self, client: AsyncClient, admin_headers, test_user):
        r = await client.get("/api/admin/stats", headers=admin_headers)
        assert r.json()["total_users"] >= 1

    async def test_stats_users_por_plan(self, client: AsyncClient, admin_headers, test_user):
        r = await client.get("/api/admin/stats", headers=admin_headers)
        data = r.json()
        assert "users_free" in data or "users_pro" in data or "users_enterprise" in data


class TestAdminActividad:
    async def test_listar_actividad(self, client: AsyncClient, admin_headers):
        r = await client.get("/api/admin/activity", headers=admin_headers)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    async def test_actividad_con_limit(self, client: AsyncClient, admin_headers):
        r = await client.get("/api/admin/activity?limit=5", headers=admin_headers)
        assert r.status_code == 200
        assert len(r.json()) <= 5


class TestAdminSistema:
    async def test_sistema_status(self, client: AsyncClient, admin_headers):
        r = await client.get("/api/admin/sistema", headers=admin_headers)
        assert r.status_code == 200
        data = r.json()
        assert "api" in data
        assert data["api"]["ok"] is True

    async def test_sistema_devuelve_motor_activo(self, client: AsyncClient, admin_headers):
        r = await client.get("/api/admin/sistema", headers=admin_headers)
        assert r.status_code == 200
        assert "motor_activo" in r.json()

    async def test_sistema_devuelve_database(self, client: AsyncClient, admin_headers):
        r = await client.get("/api/admin/sistema", headers=admin_headers)
        data = r.json()
        assert "database" in data
        assert data["database"]["ok"] is True
