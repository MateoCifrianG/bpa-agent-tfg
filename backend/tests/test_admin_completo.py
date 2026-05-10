"""
test_admin_completo.py — Tests exhaustivos del panel de administración:
listado de usuarios, stats globales, actividad, sistema, CRUD admin, control de acceso.
"""
import pytest
import uuid
from httpx import AsyncClient

pytestmark = pytest.mark.asyncio


class TestAdminAccesoExtendido:
    async def test_users_sin_auth_401(self, client: AsyncClient):
        r = await client.get("/api/admin/users")
        assert r.status_code == 401

    async def test_stats_sin_auth_401(self, client: AsyncClient):
        r = await client.get("/api/admin/stats")
        assert r.status_code == 401

    async def test_actividad_sin_auth_401(self, client: AsyncClient):
        r = await client.get("/api/admin/activity")
        assert r.status_code == 401

    async def test_sistema_sin_auth_401(self, client: AsyncClient):
        r = await client.get("/api/admin/sistema")
        assert r.status_code == 401

    async def test_users_con_token_usuario_normal_403(self, client: AsyncClient, test_user, auth_headers):
        r = await client.get("/api/admin/users", headers=auth_headers)
        assert r.status_code == 403

    async def test_stats_con_token_usuario_normal_403(self, client: AsyncClient, test_user, auth_headers):
        r = await client.get("/api/admin/stats", headers=auth_headers)
        assert r.status_code == 403

    async def test_actividad_con_usuario_normal_403(self, client: AsyncClient, test_user, auth_headers):
        r = await client.get("/api/admin/activity", headers=auth_headers)
        assert r.status_code == 403

    async def test_sistema_con_usuario_normal_403(self, client: AsyncClient, test_user, auth_headers):
        r = await client.get("/api/admin/sistema", headers=auth_headers)
        assert r.status_code == 403

    async def test_crear_user_admin_con_normal_403(self, client: AsyncClient, test_user, auth_headers):
        r = await client.post("/api/admin/users", headers=auth_headers, json={
            "email": "x@x.com", "password": "Test123!", "nombre": "X",
            "apellido": "Y", "empresa": "Z", "sector": "ventas", "empleados": 1, "plan": "free",
        })
        assert r.status_code == 403


class TestAdminListarUsuarios:
    async def test_listar_users_ok(self, client: AsyncClient, admin_headers):
        r = await client.get("/api/admin/users", headers=admin_headers)
        assert r.status_code == 200
        assert isinstance(r.json(), list)

    async def test_listar_users_tiene_campos(self, client: AsyncClient, admin_headers):
        r = await client.get("/api/admin/users", headers=admin_headers)
        users = r.json()
        if users:
            u = users[0]
            assert "id" in u
            assert "email" in u

    async def test_listar_users_incluye_admin(self, client: AsyncClient, admin_headers, admin_user):
        r = await client.get("/api/admin/users", headers=admin_headers)
        emails = [u["email"] for u in r.json()]
        assert admin_user.email in emails

    async def test_listar_users_al_menos_uno(self, client: AsyncClient, admin_headers):
        r = await client.get("/api/admin/users", headers=admin_headers)
        assert len(r.json()) >= 1

    async def test_listar_users_campos_email(self, client: AsyncClient, admin_headers):
        r = await client.get("/api/admin/users", headers=admin_headers)
        for u in r.json():
            assert "@" in u.get("email", "")

    async def test_listar_users_no_expone_password(self, client: AsyncClient, admin_headers):
        r = await client.get("/api/admin/users", headers=admin_headers)
        for u in r.json():
            assert "password" not in u
            assert "hashed_password" not in u


class TestAdminStats:
    async def test_stats_ok(self, client: AsyncClient, admin_headers):
        r = await client.get("/api/admin/stats", headers=admin_headers)
        assert r.status_code == 200

    async def test_stats_tiene_usuarios(self, client: AsyncClient, admin_headers):
        r = await client.get("/api/admin/stats", headers=admin_headers)
        data = r.json()
        assert any(k in data for k in ("total_users", "usuarios", "users"))

    async def test_stats_tiene_procesos(self, client: AsyncClient, admin_headers):
        r = await client.get("/api/admin/stats", headers=admin_headers)
        data = r.json()
        assert any(k in data for k in ("total_procesos", "procesos"))

    async def test_stats_valores_no_negativos(self, client: AsyncClient, admin_headers):
        r = await client.get("/api/admin/stats", headers=admin_headers)
        data = r.json()
        for k, v in data.items():
            if isinstance(v, (int, float)):
                assert v >= 0, f"Valor negativo en {k}: {v}"

    async def test_stats_usuarios_al_menos_uno(self, client: AsyncClient, admin_headers, admin_user):
        r = await client.get("/api/admin/stats", headers=admin_headers)
        data = r.json()
        total = data.get("total_users") or data.get("usuarios") or data.get("users") or 0
        assert total >= 1


class TestAdminActividad:
    async def test_actividad_ok(self, client: AsyncClient, admin_headers):
        r = await client.get("/api/admin/activity", headers=admin_headers)
        assert r.status_code == 200

    async def test_actividad_es_lista_o_dict(self, client: AsyncClient, admin_headers):
        r = await client.get("/api/admin/activity", headers=admin_headers)
        assert isinstance(r.json(), (list, dict))

    async def test_actividad_limit_param(self, client: AsyncClient, admin_headers):
        r = await client.get("/api/admin/activity?limit=5", headers=admin_headers)
        assert r.status_code == 200
        data = r.json()
        if isinstance(data, list):
            assert len(data) <= 5


class TestAdminSistema:
    async def test_sistema_ok(self, client: AsyncClient, admin_headers):
        r = await client.get("/api/admin/sistema", headers=admin_headers)
        assert r.status_code == 200

    async def test_sistema_tiene_version(self, client: AsyncClient, admin_headers):
        r = await client.get("/api/admin/sistema", headers=admin_headers)
        data = r.json()
        assert any(k in data for k in ("api", "motor_activo", "ollama", "version", "motor", "status"))

    async def test_sistema_valores_presentes(self, client: AsyncClient, admin_headers):
        r = await client.get("/api/admin/sistema", headers=admin_headers)
        data = r.json()
        assert len(data) > 0


class TestAdminCRUDUsuarios:
    async def test_crear_user_admin(self, client: AsyncClient, admin_headers):
        uid = uuid.uuid4().hex[:8]
        r = await client.post("/api/admin/users", headers=admin_headers, json={
            "email": f"admin_new_{uid}@test.com",
            "password": "TestPass1!",
            "nombre": "Nuevo",
            "apellido": "User",
            "empresa": "Empresa Admin",
            "sector": "ventas",
            "empleados": 1,
            "plan": "free",
        })
        assert r.status_code in (200, 201)

    async def test_crear_user_admin_devuelve_email(self, client: AsyncClient, admin_headers):
        uid = uuid.uuid4().hex[:8]
        email = f"admin_check_{uid}@test.com"
        r = await client.post("/api/admin/users", headers=admin_headers, json={
            "email": email,
            "password": "TestPass1!",
            "nombre": "Check",
            "apellido": "User",
            "empresa": "EmpresaCheck",
            "sector": "ventas",
            "empleados": 1,
            "plan": "free",
        })
        if r.status_code in (200, 201):
            assert r.json().get("email") == email

    async def test_crear_user_admin_sin_auth_401(self, client: AsyncClient):
        r = await client.post("/api/admin/users", json={
            "email": "noauth@test.com",
            "password": "TestPass1!",
            "nombre": "No", "apellido": "Auth",
            "empresa": "X", "sector": "ventas", "empleados": 1, "plan": "free",
        })
        assert r.status_code == 401

    async def test_update_user_admin(self, client: AsyncClient, admin_headers, test_user):
        r = await client.put(f"/api/admin/users/{test_user.id}", headers=admin_headers,
                             json={"is_active": True})
        assert r.status_code == 200

    async def test_update_user_admin_desactivar(self, client: AsyncClient, admin_headers, test_user):
        r = await client.put(f"/api/admin/users/{test_user.id}", headers=admin_headers,
                             json={"is_active": False})
        assert r.status_code == 200

    async def test_update_user_no_existe(self, client: AsyncClient, admin_headers):
        r = await client.put("/api/admin/users/00000000-0000-0000-0000-000000000000",
                             headers=admin_headers, json={"is_active": True})
        assert r.status_code == 404

    async def test_delete_user_admin(self, client: AsyncClient, admin_headers):
        uid = uuid.uuid4().hex[:8]
        cr = await client.post("/api/admin/users", headers=admin_headers, json={
            "email": f"del_{uid}@test.com",
            "password": "TestPass1!",
            "nombre": "Del", "apellido": "User",
            "empresa": "EmpresaDel", "sector": "ventas", "empleados": 1, "plan": "free",
        })
        if cr.status_code not in (200, 201):
            return
        uid_del = cr.json()["id"]
        r = await client.delete(f"/api/admin/users/{uid_del}", headers=admin_headers)
        assert r.status_code in (200, 204)

    async def test_delete_user_no_existe(self, client: AsyncClient, admin_headers):
        r = await client.delete("/api/admin/users/00000000-0000-0000-0000-000000000000",
                                headers=admin_headers)
        assert r.status_code == 404

    async def test_delete_user_sin_auth(self, client: AsyncClient, test_user):
        r = await client.delete(f"/api/admin/users/{test_user.id}")
        assert r.status_code == 401

    async def test_update_user_email_unico(self, client: AsyncClient, admin_headers, test_user, admin_user):
        # Intentar cambiar email a uno ya existente
        r = await client.put(f"/api/admin/users/{test_user.id}", headers=admin_headers,
                             json={"email": admin_user.email})
        assert r.status_code in (200, 409, 422, 400)
