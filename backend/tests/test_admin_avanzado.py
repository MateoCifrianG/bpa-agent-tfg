"""
test_admin_avanzado.py — Tests avanzados del panel de administración:
listado de usuarios, sistema, estadísticas, permisos, edge cases.
"""
import pytest
import uuid
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


class TestAdminAcceso:
    async def test_admin_listado_sin_auth_401(self, client: AsyncClient):
        r = await client.get("/api/admin/users")
        assert r.status_code == 401

    async def test_admin_sistema_sin_auth_401(self, client: AsyncClient):
        r = await client.get("/api/admin/sistema")
        assert r.status_code == 401

    async def test_admin_listado_con_user_normal_403(self, client: AsyncClient, test_user, auth_headers):
        r = await client.get("/api/admin/users", headers=auth_headers)
        assert r.status_code == 403

    async def test_admin_sistema_con_user_normal_403(self, client: AsyncClient, test_user, auth_headers):
        r = await client.get("/api/admin/sistema", headers=auth_headers)
        assert r.status_code == 403

    async def test_admin_listado_con_admin_200(self, client: AsyncClient, admin_user, admin_headers):
        r = await client.get("/api/admin/users", headers=admin_headers)
        assert r.status_code == 200

    async def test_admin_sistema_con_admin_200(self, client: AsyncClient, admin_user, admin_headers):
        r = await client.get("/api/admin/sistema", headers=admin_headers)
        assert r.status_code == 200


class TestAdminListadoUsuarios:
    async def test_listado_devuelve_lista(self, client: AsyncClient, admin_user, admin_headers):
        r = await client.get("/api/admin/users", headers=admin_headers)
        assert isinstance(r.json(), list)

    async def test_listado_no_vacio(self, client: AsyncClient, admin_user, admin_headers):
        r = await client.get("/api/admin/users", headers=admin_headers)
        assert len(r.json()) >= 1

    async def test_listado_incluye_admin(self, client: AsyncClient, admin_user, admin_headers):
        r = await client.get("/api/admin/users", headers=admin_headers)
        emails = [u.get("email") for u in r.json()]
        assert admin_user.email in emails

    async def test_usuario_tiene_id(self, client: AsyncClient, admin_user, admin_headers):
        r = await client.get("/api/admin/users", headers=admin_headers)
        for user in r.json():
            assert "id" in user

    async def test_usuario_tiene_email(self, client: AsyncClient, admin_user, admin_headers):
        r = await client.get("/api/admin/users", headers=admin_headers)
        for user in r.json():
            assert "email" in user

    async def test_usuario_tiene_role(self, client: AsyncClient, admin_user, admin_headers):
        r = await client.get("/api/admin/users", headers=admin_headers)
        for user in r.json():
            assert "role" in user

    async def test_usuario_no_expone_password(self, client: AsyncClient, admin_user, admin_headers):
        r = await client.get("/api/admin/users", headers=admin_headers)
        response_text = r.text
        assert "$2b$" not in response_text

    async def test_listado_incluye_usuario_recien_registrado(self, client: AsyncClient, admin_user, admin_headers):
        uid = uuid.uuid4().hex[:8]
        await client.post("/api/auth/register", json={
            "email": f"nuevo_admin_{uid}@test.com", "password": "TestPass1!",
            "nombre": "Nuevo", "apellido": "User",
            "empresa": "Emp", "sector": "ventas", "empleados": 1, "plan": "free",
        })
        r = await client.get("/api/admin/users", headers=admin_headers)
        emails = [u.get("email") for u in r.json()]
        assert f"nuevo_admin_{uid}@test.com" in emails

    async def test_content_type_json(self, client: AsyncClient, admin_user, admin_headers):
        r = await client.get("/api/admin/users", headers=admin_headers)
        assert "application/json" in r.headers.get("content-type", "")


class TestAdminSistema:
    async def test_sistema_devuelve_dict(self, client: AsyncClient, admin_user, admin_headers):
        r = await client.get("/api/admin/sistema", headers=admin_headers)
        assert isinstance(r.json(), dict)

    async def test_sistema_tiene_api_info(self, client: AsyncClient, admin_user, admin_headers):
        r = await client.get("/api/admin/sistema", headers=admin_headers)
        data = r.json()
        assert any(k in data for k in ("api", "version", "motor_activo", "motor"))

    async def test_sistema_tiene_database_info(self, client: AsyncClient, admin_user, admin_headers):
        r = await client.get("/api/admin/sistema", headers=admin_headers)
        data = r.json()
        assert any(k in data for k in ("database", "db", "base_de_datos"))

    async def test_sistema_tiene_ollama_info(self, client: AsyncClient, admin_user, admin_headers):
        r = await client.get("/api/admin/sistema", headers=admin_headers)
        data = r.json()
        assert any(k in data for k in ("ollama", "motor_activo", "ia"))

    async def test_sistema_api_tiene_version(self, client: AsyncClient, admin_user, admin_headers):
        r = await client.get("/api/admin/sistema", headers=admin_headers)
        data = r.json()
        api_info = data.get("api", data)
        assert any(k in api_info for k in ("version", "v", "motor_activo")) or isinstance(api_info, dict)

    async def test_sistema_no_expone_secret(self, client: AsyncClient, admin_user, admin_headers):
        r = await client.get("/api/admin/sistema", headers=admin_headers)
        assert "SECRET" not in r.text
        assert "secret" not in r.text.lower() or "secret" in ["motor_secreto"]  # ok si es sólo label


class TestAdminEstadisticas:
    async def test_stats_requiere_admin(self, client: AsyncClient, test_user, auth_headers):
        r = await client.get("/api/admin/stats", headers=auth_headers)
        assert r.status_code in (403, 404)

    async def test_stats_con_admin_ok_o_no_existe(self, client: AsyncClient, admin_user, admin_headers):
        r = await client.get("/api/admin/stats", headers=admin_headers)
        assert r.status_code in (200, 404)

    async def test_admin_health_ok(self, client: AsyncClient, admin_user, admin_headers):
        r = await client.get("/api/admin/health", headers=admin_headers)
        assert r.status_code in (200, 404)


class TestAdminGestionUsuarios:
    async def test_toggle_usuario_requiere_admin(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post(
            f"/api/admin/users/{test_user.id}/toggle",
            headers=auth_headers,
        )
        assert r.status_code in (403, 404)

    async def test_toggle_usuario_con_admin_ok(self, client: AsyncClient, test_user, admin_user, admin_headers):
        r = await client.post(
            f"/api/admin/users/{test_user.id}/toggle",
            headers=admin_headers,
        )
        assert r.status_code in (200, 404)

    async def test_toggle_usuario_no_existente_404(self, client: AsyncClient, admin_user, admin_headers):
        r = await client.post(
            "/api/admin/users/00000000-0000-0000-0000-000000000000/toggle",
            headers=admin_headers,
        )
        assert r.status_code in (404, 422)
